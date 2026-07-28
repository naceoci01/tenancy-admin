"""Reconcile tenancy quota policies for engineer compartments."""

import io
import json
import logging
import os
from dataclasses import dataclass
from typing import Any

TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}
DELETE_TAG_NAMESPACE = "Oracle-Tags"
DELETE_TAG_KEY = "DeleteCompartmentAfter"
NOISY_LOGGERS = [
    "oci",
    "oci._vendor",
    "oci._vendor.urllib3",
    "oci.circuit_breaker",
    "urllib3",
    "urllib3.connectionpool",
]
LOGGER = logging.getLogger("engineer_quota_updater")


@dataclass(frozen=True)
class QuotaUpdaterConfig:
    """Runtime settings for the scheduled quota updater.

    Args:
        engineer_root_compartment_ocid: Parent compartment for engineer compartments.
        dry_run: Whether to report quota changes without modifying OCI.
        exclude_delete_marked_compartments: Whether to omit marked compartments.
        quota_config_source: Source label for the loaded quota policy definition.
        quota_config: Quota policy definition.
    """

    engineer_root_compartment_ocid: str
    dry_run: bool
    exclude_delete_marked_compartments: bool
    quota_config_source: str
    quota_config: list[dict[str, Any]]


@dataclass(frozen=True)
class CompartmentInfo:
    """Small representation of an engineer compartment.

    Args:
        ocid: Compartment OCID.
        name: Compartment name.
        defined_tags: Defined tags attached to the compartment.
    """

    ocid: str
    name: str
    defined_tags: dict[str, dict[str, str]]


@dataclass(frozen=True)
class QuotaInfo:
    """Small representation of a tenancy quota policy.

    Args:
        ocid: Quota policy OCID.
        name: Quota policy name.
        description: Quota policy description.
        statements: Complete quota statement list.
    """

    ocid: str
    name: str
    description: str
    statements: tuple[str, ...]


class OciTenancyGateway:
    """Adapter around OCI Identity and Quotas clients."""

    def __init__(self, tenancy_ocid: str, identity_client: Any, quotas_client: Any):
        self.tenancy_ocid = tenancy_ocid
        self.identity_client = identity_client
        self.quotas_client = quotas_client

    @classmethod
    def from_resource_principal(cls, config: dict[str, Any]) -> "OciTenancyGateway":
        """Create an OCI gateway using the function resource principal.

        Args:
            config: Function configuration containing the region.

        Returns:
            An initialized OCI tenancy gateway.
        """
        import oci
        from oci.auth import signers
        from oci.identity import IdentityClient
        from oci.limits import QuotasClient

        signer = signers.get_resource_principals_signer()
        client_config = {}
        region = config.get("OCI_REGION") or config.get("REGION")
        if region:
            client_config["region"] = region
        identity_client = IdentityClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        quotas_client = QuotasClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        return cls(signer.tenancy_id, identity_client, quotas_client)

    def get_compartment_name(self, compartment_ocid: str) -> str:
        """Return an OCI compartment name.

        Args:
            compartment_ocid: Compartment OCID.

        Returns:
            Compartment display name.
        """
        return self.identity_client.get_compartment(compartment_ocid).data.name

    def list_child_compartments(self, parent_compartment_ocid: str) -> list[CompartmentInfo]:
        """List active direct-child compartments and defined tags.

        Args:
            parent_compartment_ocid: Parent compartment OCID.

        Returns:
            Active direct-child compartments.
        """
        import oci

        compartments = oci.pagination.list_call_get_all_results(
            self.identity_client.list_compartments,
            parent_compartment_ocid,
            compartment_id_in_subtree=False,
            lifecycle_state="ACTIVE",
        ).data
        return [
            CompartmentInfo(
                ocid=item.id,
                name=item.name,
                defined_tags=dict(getattr(item, "defined_tags", None) or {}),
            )
            for item in compartments
        ]

    def list_quotas(self) -> list[QuotaInfo]:
        """List active quota policies in the tenancy.

        Returns:
            Active quota policies.
        """
        import oci

        quotas = oci.pagination.list_call_get_all_results(self.quotas_client.list_quotas, self.tenancy_ocid).data
        return [
            QuotaInfo(
                ocid=item.id,
                name=item.name,
                description=getattr(item, "description", "") or "",
                statements=tuple(getattr(item, "statements", []) or []),
            )
            for item in quotas
            if getattr(item, "lifecycle_state", "ACTIVE") == "ACTIVE"
        ]

    def create_quota(self, name: str, description: str, statements: list[str]) -> QuotaInfo:
        """Create a tenancy quota policy.

        Args:
            name: Quota policy name.
            description: Quota policy description.
            statements: Complete quota statement list.

        Returns:
            The created quota policy.
        """
        from oci.limits.models import CreateQuotaDetails

        details = CreateQuotaDetails(
            compartment_id=self.tenancy_ocid,
            name=name,
            description=description,
            statements=statements,
        )
        quota = self.quotas_client.create_quota(details).data
        return QuotaInfo(ocid=quota.id, name=quota.name, description=quota.description, statements=tuple(quota.statements))

    def update_quota(self, quota_id: str, description: str, statements: list[str]) -> None:
        """Replace the description and statements of a quota policy.

        Args:
            quota_id: Quota policy OCID.
            description: Desired quota policy description.
            statements: Complete desired quota statement list.
        """
        from oci.limits.models import UpdateQuotaDetails

        self.quotas_client.update_quota(quota_id, UpdateQuotaDetails(description=description, statements=statements))


