# Autonomous Database Maintenance

One scheduled OCI Function consolidating the former ADW conversion, ATP scale-
down, and ADB conversion scripts. It uses resource-principal authentication,
discovers Autonomous Databases through Resource Search, and applies only the
enabled maintenance operations.

This function does not read, add, or modify schedule tags. Scheduling is
external: deploy the function, grant the function resource principal the
required permissions, and create the OCI Resource Scheduler schedule.

For shared Fn CLI setup and scheduler guidance, see the
[OCI Administration Functions overview](../../README.md).

## Configurable operations

| Config | Default | Operation |
| --- | ---: | --- |
| `ENABLE_ECPU_CONVERSION` | `true` | Convert OCPU databases to ECPU |
| `ENABLE_BACKUP_RETENTION` | `true` | Lower retention above `BACKUP_RETENTION_DAYS` |
| `ENABLE_COMPUTE_SCALE_DOWN` | `true` | Lower ECPU count above `MINIMUM_ECPUS` |
| `ENABLE_STORAGE_SCALE_DOWN` | `true` | Set serverless OLTP storage to usage × multiplier and enable autoscaling |
| `ENABLE_LICENSE_CONVERSION` | `true` | Convert Included license to BYOL / Standard Edition |

Additional settings include `DRY_RUN`, `BACKUP_RETENTION_DAYS`,
`MINIMUM_ECPUS`, `STORAGE_MULTIPLIER`, `MINIMUM_STORAGE_GB`, `WORKLOAD_TYPES`,
`THREADS`, `WAIT_TIMEOUT_SECONDS`, `LOG_LEVEL`, and `DEPENDENCY_LOG_LEVEL`.
Invocation payload keys use lowercase names and override function configuration
for that invocation.

The function skips dedicated, free-tier, developer-tier, standby, backup-copy,
unavailable, and non-selected workload databases. Stopped databases are started
only when a real update is needed and are returned to their original stopped
state after processing.

## Deployment

```bash
cd admin-functions/functions/autonomous_database_maintenance
fn deploy --app <FUNCTION_APP_NAME>
```

Deploy with `DRY_RUN=true`, invoke it, review the result, then set `DRY_RUN` to
`false` when the selected operations are approved. The function requires IAM
permissions for Resource Search and the Autonomous Database read/update/start/
stop operations it performs.

## Logging

Normal `INFO` logs show a dry-run/apply banner, database skips, planned or
completed actions, errors, and an end-of-run summary. OCI SDK and circuit-
breaker logs default to `WARNING`; set `DEPENDENCY_LOG_LEVEL=DEBUG` alongside
`LOG_LEVEL=DEBUG` when detailed SDK diagnostics are needed. `DRY_RUN=true` is
shown as `DRY-RUN` so planned changes are easy to distinguish from applied changes.

## Invocation

Use `{}` as the normal Resource Scheduler body. Lowercase payload keys override
their function-configuration equivalents for one invocation; for example:

```json
{
  "dry_run": true,
  "minimum_ecpus": 2,
  "workload_types": "OLTP,DW"
}
```

The function uses resource principals and requires Resource Search plus
Autonomous Database read, update, start, and stop permissions. Scope those
permissions to the relevant database compartments where possible.
