# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

# output "compartments-new" {
#   value = module.cislz_compartments.compartments
# }

# output "identity-domain-dynamic-groups" {
#   description = "The identity domain groups."
#   value       = module.cislz_identity_domains.identity_domain_dynamic_groups
# }

# output "oci_identity_domains_group" {
#   value = oci_identity_domains_group.ce-group
# }

output "CE-group-members" {
  value = data.oci_identity_domains_group.ce-group.members[*].name
}

output "CE-compartments" {
  value = data.oci_identity_compartments.engineer-comps.compartments[*].name
}

output "quota-policy-COMPUTE-CORE" {
  value = oci_limits_quota.engineer-compute-core.statements
}

output "quota-policy-COMPUTE-MEMORY" {
  value = oci_limits_quota.engineer-compute-memory.statements
}

output "quota-policy-DATABASE" {
  value = oci_limits_quota.engineer-database.statements
}

output "quota-policy-NOSQL" {
  value = oci_limits_quota.engineer-nosql.statements
}

output "quota-policy-STORAGE" {
  value = oci_limits_quota.engineer-storage.statements
}

output "quota-policy-NETWORK" {
  value = oci_limits_quota.engineer-network.statements
}