def parse_bool(value: Any, default: bool) -> bool:
    """Parse a boolean configuration value.

    Args:
        value: Boolean or common textual representation.
        default: Value to use when ``value`` is ``None``.

    Returns:
        Parsed boolean value.

    Raises:
        ValueError: If the value is not recognized.
    """
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


def load_config(config: dict[str, Any], payload: dict[str, Any]) -> QuotaUpdaterConfig:
    """Load scheduled quota updater configuration.

    Args:
        config: Function environment and OCI configuration values.
        payload: Optional JSON invocation overrides.

    Returns:
        Validated quota updater settings.

    Raises:
        ValueError: If required settings or quota configuration are invalid.
    """
    quota_config_value = payload.get("quota_config_json", config.get("QUOTA_CONFIG_JSON"))
    if quota_config_value is None:
        quota_config = load_default_quota_config()
        quota_config_source = "bundled_default"
    else:
        quota_config = parse_json_list(quota_config_value, "QUOTA_CONFIG_JSON")
        quota_config_source = "payload_override" if "quota_config_json" in payload else "function_config"

    values = {}
    for env_name, field_name in {
        "ENGINEER_ROOT_COMPARTMENT_OCID": "engineer_root_compartment_ocid",
    }.items():
        value = payload.get(field_name, config.get(env_name))
        if not value:
            raise ValueError(f"Missing required config {env_name}")
        values[field_name] = str(value)

    return QuotaUpdaterConfig(
        engineer_root_compartment_ocid=values["engineer_root_compartment_ocid"],
        dry_run=parse_bool(payload.get("dry_run", config.get("DRY_RUN")), default=True),
        exclude_delete_marked_compartments=parse_bool(
            payload.get(
                "exclude_delete_marked_compartments",
                config.get("EXCLUDE_DELETE_MARKED_COMPARTMENTS"),
            ),
            default=False,
        ),
        quota_config_source=quota_config_source,
        quota_config=quota_config,
    )


def parse_json_list(value: Any, name: str) -> list[dict[str, Any]]:
    """Parse and validate a JSON list of objects.

    Args:
        value: Python list or JSON string.
        name: Configuration name used in validation errors.

    Returns:
        Parsed list of dictionaries.

    Raises:
        ValueError: If the value is not a list of objects.
    """
    if isinstance(value, list):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{name} must be valid JSON") from exc
    else:
        raise ValueError(f"{name} must be a JSON list")
    if not isinstance(parsed, list):
        raise ValueError(f"{name} must be a JSON list")
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(f"{name}[{index}] must be an object")
    return parsed


