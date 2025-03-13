# Use CISLZ Module to create a basic Identity Domain

module "cislz_identity_domains" {
  source       = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-iam/identity-domains"
  tenancy_ocid                                  = var.tenancy_ocid
  identity_domains_configuration                = local.identity_domains_configuration
  identity_domain_groups_configuration          = local.identity_domain_groups_configuration
  # identity_domain_dynamic_groups_configuration  = local.identity_domain_dynamic_groups_configuration
}

module "cislz_compartments" {
  source = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-iam/compartments"
  tenancy_ocid = var.tenancy_ocid
  compartments_configuration = local.compartments_configuration
}

output "identity-domain-existing" {
  description = "The identity domain groups."
  value       = module.cislz_identity_domains
}
