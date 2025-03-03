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
variable "compartment_ocid" {}
variable "vcn_name" {}
variable "vcn_cidr_block" {}
variable "subnet_names" {}
variable "subnet_types" {}
variable "subnet_cidr_blocks" {}
variable "is_attach_drg" {}
variable "drg_ocid" {
    default = ""
}
# variable "network_configuration" {}