def load_default_quota_config() -> list[dict[str, Any]]:
    """Load the quota definition bundled beside ``func.py``.

    Returns:
        Default quota policy definitions.
    """
    with open(os.path.join(os.path.dirname(__file__), "default_quota_config.json"), encoding="utf-8") as config_file:
        contents = config_file.read()
    return parse_json_list(contents, "default_quota_config.json")


def validate_quota_config(quota_config: list[dict[str, Any]]) -> None:
    """Validate quota policy and statement fields.

    Args:
        quota_config: Quota policy definitions to validate.

    Raises:
        ValueError: If a required field or supported value is missing.
    """
    required_policy_fields = {"area", "quota_name", "description", "statements"}
    required_statement_fields = {"scope", "operation", "service"}
    for index, policy in enumerate(quota_config):
        missing = required_policy_fields - policy.keys()
        if missing:
            raise ValueError(f"quota_config[{index}] missing fields: {sorted(missing)}")
        if not isinstance(policy["statements"], list):
            raise ValueError(f"quota_config[{index}].statements must be a list")
        for statement_index, statement in enumerate(policy["statements"]):
            missing_statement = required_statement_fields - statement.keys()
            if missing_statement:
                raise ValueError(
                    f"quota_config[{index}].statements[{statement_index}] missing fields: {sorted(missing_statement)}"
                )
            if statement["scope"] not in {"root", "per_engineer"}:
                raise ValueError(f"Invalid quota statement scope: {statement['scope']}")
            if statement["operation"] not in {"set", "zero"}:
                raise ValueError(f"Invalid quota statement operation: {statement['operation']}")
            if statement["operation"] == "set" and "value" not in statement:
                raise ValueError("set quota statements require value")


def render_statement(statement: dict[str, Any], root_compartment_name: str, engineer_compartment_name: str | None) -> str:
    """Render one quota statement in OCI quota-policy syntax.

    Args:
        statement: Declarative quota statement.
        root_compartment_name: Root compartment name.
        engineer_compartment_name: Optional engineer compartment name.

    Returns:
        Rendered OCI quota statement.

    Raises:
        ValueError: If a per-engineer or set statement is incomplete.
    """
    service = statement["service"]
    quota_name = statement.get("quota")
    compartment_path = root_compartment_name
    if statement["scope"] == "per_engineer":
        if not engineer_compartment_name:
            raise ValueError("per_engineer statement requires engineer_compartment_name")
        compartment_path = f"{root_compartment_name}:{engineer_compartment_name}"
    if statement["operation"] == "zero":
        if quota_name:
            return f"zero {service} quota {quota_name} in compartment {compartment_path}"
        return f"zero {service} quota in compartment {compartment_path}"
    if not quota_name:
        raise ValueError("set quota statements require quota")
    return f"set {service} quota {quota_name} to {statement['value']} in compartment {compartment_path}"


def render_quota_policies(
    quota_config: list[dict[str, Any]],
    root_compartment_name: str,
    engineer_compartment_names: list[str],
) -> list[dict[str, Any]]:
    """Render all quota policies for the selected engineer compartments.

    Args:
        quota_config: Declarative quota policy definitions.
        root_compartment_name: Root compartment name.
        engineer_compartment_names: Engineer compartments receiving quotas.

    Returns:
        Rendered quota policies ready for comparison or OCI update.
    """
    validate_quota_config(quota_config)
    policies = []
    sorted_names = sorted(set(engineer_compartment_names), key=str.casefold)
    for policy in quota_config:
        rendered_statements = []
        for statement in policy["statements"]:
            if statement["scope"] == "root":
                rendered_statements.append(render_statement(statement, root_compartment_name, None))
            else:
                rendered_statements.extend(
                    render_statement(statement, root_compartment_name, name) for name in sorted_names
                )
        policies.append(
            {
                "area": policy["area"],
                "name": policy["quota_name"],
                "description": policy["description"],
                "statements": rendered_statements,
                "summary": summarize_quota_policy(policy),
            }
        )
    return policies


