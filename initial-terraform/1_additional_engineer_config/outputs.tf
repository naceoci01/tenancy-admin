# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

output "compartments-new" {
  value = module.cislz_compartments.compartments
}

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

output "compartments-existing" {
  value = data.oci_identity_compartments.engineer-comps.compartments[*].name
}

output "quota-policy-COMPUTE" {
  value = oci_limits_quota.engineer-compute.statements
}

output "quota-policy-DATABASE" {
  value = oci_limits_quota.engineer-database.statements
}

output "quota-policy-STORAGE" {
  value = oci_limits_quota.engineer-storage.statements
}

output "quota-policy-NETOWRK" {
  value = oci_limits_quota.engineer-network.statements
}