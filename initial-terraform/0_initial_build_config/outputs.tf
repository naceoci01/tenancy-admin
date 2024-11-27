# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

output "compartments" {
  value = module.cislz_compartments.compartments
}

output "identity-domain-groups" {
  description = "The identity domain groups."
  value       = module.cislz_identity_domains.identity_domain_groups
}

output "identity-domain-dynamic-groups" {
  description = "The identity domain groups."
  value       = module.cislz_identity_domains.identity_domain_dynamic_groups
}

output "policies" {
  value = module.cislz_policies.policies
}