def summarize_quota_policy(policy: dict[str, Any]) -> dict[str, list[str]]:
    """Create compact logging summaries for a quota policy.

    Args:
        policy: Declarative quota policy.

    Returns:
        Root and per-engineer summary strings.
    """
    root_statements = []
    per_engineer_statements = []
    for statement in policy["statements"]:
        summary = summarize_statement(statement)
        if statement["scope"] == "root":
            root_statements.append(summary)
        else:
            per_engineer_statements.append(summary)
    return {"root": root_statements, "per_engineer": per_engineer_statements}


def summarize_statement(statement: dict[str, Any]) -> str:
    """Summarize one declarative quota statement.

    Args:
        statement: Declarative quota statement.

    Returns:
        Human-readable summary.
    """
    service = statement["service"]
    quota_name = statement.get("quota")
    if statement["operation"] == "zero":
        return f"zero {service}" + (f" {quota_name}" if quota_name else "")
    return f"{service} {quota_name}={statement['value']}"


def reconcile_quotas(config: dict[str, Any], payload: dict[str, Any], gateway: Any) -> dict[str, Any]:
    """Reconcile tenancy quota policies without creating compartments.

    Args:
        config: Function configuration values.
        payload: Optional JSON invocation overrides.
        gateway: OCI gateway or test double.

    Returns:
        JSON-serializable reconciliation summary.
    """
    settings = load_config(config, payload)
    existing_compartments = gateway.list_child_compartments(settings.engineer_root_compartment_ocid)
    target_names = sorted({compartment.name for compartment in existing_compartments if compartment.name}, key=str.casefold)
    excluded_names = []
    if settings.exclude_delete_marked_compartments:
        marked_names = {
            compartment.name
            for compartment in existing_compartments
            if _delete_tag_value(compartment.defined_tags) is not None
        }
        excluded_names = sorted(set(target_names) & marked_names, key=str.casefold)
        target_names = [name for name in target_names if name not in marked_names]

    root_name = gateway.get_compartment_name(settings.engineer_root_compartment_ocid)
    rendered_policies = render_quota_policies(settings.quota_config, root_name, target_names)
    existing_quotas = {quota.name: quota for quota in gateway.list_quotas()}
    quota_actions = []
    for rendered_policy in rendered_policies:
        existing = existing_quotas.get(rendered_policy["name"])
        action = quota_action(existing, rendered_policy["description"], rendered_policy["statements"])
        quota_action_result = {
            "area": rendered_policy["area"],
            "name": rendered_policy["name"],
            "action": action,
            "statement_count": len(rendered_policy["statements"]),
            "root_statements": rendered_policy["summary"]["root"],
            "per_engineer_statements": rendered_policy["summary"]["per_engineer"],
        }
        quota_actions.append(quota_action_result)
        if settings.dry_run or action == "unchanged":
            continue
        if action == "create":
            created = gateway.create_quota(
                rendered_policy["name"], rendered_policy["description"], rendered_policy["statements"]
            )
            quota_action_result["ocid"] = created.ocid
        else:
            gateway.update_quota(existing.ocid, rendered_policy["description"], rendered_policy["statements"])
            quota_action_result["ocid"] = existing.ocid

    return {
        "dry_run": settings.dry_run,
        "exclude_delete_marked_compartments": settings.exclude_delete_marked_compartments,
        "quota_config_source": settings.quota_config_source,
        "quota_policy_count": len(settings.quota_config),
        "engineer_root_compartment_ocid": settings.engineer_root_compartment_ocid,
        "root_compartment_name": root_name,
        "discovered_compartment_count": len(existing_compartments),
        "quota_compartment_count": len(target_names),
        "quota_compartments": target_names,
        "excluded_delete_marked_compartments": excluded_names,
        "quotas": quota_actions,
    }


