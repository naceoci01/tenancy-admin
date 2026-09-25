# Dynamic Group Lifecycle

This weekly OCI Resource Scheduler function finds dynamic groups not referenced
by any loaded IAM policy, marks them for deletion after two weeks, and removes
the mark if a group becomes referenced again. It uses
`oci-policy-analysis==6.5.1` to inventory policies and Identity Domains and to
query the resulting dynamic-group data with `{"in_use": false}`.

OCI Functions run under a resource principal (not a compute instance
principal); the package is initialized with that resource principal so the
scheduled function follows the same authentication model as the other
functions in this repository.

## Configuration

| Name | Default | Description |
| --- | --- | --- |
| `DELETE_EXPIRED_DYNAMIC_GROUPS` | `false` | Set to `true` to delete groups that remain unused past their tag deadline. |
| `LOG_LEVEL` | `INFO` | Function log level. INFO includes per-group activity. |
| `DEPENDENCY_LOG_LEVEL` | `WARNING` | OCI SDK, `oci-policy-analysis`, and dependency log level. |
| `NOTIFICATION_TOPIC_ID` | inherited from the application | OCI Notifications topic OCID for one detailed lifecycle report per run. |

The lifecycle tag is the freeform tag `DeleteDynamicGroupAfter`, with an
ISO-8601 UTC timestamp. A newly unused group is tagged for 14 days ahead.
Repeated weekly runs preserve a valid existing deadline, so a group is eligible
for deletion after it has continuously remained unused for two weeks. Invalid
deadlines are replaced with a fresh 14-day deadline.

Tagging and untagging always occur. No deletion occurs unless
`DELETE_EXPIRED_DYNAMIC_GROUPS=true`. Use `{}` as the normal scheduler body;
`delete_expired_dynamic_groups` and `log_level` may be overridden in a
controlled invocation.

## Permissions

Grant the function resource principal read access needed by
`oci-policy-analysis` to load tenancy compartments, policies, Identity Domains,
and dynamic groups. To mark or unmark groups, it needs:

```
Allow dynamic-group <FUNCTION_RESOURCE_PRINCIPAL_GROUP> to use dynamic-groups in tenancy
```

The `use` verb covers `UpdateDynamicGroup`, which is the permission behind the
Identity Domains SCIM patch used for the OCI freeform-tag extension. If deletion
is enabled, grant `manage dynamic-groups in tenancy` instead; `manage` includes
the update permission and adds create/delete. Scope the policy to this function
principal and review it before setting deletion to `true`.

To publish its report, grant the resource principal least-privilege access to
the topic's compartment:

```
Allow dynamic-group <FUNCTION_RESOURCE_PRINCIPAL_GROUP> to use ons-topics in compartment <NOTIFICATION_TOPIC_COMPARTMENT>
```

## Deployment and logs

Deploy from this directory and configure a weekly OCI Resource Scheduler job:

```bash
fn deploy --app <FUNCTION_APP_NAME>
```

When `NOTIFICATION_TOPIC_ID` is configured, the function publishes one
plain-text report containing a summary, per-domain counts, and a row for every
evaluated dynamic group. Notification-delivery failures are logged but do not
fail the lifecycle run.

WARNING logs contain one end-of-run summary. INFO logs additionally provide
per-domain counts and individual mark, unmark, and delete details.

OCI Resource Scheduler invokes functions in detached mode, so it does not
retain the handler's JSON response. Use the notification report or function
logs for scheduled-run results.

## Tests

```bash
cd admin-functions
python3 -m unittest tests.test_dynamic_group_lifecycle
```
