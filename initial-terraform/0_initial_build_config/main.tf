# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

# Get Identity Domain Data 
data "oci_identity_domain" "default_domain" {
  domain_id = var.default_domain_ocid
}

data "oci_identity_domain" "ce_domain" {
  domain_id = var.ce_domain_ocid
}

locals {
    # Define the Identity Domain Name (from the ID in the data)
    cloud_engineering_domain_name = data.oci_identity_domain.ce_domain.display_name
}

# module "cislz_compartments" {
#   source = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-iam/compartments"
#   tenancy_ocid = var.tenancy_ocid
#   compartments_configuration = local.compartments_configuration
# }

module "cislz_policies" {
  source       = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-iam/policies"
  tenancy_ocid = var.tenancy_ocid
  policies_configuration = local.policies_configuration
}

module "cislz_identity_domains" {
  source       = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-iam/identity-domains"
  tenancy_ocid                                  = var.tenancy_ocid
  #identity_domains_configuration                = var.identity_domains_configuration  #Using existing Identity Domains
  #identity_domain_groups_configuration          = local.identity_domain_groups_configuration
  identity_domain_dynamic_groups_configuration  = local.identity_domain_dynamic_groups_configuration
}

# # See vaults.tf for vaults_configuration
# module "cislz_vaults" {
#   source = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-security/vaults"
#   providers = {
#     oci = oci
#     oci.home = oci.home
#   }
#   vaults_configuration = local.vaults_configuration
# }