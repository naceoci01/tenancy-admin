"""Publish a weekly OCI IAM cleanup findings report."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from html import escape
import io
import json
import logging
import os
import re
from typing import Any


NOISY_LOGGERS = (
    "oci-policy-analysis", "oci", "oci._vendor", "oci._vendor.urllib3", "urllib3", "urllib3.connectionpool",
)
TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}
LOGGER = logging.getLogger("policy_cleanup_report")
POLICY_ANALYSIS_RUNTIME_HOME = "/tmp/oci-policy-analysis"
GENAI_GROUPS_PER_CALL = 5
GENAI_MAX_TOKENS_PER_CALL = 900


def parse_bool(value: Any, default: bool) -> bool:
    """Parse a function configuration boolean."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def configure_logging(config: dict[str, Any], payload: dict[str, Any]) -> None:
    """Configure function and dependency logging without import-time side effects."""
    level_name = str(payload.get("log_level", config.get("LOG_LEVEL", "INFO"))).upper()
    logging.basicConfig(level=getattr(logging, level_name, logging.INFO), format="%(levelname)s %(name)s - %(message)s", force=True)
    dependency_level = getattr(logging, str(config.get("DEPENDENCY_LOG_LEVEL", "WARNING")).upper(), logging.WARNING)
    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(dependency_level)


def configure_policy_analysis_runtime() -> None:
    """Keep the dependency's settings and cache out of Functions' read-only home.

    ``oci-policy-analysis`` derives both paths from ``Path.home()`` at import
    time.  OCI Functions mounts ``/home/fn`` read-only, while ``/tmp`` is the
    supported writable, ephemeral runtime filesystem.
    """
    os.environ["HOME"] = POLICY_ANALYSIS_RUNTIME_HOME
    LOGGER.debug("Using ephemeral policy-analysis runtime home: %s", POLICY_ANALYSIS_RUNTIME_HOME)


def _notification_region(topic_id: str) -> str:
    """Return the OCI region embedded in a regional Notifications topic OCID."""
    import oci

    parts = str(topic_id).split(".", 4)
    if len(parts) < 5 or parts[:2] != ["ocid1", "onstopic"] or not parts[2] or not parts[3]:
        raise ValueError("NOTIFICATION_TOPIC_ID must be a regional OCI Notifications topic OCID")
    return oci.regions.get_region_from_short_name(parts[3])


def _one_line(value: Any) -> str:
    return str(value or "-").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _statement_details(statement: dict[str, Any]) -> dict[str, str]:
    """Keep report-safe identity fields from a package invalid-statement row."""
    return {
        "policy": str(statement.get("policy_name") or "Unknown policy"),
        "compartment": str(statement.get("compartment_path") or statement.get("effective_path") or "Unknown"),
        "statement": str(statement.get("statement_text") or "[unknown statement]"),
        "identity_domain_evidence": _identity_domain_evidence_text(statement),
    }


