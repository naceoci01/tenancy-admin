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
variable "default_domain_ocid" {
    description = "OCID of Default Identity domain (required for later creating dynamic groups within Default Domain)"
}

variable "ce_domain_name" {
    description = "Name of Identity Domain for Engineers (non-Default)"
}

variable "ce_domain_desc" {
    description = "Description of Identity Domain for Engineers (non-Default)"
}

variable "ce_domain_admin_first_name" {
    description = "First name of the Identity Domain Administrator" 
}

variable "ce_domain_admin_last_name" {
    description = "Last name of the Identity Domain Administrator" 
  
}
variable "ce_domain_admin_email" {
    description = "Email address of the Identity Domain Administrator" 
}

# Groups
variable "engineer_group_name" {
    description = "Name of shared engineer group"
    default = "cloud-engineering-domain-users"
}

variable "engineer_group_desc" {
    description = "Description of shared engineer group"
    default = "Shared group for all users in the cloud engineering domain.  Users in this group can be assigned to other groups in the domain, if desired."
}

# Optional Groups

# OIC
variable "engineer_oic_group_name" { 
    description = "Name of group for OIC Admins"
    default = "cloud-engineering-oic-admins"
}
variable "engineer_oic_group_desc" { 
    description = "Name of group for OIC Admins"
    default = "Group for users who can administer OIC Instances in OCI and have should have ServiceAdministrator role"
}

# OAC
variable "engineer_oac_group_name" {
    description = "Name of group for Analytics Admins"
    default = "cloud-engineering-oac-admins"
}
variable "engineer_oac_group_desc" {
    description = "Description of group for Analytics Admins"
    default = "Group for users who can administer OAC Instances in OCI and have should have ServiceAdministrator role"
}

# ExaCS
variable "engineer_exacs_group_name" {
    description = "Name of group for ExaCS Admins"
    default = "cloud-engineering-exacs-admins"
}
variable "engineer_exacs_group_desc" { 
    description = "Description of group for ExaCS Admins"
    default = "Group for users have full admin over VCNs and ExaCS Instances in OCI within the shared compartment for ExaCS."
}

# Data Science
variable "engineer_datascience_group_name" {
    description = "Name of group for Data Science Users"
    default = "cloud-engineering-datascience-users"
}
variable "engineer_datascience_group_desc" {
    description = "Description of group for Data Science Users"
    default = "Groups for users who can administer Data Science and Labelling in OCI."
}

# MySQL
variable "engineer_mysql_group_name" {
    description = "Name of group for MySQL Admins"
    default = "cloud-engineering-mysql-admins"
}
variable "engineer_mysql_group_desc" {
    description = "Description of group for MySQL Admins"
    default = "Group for users who can administer MySQL Heatwave Instances in OCI."
  
}

# Postgres
variable "engineer_postgres_group_name" {
    description = "Name of shared engineer group for Postgres"
    default = "cloud-engineering-postgres-users"
}
variable "engineer_postgres_group_desc" {
    description = "Description of shared engineer group for Postgres"
    default = "Shared group for all users in the cloud engineering domain who can administer Postgres Instances in OCI."
  
}

# Firewall
variable "engineer_firewall_group_name" { 
    description = "Name of group for Firewall Admins"
    default = "cloud-engineering-firewall-admins"
}
variable "engineer_firewall_group_desc" { 
    description = "Description of group for Firewall Admins"
    default = "Group for users who can administer Network Firewall Instances in OCI."
  
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

variable "create_postgres" {
    type = bool
    description = "Whether to enable Postgres"
}

variable "create_firewall" {
    type = bool
    description = "Whether to enable OCI Network Firewall"
}
