provider "oci" {
  region               = var.region
  tenancy_ocid         = var.tenancy_ocid
  user_ocid            = var.user_ocid
  fingerprint          = var.fingerprint
  private_key_path     = var.private_key_path
  private_key_password = var.private_key_password
}

terraform {
  required_version = ">= 1.5.0"
  required_providers { 
    oci = {
      source = "oracle/oci"
      configuration_aliases = [oci]
    }
  }
}