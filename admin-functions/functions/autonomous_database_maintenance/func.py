import io
import json
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import oci
from oci.auth import signers
from oci.database import DatabaseClient
from oci.database.models import UpdateAutonomousDatabaseDetails
from oci.exceptions import MaximumWaitTimeExceeded, ServiceError
from oci.resource_search import ResourceSearchClient
from oci.resource_search.models import StructuredSearchDetails

logger = logging.getLogger("autonomous_database_maintenance")
WORKLOAD_ALIASES = {
    "ATP": "ATP",
    "OLTP": "ATP",
    "ADW": "ADW",
    "DW": "ADW",
    "JSON": "JSON",
    "AJD": "JSON",
    "APEX": "APEX",
    "LH": "LH",
}
SUPPORTED_WORKLOADS = {"ATP", "ADW", "JSON", "APEX", "LH"}
NOISY_LOGGERS = [
    "oci",
    "oci._vendor",
    "oci._vendor.urllib3",
    "oci.circuit_breaker",
    "urllib3",
    "urllib3.connectionpool",
]


def _bool(value, default):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def configure_logging(config, payload):
    """Configure function and OCI SDK logging."""
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


def _int(value, name, default):
    if value is None:
        return default
    result = int(value)
    if result < 1:
        raise ValueError(f"{name} must be greater than zero")
    return result


def _float(value, name, default):
    if value is None:
        return default
    result = float(value)
    if result < 1:
        raise ValueError(f"{name} must be at least 1")
    return result


def _resource_principal_region():
    return str(getattr(signers.get_resource_principals_signer(), "region", "")).strip()


def _notification_region(topic_id):
    parts = str(topic_id).split(".", 4)
    if len(parts) < 5 or parts[:2] != ["ocid1", "onstopic"] or not parts[2] or not parts[3]:
        raise ValueError("NOTIFICATION_TOPIC_ID must be a regional OCI Notifications topic OCID")
    return oci.regions.get_region_from_short_name(parts[3])


def load_config(config, payload):
    value = lambda name, default=None: payload.get(name.lower(), config.get(name, default))
    default_region = config.get("OCI_REGION") or config.get("REGION") or _resource_principal_region()
    regions_value = value("REGIONS", "")
    if not str(regions_value).strip():
        regions_value = default_region
    regions = [
        item.strip()
        for item in str(regions_value).split(",")
        if item.strip()
    ]
    if not regions:
        raise ValueError("REGIONS must contain at least one OCI region")
    workloads = value("WORKLOAD_TYPES", "ATP,ADW,JSON,APEX,LH")
    workloads = [
        WORKLOAD_ALIASES.get(item.strip().upper(), item.strip().upper())
        for item in str(workloads).split(",")
        if item.strip()
    ]
    if not workloads:
        raise ValueError("WORKLOAD_TYPES must contain at least one workload")
    unsupported = sorted(set(workloads) - SUPPORTED_WORKLOADS)
    if unsupported:
        raise ValueError(f"Unsupported WORKLOAD_TYPES: {', '.join(unsupported)}")
    return {
        "regions": regions,
        "dry_run": _bool(value("DRY_RUN"), True),
        "threads": _int(value("THREADS"), "THREADS", 5),
        "backup_retention": _int(value("BACKUP_RETENTION_DAYS"), "BACKUP_RETENTION_DAYS", 14),
        "minimum_ecpus": _float(value("MINIMUM_ECPUS"), "MINIMUM_ECPUS", 2.0),
        "storage_multiplier": _float(value("STORAGE_MULTIPLIER"), "STORAGE_MULTIPLIER", 2.0),
        "minimum_storage_gb": _int(value("MINIMUM_STORAGE_GB"), "MINIMUM_STORAGE_GB", 20),
        "workloads": workloads,
        "convert_to_ecpu": _bool(value("ENABLE_ECPU_CONVERSION"), True),
        "reduce_backup_retention": _bool(value("ENABLE_BACKUP_RETENTION"), True),
        "reduce_ecpus": _bool(value("ENABLE_COMPUTE_SCALE_DOWN"), True),
        "scale_storage": _bool(value("ENABLE_STORAGE_SCALE_DOWN"), True),
        "convert_license": _bool(value("ENABLE_LICENSE_CONVERSION"), True),
        "wait_timeout": _int(value("WAIT_TIMEOUT_SECONDS"), "WAIT_TIMEOUT_SECONDS", 300),
        "notification_topic_id": str(config.get("NOTIFICATION_TOPIC_ID", "")).strip(),
    }


