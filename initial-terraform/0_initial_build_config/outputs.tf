# What did we build

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

output "quota-policies" {
  value = oci_limits_quota.global-super-restrict.statements
}

output "vault" {
  value = module.cislz_vaults.vaults
}