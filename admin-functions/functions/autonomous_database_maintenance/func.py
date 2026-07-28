import io
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor

import oci
from oci.auth import signers
from oci.database import DatabaseClient
from oci.database.models import UpdateAutonomousDatabaseDetails
from oci.exceptions import MaximumWaitTimeExceeded, ServiceError
from oci.resource_search import ResourceSearchClient
from oci.resource_search.models import StructuredSearchDetails

logger = logging.getLogger("autonomous_database_maintenance")
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


def load_config(config, payload):
    value = lambda name, default=None: payload.get(name.lower(), config.get(name, default))
    workloads = value("WORKLOAD_TYPES", "OLTP,JSON,DW,AJD,APEX")
    workloads = [item.strip().upper() for item in str(workloads).split(",") if item.strip()]
    if not workloads:
        raise ValueError("WORKLOAD_TYPES must contain at least one workload")
    return {
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
    }


def _clients(config):
    signer = signers.get_resource_principals_signer()
    client_config = {}
    region = config.get("OCI_REGION") or config.get("REGION")
    if region:
        client_config["region"] = region
    return (
        DatabaseClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY),
        ResourceSearchClient(client_config, signer=signer, retry_strategy=oci.retry.DEFAULT_RETRY_STRATEGY),
    )


def _wait_available(client, db_id, settings, start=False):
    db = client.get_autonomous_database(db_id).data
    if start and db.lifecycle_state == "STOPPED":
        logger.info("%s %s: start stopped database", _mode(settings), db.display_name)
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


def _update(client, db, details, settings):
    _wait_available(client, db.id, settings, start=True)
    if not settings["dry_run"]:
        client.update_autonomous_database(
            autonomous_database_id=db.id,
            update_autonomous_database_details=details,
        )
    _wait_available(client, db.id, settings)


def _restore_stopped(client, db_id, initial_state, settings):
    if initial_state != "STOPPED" or settings["dry_run"]:
        return
    db = client.get_autonomous_database(db_id).data
    if db.lifecycle_state == "AVAILABLE":
        client.stop_autonomous_database(db_id)


def reconcile_database(client, db_id, settings):
    db = client.get_autonomous_database(db_id).data
    result = {"detail": {"name": db.display_name, "ocid": db.id, "workload": db.db_workload}, "actions": []}
    initial_state = db.lifecycle_state
    try:
        if db.is_dedicated or db.is_free_tier or db.is_dev_tier:
            result["no_op"] = "dedicated/free/developer tier"
            logger.info("SKIP %s (%s)", db.display_name, result["no_op"])
            return result
        if db.role in {"STANDBY", "BACKUP_COPY"} or db.lifecycle_state == "UNAVAILABLE":
            result["no_op"] = f"role/lifecycle: {db.role}/{db.lifecycle_state}"
            logger.info("SKIP %s (%s)", db.display_name, result["no_op"])
            return result
        if str(db.db_workload).upper() not in settings["workloads"]:
            result["no_op"] = f"workload not enabled: {db.db_workload}"
            logger.info("SKIP %s (%s)", db.display_name, result["no_op"])
            return result

        if settings["convert_to_ecpu"] and db.compute_model == "OCPU":
            logger.info("%s %s: convert OCPU to ECPU", _mode(settings), db.display_name)
            _update(client, db, UpdateAutonomousDatabaseDetails(compute_model="ECPU"), settings)
            result["actions"].append("convert_to_ecpu")
        if settings["reduce_backup_retention"] and db.backup_retention_period_in_days > settings["backup_retention"]:
            logger.info("%s %s: reduce backup retention to %sd", _mode(settings), db.display_name, settings["backup_retention"])
            _update(client, db, UpdateAutonomousDatabaseDetails(
                backup_retention_period_in_days=settings["backup_retention"]), settings)
            result["actions"].append("reduce_backup_retention")
        if settings["reduce_ecpus"] and db.compute_model == "ECPU" and db.compute_count > settings["minimum_ecpus"]:
            logger.info("%s %s: reduce ECPU count to %s", _mode(settings), db.display_name, settings["minimum_ecpus"])
            _update(client, db, UpdateAutonomousDatabaseDetails(compute_count=settings["minimum_ecpus"]), settings)
            result["actions"].append("reduce_ecpus")
        if settings["scale_storage"] and db.db_workload in {"OLTP", "AJD", "APEX"} and db.data_storage_size_in_tbs:
            target = max(settings["minimum_storage_gb"], int(db.allocated_storage_size_in_tbs * 1024 * settings["storage_multiplier"]))
            if target < int(db.data_storage_size_in_tbs * 1024):
                logger.info("%s %s: set storage to %sGB and enable autoscaling", _mode(settings), db.display_name, target)
                _update(client, db, UpdateAutonomousDatabaseDetails(
                    data_storage_size_in_gbs=target, is_auto_scaling_for_storage_enabled=True), settings)
                result["actions"].append({"scale_storage_gb": target})
        if settings["convert_license"] and db.db_workload in {"OLTP", "DW"} and db.license_model == "LICENSE_INCLUDED":
            logger.info("%s %s: convert license to BYOL / Standard Edition", _mode(settings), db.display_name)
            _update(client, db, UpdateAutonomousDatabaseDetails(
                license_model="BRING_YOUR_OWN_LICENSE", database_edition="STANDARD_EDITION"), settings)
            result["actions"].append("convert_license_to_byol_standard")
        if not result["actions"]:
            result["no_op"] = "no configured changes required"
            logger.info("NO-OP %s (%s)", db.display_name, result["no_op"])
        else:
            logger.info("%s %s: %s", "PLANNED" if settings["dry_run"] else "COMPLETED", db.display_name, _action_names(result["actions"]))
    except (ServiceError, MaximumWaitTimeExceeded) as exc:
        logger.warning("Failed processing %s: %s", db.display_name, exc)
        result["error"] = str(exc)
    finally:
        try:
            _restore_stopped(client, db_id, initial_state, settings)
        except ServiceError as exc:
            result["restore_error"] = str(exc)
    return result


def _mode(settings):
    return "DRY-RUN" if settings["dry_run"] else "APPLY"


def _action_names(actions):
    names = []
    for action in actions:
        names.extend(action.keys() if isinstance(action, dict) else [action])
    return ", ".join(names)


def _log_summary(results, settings):
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
    logger.info(
        "%s complete: databases=%s changed=%s no_op=%s errors=%s actions=%s",
        _mode(settings), len(results), len(results) - no_op_count - error_count,
        no_op_count, error_count, action_counts or "none",
    )


def handler(ctx, data: io.BytesIO = None):
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
    client, search = _clients(config)
    query = 'query autonomousdatabase resources return allAdditionalFields where (workloadType="' + '" or workloadType="'.join(settings["workloads"]) + '")'
    resources = search.search_resources(
        search_details=StructuredSearchDetails(type="Structured", query=query), limit=1000).data.items
    ids = [item.identifier for item in resources]
    logger.info("%s starting: databases=%s workloads=%s", _mode(settings), len(ids), ",".join(settings["workloads"]))
    with ThreadPoolExecutor(max_workers=settings["threads"], thread_name_prefix="adb") as executor:
        results = list(executor.map(lambda db_id: reconcile_database(client, db_id, settings), ids))
    _log_summary(results, settings)
    return json.dumps({"database_count": len(results), "results": results}, indent=2, sort_keys=True)