def quota_action(existing: QuotaInfo | None, description: str, statements: list[str]) -> str:
    """Determine the required action for one quota policy.

    Args:
        existing: Existing quota policy, if any.
        description: Desired description.
        statements: Desired complete statement list.

    Returns:
        ``create``, ``update``, or ``unchanged``.
    """
    if existing is None:
        return "create"
    if existing.description != description or list(existing.statements) != statements:
        return "update"
    return "unchanged"


def configure_logging(config: dict[str, Any], payload: dict[str, Any]) -> None:
    """Configure function and dependency logging.

    Args:
        config: Function environment and configuration values.
        payload: Optional JSON logging overrides.
    """
    log_level_name = str(payload.get("log_level", config.get("LOG_LEVEL", "INFO"))).upper()
    logging.basicConfig(
        level=getattr(logging, log_level_name, logging.INFO),
        format="%(levelname)s %(name)s - %(message)s",
        force=True,
    )
    dependency_level_name = str(config.get("DEPENDENCY_LOG_LEVEL", "WARNING")).upper()
    dependency_level = getattr(logging, dependency_level_name, logging.WARNING)
    for logger_name in NOISY_LOGGERS:
        logging.getLogger(logger_name).setLevel(dependency_level)


def log_summary(logger: logging.Logger, result: dict[str, Any]) -> None:
    """Write a concise reconciliation summary to the function log.

    Args:
        logger: Logger receiving summary messages.
        result: Result returned by ``reconcile_quotas``.
    """
    action_counts = {}
    for quota in result["quotas"]:
        action_counts[quota["action"]] = action_counts.get(quota["action"], 0) + 1
    logger.info(
        "Summary dry_run=%s exclude_delete_marked=%s quota_config_source=%s "
        "quota_policy_count=%s discovered_compartments=%s quota_compartments=%s excluded=%s quota_actions=%s",
        result["dry_run"],
        result["exclude_delete_marked_compartments"],
        result["quota_config_source"],
        result["quota_policy_count"],
        result["discovered_compartment_count"],
        result["quota_compartment_count"],
        len(result["excluded_delete_marked_compartments"]),
        action_counts,
    )
    if result["excluded_delete_marked_compartments"]:
        logger.info("Excluded delete-marked compartments: %s", ", ".join(result["excluded_delete_marked_compartments"]))
    for quota in result["quotas"]:
        logger.info(
            "Quota %s area=%s action=%s statements=%s",
            quota["name"], quota["area"], quota["action"], quota["statement_count"],
        )


def handler(ctx, data: io.BytesIO = None):
    """Handle one scheduled invocation.

    Args:
        ctx: OCI Functions context containing function configuration.
        data: Optional JSON object containing invocation overrides. ``{}`` is
            sufficient for normal scheduled execution.

    Returns:
        JSON quota reconciliation result.
    """
    payload = {}
    if data:
        raw_payload = data.getvalue()
        if raw_payload:
            payload = json.loads(raw_payload.decode("utf-8"))
    config = dict(os.environ)
    try:
        config.update(ctx.Config())
    except Exception:
        pass
    configure_logging(config, payload)
    LOGGER.info("Starting engineer quota update")
    gateway = OciTenancyGateway.from_resource_principal(config)
    result = reconcile_quotas(config, payload, gateway)
    log_summary(LOGGER, result)
    return json.dumps(result, indent=2, sort_keys=True)


def _delete_tag_value(defined_tags: dict[str, dict[str, str]]) -> str | None:
    """Return the delete-mark tag value when present.

    Args:
        defined_tags: Compartment defined-tag mapping.

    Returns:
        Tag value, or ``None`` when the compartment is not marked.
    """
    value = (defined_tags.get(DELETE_TAG_NAMESPACE) or {}).get(DELETE_TAG_KEY)
    return str(value) if value not in (None, "") else None


if __name__ == "__main__":
    raise SystemExit("This module is intended to run through the OCI Functions handler")
