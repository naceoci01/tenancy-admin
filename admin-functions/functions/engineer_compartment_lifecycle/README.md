# Engineer Compartment Lifecycle

This OCI Function reconciles an engineer compartment in response to OCI Events
for users in the configured Identity Domain. Every user in this domain may have
a compartment; Identity Domain groups and IAM policies determine whether the
user can access it.

The function is **event-driven**. It creates or repairs a compartment for an active
user and marks a compartment for delayed deletion when a user is inactive or
deleted. It does not move, stop, clean, or delete resources. A separate
scheduled process can later move compartments whose deletion deadline has
passed to a staging area.

For shared Fn CLI setup and OCI Events guidance, see the
[OCI Administration Functions overview](../../README.md).

## Invocation model

OCI Events invokes the function with one CloudEvents-style JSON payload. The
function does not accept a business-operation payload separate from the event.
Unsupported or incomplete events return a successful no-op so a broad Events
rule can safely target the function.

Supported event labels are:

- `User - Create`
- `User - Update`
- `User - Activate`
- `User - Deactivate`
- `User - Delete`

The implementation also accepts the corresponding Identity Control Plane event
names, including `CreateUser`, `UpdateUser`, `UpdateUserState`,
`ActivateUser`, `DeactivateUser`, and `DeleteUser` variants.

For reliable coverage, create an OCI Events rule for user creation, user
updates, user state changes, activation, deactivation, and deletion in the
configured Identity Domain. The exact event display names can vary by OCI
Events console version; verify the emitted `eventType` values in the tenancy
and include the matching values in the rule.

## Configuration

| Name | Required | Default | Description |
| --- | --- | --- | --- |
| `DOMAIN_ID` | Yes | — | Identity Domain OCID containing the users. |
| `ENGINEER_ROOT_COMPARTMENT_OCID` | Yes | — | Parent for direct-child engineer compartments. |
| `DELETE_GRACE_PERIOD_HOURS` | No | `72` | Hours from the OCI event time until the compartment is eligible for staging. |
| `DRY_RUN` | No | `false` | The declared Function default applies changes; set it to `true` for a non-mutating validation run. |
| `LOG_LEVEL` | No | `INFO` | Python logging level. |
| `DEPENDENCY_LOG_LEVEL` | No | `WARNING` | OCI SDK and dependency logging level. |

Invocation payload overrides use lower-case names, for example:

```json
{
  "dry_run": true,
  "delete_grace_period_hours": 72
}
```

The production event body must remain the OCI Events event itself. Configuration
overrides are mainly useful for local tests and controlled invocations.

## Lifecycle behavior

The compartment name is the portion of the user name before the first `@`.
Username changes are not handled as a normal workflow.

For an active user, the function creates the direct-child compartment if it is
missing. Existing compartments are left unchanged unless they carry the
deletion tag, in which case the tag is removed.

For an inactive or deleted user, the function adds this defined tag:

```text
Namespace: Oracle-Tags
Key:       DeleteCompartmentAfter
Value:     2026-07-30T12:00:00Z
```

The value is an ISO-8601 UTC timestamp calculated from the OCI event time plus
`DELETE_GRACE_PERIOD_HOURS`. If the tag already exists, repeated events do not
extend the deadline. Other defined tags are preserved.

Delete events use the username in the event because the Identity Domain lookup
may no longer find the deleted user. A missing matching compartment is a
successful no-op.

## Idempotency and failures

The function converges on the desired compartment and tag state. Repeated OCI
Events deliveries are safe. OCI Functions or Events may retry a failed
invocation; the function does not maintain local state and relies on OCI as the
source of truth.

The function does not perform staging. A scheduled staging function should
independently re-check the deletion tag and current user state before moving a
compartment.

## Resource-principal permissions

The function needs permission to:

- read the configured Identity Domain and users;
- inspect compartments in the tenancy;
- manage compartments under the engineer root compartment.

The function does not need quota-management or delete-staging permissions.
Grant permissions to the specific function principal and review the policy
scope against the tenancy's current OCI policy syntax.

## Deploy and configure

Deploy from this directory:

```bash
cd admin-functions/functions/engineer_compartment_lifecycle
fn deploy --app <FUNCTION_APP_NAME>
```

The checked-in `func.yaml` currently defaults to `DRY_RUN=false`. Before
attaching a production Events rule, explicitly set it to `true` for a
non-mutating test. Send a representative OCI Events payload, inspect the JSON
result and function logs, then set it to `false` only after confirming the
target compartment and tag behavior.

## Local tests

Run the focused tests from the `admin-functions` directory:

```bash
cd admin-functions
python3 -m unittest tests.test_lifecycle
```

The tests use an in-memory gateway and do not call OCI.
