# Tenancy Terraform stacks

This directory contains separate Terraform stacks for building and extending an
OCI Cloud Engineer tenancy. Apply each stack from its own directory; each has
its own providers, variables, and state. Review `schema.yaml` where present
and the variable definitions before using it with OCI Resource Manager.

## Current deployment scope

Only these stacks are in use today:

| Stack | Purpose |
| --- | --- |
| [`00_identity_domain/`](00_identity_domain/) | Creates the Identity Domain foundation and initial groups. Run carefully because group changes can affect membership. |
| [`0_initial_build_config/`](0_initial_build_config/) | Creates the active baseline compartments, identity-domain groups, dynamic groups, IAM policies, quotas, and vault configuration. |

Apply stack 00 before the baseline when a new Identity Domain is needed.

## Superseded and in-flight stacks

| Stack | Status |
| --- | --- |
| [`1_additional_engineer_config/`](1_additional_engineer_config/) | Superseded. Its ongoing engineer-compartment and quota work is now implemented by the [OCI Administration Functions](../admin-functions/README.md). |
| [`2_admin/`](2_admin/) | In flight. |
| [`3_shared_vcn/`](3_shared_vcn/) | In flight. |
| [`4_multi_region_services/`](4_multi_region_services/) | In flight. |
| [`5_special_project/`](5_special_project/) | In flight. |

The `test-*` and `xx_*` directories are working or historical material, not
current deployment stacks.

## Stack reference

| Stack | Purpose | Typical use |
| --- | --- | --- |
| [`00_identity_domain/`](00_identity_domain/) | Identity Domain foundation and initial groups. | In use. |
| [`0_initial_build_config/`](0_initial_build_config/) | Baseline tenancy configuration. | In use. |
| [`1_additional_engineer_config/`](1_additional_engineer_config/) | Engineer configuration. | Superseded by OCI Functions. |
| [`2_admin/`](2_admin/) | Administration compartment and networking foundation. | In flight. |
| [`3_shared_vcn/`](3_shared_vcn/) | Shared-network infrastructure. | In flight. |
| [`4_multi_region_services/`](4_multi_region_services/) | Multi-region service networking. | In flight. |
| [`5_special_project/`](5_special_project/) | Project-specific compartment, policies, and identity configuration. | In flight. |

The numeric prefixes show the intended progression; they do not mean every
directory should be applied.

## Apply a stack

Run Terraform in the target stack directory with credentials and variable files
for the tenancy you intend to change:

```bash
cd initial-terraform/0_initial_build_config
terraform init
terraform plan
terraform apply
```

Use isolated state per tenancy and keep state files, `*.tfvars`, credentials,
and other environment-specific material out of commits. Terraform-managed
resources should be changed in the corresponding stack rather than manually in
the OCI Console, because a later apply can reconcile them back to configuration.

## Related automation

The Terraform stacks establish infrastructure; recurring engineer-compartment
and quota operations are implemented as OCI Functions in
[`../admin-functions/`](../admin-functions/README.md).