def _clients(config, region):
    signer = signers.get_resource_principals_signer()
    client_config = {"region": region}
    return (
        DatabaseClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY),
        ResourceSearchClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY),
    )


def _notification_client(config, region):
    signer = signers.get_resource_principals_signer()
    return oci.ons.NotificationDataPlaneClient(
        {"region": region}, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY
    )


class _OperationLog(list):
    def __init__(self, prefix):
        super().__init__()
        self.prefix = prefix


def _record(operation_log, level, message, *args):
    if operation_log is None:
        getattr(logger, level)(message, *args)
        return
    prefix = getattr(operation_log, "prefix", "")
    operation_log.append((level, prefix + (message % args if args else message)))


def _emit_operation_log(operation_log):
    for level, message in operation_log:
        getattr(logger, level)(message)


def _reconcile_with_log(client, item, settings, region=None, sequence=1):
    db_id = item.identifier
    db_name = getattr(item, "display_name", None) or db_id
    operation_log = _OperationLog(f"[{region}][{sequence}] " if region else "")
    compartment_id = getattr(item, "compartment_id", None)
    try:
        result = reconcile_database(client, db_id, settings, compartment_id, operation_log, db_name, region)
    except Exception as exc:
        _record(operation_log, "warning", "Unexpected reconcile failure for %s: %s", db_name, exc)
        _record(operation_log, "info", "RECONCILE finish: database=%s outcome=ERROR", db_name)
        result = {
            "detail": {"compartment_id": compartment_id, "ocid": db_id, "region": region},
            "actions": [],
            "error": str(exc),
        }
    return result, operation_log


def _wait_available(client, db_id, settings, operation_log=None, start=False):
    db = client.get_autonomous_database(db_id).data
    if start and db.lifecycle_state == "STOPPED":
        _log_action(db, "start database", settings, operation_log)
        _record(operation_log, "info", "%s %s: start stopped database", _mode(settings), db.display_name)
        if settings["dry_run"]:
            return
        client.start_autonomous_database(db_id)
    if settings["dry_run"]:
        return
    response = client.get_autonomous_database(db_id)
    oci.wait_until(
        client, response, "lifecycle_state", "AVAILABLE",
        max_wait_seconds=settings["wait_timeout"], max_interval_seconds=30,
    )


def _update(client, db, action, details, settings, operation_log=None):
    _wait_available(client, db.id, settings, operation_log, start=True)
    _log_action(db, action, settings, operation_log)
    if not settings["dry_run"]:
        client.update_autonomous_database(
            autonomous_database_id=db.id,
            update_autonomous_database_details=details,
        )
    _wait_available(client, db.id, settings, operation_log)


def _restore_stopped(client, db_id, initial_state, settings, operation_log=None):
    if initial_state != "STOPPED" or settings["dry_run"]:
        return
    db = client.get_autonomous_database(db_id).data
    if db.lifecycle_state == "AVAILABLE":
        _log_action(db, "restore stopped state", settings, operation_log)
        client.stop_autonomous_database(db_id)


