# Tenancy Admin

Tooling for administering an Oracle Cloud Infrastructure (OCI) Cloud Engineer
tenancy. The repository has 3 sections:

## Terraform stacks

[`initial-terraform/`](initial-terraform/README.md) contains independently
applied Terraform stacks for identity, baseline tenancy configuration, engineer
configuration, administration, networking, and project-specific services.
Start with its README for the stack order, scope, and execution guidance.

## OCI Functions

[`admin-functions/`](admin-functions/README.md) contains independently
deployable OCI Functions for engineer-compartment lifecycle management, quota
reconciliation, delete staging, and Autonomous Database maintenance. Start with
its README for shared deployment and scheduler guidance, then follow the
function-specific README for configuration and IAM requirements.

## Standalone Scripts

[`standalone-scripts/`](standalone-scripts/README.md) contains independent python scripts
written at various times.  Some have been converted to functions, for example the autonomous 
database maintenance.  These are use-at-your-own-risk, but if there are updates needed, please make
them and re-contribute.

## Repository layout

```text
initial-terraform/  Terraform stacks and Terraform-specific documentation
admin-functions/    OCI Functions, tests, samples, and function documentation
standalone-scripts/    Python scripts
```


