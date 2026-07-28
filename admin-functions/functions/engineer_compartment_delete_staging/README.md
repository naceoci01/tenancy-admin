# Engineer Compartment Delete Staging

This nightly OCI Function moves expired engineer compartments from the
configured engineer root to a delete-staging compartment. It never deletes a
compartment or its resources.

For shared Fn CLI setup and scheduler guidance, see the
[OCI Administration Functions overview](../../README.md).

## Behavior

The function uses the OCI pagination API to list active direct children of
`ENGINEER_ROOT_COMPARTMENT_OCID`. A compartment is moved only when its
`Oracle-Tags.DeleteCompartmentAfter` defined tag is an ISO-8601 timestamp that
is earlier than the current UTC time. Missing, future, and malformed tags are
left in place; malformed tag values are reported in the invocation result.
For a real run, the function submits each OCI move request and returns its
work-request OCID in the invocation result. OCI performs the move
asynchronously; use the work-request OCID to inspect its final state. This
keeps a long-running compartment move from exceeding the function invocation
timeout.

If OCI rejects a move with HTTP 409 (for example, because a compartment with
the same name already exists in delete staging), the invocation remains
successful and reports that item as `move_conflict`, including OCI's status,
code, message, and request ID when available. Any other move failure for one
candidate is reported as `move_failed` and
does not stop moves for the remaining candidates. Function initialization,
authentication, and compartment-listing failures still fail the invocation.

## Configuration

| Name | Required | Default | Description |
| --- | --- | --- | --- |
| `ENGINEER_ROOT_COMPARTMENT_OCID` | Yes | — | Parent of direct-child engineer compartments. |
| `DELETE_STAGING_COMPARTMENT_OCID` | Yes | — | Destination parent for expired compartments. |
| `DRY_RUN` | No | `true` | Reports moves without changing OCI state. |
| `LOG_LEVEL` | No | `INFO` | Python logging level. |
| `DEPENDENCY_LOG_LEVEL` | No | `WARNING` | OCI SDK and dependency logging level. |

Use `{}` as the normal Resource Scheduler request body. For controlled runs,
the request may override `engineer_root_compartment_ocid`,
`delete_staging_compartment_ocid`, `dry_run`, or `log_level`.

## Permissions

Grant the function resource principal permission to inspect compartments in the
tenancy and manage compartments under both the engineer root and delete-staging
parents. Scope the policy to the function principal and review it in the target
tenancy before deployment.

## Deployment

Deploy from this directory and configure a nightly OCI Resource Scheduler job
to invoke it with `{}`. Keep `DRY_RUN=true` for the first scheduled run.

```bash
fn deploy --app <FUNCTION_APP_NAME>
```

## Tests

Run the focused tests from the `admin-functions` directory:

```bash
python3 -m unittest tests.test_delete_staging
```

The tests use an in-memory gateway and do not call OCI.
