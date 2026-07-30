# OCI Administration Functions

Independently deployable OCI Functions for recurring tenancy administration.
The lifecycle function is invoked by OCI Events; the other functions are
normally invoked by OCI Resource Scheduler. Each function owns its runtime
configuration, payload contract, IAM guidance, and deployment instructions.

## Function set

| Function | Trigger | Summary |
| --- | --- | --- |
| [`engineer_compartment_lifecycle`](functions/engineer_compartment_lifecycle/README.md) | OCI Events | Creates an active user's engineer compartment or marks an inactive/deleted user's compartment for delayed staging. |
| [`engineer_compartment_delete_staging`](functions/engineer_compartment_delete_staging/README.md) | Resource Scheduler | Moves engineer compartments whose deletion deadline has passed into a staging compartment; it never deletes the compartment or its contents. |
| [`engineer_quota_updater`](functions/engineer_quota_updater/README.md) | Resource Scheduler | Reconciles tenancy quota policies for direct-child engineer compartments. |
| [`autonomous_database_maintenance`](functions/autonomous_database_maintenance/README.md) | Resource Scheduler | Reconciles selected Autonomous Database cost and capacity settings across configured regions and workloads; it supports dry runs, per-database results, and an optional OCI Notifications summary. |

The engineer-compartment functions form a workflow: lifecycle marks a
compartment with `Oracle-Tags.DeleteCompartmentAfter`, delete staging moves it
after the deadline, and the quota updater can exclude marked compartments.

## Shared prerequisites

- OCI CLI and Fn CLI configured for the target region.
- An OCI Function App and an OCIR repository accessible to the deploying
  principal.
- A Function resource principal with the least-privilege policies required by
  the chosen function. See that function's README for its IAM scope.
- An OCI Events rule for `engineer_compartment_lifecycle`, or an OCI Resource
  Scheduler schedule for the scheduled functions.
- An OCI Notifications topic and publish permission only when
  `autonomous_database_maintenance` is configured with `NOTIFICATION_TOPIC_ID`.

OCI user credentials, key files, fingerprints, and tenancy OCIDs are not used
by function code at runtime; the functions use OCI resource principals.

## Deploy a function

Create the Function App and configure an Fn context for its region and OCIR
repository. Then deploy from the individual function directory:

```bash
cd admin-functions/functions/engineer_quota_updater
fn deploy --app <FUNCTION_APP_NAME>
```

Use `fn list functions <FUNCTION_APP_NAME>` to find the deployed function. For
a scheduled function, create the Resource Scheduler target only after a
controlled invocation and IAM review. `{}` is the normal request body unless
the function README documents a payload override.

For functions whose `func.yaml` currently sets `DRY_RUN=true`, retain that
setting for the first invocation and review the result before enabling writes.
The lifecycle function currently defaults to `DRY_RUN=false`; explicitly set it
to `true` before its first production event-rule test if you need a non-mutating
validation run.

## Test locally

The test suite requires Python 3.11 or newer and uses test doubles rather than
calling OCI:

```bash
cd admin-functions
python3 -m unittest discover -s tests
```

See each function README for focused test commands and function-specific
configuration, payloads, policy statements, and verification steps.
