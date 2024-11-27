# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

# Tenancy Stuff
variable "tenancy_ocid" {}
variable "region" {}
variable "user_ocid" { default = "" }
variable "fingerprint" { default = "" }
variable "private_key_path" { default = "" }
variable "private_key_password" { default = "" }

# Required Inputs
variable "domain_id" {
    description = "OCID of Identity domain (nondefault)"
}

# variable "cislz_top_policy_compartment_ocid" {
#     description = "OCID of compartment where common cloud-engineering policies can be created"
# }

# variable "cislz_top_policy_compartment_name" {
#     description = "Name of compartment where common cloud-engineering exists"
# }