def _group_invalid_statements(statements: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    """Group each invalid statement under every validation reason it carries."""
    by_reason: dict[str, list[dict[str, str]]] = defaultdict(list)
    for statement in statements:
        reasons = statement.get("invalid_reasons") or ["Failed validation"]
        for reason in reasons:
            by_reason[str(reason) or "Failed validation"].append(_statement_details(statement))
    return dict(sorted(by_reason.items(), key=lambda item: item[0].casefold()))


def _display_domain(domain: Any) -> str:
    """Use the conventional display name for the package's default domain."""
    value = str(domain or "default").strip()
    return "Default" if value.casefold() == "default" else value


def _missing_principal_domain_matches(
    statements: list[dict[str, Any]], groups: list[dict[str, Any]], dynamic_groups: list[dict[str, Any]],
) -> None:
    """Attach same-name, other-domain candidates to missing principal findings.

    A candidate is evidence for a domain qualification review, not proof that a
    policy should be changed.  This uses the inventory already loaded by the
    analysis package and makes no additional OCI calls.
    """
    inventories = {
        "group": (groups, "group_name"),
        "dynamic-group": (dynamic_groups, "dynamic_group_name"),
    }
    for statement in statements:
        principal_type = str(statement.get("subject_type") or "")
        if principal_type not in inventories:
            continue
        inventory, name_key = inventories[principal_type]
        reasons = [str(reason).casefold() for reason in statement.get("invalid_reasons") or []]
        subjects = statement.get("subject") or []
        matches: list[dict[str, str]] = []
        for subject in subjects:
            if not isinstance(subject, (list, tuple)) or len(subject) < 2:
                continue
            referenced_domain, principal_name = subject[0] or "default", str(subject[1] or "").strip()
            if not principal_name or not any(
                "not found in tenancy" in reason and principal_name.casefold() in reason for reason in reasons
            ):
                continue
            other_domains = sorted({
                _display_domain(candidate.get("domain_name"))
                for candidate in inventory
                if str(candidate.get(name_key) or "").casefold() == principal_name.casefold()
                and _display_domain(candidate.get("domain_name")).casefold() != _display_domain(referenced_domain).casefold()
            }, key=str.casefold)
            if other_domains:
                matches.append({
                    "principal_type": principal_type,
                    "principal_name": principal_name,
                    "referenced_domain": _display_domain(referenced_domain),
                    "other_domains": ", ".join(other_domains),
                })
        if matches:
            statement["identity_domain_matches"] = matches


def _identity_domain_evidence_text(statement: dict[str, Any]) -> str:
    """Render cross-domain matches as a compact, non-prescriptive fact."""
    matches = statement.get("identity_domain_matches") or []
    if not matches:
        return "-"
    return "; ".join(
        f"Same-named {match['principal_type']} {match['principal_name']!r} exists in other domain(s): {match['other_domains']} "
        f"(policy references {_display_domain(match['referenced_domain'])})"
        for match in matches
    )


def _principal_policy_references(statements: list[dict[str, Any]], principal_type: str) -> dict[tuple[str, str], set[str]]:
    """Index policy references by case-insensitive domain/name for cleanup context."""
    references: dict[tuple[str, str], set[str]] = defaultdict(set)
    for statement in statements:
        if str(statement.get("subject_type") or "") != principal_type:
            continue
        for subject in statement.get("subject") or []:
            if not isinstance(subject, (list, tuple)) or len(subject) < 2:
                continue
            domain = _display_domain(subject[0]).casefold()
            name = str(subject[1] or "").strip().casefold()
            if name:
                references[(domain, name)].add(str(statement.get("policy_name") or "Unknown policy"))
    return references


def _resolution_guidance(reason: str) -> str:
    """Provide a deterministic fallback when GenAI is intentionally disabled."""
    normalized = reason.casefold()
    if "group" in normalized or "user" in normalized or "dynamic" in normalized:
        return "Verify the referenced Identity Domain principal exists and its name/domain is correct. A same-name match in another domain is a qualification candidate, not proof of intent; confirm the correct fully qualified reference before updating or removing the statement."
    if "compartment" in normalized:
        return "Verify the target compartment exists, has been loaded, and is referenced with its current name or OCID; then correct the statement scope."
    if "verb" in normalized or "resource" in normalized or "permission" in normalized:
        return "Check the OCI IAM policy grammar and service permission reference; replace the unsupported verb or resource with a valid least-privilege alternative."
    if "condition" in normalized or "where" in normalized:
        return "Validate the where-clause grammar and referenced request attributes, then simplify or correct the condition before applying it."
    return "Review the referenced principal, target, and policy grammar; correct the invalid reference or remove the statement if it is no longer needed."


def build_cleanup_report() -> dict[str, Any]:
    """Load tenancy once and shape actionable policy and principal cleanup findings."""
    configure_policy_analysis_runtime()
    from oci_policy_analysis.application.context import AppContext
    from oci_policy_analysis.application.core.support.config import load_settings
    from oci_policy_analysis.application.services.load_service import LoadService

    context = AppContext.from_settings(load_settings())
    result = LoadService(context).load_from_tenancy(
        use_instance_principal=False, use_resource_principal=True, recursive=True,
        load_all_users=True, compartment_domain_search_depth=1,
        post_load_profile="full", save_cache_after_load=False,
    )
    if not result.success:
        raise RuntimeError(f"OCI policy analysis tenancy load failed: {result.message}")

    repo = context.policy_repo
    cleanup = (getattr(context.intelligence, "overlay", {}) or {}).get("cleanup_items", {}) or {}
    invalid = list(cleanup.get("invalid_statements", []) or [])
    groups = list(cleanup.get("unused_groups", []) or [])
    dynamic_groups = list(cleanup.get("unused_dynamic_groups", []) or [])
    _missing_principal_domain_matches(
        invalid,
        list(getattr(repo, "groups", []) or []),
        list(getattr(repo, "dynamic_groups", []) or []),
    )
    statements = list(getattr(repo, "regular_statements", []) or [])
    group_policy_references = _principal_policy_references(statements, "group")
    dynamic_group_policy_references = _principal_policy_references(statements, "dynamic-group")
    groups_without_users = []
    for group in groups:
        domain = _display_domain(group.get("domain_name"))
        name = str(group.get("group_name") or "[unknown]")
        policies = sorted(group_policy_references.get((domain.casefold(), name.casefold()), set()), key=str.casefold)
        groups_without_users.append({
            "domain": domain, "name": name, "ocid": str(group.get("group_ocid") or ""),
            "user_count": 0, "referencing_policy_count": len(policies), "referencing_policies": policies[:5],
        })
    unreferenced_dynamic_groups = []
    for group in dynamic_groups:
        domain = _display_domain(group.get("domain_name"))
        name = str(group.get("dynamic_group_name") or "[unknown]")
        policies = sorted(dynamic_group_policy_references.get((domain.casefold(), name.casefold()), set()), key=str.casefold)
        unreferenced_dynamic_groups.append({
            "domain": domain, "name": name, "ocid": str(group.get("dynamic_group_ocid") or ""),
            "matching_rule": str(group.get("matching_rule") or ""),
            "referencing_policy_count": len(policies), "referencing_policies": policies[:5],
        })

    return {
        "generated_at": datetime.now(UTC).isoformat(), "tenancy": {
            "tenancy_name": getattr(repo, "tenancy_name", None),
            "data_as_of": getattr(repo, "data_as_of", None),
        },
        "load_summary": result.summary or {},
        "invalid_statement_count": len(invalid), "invalid_by_reason": _group_invalid_statements(invalid),
        "groups_without_users": groups_without_users,
        "unreferenced_dynamic_groups": unreferenced_dynamic_groups,
        "cleanup_counts": {
            "invalid_statements": len(invalid),
            "groups_without_users": len(groups_without_users),
            "unreferenced_dynamic_groups": len(unreferenced_dynamic_groups),
        },
    }


def _genai_groups(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build bounded, compact inputs for policy and principal cleanup advice."""
    issues = [{
        "reason": reason,
        "count": len(items),
        "examples": [{"statement": item["statement"], "identity_domain_evidence": item["identity_domain_evidence"]} for item in items[:3]],
    } for reason, items in report["invalid_by_reason"].items()]
    empty_groups = report.get("groups_without_users") or []
    if empty_groups:
        result = [{
            "domain": item["domain"], "name": item["name"], "user_count": item["user_count"],
            "referencing_policy_count": item["referencing_policy_count"],
        } for item in empty_groups[:5]]
        issues.append({"reason": "Groups with no user members (cleanup review)", "count": len(empty_groups), "examples": result})
    dynamic_groups = report.get("unreferenced_dynamic_groups") or []
    if dynamic_groups:
        examples = [{
            "domain": item["domain"], "name": item["name"], "referencing_policy_count": item["referencing_policy_count"],
            "matching_rule": item["matching_rule"][:500],
        } for item in dynamic_groups[:5]]
        issues.append({"reason": "Dynamic groups not referenced by scanned policies (cleanup review)", "count": len(dynamic_groups), "examples": examples})
    return issues


def _genai_prompt(groups: list[dict[str, Any]] | dict[str, Any]) -> str:
    """Ask for short, safe guidance for one batch of validation reasons."""
    if isinstance(groups, dict) and "invalid_by_reason" in groups:
        groups = _genai_groups(groups)
    return (
        "You are an OCI IAM policy cleanup assistant. For each cleanup issue below, give concise, safe guidance. "
        "Do not invent OCI permissions, OCIDs, principals, or policy syntax. State when the operator must validate the service permission reference or Identity Domain object. "
        "Identity-domain evidence is only a same-name candidate in a different loaded domain: never treat it as proof of the intended principal. Tell the operator to confirm the correct fully qualified domain/name reference before changing a policy. "
        "For groups with no users or dynamic groups not referenced by scanned policies, explain the finding and recommend checks before removal; never claim that removal is automatically safe. "
        "Use strict Markdown. For each reason, use its exact reason as a heading and no more than two short bullets. Avoid repeating generic re-validation instructions unless needed.\n\n"
        + json.dumps(groups, ensure_ascii=False)
    )


def _extract_genai_text(content: Any) -> str:
    """Extract text blocks from OCI SDK chat content without stringifying models."""
    if isinstance(content, str):
        return content
    if not isinstance(content, (list, tuple)):
        text_value = getattr(content, "text", None)
        return str(text_value if text_value is not None else content)
    blocks = []
    for item in content:
        if isinstance(item, dict):
            value = item.get("text")
        else:
            value = getattr(item, "text", None)
        if value is not None:
            blocks.append(str(value))
    return "\n".join(blocks)


def _call_genai(prompt: str, model_id: str, compartment_id: str) -> str:
    """Make one OCI GenAI chat request and return plain text content."""
    import oci
    from oci.auth import signers
    from oci.generative_ai_inference import GenerativeAiInferenceClient
    from oci.generative_ai_inference.models import BaseChatRequest, ChatDetails, GenericChatRequest, Message, OnDemandServingMode, TextContent

    signer = signers.get_resource_principals_signer()
    request = GenericChatRequest(
        api_format=BaseChatRequest.API_FORMAT_GENERIC,
        messages=[Message(role="USER", content=[TextContent(text=prompt)])],
        temperature=0, top_p=0.25, max_tokens=GENAI_MAX_TOKENS_PER_CALL,
    )
    details = ChatDetails(compartment_id=compartment_id, serving_mode=OnDemandServingMode(model_id=model_id), chat_request=request)
    response = GenerativeAiInferenceClient({"region": signer.region}, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY).chat(details)
    choices = response.data.chat_response.choices
    if not choices:
        raise RuntimeError("GenAI response contained no choices")
    return _extract_genai_text(choices[0].message.content).strip()


def generate_ai_guidance(report: dict[str, Any], config: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Optionally enrich findings through OCI GenAI with resource-principal auth."""
    enabled = parse_bool(payload.get("enable_genai_enrichment", config.get("ENABLE_GENAI_ENRICHMENT")), False)
    cleanup_counts = report.get("cleanup_counts") or {}
    if not enabled or not (report.get("invalid_by_reason") or cleanup_counts.get("groups_without_users") or cleanup_counts.get("unreferenced_dynamic_groups")):
        return None
    model_id = str(payload.get("genai_model_id", config.get("GENAI_MODEL_ID", ""))).strip()
    compartment_id = str(payload.get("genai_compartment_id", config.get("GENAI_COMPARTMENT_ID", ""))).strip()
    if not model_id or not compartment_id:
        return "GenAI enrichment was enabled but GENAI_MODEL_ID or GENAI_COMPARTMENT_ID is not configured."
    groups = _genai_groups(report)
    batches = [groups[index:index + GENAI_GROUPS_PER_CALL] for index in range(0, len(groups), GENAI_GROUPS_PER_CALL)]
    results: list[str] = []
    for batch_number, batch in enumerate(batches, start=1):
        labels = ", ".join(group["reason"] for group in batch)
        try:
            guidance = _call_genai(_genai_prompt(batch), model_id, compartment_id)
            if guidance:
                results.append(guidance)
        except Exception as error:
            LOGGER.exception("GenAI remediation batch %d/%d failed", batch_number, len(batches))
            results.append(f"### Guidance unavailable for batch {batch_number} ({labels})\n\nGenAI request failed: {error}")
            status = getattr(error, "status", None)
            if status in {401, 403, 404}:
                remaining = len(batches) - batch_number
                if remaining:
                    results.append(f"{remaining} later batch(es) were skipped because the model or authorization error applies to every request.")
                break
    return "\n\n".join(results) or "GenAI returned no guidance."


def _inline_markdown(value: str) -> str:
    """Render a small safe Markdown subset after escaping all source text."""
    value = escape(value, quote=True)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    return value


def _markdown_to_html(markdown: str) -> str:
    """Render headings, bullets, paragraphs, and inline emphasis safely."""
    output: list[str] = []
    paragraph: list[str] = []
    in_list = False

    def flush_paragraph() -> None:
        if paragraph:
            output.append(f"<p>{'<br> '.join(_inline_markdown(line) for line in paragraph)}</p>")
            paragraph.clear()

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            output.append("</ul>")
            in_list = False

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            close_list()
        elif line.startswith("### ") or line.startswith("## "):
            flush_paragraph()
            close_list()
            output.append(f"<h3>{_inline_markdown(line.split(' ', 1)[1].strip())}</h3>")
        elif line.startswith("# "):
            flush_paragraph()
            close_list()
            output.append(f"<h2>{_inline_markdown(line[2:].strip())}</h2>")
        elif line.startswith(("- ", "* ")):
            flush_paragraph()
            if not in_list:
                output.append("<ul>")
                in_list = True
            output.append(f"<li>{_inline_markdown(line[2:].strip())}</li>")
        else:
            close_list()
            paragraph.append(line)
    flush_paragraph()
    close_list()
    return "\n".join(output) or "<p>No GenAI guidance was generated.</p>"


def _report_html(report: dict[str, Any], ai_guidance: str | None) -> str:
    """Build a self-contained, escaped HTML report for Object Storage."""
    tenancy = report.get("tenancy") or {}
    counts = report.get("cleanup_counts") or {}
    summary = [
        ("Invalid policy statements", counts.get("invalid_statements", report.get("invalid_statement_count", 0))),
        ("Groups with no users", counts.get("groups_without_users", len(report.get("groups_without_users") or []))),
        ("Unreferenced dynamic groups", counts.get("unreferenced_dynamic_groups", len(report.get("unreferenced_dynamic_groups") or []))),
    ]
    summary_cards = "\n".join(
        f'<div class="metric"><span>{escape(str(label))}</span><strong>{escape(str(value))}</strong></div>'
        for label, value in summary
    )
    invalid_sections: list[str] = []
    for reason, findings in (report.get("invalid_by_reason") or {}).items():
        rows = []
        for item in findings:
            rows.append(
                '<article class="finding">'
                f'<div class="finding-meta"><span>{escape(str(item.get("policy", "Unknown policy")))}</span>'
                f'<span>{escape(str(item.get("compartment", "Unknown")))}</span></div>'
                f'<pre>{escape(str(item.get("statement", "[unknown statement]")))}</pre>'
                + (f'<p class="evidence">{escape(str(item["identity_domain_evidence"]))}</p>' if item.get("identity_domain_evidence") not in (None, "", "-") else "")
                + '</article>'
            )
        invalid_sections.append(
            '<details class="reason">'
            f'<summary>{escape(str(reason))}<span class="count">{len(findings)}</span></summary>'
            f'<p class="baseline">{escape(_resolution_guidance(str(reason)))}</p>'
            + ("".join(rows) or '<p class="muted">No statement details.</p>')
            + '</details>'
        )
    group_sections = []
    for group in report.get("groups_without_users") or []:
        policy_names = group.get("referencing_policies") or []
        reference_detail = (
            f'<p class="evidence">Referenced by {group.get("referencing_policy_count", 0)} policy/policies: '
            f'{escape(", ".join(str(name) for name in policy_names))}'
            f'{" …" if group.get("referencing_policy_count", 0) > len(policy_names) else ""}. Review these policies before considering removal.</p>'
            if group.get("referencing_policy_count") else '<p class="muted">No policy reference was found in the scanned statements.</p>'
        )
        group_sections.append(
            '<details class="reason"><summary>'
            f'{escape(str(group.get("domain", "Default")))}/{escape(str(group.get("name", "[unknown]")))}'
            f'<span class="count">0 users</span></summary>'
            f'<p class="baseline">This group has no user members. Confirm its intended role and other dependencies before removal.</p>'
            f'{reference_detail}'
            + (f'<p class="muted">OCID: <code>{escape(str(group["ocid"]))}</code></p>' if group.get("ocid") else "")
            + '</details>'
        )
    dynamic_group_sections = []
    for group in report.get("unreferenced_dynamic_groups") or []:
        dynamic_group_sections.append(
            '<details class="reason"><summary>'
            f'{escape(str(group.get("domain", "Default")))}/{escape(str(group.get("name", "[unknown]")))}'
            '<span class="count">0 policy references</span></summary>'
            '<p class="baseline">No reference was found in the scanned policy statements. Check whether automation or planned work depends on this dynamic group before removal.</p>'
            + (f'<pre>{escape(str(group["matching_rule"]))}</pre>' if group.get("matching_rule") else "")
            + (f'<p class="muted">OCID: <code>{escape(str(group["ocid"]))}</code></p>' if group.get("ocid") else "")
            + '</details>'
        )
    ai_section = (
        f'<section class="panel"><h2>AI remediation guidance</h2>{_markdown_to_html(ai_guidance)}</section>'
        if ai_guidance else ""
    )
    generated_at = escape(str(report.get("generated_at", "Unknown")))
    tenancy_name = escape(str(tenancy.get("tenancy_name", "Unknown tenancy")))
    data_as_of = escape(str(tenancy.get("data_as_of", "Unknown")))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><title>OCI IAM Policy Cleanup Report</title>
<style>
:root{{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172b4d;background:#f4f7fb;font-synthesis:none}}
body{{margin:0}}main{{max-width:1100px;margin:0 auto;padding:32px 20px 64px}}header{{background:#102a43;color:white;padding:30px 34px;border-radius:16px}}h1{{font-size:clamp(1.7rem,4vw,2.4rem);margin:0 0 12px}}header p{{margin:5px 0;color:#d9e6f2}}h2{{font-size:1.25rem;margin:0 0 18px}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:20px 0}}.metric,.panel,.reason{{background:white;border:1px solid #dce5ef;border-radius:12px}}.metric{{padding:18px}}.metric span{{display:block;color:#5c6f82;font-size:.9rem}}.metric strong{{display:block;font-size:1.7rem;margin-top:6px}}.panel{{padding:22px;margin:20px 0}}.reason{{margin:12px 0;overflow:hidden}}summary{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 18px;font-weight:650;cursor:pointer}}summary:hover{{background:#f8fafc}}.count{{white-space:nowrap;background:#e9f2fb;color:#164e78;border-radius:999px;padding:4px 10px;font-size:.82rem}}.baseline{{margin:0 18px 12px;color:#5c6f82;font-size:.92rem}}.finding{{border-top:1px solid #e6edf4;padding:15px 18px}}.finding-meta{{display:flex;gap:12px;flex-wrap:wrap;color:#52667a;font-size:.86rem}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f5f7fa;padding:12px;border-radius:8px;font: .9rem/1.55 ui-monospace,SFMono-Regular,monospace}}.evidence{{color:#075e55;background:#e8f7f3;padding:10px 12px;border-radius:8px;overflow-wrap:anywhere}}.muted,footer{{color:#687b8e;font-size:.9rem}}.panel p{{line-height:1.6}}.panel li{{line-height:1.55;margin:5px 0}}code{{background:#eef2f6;padding:2px 5px;border-radius:4px}}footer{{margin:22px 2px}}
</style></head><body><main>
<header><h1>OCI IAM Policy Cleanup Report</h1><p>{tenancy_name}</p><p>Generated {generated_at} · Data as of {data_as_of}</p></header>
<section class="metrics">{summary_cards}</section>
{ai_section}
<section class="panel"><h2>Invalid policy statements by reason</h2>{''.join(invalid_sections) or '<p class="muted">No invalid statements found.</p>'}</section>
<section class="panel"><h2>Groups with no user members</h2>{''.join(group_sections) or '<p class="muted">None found.</p>'}</section>
<section class="panel"><h2>Dynamic groups not referenced by scanned policies</h2>{''.join(dynamic_group_sections) or '<p class="muted">None found.</p>'}</section>
<footer>Generated by the OCI IAM Policy Cleanup Report function.</footer></main></body></html>'''


def publish_html_report(report: dict[str, Any], ai_guidance: str | None, config: dict[str, Any]) -> dict[str, str] | None:
    """Write dated and latest HTML report objects to the configured bucket."""
    bucket_name = str(config.get("REPORT_BUCKET_NAME", "")).strip()
    if not bucket_name:
        return None
    try:
        import oci
        from oci.auth import signers

        namespace = str(config.get("REPORT_NAMESPACE", "")).strip()
        signer = signers.get_resource_principals_signer()
        client = oci.object_storage.ObjectStorageClient({"region": signer.region}, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        namespace = namespace or client.get_namespace().data
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        dated_object = f"policy-cleanup-reports/{timestamp}/report.html"
        html_report = _report_html(report, ai_guidance).encode("utf-8")
        for object_name in (dated_object, "policy-cleanup-reports/latest.html"):
            client.put_object(
                namespace_name=namespace, bucket_name=bucket_name, object_name=object_name,
                put_object_body=io.BytesIO(html_report), content_type="text/html; charset=utf-8",
            )
        latest_object = "policy-cleanup-reports/latest.html"
        LOGGER.info(
            "Wrote HTML report to Object Storage: bucket=%s dated_object=%s latest_object=%s",
            bucket_name, dated_object, latest_object,
        )
        return {"namespace": namespace, "bucket": bucket_name, "dated_object": dated_object, "latest_object": latest_object}
    except Exception:
        LOGGER.exception("Unable to write HTML report to Object Storage bucket %s", bucket_name)
        raise


def format_notification(report: dict[str, Any], ai_guidance: str | None = None, report_object: dict[str, str] | None = None) -> str:
    """Produce a compact Notifications summary for the cleanup findings."""
    tenancy = report["tenancy"]
    counts = report.get("cleanup_counts") or {}
    invalid_count = counts.get("invalid_statements", report.get("invalid_statement_count", 0))
    group_count = counts.get("groups_without_users", len(report.get("groups_without_users") or []))
    dynamic_group_count = counts.get("unreferenced_dynamic_groups", len(report.get("unreferenced_dynamic_groups") or []))
    lines = [
        "OCI IAM POLICY CLEANUP REPORT", "", "SUMMARY",
        f"Tenancy:\t{_one_line(tenancy.get('tenancy_name'))}", f"Data as of:\t{_one_line(tenancy.get('data_as_of'))}",
        f"Generated (UTC):\t{report['generated_at']}", f"Invalid policy statements:\t{invalid_count}",
        f"Groups with no users:\t{group_count}", f"Unreferenced dynamic groups:\t{dynamic_group_count}",
    ]
    if report_object:
        lines += ["", "FULL REPORT", f"Object Storage bucket:\t{_one_line(report_object['bucket'])}",
                  f"Latest report object:\t{_one_line(report_object['latest_object'])}",
                  f"Dated report object:\t{_one_line(report_object['dated_object'])}",
                  "Open the object in the OCI Console or use your separately managed access link."]
        return "\n".join(lines)
    lines += ["", "INVALID POLICY STATEMENTS BY REASON"]
    if not report["invalid_by_reason"]:
        lines.append("None found.")
    for reason, findings in report["invalid_by_reason"].items():
        lines += ["", f"{reason}\t({len(findings)})", "Policy\tCompartment\tStatement\tIdentity-domain evidence"]
        lines.extend("\t".join(_one_line(item.get(field, "-")) for field in ("policy", "compartment", "statement", "identity_domain_evidence")) for item in findings)
    lines += ["", "GROUPS WITH NO USER MEMBERS"]
    lines.extend(f"{_one_line(group['domain'])}/{_one_line(group['name'])}\t0 users\t{group['referencing_policy_count']} referencing policies" for group in report.get("groups_without_users", []))
    if not report.get("groups_without_users"):
        lines.append("None found.")
    lines += ["", "DYNAMIC GROUPS NOT REFERENCED BY SCANNED POLICIES"]
    lines.extend(f"{_one_line(group['domain'])}/{_one_line(group['name'])}\t{_one_line(group.get('matching_rule'))}" for group in report.get("unreferenced_dynamic_groups", []))
    if not report.get("unreferenced_dynamic_groups"):
        lines.append("None found.")
    if ai_guidance:
        lines += ["", "GENAI REMEDIATION GUIDANCE", ai_guidance]
    return "\n".join(lines)


def publish_summary(topic_id: str, report: dict[str, Any], ai_guidance: str | None, report_object: dict[str, str] | None = None) -> None:
    """Publish report while retaining the function result if Notifications fails."""
    if not topic_id:
        return
    try:
        import oci
        from oci.auth import signers

        client = oci.ons.NotificationDataPlaneClient({"region": _notification_region(topic_id)}, signer=signers.get_resource_principals_signer(), retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        client.publish_message(topic_id=topic_id, message_details=oci.ons.models.MessageDetails(title="OCI IAM Policy Cleanup Report", body=format_notification(report, ai_guidance, report_object)), message_type="RAW_TEXT")
        LOGGER.info("Published policy cleanup report to notification topic")
    except Exception:
        LOGGER.exception("Unable to publish policy cleanup report to notification topic")


def should_publish_notification(config: dict[str, Any], payload: dict[str, Any]) -> bool:
    """Require an explicit opt-in before using an inherited application topic."""
    return parse_bool(
        payload.get("publish_notification", config.get("PUBLISH_NOTIFICATION")),
        False,
    )


def handler(ctx, data: io.BytesIO = None):
    """Handle a weekly OCI Resource Scheduler invocation."""
    payload = json.loads(data.getvalue().decode("utf-8")) if data and data.getvalue() else {}
    config = dict(os.environ)
    try:
        config.update(ctx.Config())
    except Exception:
        pass
    configure_logging(config, payload)
    report = build_cleanup_report()
    ai_guidance = generate_ai_guidance(report, config, payload)
    report_config = dict(config)
    if "report_bucket_name" in payload:
        report_config["REPORT_BUCKET_NAME"] = payload["report_bucket_name"]
    if "report_namespace" in payload:
        report_config["REPORT_NAMESPACE"] = payload["report_namespace"]
    report_object = publish_html_report(report, ai_guidance, report_config)
    if report_object is None:
        LOGGER.warning("HTML report not published: REPORT_BUCKET_NAME is empty")
    if should_publish_notification(config, payload):
        publish_summary(str(config.get("NOTIFICATION_TOPIC_ID", "")).strip(), report, ai_guidance, report_object)
    else:
        LOGGER.info("Notification publication disabled; returning report only")
    return json.dumps({**report, "genai_guidance": ai_guidance, "report_object": report_object}, indent=2, sort_keys=True)
