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
variable "vcn_cidr_block" {
    default = "172.17.99.0/24"
}
variable "subnet_names" {
  type = list(string)
  default = ["web","app"]
}
variable "subnet_types" {
  type = list(string)
  default = ["public","private"]
}
variable "subnet_cidr_blocks" {
  type = list(string)
  default = ["172.17.99.0/25","172.17.99.128/25"]
}
variable "is_attach_drg" {}
variable "drg_ocid" {
  default = ""
}
# variable "network_configuration" {}
