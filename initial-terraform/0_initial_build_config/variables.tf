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
    description = "OCID of Identity domain (nondefault)"
}

variable "engineer_group_name" {
    description = "Name of shared engineer group"
    default = "cloud-engineering-domain-users"
}

variable "engineer_datascience_group_name" {
    description = "Name of shared engineer group for Data Science"
    default = "cloud-engineering-datascience-users"
}

variable "engineer_compartment_base_name" { 
    description = "Name of shared engineer compartment"
    default = "cloud-engineering"
}

# variable "use_drg" {
#     type = bool
#     description = "Whether to create a DRG"
# }
# variable "rpc_peer_ocid" {
#     description = "OCID of RPC Peering Connection (optional)"
#     default = null
# }
# variable "rpc_peer_attachment_name" {
#     description = "Name of the attachment"
# }
# variable "rpc_peer_region" {
#     description = "OCID of RPC Peering Connection (optional)"
#     default = null
# }