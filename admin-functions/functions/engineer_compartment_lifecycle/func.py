"""Reconcile engineer compartments in response to OCI Identity Events."""

import io
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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

CREATE_EVENT_TYPES = {
    "com.oraclecloud.identitycontrolplane.createuser",
    "com.oraclecloud.identitycontrolplane.createfederateduser"
}
UPDATE_EVENT_TYPES = {
    "com.oraclecloud.identitycontrolplane.updateuser",
}
ACTIVATE_EVENT_TYPES = {
    "com.oraclecloud.identitycontrolplane.activateuser",
}
DEACTIVATE_EVENT_TYPES = {
    "com.oraclecloud.identitycontrolplane.deactivateuser",
}
DELETE_EVENT_TYPES = {
    "com.oraclecloud.identitycontrolplane.deleteuser",
}
LOGGER = logging.getLogger("engineer_compartment_lifecycle")


@dataclass(frozen=True)
class LifecycleConfig:
    """Runtime settings for the event-driven lifecycle function.

    Args:
        domain_id: Identity Domain OCID used to resolve user IDs.
        engineer_root_compartment_ocid: Parent for engineer compartments.
        delete_grace_period_hours: Delay before a marked compartment is staged.
        dry_run: Whether to report changes without modifying OCI resources.
    """

    domain_id: str
    engineer_root_compartment_ocid: str
    delete_grace_period_hours: int
    dry_run: bool


@dataclass(frozen=True)
class CompartmentInfo:
    """Small representation of an OCI compartment.

    Args:
        ocid: Compartment OCID.
        name: Compartment name.
        defined_tags: Defined tags currently attached to the compartment.
    """

    ocid: str
    name: str
    defined_tags: dict[str, dict[str, str]]


@dataclass(frozen=True)
class UserInfo:
    """Small representation of an Identity Domain user.

    Args:
        user_name: Canonical user name or email address.
        active: Whether the user is currently active.
    """

    user_name: str
    active: bool


