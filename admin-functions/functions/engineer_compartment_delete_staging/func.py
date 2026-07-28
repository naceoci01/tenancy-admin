"""Stage expired engineer compartments for deletion."""

from dataclasses import dataclass
from datetime import datetime, timezone
import io
import json
import logging
import os
import time
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
LOGGER = logging.getLogger("engineer_compartment_delete_staging")


@dataclass(frozen=True)
class DeleteStagingConfig:
    """Runtime settings for the scheduled delete-staging function.

    Args:
        engineer_root_compartment_ocid: Parent of the engineer compartments.
        delete_staging_compartment_ocid: Destination for expired compartments.
        dry_run: Whether to report moves without changing OCI state.
    """

    engineer_root_compartment_ocid: str
    delete_staging_compartment_ocid: str
    dry_run: bool


@dataclass(frozen=True)
class CompartmentInfo:
    """The compartment data needed for delete staging.

    Args:
        ocid: Compartment OCID.
        name: Compartment name.
        defined_tags: Defined tags attached to the compartment.
    """

    ocid: str
    name: str
    defined_tags: dict[str, dict[str, str]]


class CompartmentMoveConflictError(RuntimeError):
    """An OCI 409 returned while requesting a compartment move."""

    def __init__(self, error: Exception):
        super().__init__(str(error))
        self.code = getattr(error, "code", None)
        self.message = getattr(error, "message", None) or str(error)
        self.request_id = getattr(error, "request_id", None)
        self.status = getattr(error, "status", None)


class OciDeleteStagingGateway:
    """Adapter around OCI Identity compartment operations."""

    def __init__(self, identity_client: Any):
        """Initialize the gateway.

        Args:
            identity_client: Authenticated OCI Identity client.
        """
        self.identity_client = identity_client

    @classmethod
    def from_resource_principal(cls, config: dict[str, Any]) -> "OciDeleteStagingGateway":
        """Create a gateway using the function resource principal.

        Args:
            config: Function configuration containing an optional OCI region.

        Returns:
            An initialized OCI gateway.
        """
        import oci
        from oci.auth import signers
        from oci.identity import IdentityClient

        signer = signers.get_resource_principals_signer()
        client_config = {}
        region = config.get("OCI_REGION") or config.get("REGION")
        if region:
            client_config["region"] = region
        identity_client = IdentityClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY)
        return cls(identity_client)

    def list_child_compartments(self, parent_compartment_ocid: str) -> list[CompartmentInfo]:
        """List all active direct children using OCI pagination.

        Args:
            parent_compartment_ocid: Parent compartment OCID.

        Returns:
            Active direct-child compartments with defined tags.
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

    def move_compartment(self, compartment_ocid: str, destination_compartment_ocid: str) -> str | None:
        """Request a compartment move and return OCI's work-request OCID.

        Args:
            compartment_ocid: Compartment OCID to move.
            destination_compartment_ocid: Destination parent compartment OCID.

        Returns:
            OCI work-request OCID, when supplied by the service.

        Raises:
            Exception: Propagates OCI SDK errors after logging their full context.
        """
        from oci.identity.models import MoveCompartmentDetails

        try:
            response = self.identity_client.move_compartment(
                compartment_ocid,
                MoveCompartmentDetails(target_compartment_id=destination_compartment_ocid),
            )
        except Exception as error:
            if getattr(error, "status", None) == 409:
                LOGGER.warning(
                    "Compartment move conflicts with existing destination state "
                    "compartment_ocid=%s destination_compartment_ocid=%s oci_code=%s oci_request_id=%s",
                    compartment_ocid,
                    destination_compartment_ocid,
                    getattr(error, "code", None) or "unknown",
                    getattr(error, "request_id", None) or "not-returned",
                )
                raise CompartmentMoveConflictError(error) from error
            LOGGER.exception(
                "Failed to request compartment move compartment_ocid=%s destination_compartment_ocid=%s",
                compartment_ocid,
                destination_compartment_ocid,
            )
            raise
        work_request_id = response.headers.get("opc-work-request-id")
        LOGGER.info(
            "Compartment move requested compartment_ocid=%s destination_compartment_ocid=%s work_request_id=%s",
            compartment_ocid,
            destination_compartment_ocid,
            work_request_id or "not-returned",
        )
        return work_request_id


def parse_bool(value: Any, default: bool) -> bool:
    """Parse a boolean configuration value.

    Args:
        value: Boolean or textual boolean representation.
        default: Value to use when ``value`` is ``None``.

    Returns:
        The parsed boolean.

    Raises:
        ValueError: If the value is not a recognized boolean.
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


def load_config(config: dict[str, Any], payload: dict[str, Any]) -> DeleteStagingConfig:
    """Load and validate scheduled delete-staging settings.

    Args:
        config: Function environment and configuration values.
        payload: Optional invocation overrides.

    Returns:
        Validated delete-staging settings.

    Raises:
        ValueError: If a required configuration value is missing.
    """
    values = {}
    for env_name, field_name in {
        "ENGINEER_ROOT_COMPARTMENT_OCID": "engineer_root_compartment_ocid",
        "DELETE_STAGING_COMPARTMENT_OCID": "delete_staging_compartment_ocid",
    }.items():
        value = payload.get(field_name, config.get(env_name))
        if not value:
            raise ValueError(f"Missing required config {env_name}")
        values[field_name] = str(value)
    return DeleteStagingConfig(
        engineer_root_compartment_ocid=values["engineer_root_compartment_ocid"],
        delete_staging_compartment_ocid=values["delete_staging_compartment_ocid"],
        dry_run=parse_bool(payload.get("dry_run", config.get("DRY_RUN")), default=True),
    )