def reconcile_database(
    client, db_id, settings, compartment_id=None, operation_log=None, database_name=None, region=None
):
    database_label = database_name or db_id
    _record(operation_log, "info", "RECONCILE start: database=%s", database_label)
    try:
        db = client.get_autonomous_database(db_id).data
    except ServiceError as exc:
        if exc.code == "NotAuthorizedOrNotFound":
            _record(operation_log, "warning", "Unable to find database %s: %s", database_label, exc)
            _record(operation_log, "info", "RECONCILE finish: database=%s outcome=SKIP", database_label)
            return {
                "detail": {"compartment_id": compartment_id, "ocid": db_id, "region": region},
                "actions": [],
                "no_op": "database not found",
            }
        _record(operation_log, "warning", "Unable to retrieve database %s: %s", database_label, exc)
        _record(operation_log, "info", "RECONCILE finish: database=%s outcome=ERROR", database_label)
        return {"detail": {"compartment_id": compartment_id, "ocid": db_id, "region": region}, "actions": [], "error": str(exc)}
    except Exception as exc:
        _record(operation_log, "warning", "Unexpected error retrieving database %s: %s", database_label, exc)
        _record(operation_log, "info", "RECONCILE finish: database=%s outcome=ERROR", database_label)
        return {"detail": {"compartment_id": compartment_id, "ocid": db_id, "region": region}, "actions": [], "error": str(exc)}

    api_workload = str(db.db_workload).upper()
    workload = _canonical_workload(api_workload)
    result = {"detail": {
        "compartment_id": compartment_id,
        "name": db.display_name,
        "ocid": db.id,
        "region": region,
        "workload": workload,
        "api_workload": api_workload,
    }, "actions": []}
    initial_state = db.lifecycle_state
    try:
        if db.is_dedicated or db.is_free_tier or db.is_dev_tier:
            result["no_op"] = "dedicated/free/developer tier"
            _record(operation_log, "info", "SKIP %s (%s)", db.display_name, result["no_op"])
            return result
        if db.role in {"STANDBY", "BACKUP_COPY"} or db.lifecycle_state == "UNAVAILABLE":
            result["no_op"] = f"role/lifecycle: {db.role}/{db.lifecycle_state}"
            _record(operation_log, "info", "SKIP %s (%s)", db.display_name, result["no_op"])
            return result
        if workload not in settings["workloads"]:
            result["no_op"] = f"workload not enabled: {workload}"
            _record(operation_log, "info", "SKIP %s (%s)", db.display_name, result["no_op"])
            return result

        if settings["convert_to_ecpu"] and db.compute_model == "OCPU":
            _record(operation_log, "info", "%s %s: convert OCPU to ECPU", _mode(settings), db.display_name)
            _update(client, db, "convert OCPU to ECPU", UpdateAutonomousDatabaseDetails(compute_model="ECPU"), settings, operation_log)
            result["actions"].append("convert_to_ecpu")
        if settings["reduce_backup_retention"] and db.backup_retention_period_in_days > settings["backup_retention"]:
            _record(operation_log, "info", "%s %s: reduce backup retention to %sd", _mode(settings), db.display_name, settings["backup_retention"])
            _update(client, db, "reduce backup retention", UpdateAutonomousDatabaseDetails(
                backup_retention_period_in_days=settings["backup_retention"]), settings, operation_log)
            result["actions"].append("reduce_backup_retention")
        if settings["reduce_ecpus"] and db.compute_model == "ECPU" and db.compute_count > settings["minimum_ecpus"]:
            _record(operation_log, "info", "%s %s: reduce ECPU count to %s", _mode(settings), db.display_name, settings["minimum_ecpus"])
            _update(client, db, "reduce ECPU count", UpdateAutonomousDatabaseDetails(compute_count=settings["minimum_ecpus"]), settings, operation_log)
            result["actions"].append("reduce_ecpus")
        if settings["scale_storage"] and workload in SUPPORTED_WORKLOADS and db.data_storage_size_in_tbs:
            minimum_storage_gb = max(
                settings["minimum_storage_gb"],
                1024 if workload in {"ADW", "LH"} else 0,
            )
            target_gb = max(
                minimum_storage_gb,
                int(db.allocated_storage_size_in_tbs * 1024 * settings["storage_multiplier"]),
            )
            if workload in {"ADW", "LH"}:
                # ADW and Lakehouse Autonomous AI Databases only accept data storage in TB.
                target_tbs = math.ceil(target_gb / 1024)
                if target_tbs < db.data_storage_size_in_tbs:
                    _record(operation_log, "info", "%s %s: set storage to %sTB and enable autoscaling", _mode(settings), db.display_name, target_tbs)
                    _update(client, db, "scale storage and enable autoscaling", UpdateAutonomousDatabaseDetails(
                        data_storage_size_in_tbs=target_tbs, is_auto_scaling_for_storage_enabled=True), settings, operation_log)
                    result["actions"].append({"scale_storage_tb": target_tbs})
            elif target_gb < int(db.data_storage_size_in_tbs * 1024):
                _record(operation_log, "info", "%s %s: set storage to %sGB and enable autoscaling", _mode(settings), db.display_name, target_gb)
                _update(client, db, "scale storage and enable autoscaling", UpdateAutonomousDatabaseDetails(
                    data_storage_size_in_gbs=target_gb, is_auto_scaling_for_storage_enabled=True), settings, operation_log)
                result["actions"].append({"scale_storage_gb": target_gb})
        if settings["convert_license"] and workload in {"ATP", "ADW", "LH"} and db.license_model == "LICENSE_INCLUDED":
            _record(operation_log, "info", "%s %s: convert license to BYOL / Standard Edition", _mode(settings), db.display_name)
            _update(client, db, "convert license to BYOL / Standard Edition", UpdateAutonomousDatabaseDetails(
                license_model="BRING_YOUR_OWN_LICENSE", database_edition="STANDARD_EDITION"), settings, operation_log)
            result["actions"].append("convert_license_to_byol_standard")
        if not result["actions"]:
            result["no_op"] = "no configured changes required"
            _record(operation_log, "info", "NO-OP %s (%s)", db.display_name, result["no_op"])
        else:
            _record(operation_log, "info", "%s %s: %s", "PLANNED" if settings["dry_run"] else "COMPLETED", db.display_name, _action_names(result["actions"]))
    except (ServiceError, MaximumWaitTimeExceeded) as exc:
        _record(operation_log, "warning", "Failed processing %s: %s", db.display_name, exc)
        result["error"] = str(exc)
    finally:
        try:
            _restore_stopped(client, db_id, initial_state, settings, operation_log)
        except ServiceError as exc:
            result["restore_error"] = str(exc)
            _record(operation_log, "warning", "Failed restoring stopped state for %s: %s", db.display_name, exc)
        outcome = "ERROR" if result.get("error") else "SKIP" if result.get("no_op") else "CHANGED"
        _record(operation_log, "info", "RECONCILE finish: database=%s outcome=%s", db.display_name, outcome)
    return result


