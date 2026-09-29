# Policy Cleanup Report

This weekly OCI Resource Scheduler function uses `oci-policy-analysis==6.5.1`
through its supported `AppContext` and `LoadService` interfaces. It loads the
tenancy with the function resource principal and focuses this report on invalid
policy statements, groups with no users, and dynamic groups that are not
referenced by scanned policy statements.

When `REPORT_BUCKET_NAME` is configured, the function also writes a standalone
HTML report to Object Storage. It writes a dated copy under
`policy-cleanup-reports/YYYYMMDDTHHMMSSZ/report.html` and overwrites
`policy-cleanup-reports/latest.html` for a stable latest-report target. The
HTML includes those findings, cross-domain evidence, and AI guidance. GenAI
processes up to five issue groups per request so large reports are split into
smaller calls; a failed batch is reported while the remaining batches continue.

For groups with no users, the report also shows whether scanned policies
reference the group. Dynamic group candidates include their matching rule.
These findings are prompts for review; check dependencies before removing an
identity object. Optional OCI Generative AI guidance covers invalid policy
reasons and safe checks for group cleanup. It is off by default.

The function redirects `oci-policy-analysis` settings and cache files to the
ephemeral writable directory `/tmp/oci-policy-analysis` before importing that
package. Nothing is written under OCI Functions' read-only `/home/fn`, and the
cache is intentionally discarded when the function container is recycled.

For a missing group or dynamic group, the report also checks the already-loaded
Identity Domain inventory for same-named principals in other domains. It marks
these only as candidates to review: a same-name match does not prove that the
policy should reference that principal. The evidence is supplied to optional
GenAI guidance, which is instructed to require operator confirmation of the
fully qualified domain/name reference.

## Configuration

| Name | Default | Description |
| --- | --- | --- |
| `NOTIFICATION_TOPIC_ID` | inherited from application | Regional OCI Notifications topic OCID for the report. |
| `LOG_LEVEL` | `INFO` | Function log level. |
| `DEPENDENCY_LOG_LEVEL` | `WARNING` | OCI SDK and package log level. |
| `PUBLISH_NOTIFICATION` | `false` | Set to `true` only when this invocation should publish to the inherited topic. |
| `ENABLE_GENAI_ENRICHMENT` | `false` | Enables OCI Generative AI remediation guidance. |
| `GENAI_MODEL_ID` | unset | On-demand chat model ID, required only when GenAI is enabled. |
| `GENAI_COMPARTMENT_ID` | unset | Compartment used for the Generative AI inference request. |
| `REPORT_BUCKET_NAME` | `policy-health-reports` | Existing Object Storage bucket for the HTML report. Set in `func.yaml` or override per invocation with `report_bucket_name`. An explicitly empty value disables the HTML upload. |
| `REPORT_NAMESPACE` | unset | Object Storage namespace. When unset, the function resolves it from Object Storage. |

The default bucket is set in the `config` section of `func.yaml`. Deploy the
updated function config for the default to take effect. `REPORT_NAMESPACE` is
usually safe to leave blank; the function resolves the current tenancy's Object
Storage namespace with its resource principal. The bucket must already exist
and be accessible from the function's region. Resource Scheduler JSON can
override the bucket (or namespace) with `report_bucket_name` (or
`report_namespace`).

Use `{}` to test the report with INFO logging and no notification, even when
the Function App provides `NOTIFICATION_TOPIC_ID`. A controlled invocation may
override `publish_notification`, `enable_genai_enrichment`, `genai_model_id`,
`genai_compartment_id`, or `log_level` without changing deployed config.

Examples:

```json
{}
```

```json
{
  "log_level": "INFO",
  "enable_genai_enrichment": true,
  "genai_model_id": "<ON_DEMAND_CHAT_MODEL_ID>",
  "genai_compartment_id": "<GENAI_COMPARTMENT_OCID>",
  "report_bucket_name": "policy-health-reports"
}
```

