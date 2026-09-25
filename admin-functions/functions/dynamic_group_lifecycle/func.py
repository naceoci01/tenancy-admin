"""Mark and, when explicitly enabled, remove unused OCI dynamic groups."""

import io
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}
DELETE_TAG_KEY = "DeleteDynamicGroupAfter"
DELETE_AFTER_DAYS = 14
OCI_TAGS_SCHEMA = "urn:ietf:params:scim:schemas:oracle:idcs:extension:OCITags"
SCIM_PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
NOISY_LOGGERS = [
    "oci-policy-analysis",
    "oci",
    "oci._vendor",
    "oci._vendor.urllib3",
    "urllib3",
    "urllib3.connectionpool",
]
LOGGER = logging.getLogger("dynamic_group_lifecycle")


@dataclass(frozen=True)
class DynamicGroupLifecycleConfig:
    """Runtime settings for the scheduled dynamic-group lifecycle function."""

    delete_expired_dynamic_groups: bool


def parse_bool(value: Any, default: bool) -> bool:
    """Parse a boolean configuration value."""
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
    """Configure function and dependency logging."""
    level_name = str(payload.get("log_level", config.get("LOG_LEVEL", "INFO"))).upper()
    logging.basicConfig(
        level=getattr(logging, level_name, logging.INFO),
        format="%(levelname)s %(name)s - %(message)s",
        force=True,
    )
    dependency_level = getattr(
        logging,
        str(config.get("DEPENDENCY_LOG_LEVEL", "WARNING")).upper(),
        logging.WARNING,
    )
    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(dependency_level)


def _notification_region(topic_id: str) -> str:
    """Return the OCI region encoded in a regional Notifications topic OCID."""
    import oci

    parts = str(topic_id).split(".", 4)
    if len(parts) < 5 or parts[:2] != ["ocid1", "onstopic"] or not parts[2] or not parts[3]:
        raise ValueError("NOTIFICATION_TOPIC_ID must be a regional OCI Notifications topic OCID")
    return oci.regions.get_region_from_short_name(parts[3])


def _tabular(value: Any) -> str:
    """Keep notification table cells to one physical line."""
    return str(value or "-").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def format_notification(result: dict[str, Any]) -> str:
    """Format a detailed lifecycle report for an OCI Notifications topic."""
    action_counts = ", ".join(
        f"{name}={count}" for name, count in sorted(result["action_counts"].items())
    ) or "none"
    domain_counts = result["domain_counts"]
    unused_count = sum(summary["unused"] for summary in domain_counts.values())
    lines = [
        "DYNAMIC GROUP LIFECYCLE",
        "",
        "SUMMARY",
        f"Evaluated (UTC):\t{result['evaluated_at']}",
        f"Deletion enabled:\t{result['delete_expired_dynamic_groups']}",
        f"Dynamic groups evaluated:\t{sum(summary['evaluated'] for summary in domain_counts.values())}",
        f"Unused dynamic groups:\t{unused_count}",
        f"Actions:\t{action_counts}",
        "",
        "BY DOMAIN",
        "Domain\tEvaluated\tUnused\tMarked\tUnmarked\tDeleted",
    ]
    for domain, summary in sorted(domain_counts.items()):
        lines.append("\t".join(_tabular(value) for value in (
            domain,
            summary["evaluated"],
            summary["unused"],
            summary["marked"],
            summary["unmarked"],
            summary["deleted"],
        )))
    lines.extend([
        "",
        "DETAILS",
        "Outcome\tDomain\tDynamic group\tOCID\tDelete after (UTC)",
    ])
    for action in result["actions"]:
        lines.append("\t".join(_tabular(value) for value in (
            action["action"],
            action["domain"],
            action["name"],
            action["ocid"],
            action.get("delete_after"),
        )))
    return "\n".join(lines)


def publish_summary(topic_id: str, result: dict[str, Any]) -> None:
    """Publish one report without turning delivery failure into a failed run."""
    if not topic_id:
        return
    try:
        import oci
        from oci.auth import signers

        client = oci.ons.NotificationDataPlaneClient(
            {"region": _notification_region(topic_id)},
            signer=signers.get_resource_principals_signer(),
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )
        client.publish_message(
            topic_id=topic_id,
            message_details=oci.ons.models.MessageDetails(
                title="Dynamic Group Lifecycle Summary",
                body=format_notification(result),
            ),
            message_type="RAW_TEXT",
        )
        LOGGER.info("Published dynamic-group lifecycle summary to notification topic")
    except Exception:
        LOGGER.exception("Unable to publish dynamic-group lifecycle summary to notification topic")


