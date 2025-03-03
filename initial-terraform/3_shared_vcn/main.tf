# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

module "terraform-oci-landing-zone-networking" {
  source = "github.com/oci-landing-zones/terraform-oci-modules-networking"
  network_configuration = local.network_configuration
}