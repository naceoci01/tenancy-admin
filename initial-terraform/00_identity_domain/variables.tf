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
variable "ce_domain_name" {
    description = "Name of Identity Domain (nondefault)"
}

variable "ce_domain_desc" {
    description = "Description of Identity Domain (nondefault)"
}

variable "default_domain_ocid" {
    description = "OCID of Cloud Engineers Identity domain (Default)"
}

# Compartments
variable "engineer_compartment_base_name" { 
    description = "Name of shared engineer compartment. Engineers and Shared Compartments key off this"
    default = "cloud-engineering"
}

variable "shared_compartment_oic_name" { 
    description = "Name of shared compartment for OIC"
    default = "OIC"
}

variable "shared_compartment_oac_name" { 
    description = "Name of shared compartment for OAC"
    default = "OAC"
}

variable "shared_compartment_gg_name" { 
    description = "Name of shared compartment for GoldenGate"
    default = "GoldenGate"
}


# Groups
variable "engineer_group_name" {
    description = "Name of shared engineer group"
    default = "cloud-engineering-domain-users"
}

variable "engineer_datascience_group_name" {
    description = "Name of group for Data Science Users"
    default = "cloud-engineering-datascience-users"
}

variable "engineer_oac_group_name" {
    description = "Name of group for Analytics Admins"
    default = "cloud-engineering-oac-admins"
}

variable "engineer_mysql_group_name" {
    description = "Name of group for MySQL Admins"
    default = "cloud-engineering-mysql-admins"
}

variable "engineer_postgres_group_name" {
    description = "Name of shared engineer group for Postgres"
    default = "cloud-engineering-postgres-users"
}

variable "engineer_exacs_group_name" {
    description = "Name of group for ExaCS Admins"
    default = "cloud-engineering-exacs-admins"
}

variable "engineer_exacs_group_desc" {
    description = "Description of group for ExaCS Admins"
    default = "ExaCS Admins Group"
}

variable "engineer_firewall_group_name" { 
    description = "Name of group for Firewall Admins"
    default = "cloud-engineering-firewall-admins"
}

variable "engineer_oic_group_name" { 
    description = "Name of group for OIC Admins"
    default = "cloud-engineering-oic-admins"
}

variable "engineer_oic_group_desc" { 
    description = "Name of group for OIC Admins"
    default = "Group for users who can administer OIC Instances in OCI and have ServiceAdministrator role"
}

# Booleans for creation or not
variable "create_oic" {
    type = bool
    description = "Whether to enable Oracle Integration"
}

variable "create_exa" {
    type = bool
    description = "Whether to enable Oracle Integration"
}

variable "create_oda" {
    type = bool
    description = "Whether to enable Oracle Digital Assistant"
}

variable "create_mysql" {
    type = bool
    description = "Whether to enable MySQL"
}

variable "create_oac" {
    type = bool
    description = "Whether to enable Oracle Analytics Cloud"
}

variable "create_ds" {
    type = bool
    description = "Whether to enable Data Science and Labelling"
}

variable "create_ai" {
    type = bool
    description = "Whether to enable AI and GenAI"
}

variable "create_gg" {
    type = bool
    description = "Whether to enable GoldenGate"
}

variable "create_postgres" {
    type = bool
    description = "Whether to enable Postgres"
}

variable "create_opensearch" {
    type = bool
    description = "Whether to enable OpenSearch"
}

variable "create_func" {
    type = bool
    description = "Whether to enable OCI Functions"
}

variable "create_di" {
    type = bool
    description = "Whether to enable OCI Data Integration"
}

variable "create_firewall" {
    type = bool
    description = "Whether to enable OCI Network Firewall"
}