class OciLifecycleGateway:
    """Adapt OCI Identity and Identity Domains clients to lifecycle operations."""

    def __init__(self, identity_client: Any, identity_domains_client: Any):
        self.identity_client = identity_client
        self.identity_domains_client = identity_domains_client

    @classmethod
    def from_resource_principal(cls, config: dict[str, Any]) -> "OciLifecycleGateway":
        """Create an OCI gateway authenticated with the function resource principal.

        Args:
            config: Function configuration containing ``DOMAIN_ID`` and region.

        Returns:
            An initialized OCI gateway.
        """
        import oci
        from oci.auth import signers
        from oci.identity import IdentityClient
        from oci.identity_domains import IdentityDomainsClient

        signer = signers.get_resource_principals_signer()
        client_config = {}
        region = config.get("OCI_REGION") or config.get("REGION")
        if region:
            client_config["region"] = region
        identity_client = IdentityClient(
            client_config,
            signer=signer,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )
        domain = identity_client.get_domain(config["DOMAIN_ID"]).data
        domain_url = getattr(domain, "url", None)
        if not domain_url:
            raise ValueError("Identity domain lookup did not return a URL")
        domains_client = IdentityDomainsClient(
            client_config,
            signer=signer,
            service_endpoint=domain_url,
            retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY,
        )
        return cls(identity_client, domains_client)

    def get_user(self, user_id: str) -> UserInfo | None:
        """Resolve a user ID and return its current name and active state.

        Args:
            user_id: Identity Domains user identifier from the event.

        Returns:
            Current user information, or ``None`` if the user no longer exists.
        """
        try:
            user = self.identity_domains_client.get_user(user_id, attribute_sets=["all"]).data
        except Exception:
            return None
        user_name = _first_attr(user, "user_name", "userName", "display_name", "name")
        if not user_name:
            return None
        return UserInfo(user_name=str(user_name), active=bool(_first_attr(user, "active", default=True)))

    def list_child_compartments(self, parent_ocid: str) -> list[CompartmentInfo]:
        """List active direct children of a compartment.

        Args:
            parent_ocid: Parent compartment OCID.

        Returns:
            Active direct child compartments and their defined tags.
        """
        import oci

        compartments = oci.pagination.list_call_get_all_results(
            self.identity_client.list_compartments,
            parent_ocid,
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

    def find_child_compartment(self, parent_ocid: str, name: str) -> CompartmentInfo | None:
        """Find an active direct child by exact name.

        Args:
            parent_ocid: Parent compartment OCID.
            name: Exact compartment name.

        Returns:
            Matching compartment, or ``None`` when it is absent.
        """
        return next(
            (item for item in self.list_child_compartments(parent_ocid) if item.name == name),
            None,
        )

    def create_compartment(self, parent_ocid: str, name: str, description: str) -> CompartmentInfo:
        """Create an engineer compartment.

        Args:
            parent_ocid: Parent compartment OCID.
            name: New compartment name.
            description: New compartment description.

        Returns:
            The created compartment.
        """
        from oci.identity.models import CreateCompartmentDetails

        details = CreateCompartmentDetails(
            compartment_id=parent_ocid,
            name=name,
            description=description,
            defined_tags={"Oracle-Tags": {"AllowCompartmentCreation": "true"}},
        )
        compartment = self.identity_client.create_compartment(details).data
        return CompartmentInfo(
            ocid=compartment.id,
            name=compartment.name,
            defined_tags=dict(getattr(compartment, "defined_tags", None) or {}),
        )

    def update_defined_tags(self, compartment_ocid: str, defined_tags: dict[str, dict[str, str]]) -> None:
        """Replace a compartment's defined tags with the supplied values.

        Args:
            compartment_ocid: Compartment OCID to update.
            defined_tags: Complete desired defined-tag mapping.
        """
        from oci.identity.models import UpdateCompartmentDetails

        self.identity_client.update_compartment(
            compartment_ocid,
            update_compartment_details=UpdateCompartmentDetails(defined_tags=defined_tags),
        )


def parse_bool(value: Any, default: bool) -> bool:
    """Parse a boolean function setting.

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


def configure_logging(config: dict[str, Any], payload: dict[str, Any]) -> None:
    """Configure function and OCI SDK logging.

    Args:
        config: Function environment and configuration values.
        payload: Optional invocation overrides.
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


def load_config(config: dict[str, Any], payload: dict[str, Any]) -> LifecycleConfig:
    """Load and validate lifecycle settings.

    Args:
        config: Environment and OCI Function configuration values.
        payload: Optional top-level invocation overrides.

    Returns:
        Validated lifecycle settings.

    Raises:
        ValueError: If required configuration is missing or invalid.
    """
    values = {}
    for env_name, field_name in {
        "DOMAIN_ID": "domain_id",
        "ENGINEER_ROOT_COMPARTMENT_OCID": "engineer_root_compartment_ocid",
    }.items():
        value = payload.get(field_name, config.get(env_name))
        if not value:
            raise ValueError(f"Missing required config {env_name}")
        values[field_name] = str(value)

    grace_value = payload.get("delete_grace_period_hours", config.get("DELETE_GRACE_PERIOD_HOURS", "72"))
    try:
        grace_period_hours = int(grace_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("DELETE_GRACE_PERIOD_HOURS must be an integer") from exc
    if grace_period_hours <= 0:
        raise ValueError("DELETE_GRACE_PERIOD_HOURS must be greater than zero")

    return LifecycleConfig(
        domain_id=values["domain_id"],
        engineer_root_compartment_ocid=values["engineer_root_compartment_ocid"],
        delete_grace_period_hours=grace_period_hours,
        dry_run=parse_bool(payload.get("dry_run", config.get("DRY_RUN")), default=True),
    )


def process_event(event: dict[str, Any], settings: LifecycleConfig, gateway: Any) -> dict[str, Any]:
    """Reconcile one OCI user event with its engineer compartment.

    Args:
        event: OCI Events CloudEvent payload.
        settings: Validated lifecycle settings.
        gateway: OCI gateway or test double.

    Returns:
        A JSON-serializable action result. Unsupported or incomplete events are
        successful no-ops so broad OCI Events rules are safe.
    """
    event_type = str(event.get("eventType", ""))
    lifecycle_action = _event_action(event_type, event)
    base_result = {"event_id": event.get("eventID"), "event_type": event_type}
    LOGGER.info(
        "Received lifecycle event: event_id=%s event_type=%s classified_action=%s dry_run=%s",
        base_result["event_id"],
        event_type or "<missing>",
        lifecycle_action or "ignored",
        settings.dry_run,
    )
    if lifecycle_action is None:
        return {**base_result, "action": "ignored", "reason": "unsupported_event"}

    data = event.get("data") or {}
    additional = data.get("additionalDetails") or {}
    user_id = _first(data, "resourceId", "userId") or _first(additional, "userId")
    event_user_name = _first(data, "resourceName", "userName", "username", "email")
    user = gateway.get_user(str(user_id)) if user_id else None
    user_name = user.user_name if user else event_user_name
    if not user_name:
        return {**base_result, "action": "noop", "reason": "missing_user_identity", "lifecycle_action": lifecycle_action}

    compartment_name = str(user_name).split("@", 1)[0]
    should_delete = lifecycle_action in {"delete", "deactivate"} or (user is not None and not user.active)
    compartment = gateway.find_child_compartment(settings.engineer_root_compartment_ocid, compartment_name)
    if should_delete:
        if compartment is None:
            return {
                **base_result,
                "action": "noop",
                "reason": "compartment_not_found_under_engineer_root",
                "compartment_name": compartment_name,
                "lifecycle_action": lifecycle_action,
            }
        return _mark_for_deletion(event, compartment, settings, base_result, lifecycle_action, gateway)

    if compartment is None:
        result = {
            **base_result,
            "action": "dry_run" if settings.dry_run else "created",
            "compartment_name": compartment_name,
            "lifecycle_action": lifecycle_action,
        }
        if not settings.dry_run:
            created = gateway.create_compartment(
                settings.engineer_root_compartment_ocid,
                compartment_name,
                f"{compartment_name} compartment",
            )
            result["compartment_ocid"] = created.ocid
        LOGGER.info("%s compartment %s", "Would create" if settings.dry_run else "Created", compartment_name)
        return result

    existing_deadline = _delete_deadline(compartment.defined_tags)
    if existing_deadline is None:
        return {
            **base_result,
            "action": "unchanged",
            "compartment_name": compartment_name,
            "compartment_ocid": compartment.ocid,
            "lifecycle_action": lifecycle_action,
        }

    desired_tags = _without_delete_tag(compartment.defined_tags)
    result = {
        **base_result,
        "action": "dry_run" if settings.dry_run else "unmarked",
        "compartment_name": compartment_name,
        "compartment_ocid": compartment.ocid,
        "lifecycle_action": lifecycle_action,
    }
    if not settings.dry_run:
        gateway.update_defined_tags(compartment.ocid, desired_tags)
    LOGGER.info("%s deletion mark for compartment %s", "Would remove" if settings.dry_run else "Removed", compartment_name)
    return result


def _mark_for_deletion(
    event: dict[str, Any],
    compartment: CompartmentInfo,
    settings: LifecycleConfig,
    base_result: dict[str, Any],
    lifecycle_action: str,
    gateway: Any,
) -> dict[str, Any]:
    """Add a deletion deadline to a compartment unless it is already marked.

    Args:
        event: OCI Events CloudEvent payload.
        compartment: Matching engineer compartment.
        settings: Validated lifecycle settings.
        base_result: Common result fields.
        lifecycle_action: Classified user lifecycle action.
        gateway: OCI gateway or test double.

    Returns:
        Action result describing the tag operation.
    """
    existing_deadline = _delete_deadline(compartment.defined_tags)
    if existing_deadline is not None:
        return {
            **base_result,
            "action": "unchanged",
            "reason": "deletion_deadline_already_set",
            "compartment_name": compartment.name,
            "compartment_ocid": compartment.ocid,
            "delete_after": existing_deadline,
            "lifecycle_action": lifecycle_action,
        }

    event_time = _event_time(event)
    delete_after = event_time + timedelta(hours=settings.delete_grace_period_hours)
    delete_after_value = _format_timestamp(delete_after)
    desired_tags = _with_delete_tag(compartment.defined_tags, delete_after_value)
    result = {
        **base_result,
        "action": "dry_run" if settings.dry_run else "marked",
        "compartment_name": compartment.name,
        "compartment_ocid": compartment.ocid,
        "delete_after": delete_after_value,
        "lifecycle_action": lifecycle_action,
    }
    if not settings.dry_run:
        gateway.update_defined_tags(compartment.ocid, desired_tags)
    LOGGER.info(
        "%s deletion mark for compartment %s after %s",
        "Would set" if settings.dry_run else "Set",
        compartment.name,
        delete_after_value,
    )
    return result


def handler(ctx, data: io.BytesIO = None):
    """Handle one OCI Events invocation.

    Args:
        ctx: OCI Functions context containing function configuration.
        data: Request body containing an OCI Events CloudEvent.

    Returns:
        JSON action result for the event invocation.
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
    settings = load_config(config, payload)
    LOGGER.info(
        "Lifecycle function configured: dry_run=%s engineer_root=%s grace_hours=%s",
        settings.dry_run,
        settings.engineer_root_compartment_ocid,
        settings.delete_grace_period_hours,
    )
    gateway = OciLifecycleGateway.from_resource_principal(config)
    result = process_event(payload, settings, gateway)
    LOGGER.info("Lifecycle result: %s", result)
    return json.dumps(result, indent=2, sort_keys=True)


def _event_action(event_type: str, event: dict[str, Any]) -> str | None:
    """Classify an OCI event into a supported lifecycle action.

    Args:
        event_type: OCI event type string.
        event: Full event payload, used for state-update events.

    Returns:
        ``create``, ``update``, ``activate``, ``deactivate``, ``delete``, or
        ``None`` for unsupported events.
    """
    if event_type in DELETE_EVENT_TYPES:
        return "delete"
    if event_type in CREATE_EVENT_TYPES:
        return "create"
    if event_type in UPDATE_EVENT_TYPES:
        return "update"
    if event_type in ACTIVATE_EVENT_TYPES:
        return "activate"
    if event_type in DEACTIVATE_EVENT_TYPES:
        data = event.get("data") or {}
        additional = data.get("additionalDetails") or {}
        state = _first(data, "state", "status", "lifecycleState") or _first(additional, "state", "status")
        if state is None or str(state).strip().lower() in {"inactive", "deactivated", "disabled", "false"}:
            return "deactivate"
        return "activate"
    return None


def _event_time(event: dict[str, Any]) -> datetime:
    """Read an event timestamp, falling back to the current UTC time.

    Args:
        event: OCI Events CloudEvent payload.

    Returns:
        Timezone-aware UTC timestamp.
    """
    value = event.get("eventTime") or event.get("time")
    if not value:
        return datetime.now(timezone.utc)
    normalized = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _format_timestamp(value: datetime) -> str:
    """Format a timestamp for the OCI defined tag value.

    Args:
        value: Timezone-aware timestamp.

    Returns:
        UTC ISO-8601 timestamp ending in ``Z``.
    """
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _delete_deadline(defined_tags: dict[str, dict[str, str]]) -> str | None:
    """Return the lifecycle deletion tag value when present.

    Args:
        defined_tags: Compartment defined-tag mapping.

    Returns:
        Existing deletion deadline, or ``None``.
    """
    namespace_tags = defined_tags.get(DELETE_TAG_NAMESPACE) or {}
    value = namespace_tags.get(DELETE_TAG_KEY)
    return str(value) if value not in (None, "") else None


def _with_delete_tag(defined_tags: dict[str, dict[str, str]], value: str) -> dict[str, dict[str, str]]:
    """Return defined tags with the lifecycle deletion tag set.

    Args:
        defined_tags: Existing defined-tag mapping.
        value: New deletion deadline.

    Returns:
        Copy of the desired defined-tag mapping.
    """
    result = {namespace: dict(tags) for namespace, tags in defined_tags.items()}
    result.setdefault(DELETE_TAG_NAMESPACE, {})[DELETE_TAG_KEY] = value
    return result


def _without_delete_tag(defined_tags: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    """Return defined tags without the lifecycle deletion tag.

    Args:
        defined_tags: Existing defined-tag mapping.

    Returns:
        Copy of the desired defined-tag mapping without the lifecycle tag.
    """
    result = {namespace: dict(tags) for namespace, tags in defined_tags.items()}
    namespace_tags = result.get(DELETE_TAG_NAMESPACE)
    if namespace_tags is not None:
        namespace_tags.pop(DELETE_TAG_KEY, None)
        if not namespace_tags:
            result.pop(DELETE_TAG_NAMESPACE, None)
    return result


def _first(mapping: Any, *names: str) -> Any:
    """Return the first non-empty value from a dictionary.

    Args:
        mapping: Candidate dictionary.
        *names: Keys to inspect in order.

    Returns:
        First non-empty value, or ``None``.
    """
    if not isinstance(mapping, dict):
        return None
    for name in names:
        value = mapping.get(name)
        if value not in (None, ""):
            return value
    return None


def _first_attr(value: Any, *names: str, default: Any = None) -> Any:
    """Return the first non-empty attribute or dictionary value.

    Args:
        value: Object or dictionary to inspect.
        *names: Attributes or keys to inspect in order.
        default: Value to return when no name is present.

    Returns:
        First non-empty value, or ``default``.
    """
    for name in names:
        candidate = value.get(name) if isinstance(value, dict) else getattr(value, name, None)
        if candidate not in (None, ""):
            return candidate
    return default
