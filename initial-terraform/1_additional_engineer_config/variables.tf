# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

# Tenancy Stuff
variable "tenancy_ocid" {}
variable "region" {}
variable "user_ocid" { default = "" }
variable "fingerprint" { default = "" }
variable "private_key_path" { default = "" }
variable "private_key_password" { default = "" }
variable "home_region" {description = "Your tenancy home region"}


# Required Inputs
variable "domain_id" {
    type = string
    description = "OCID of Identity domain (nondefault)"
}

variable "cloud_engineering_root_compartment_ocid" {
    type = string
    description = "OCID of compartment where engineer compartments are created"
}