Add `"publish_notification": true` only after reviewing the synchronous
invocation result. The function always returns its JSON report to the caller;
an OCI Notifications message is an optional copy.

## Permissions

Grant the function resource principal the read permissions required by
`oci-policy-analysis` to load tenancy compartments, policies, Identity
Domains, groups, users, and dynamic groups. This function never changes IAM
policies or identity resources.

To publish the report:

```
Allow dynamic-group <FUNCTION_RESOURCE_PRINCIPAL_GROUP> to use ons-topics in compartment <NOTIFICATION_TOPIC_COMPARTMENT>
```

If GenAI enrichment is enabled, grant only the inference permission required
for the selected model and compartment, for example:

```
Allow dynamic-group <FUNCTION_RESOURCE_PRINCIPAL_GROUP> to use generative-ai-family in compartment <GENAI_COMPARTMENT>
```

When `REPORT_BUCKET_NAME` is set, allow the function resource principal to
create and overwrite objects in that bucket's compartment. For example:

```
Allow dynamic-group <FUNCTION_RESOURCE_PRINCIPAL_GROUP> to manage objects in compartment <REPORT_BUCKET_COMPARTMENT> where all {target.bucket.name = '<REPORT_BUCKET_NAME>', any {request.permission = 'OBJECT_CREATE', request.permission = 'OBJECT_OVERWRITE'}}
```

The function does not create a PAR. Its synchronous result includes the bucket
and object names. Notifications, when enabled, contain a short summary and the
stable `latest.html` object name rather than repeating the full report. Set up
reader access separately; a PAR URL is a bearer link and should be shared with
care.

Review whether policy statement text may leave the function boundary before
enabling GenAI. The prompt includes validation reasons with up to three sample
statements per reason, plus up to five examples from each principal cleanup
category. The HTML report remains available if enrichment fails.

## Deploy and schedule

Deploy from this directory, then configure a weekly OCI Resource Scheduler job:

```bash
fn deploy --app <FUNCTION_APP_NAME>
```

## Invoke from your terminal

These commands invoke the deployed function synchronously from your local
terminal. That is the recommended test path because the deployed function has
its OCI resource principal; `fn run` does not provide that principal and cannot
load the tenancy in the same way.

Baseline test: INFO logs, JSON response, no GenAI call, and no notification
even if the Function App has an inherited `NOTIFICATION_TOPIC_ID`:

```bash
fn invoke --content-type application/json <FUNCTION_APP_NAME> policy-cleanup-report <<'JSON'
{"log_level":"INFO"}
JSON
```

GenAI test without publishing a notification. Replace the two placeholders
with the selected on-demand chat model ID and the compartment authorized for
inference:

```bash
fn invoke --content-type application/json <FUNCTION_APP_NAME> policy-cleanup-report <<'JSON'
{
  "log_level": "INFO",
  "enable_genai_enrichment": true,
  "genai_model_id": "<ON_DEMAND_CHAT_MODEL_ID>",
  "genai_compartment_id": "<GENAI_COMPARTMENT_OCID>"
}
JSON
```

After reviewing the returned JSON, test report delivery explicitly. This is
the only invocation that uses the inherited Notifications topic:

```bash
fn invoke --content-type application/json <FUNCTION_APP_NAME> policy-cleanup-report <<'JSON'
{
  "log_level": "INFO",
  "publish_notification": true
}
JSON
```

## Resource Scheduler body

OCI Resource Scheduler invokes functions in detached mode, so use the
Notifications message and Function logs as the scheduled-run record. Use this
normal weekly request body after the delivery test succeeds:

```json
{
  "log_level": "INFO",
  "publish_notification": true
}
```

To enable the optional remediation playbook in the scheduled report, use:

```json
{
  "log_level": "INFO",
  "publish_notification": true,
  "enable_genai_enrichment": true,
  "genai_model_id": "<ON_DEMAND_CHAT_MODEL_ID>",
  "genai_compartment_id": "<GENAI_COMPARTMENT_OCID>"
}
```