def parse_delete_after(value: str) -> datetime:
    """Parse a UTC deletion deadline from the lifecycle tag.

    Args:
        value: ISO-8601 timestamp from ``Oracle-Tags.DeleteCompartmentAfter``.

    Returns:
        A timezone-aware UTC timestamp.

    Raises:
        ValueError: If the value is not an offset-aware ISO-8601 timestamp.
    """
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("DeleteCompartmentAfter must include a timezone")
    return parsed.astimezone(timezone.utc)


def delete_tag_value(compartment: CompartmentInfo) -> str | None:
    """Return the configured delete deadline, if present.

    Args:
        compartment: Compartment to inspect.

    Returns:
        The nonempty deletion deadline string, or ``None``.
    """
    value = (compartment.defined_tags.get(DELETE_TAG_NAMESPACE) or {}).get(DELETE_TAG_KEY)
    return str(value) if value not in (None, "") else None


def stage_expired_compartments(
    config: dict[str, Any],
    payload: dict[str, Any],
    gateway: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Move expired direct-child engineer compartments to delete staging.

    Args:
        config: Function configuration values.
        payload: Optional invocation overrides.
        gateway: OCI gateway or test double.
        now: UTC time for comparison; injectable for tests.

    Returns:
        A JSON-serializable staging summary.
    """
    settings = load_config(config, payload)
    current_time = now or datetime.now(timezone.utc)
    if current_time.tzinfo is None:
        raise ValueError("now must include a timezone")
    current_time = current_time.astimezone(timezone.utc)

    actions = []
    expired_compartments = []
    for compartment in sorted(
        gateway.list_child_compartments(settings.engineer_root_compartment_ocid),
        key=lambda item: item.name.casefold(),
    ):
        delete_after = delete_tag_value(compartment)
        if delete_after is None:
            continue
        try:
            deadline = parse_delete_after(delete_after)
        except ValueError:
            actions.append({"name": compartment.name, "ocid": compartment.ocid, "action": "invalid_delete_after", "delete_after": delete_after})
            continue
        if deadline >= current_time:
            actions.append({"name": compartment.name, "ocid": compartment.ocid, "action": "not_due", "delete_after": delete_after})
            continue
        action_result = {
            "name": compartment.name,
            "ocid": compartment.ocid,
            "action": "dry_run" if settings.dry_run else "pending",
            "delete_after": delete_after,
        }
        expired_compartments.append((compartment, action_result))
        actions.append(action_result)

    planned_names = [compartment.name for compartment, _ in expired_compartments]
    LOGGER.info(
        "Delete-staging candidates dry_run=%s count=%s compartments=%s",
        settings.dry_run,
        len(planned_names),
        ", ".join(planned_names) if planned_names else "none",
    )
    if not settings.dry_run:
        move_started = time.monotonic()
        for compartment, action_result in expired_compartments:
            try:
                work_request_id = gateway.move_compartment(compartment.ocid, settings.delete_staging_compartment_ocid)
            except CompartmentMoveConflictError as error:
                action_result["action"] = "move_conflict"
                action_result["oci_status"] = error.status
                action_result["oci_message"] = error.message
                if error.code:
                    action_result["oci_code"] = error.code
                if error.request_id:
                    action_result["oci_request_id"] = error.request_id
                continue
            except Exception as error:
                LOGGER.exception(
                    "Compartment move failed; continuing with remaining candidates "
                    "compartment_ocid=%s destination_compartment_ocid=%s",
                    compartment.ocid,
                    settings.delete_staging_compartment_ocid,
                )
                action_result["action"] = "move_failed"
                action_result["error_type"] = type(error).__name__
                action_result["error_message"] = getattr(error, "message", None) or str(error)
                status = getattr(error, "status", None)
                if status is not None:
                    action_result["oci_status"] = status
                code = getattr(error, "code", None)
                if code:
                    action_result["oci_code"] = code
                request_id = getattr(error, "request_id", None)
                if request_id:
                    action_result["oci_request_id"] = request_id
                continue
            action_result["action"] = "move_requested"
            if work_request_id:
                action_result["work_request_id"] = work_request_id
        LOGGER.info(
            "Delete staging move requests submitted: count=%s elapsed_seconds=%.2f",
            len(expired_compartments),
            time.monotonic() - move_started,
        )

    action_counts = {}
    for action in actions:
        action_counts[action["action"]] = action_counts.get(action["action"], 0) + 1
    return {
        "dry_run": settings.dry_run,
        "engineer_root_compartment_ocid": settings.engineer_root_compartment_ocid,
        "delete_staging_compartment_ocid": settings.delete_staging_compartment_ocid,
        "evaluated_at": current_time.isoformat().replace("+00:00", "Z"),
        "actions": actions,
        "action_counts": action_counts,
    }


def handler(ctx, data: io.BytesIO = None):
    """Handle a scheduled delete-staging invocation.

    Args:
        ctx: OCI Functions context containing configuration.
        data: Optional JSON invocation overrides.

    Returns:
        JSON delete-staging result.
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
    try:
        result = stage_expired_compartments(config, payload, OciDeleteStagingGateway.from_resource_principal(config))
    except Exception:
        LOGGER.exception("Delete-staging invocation failed")
        raise
    LOGGER.info("Delete staging summary: %s", result["action_counts"])
    return json.dumps(result, indent=2, sort_keys=True)