def _mode(settings):
    return "DRY-RUN" if settings["dry_run"] else "APPLY"


def _canonical_workload(workload):
    normalized = str(workload or "").upper()
    return WORKLOAD_ALIASES.get(normalized, normalized)


def _log_action(db, action, settings, operation_log=None):
    _record(operation_log, "debug", "%s action: name=%s id=%s action=%s", _mode(settings), db.display_name, db.id, action)


def _action_names(actions):
    names = []
    for action in actions:
        names.extend(action.keys() if isinstance(action, dict) else [action])
    return ", ".join(names)


def _format_action(action):
    if isinstance(action, dict):
        return ", ".join(
            f"{name.replace('_', ' ')}: {value} {'TB' if name.endswith('_tb') else 'GB'}"
            for name, value in action.items()
        )
    return action.replace("_", " ")


def _tabular(value):
    return str(value or "-").replace("\t", " ").replace("\r", " ").replace("\n", " ")


def _format_notification(summary):
    actions = ", ".join(
        f"{name.replace('_', ' ')}={count}" for name, count in sorted(summary["actions"].items())
    ) or "none"
    lines = [
        "AUTONOMOUS DATABASE MAINTENANCE",
        "",
        "SUMMARY",
        f"Mode:\t{summary['mode']}",
        f"Started (UTC):\t{summary['started_at']}",
        f"Completed (UTC):\t{summary['completed_at']}",
        f"Duration:\t{summary['duration_seconds']} seconds",
        f"Regions:\t{', '.join(summary.get('regions', [])) or '-'}",
        f"Databases:\t{summary['database_count']}",
        f"Changed:\t{summary['changed_count']}",
        f"No-op:\t{summary['no_op_count']}",
        f"Errors:\t{summary['error_count']}",
        f"Actions:\t{actions}",
        "",
        "DETAILS",
        "Outcome\tName\tWorkload\tRegion\tCompartment OCID\tDatabase OCID\tActions / reason",
    ]
    for result in summary["results"]:
        detail = result["detail"]
        if result.get("error"):
            outcome, description = "ERROR", result["error"]
        elif result.get("no_op"):
            outcome, description = "NO-OP", result["no_op"]
        else:
            outcome = "PLANNED" if summary["mode"] == "DRY-RUN" else "CHANGED"
            description = ", ".join(_format_action(action) for action in result["actions"])
            if result.get("restore_error"):
                description += f"; restore error: {result['restore_error']}"
        lines.append("\t".join(_tabular(value) for value in (
            outcome,
            detail.get("name"),
            detail.get("workload"),
            detail.get("region"),
            detail.get("compartment_id"),
            detail.get("ocid"),
            description,
        )))
    return "\n".join(lines)