def load_config(config: dict[str, Any], payload: dict[str, Any]) -> DynamicGroupLifecycleConfig:
    """Load scheduled lifecycle settings.

    Tagging is always enabled: it is the two-week approval window. Destructive
    deletion remains opt-in and defaults to false.
    """
    return DynamicGroupLifecycleConfig(
        delete_expired_dynamic_groups=parse_bool(
            payload.get("delete_expired_dynamic_groups", config.get("DELETE_EXPIRED_DYNAMIC_GROUPS")),
            default=False,
        )
    )


def format_timestamp(value: datetime) -> str:
    """Format an aware datetime as a whole-second UTC ISO-8601 value."""
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_delete_after(value: str) -> datetime:
    """Parse an offset-aware deletion deadline into UTC."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("deletion tag must include a timezone")
    return parsed.astimezone(timezone.utc)


class OciDynamicGroupGateway:
    """Adapt policy analysis inventory and OCI Identity Domains mutations."""

    def inventory(self) -> list[dict[str, Any]]:
        """Load IAM and policy data, then return unused dynamic groups by query."""
        from oci_policy_analysis.application.core.engine import PolicyIntelligenceEngine
        from oci_policy_analysis.application.core.repo import PolicyAnalysisRepository

        repo = PolicyAnalysisRepository()
        # OCI Functions use a resource principal.  The policy-analysis package
        # initializes its OCI clients and tenancy inventory from that principal.
        if not repo.initialize_client(use_instance_principal=False, use_resource_principal=True, recursive=True):
            raise RuntimeError("oci-policy-analysis could not initialize its resource-principal client")
        if not repo.load_policies_and_compartments():
            raise RuntimeError("oci-policy-analysis could not load policies and compartments")
        if not repo.load_complete_identity_domains(load_all_users=False):
            raise RuntimeError("oci-policy-analysis could not load Identity Domains")
        PolicyIntelligenceEngine(repo).run_dg_in_use_analysis()
        self.all_dynamic_groups = list(repo.dynamic_groups)
        self._domain_clients = dict(repo.domain_clients)

        # The package owns the policy-reference determination and exposes its
        # JSON query filter for the resulting unused dynamic-group inventory.
        unused_ocids = {
            str(item.get("dynamic_group_ocid"))
            for item in repo.filter_dynamic_groups({"in_use": False})
            if item.get("dynamic_group_ocid")
        }
        return [item for item in self.all_dynamic_groups if str(item.get("dynamic_group_ocid")) in unused_ocids]

    def get_freeform_tags(self, dynamic_group: dict[str, Any]) -> dict[str, str]:
        """Fetch current OCI freeform tags from the Identity Domains service."""
        group = self._get_dynamic_group(dynamic_group)
        oci_tags = getattr(group, "urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags", None)
        return {
            str(tag.key): str(tag.value)
            for tag in (getattr(oci_tags, "freeform_tags", None) or [])
            if getattr(tag, "key", None) is not None and getattr(tag, "value", None) is not None
        }

    def update_freeform_tags(self, dynamic_group: dict[str, Any], tags: dict[str, str]) -> None:
        """Replace freeform tags while preserving every unrelated tag.

        Identity Domains exposes Dynamic Resource Group updates as SCIM PATCH,
        not an Update*Details request. Freeform tags are represented as a list
        in the OCI Tags extension rather than a dict on the resource itself.
        """
        from oci.identity_domains.models import FreeformTags, Operations, PatchOp

        client = self._domain_client(dynamic_group)
        operation = (
            Operations(
                op=Operations.OP_REPLACE,
                path=f"{OCI_TAGS_SCHEMA}:freeformTags",
                value=[FreeformTags(key=key, value=value) for key, value in sorted(tags.items())],
            )
            if tags
            else Operations(
                op=Operations.OP_REMOVE,
                path=f"{OCI_TAGS_SCHEMA}:freeformTags",
            )
        )
        client.patch_dynamic_resource_group(
            dynamic_resource_group_id=dynamic_group["dynamic_group_id"],
            patch_op=PatchOp(
                schemas=[SCIM_PATCH_SCHEMA],
                operations=[operation],
            ),
        )

    def delete_dynamic_group(self, dynamic_group: dict[str, Any]) -> None:
        """Delete an already-expired unused dynamic group."""
        self._domain_client(dynamic_group).delete_dynamic_resource_group(
            dynamic_resource_group_id=dynamic_group["dynamic_group_id"]
        )

    def _domain_client(self, dynamic_group: dict[str, Any]):
        domain_ocid = dynamic_group.get("domain_ocid")
        client = self._domain_clients.get(domain_ocid)
        if client is None:
            raise ValueError(f"No Identity Domains client loaded for domain {domain_ocid!r}")
        return client

    def _get_dynamic_group(self, dynamic_group: dict[str, Any]):
        return self._domain_client(dynamic_group).get_dynamic_resource_group(
            dynamic_resource_group_id=dynamic_group["dynamic_group_id"], attribute_sets=["all"]
        ).data


def reconcile_dynamic_groups(
    config: dict[str, Any],
    payload: dict[str, Any],
    gateway: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Tag unused groups, untag groups now in use, and optionally delete due groups."""
    settings = load_config(config, payload)
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    unused = list(gateway.inventory())
    unused_ocids = {str(group["dynamic_group_ocid"]) for group in unused}
    all_groups = list(getattr(gateway, "all_dynamic_groups", unused))
    actions: list[dict[str, Any]] = []

    for group in sorted(all_groups, key=lambda item: (str(item.get("domain_name") or "Default").casefold(), str(item.get("dynamic_group_name")).casefold())):
        group_ocid = str(group["dynamic_group_ocid"])
        tags = gateway.get_freeform_tags(group)
        delete_after = tags.get(DELETE_TAG_KEY)
        is_unused = group_ocid in unused_ocids
        action = {"domain": group.get("domain_name") or "Default", "name": group.get("dynamic_group_name"), "ocid": group_ocid}
        if not is_unused:
            if delete_after is None:
                action["action"] = "in_use"
            else:
                tags.pop(DELETE_TAG_KEY, None)
                gateway.update_freeform_tags(group, tags)
                action["action"] = "unmarked"
                LOGGER.info("Removed deletion mark from in-use dynamic group domain=%s name=%s", action["domain"], action["name"])
            actions.append(action)
            continue

        if delete_after is None:
            delete_after = format_timestamp(current_time + timedelta(days=DELETE_AFTER_DAYS))
            tags[DELETE_TAG_KEY] = delete_after
            gateway.update_freeform_tags(group, tags)
            action.update(action="marked", delete_after=delete_after)
            LOGGER.info("Marked unused dynamic group domain=%s name=%s delete_after=%s", action["domain"], action["name"], delete_after)
        else:
            try:
                deadline = parse_delete_after(delete_after)
            except ValueError:
                deadline = current_time + timedelta(days=DELETE_AFTER_DAYS)
                delete_after = format_timestamp(deadline)
                tags[DELETE_TAG_KEY] = delete_after
                gateway.update_freeform_tags(group, tags)
                action.update(action="remarked_invalid_deadline", delete_after=delete_after)
            else:
                if settings.delete_expired_dynamic_groups and deadline < current_time:
                    gateway.delete_dynamic_group(group)
                    action.update(action="deleted", delete_after=delete_after)
                    LOGGER.info("Deleted expired unused dynamic group domain=%s name=%s", action["domain"], action["name"])
                else:
                    action.update(action="marked_not_due", delete_after=delete_after)
        actions.append(action)

    counts: dict[str, int] = {}
    domain_counts: dict[str, dict[str, int]] = {}
    for action in actions:
        counts[action["action"]] = counts.get(action["action"], 0) + 1
        domain = action["domain"]
        domain_counts.setdefault(domain, {"evaluated": 0, "unused": 0, "marked": 0, "unmarked": 0, "deleted": 0})
        domain_counts[domain]["evaluated"] += 1
        if action["ocid"] in unused_ocids:
            domain_counts[domain]["unused"] += 1
        if action["action"] in {"marked", "remarked_invalid_deadline"}:
            domain_counts[domain]["marked"] += 1
        if action["action"] == "unmarked":
            domain_counts[domain]["unmarked"] += 1
        if action["action"] == "deleted":
            domain_counts[domain]["deleted"] += 1
    for domain, summary in sorted(domain_counts.items()):
        LOGGER.info("Dynamic-group lifecycle domain=%s counts=%s", domain, summary)
    LOGGER.warning(
        "Dynamic-group lifecycle complete: evaluated=%s unused=%s actions=%s deletion_enabled=%s",
        len(actions),
        len(unused_ocids),
        counts,
        settings.delete_expired_dynamic_groups,
    )
    return {"evaluated_at": format_timestamp(current_time), "delete_expired_dynamic_groups": settings.delete_expired_dynamic_groups, "actions": actions, "action_counts": counts, "domain_counts": domain_counts}


def handler(ctx, data: io.BytesIO = None):
    """Handle the weekly OCI Resource Scheduler invocation."""
    payload = json.loads(data.getvalue().decode("utf-8")) if data and data.getvalue() else {}
    config = dict(os.environ)
    try:
        config.update(ctx.Config())
    except Exception:
        pass
    configure_logging(config, payload)
    result = reconcile_dynamic_groups(config, payload, OciDynamicGroupGateway())
    publish_summary(str(config.get("NOTIFICATION_TOPIC_ID", "")).strip(), result)
    return json.dumps(result, indent=2, sort_keys=True)
