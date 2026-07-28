# Engineer Quota Updater

This OCI Function is a scheduled, quota-only reconciler for engineer
compartments. It lists active direct children of the configured engineer root,
renders tenancy-wide quota policies, and creates or updates those policies so
they match the current desired state.

Compartment creation and lifecycle tagging belong to
`engineer_compartment_lifecycle`. This function never creates, updates, moves,
or deletes compartments.

For shared Fn CLI setup and scheduler guidance, see the
[OCI Administration Functions overview](../../README.md).

## Invocation model

The OCI Resource Scheduler invokes this function on a schedule. No input is
required; `{}` is the normal request body. An optional JSON object can override
configuration for a controlled run, including the quota definition.

Example scheduled request body:

```json
{}
```

Example dry-run request with delete-mark exclusion enabled:

```json
{
  "dry_run": true,
  "exclude_delete_marked_compartments": true
}
```

## Configuration

| Function configuration | Payload override | Default | Description |
| --- | --- | --- | --- |
| `ENGINEER_ROOT_COMPARTMENT_OCID` | `engineer_root_compartment_ocid` | — | Engineer compartment parent. |
| `DRY_RUN` | `dry_run` | `true` | Report changes without writing quota policies. |
| `LOG_LEVEL` | `log_level` | `INFO` | Function log level. |
| `DEPENDENCY_LOG_LEVEL` | — | `WARNING` | OCI SDK/dependency log level. |
| `EXCLUDE_DELETE_MARKED_COMPARTMENTS` | `exclude_delete_marked_compartments` | `false` | Omit compartments carrying `Oracle-Tags.DeleteCompartmentAfter`. |
| `QUOTA_CONFIG_JSON` | `quota_config_json` | bundled default | Complete quota policy definition. |

Configuration values belong in the function configuration for normal scheduled
operation. Payload overrides are intended for testing, temporary policy
changes, or a one-off scheduled invocation.

## Quota configuration payload

`quota_config_json` replaces the complete bundled quota definition; it is not
a partial merge. It may be supplied as a JSON array or as a JSON-encoded string
when configured as `QUOTA_CONFIG_JSON`.

Each policy has `area`, `quota_name`, `description`, and `statements`. Each
statement has `scope` (`root` or `per_engineer`), `operation` (`set` or `zero`),
and `service`. `set` statements also require `quota` and `value`; `zero`
statements may omit `quota` to zero the service quota broadly.

The complete example is in
[`payload-quota-config-example.json`](payload-quota-config-example.json).
The existing quota payload shape remains compatible with the renamed function.

## Delete-marked compartments

The lifecycle function marks a compartment with the defined tag:

```text
Namespace: Oracle-Tags
Key:       DeleteCompartmentAfter
```

The function always lists active direct children of the engineer root using the
OCI pagination API. When `EXCLUDE_DELETE_MARKED_COMPARTMENTS=true`, it omits
children carrying this tag from all per-engineer quota statements. Root-level
quota statements are unchanged. The tag's timestamp is not interpreted here;
its presence is the exclusion signal. When the option is false, all active
direct children are included.

## Behavior and idempotency

The function compares each rendered policy's description and complete ordered
statement list with the existing tenancy policy. It creates missing policies,
updates changed policies, and leaves unchanged policies alone. A run is safe to
retry and does not maintain local state.

The function does not create, update, move, or delete compartments. A quota
statement is rendered only for an active direct-child compartment that exists
under the configured engineer root.

## Resource-principal permissions

The function needs permission to inspect compartments in the tenancy and read
and manage quotas in the tenancy. It does not need Identity Domains, user, or
compartment-management permissions.

Example policy text is in
[`policy-examples.md`](policy-examples.md). Replace placeholders and review
scope against the tenancy's current OCI policy syntax before applying it.

## Deploy and update the schedule

Deploy from this directory:

```bash
cd admin-functions/functions/engineer_quota_updater
fn deploy --app <FUNCTION_APP_NAME>
```

The deployed function name is `engineer-quota-updater`. Update the OCI Resource
Scheduler target from the old `engineer-compartment-reconciler` function to the
new function OCID. The schedule can continue sending `{}` if all settings are
in function configuration.

If the schedule currently sends the old payload, the existing keys remain
valid. The new optional key is:

```json
"exclude_delete_marked_compartments": true
```

Keep `DRY_RUN=true` for the first deployment and scheduled invocation. Review
the JSON result and logs, then set it to `false` in function configuration or
the scheduled payload.

## Tests

Run the focused tests from the `admin-functions` directory:

```bash
python3 -m unittest \
  tests.test_quota_updater \
  tests.test_quota_updater_config \
  tests.test_quota_updater_logging \
  tests.test_quota_rendering
```

The tests use an in-memory gateway and do not call OCI.