def _summary(results, settings, started_at, completed_at):
    action_counts = {}
    no_op_count = 0
    error_count = 0
    for result in results:
        if result.get("error"):
            error_count += 1
        if result.get("no_op"):
            no_op_count += 1
        for action in result.get("actions", []):
            for name in action.keys() if isinstance(action, dict) else [action]:
                action_counts[name] = action_counts.get(name, 0) + 1
    summary = {
        "mode": _mode(settings),
        "regions": settings["regions"],
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
        "database_count": len(results),
        "changed_count": len(results) - no_op_count - error_count,
        "no_op_count": no_op_count,
        "error_count": error_count,
        "actions": action_counts,
        "results": results,
    }
    logger.info(
        "%s complete: databases=%s changed=%s no_op=%s errors=%s actions=%s",
        summary["mode"], summary["database_count"], summary["changed_count"],
        summary["no_op_count"], summary["error_count"], action_counts or "none",
    )
    return summary


def _publish_summary(notification_client, settings, summary):
    if not settings["notification_topic_id"] or notification_client is None:
        return
    try:
        notification_client.publish_message(
            topic_id=settings["notification_topic_id"],
            message_details=oci.ons.models.MessageDetails(
                title="Autonomous Database Maintenance Summary",
                body=_format_notification(summary),
            ),
            message_type="RAW_TEXT",
        )
        logger.info("Published maintenance summary to notification topic")
    except Exception:
        logger.exception("Unable to publish maintenance summary to notification topic")


def _search_all_resources(search, search_details):
    resources = []
    page = None
    while True:
        kwargs = {"search_details": search_details, "limit": 1000}
        if page:
            kwargs["page"] = page
        response = search.search_resources(**kwargs)
        resources.extend(response.data.items)
        page = (getattr(response, "headers", {}) or {}).get("opc-next-page")
        if not page:
            return resources


def _process_region(client, search, settings, region):
    query = 'query autonomousdatabase resources return allAdditionalFields where (workloadType="' + '" || workloadType="'.join(settings["workloads"]) + '")'
    logger.debug("Resource search query: region=%s query=%s", region, query)
    resources = _search_all_resources(
        search,
        StructuredSearchDetails(type="Structured", query=query),
    )
    logger.info(
        "%s starting: region=%s databases=%s workloads=%s",
        _mode(settings), region, len(resources), ",".join(settings["workloads"]),
    )
    with ThreadPoolExecutor(max_workers=settings["threads"], thread_name_prefix="adb") as executor:
        futures = {
            executor.submit(_reconcile_with_log, client, item, settings, region, index + 1): index
            for index, item in enumerate(resources)
        }
        results = [None] * len(resources)
        for future in as_completed(futures):
            index = futures[future]
            results[index], operation_log = future.result()
            _emit_operation_log(operation_log)
    return results


def handler(ctx, data: io.BytesIO = None):
    started_at = datetime.now(timezone.utc)
    payload = {}
    if data and data.getvalue():
        payload = json.loads(data.getvalue().decode("utf-8"))
    config = dict(os.environ)
    try:
        config.update(ctx.Config())
    except Exception:
        pass
    settings = load_config(config, payload)
    configure_logging(config, payload)
    if settings["notification_topic_id"]:
        notification_client = _notification_client(
            config, _notification_region(settings["notification_topic_id"])
        )
    results = []
    for region in settings["regions"]:
        client, search = _clients(config, region)
        results.extend(_process_region(client, search, settings, region))
    completed_at = datetime.now(timezone.utc)
    summary = _summary(results, settings, started_at, completed_at)
    if settings["notification_topic_id"]:
        _publish_summary(notification_client, settings, summary)
    return json.dumps(summary, indent=2, sort_keys=True)
