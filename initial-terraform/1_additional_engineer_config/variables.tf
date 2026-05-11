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
    type = string
    description = "OCID of Identity domain (nondefault)"
}

variable "cloud_engineering_root_compartment_ocid" {
    type = string
    description = "OCID of compartment where engineer compartments are created"
}

variable "cloud_engineering_groupid" {
    type = string
    description = "This group ID is NOT an OCID.  It is found via API and it is the IDCS ID"
    default = "cf91a190f2584c65bcf29360fd17c277"
}

variable "per-engineer-vcn-quota" {
    type = number
    description = "Number of VCNs allowed per engineer"
    default = 3
}

variable "per-engineer-core-quota" {
    type = number
    description = "Number of compute cores allowed per engineer - will apply to all engineer compartments and all types we allow - E5/E6/Standard3"
    default = 12
}

variable "per-engineer-memory-quota" {
    type = number
    description = "Amount of memory allowed per engineer - will apply to all engineer compartments and all types we allow - E5/E6/Standard3"
    default = 200
}

variable "per-engineer-oke-nodes-quota" {
    type = number
    description = "Number of virtual OKE nodes allowed per engineer"
    default = 3
}

variable "per-engineer-block-storage-quota" {
    type = number
    description = "Amount of block storage (in GBs) allowed per engineer"
    default = 4096
}

variable "per-engineer-file-system-quota" {
    type = number
    description = "Number of file systems allowed per engineer"
    default = 2
}

variable "per-engineer-mount-target-quota" {
    type = number
    description = "Number of mount targets allowed per engineer"
    default = 1
}
