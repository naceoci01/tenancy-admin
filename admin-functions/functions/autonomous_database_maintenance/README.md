# Autonomous Database Maintenance

This scheduled OCI Function reconciles selected Autonomous Database cost and
capacity settings. It uses resource-principal authentication, discovers
Autonomous Databases through Resource Search, and applies only the enabled
maintenance operations.

The function does not read, add, or modify schedule tags. Scheduling is
external: deploy the function, grant its resource principal the required
permissions, and create an OCI Resource Scheduler schedule.

For shared Fn CLI setup and scheduler guidance, see the
[OCI Administration Functions overview](../../README.md).

## Invocation model

OCI Resource Scheduler normally invokes this function with `{}`. A JSON
payload can override the documented lowercase configuration keys for one
controlled run.

Example dry-run request body:

```json
{
  "dry_run": true,
  "regions": "us-phoenix-1,us-ashburn-1",
  "workload_types": "ATP,ADW",
  "minimum_ecpus": 2
}
```

The response contains an execution summary with UTC start and completion
times, per-outcome counts, action totals, and a result for each discovered
database. Each database result includes its name, compartment OCID, database
OCID, canonical workload, region, actions, and any no-op reason or error.

## Configuration

| Function configuration | Payload override | Default | Description |
| --- | --- | --- | --- |
| `REGIONS` | `regions` | current function region | Comma-separated OCI regions to process. A blank value uses the function resource principal's region. |
| `WORKLOAD_TYPES` | `workload_types` | `ATP,ADW,JSON,APEX,LH` | Comma-separated workloads to discover and reconcile. |
| `DRY_RUN` | `dry_run` | `true` | Report planned changes without updating OCI. |
| `ENABLE_ECPU_CONVERSION` | `enable_ecpu_conversion` | `true` | Convert OCPU databases to ECPU. |
| `ENABLE_BACKUP_RETENTION` | `enable_backup_retention` | `true` | Reduce retention above `BACKUP_RETENTION_DAYS`. |
| `BACKUP_RETENTION_DAYS` | `backup_retention_days` | `14` | Target backup-retention period in days. |
| `ENABLE_COMPUTE_SCALE_DOWN` | `enable_compute_scale_down` | `true` | Reduce ECPU count above `MINIMUM_ECPUS`. |
| `MINIMUM_ECPUS` | `minimum_ecpus` | `2` | Lowest ECPU count the function sets. |
| `ENABLE_STORAGE_SCALE_DOWN` | `enable_storage_scale_down` | `true` | Reduce storage and enable storage autoscaling when the calculated target is lower. |
| `STORAGE_MULTIPLIER` | `storage_multiplier` | `2` | Multiplier applied to reported allocated storage when calculating the storage target. |
| `MINIMUM_STORAGE_GB` | `minimum_storage_gb` | `20` | General lower bound for a storage target in GB. ADW and LH have an effective 1-TB lower bound; their targets are rounded up and sent to OCI in TB. |
| `ENABLE_LICENSE_CONVERSION` | `enable_license_conversion` | `true` | Convert Included License ATP, ADW, and LH databases to BYOL / Standard Edition. |
| `THREADS` | `threads` | `5` | Concurrent database reconciliation workers per region. |
| `WAIT_TIMEOUT_SECONDS` | `wait_timeout_seconds` | `300` | Maximum time to wait for an update or started database to become available. |
| `LOG_LEVEL` | `log_level` | `INFO` | Function log level. |
| `DEPENDENCY_LOG_LEVEL` | — | `WARNING` | OCI SDK and dependency log level. |
| `NOTIFICATION_TOPIC_ID` | — | empty | Optional OCI Notifications topic OCID for one execution-summary message. |

`WORKLOAD_TYPES` accepts `ATP`, `ADW`, `JSON`, `APEX`, and `LH`. Legacy API
aliases `OLTP`, `DW`, and `AJD` are normalized to `ATP`, `ADW`, and `JSON`.
All listed payload overrides use lowercase names. Configuration values are the
normal choice for scheduled operation; payload overrides are useful for
testing and one-off controlled invocations.

## Maintenance behavior

The function skips dedicated, free-tier, developer-tier, standby, backup-copy,
unavailable, and non-selected-workload databases. A database already matching
the enabled targets is reported as a no-op.

For each eligible database, the function can convert OCPU to ECPU, lower
backup retention, lower ECPU count, calculate a lower storage target and enable
storage autoscaling, and convert an Included License database to BYOL / Standard
Edition where that conversion is enabled for its workload. ADW and LH storage
targets never fall below 1 TB; ADW and Lakehouse (LH) updates use OCI's TB
storage field.
The function starts a stopped database only when
a real update is required and returns it to its original stopped state after
processing.

Resource Search is paginated independently in every configured region. Results
are returned in discovery order, even though database work is performed
concurrently.

## Notifications and logging

When `NOTIFICATION_TOPIC_ID` is configured, the function derives the topic's
region from its OCI topic OCID and publishes one plain-text execution summary to
that topic. The message contains a `SUMMARY` section with UTC timestamps,
duration, counts, and action totals, then a tab-separated `DETAILS` table with
each database's name, workload, compartment OCID, database OCID, region, and
outcome. A notification-delivery failure is logged and does not fail the
maintenance run.

Normal `INFO` logs show a dry-run/apply banner, an end-of-run summary, and one
contiguous start/action/finish block per database after its reconciliation
worker completes. OCI SDK and circuit-breaker logs default to `WARNING`; set
`DEPENDENCY_LOG_LEVEL=DEBUG` alongside `LOG_LEVEL=DEBUG` for detailed SDK
diagnostics. `DRY_RUN=true` is shown as `DRY-RUN` so planned changes are easy to
distinguish from applied changes.

## Resource-principal permissions

Grant the function resource principal permission to use Resource Search and to
read, update, start, and stop Autonomous Databases in the relevant database
compartments. If notifications are enabled, also grant it permission to publish
to the configured Notifications topic. Scope permissions to the required
resources and regions where possible, and review the policy syntax in the
target tenancy before deployment.

## Deployment

Deploy from this directory:

```bash
cd admin-functions/functions/autonomous_database_maintenance
fn deploy --app <FUNCTION_APP_NAME>
```

Keep `DRY_RUN=true` for the first deployment and scheduled invocation. Review
the response, logs, and—when configured—the notification summary before
setting it to `false`. Create or update the OCI Resource Scheduler target to
invoke the deployed function with `{}` once the function configuration is set.

## Tests

Run the focused tests from this function directory:

```bash
python3 -m unittest test_func
```

The tests stub OCI clients and do not call OCI.
