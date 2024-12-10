# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

module "cislz_compartments" {
  source = "github.com/oracle-quickstart/terraform-oci-cis-landing-zone-iam/compartments"
  tenancy_ocid = var.tenancy_ocid
  compartments_configuration = local.compartments_configuration
}

module "terraform-oci-landing-zone-networking" {
  source = "github.com/oci-landing-zones/terraform-oci-modules-networking"
  network_configuration = var.network_configuration
}