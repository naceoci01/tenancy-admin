
# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

locals {

    # Keys
    cloud_engineering_group_key = "CLOUD-ENGINEERS-GROUP"
    # cloud_engineering_group_name = "cloud-engineering-users"
    cloud_engineering_group_description = "Group for all users that are Cloud Engineers (CE) in group ${var.engineer_group_name}"

    # Groups
    cloud_engineers_group = {
        (local.cloud_engineering_group_key) = {
            identity_domain_id        = var.domain_id
            name                      = var.engineer_group_name
            description               = local.cloud_engineering_group_description
            members                   = ["andrew.gregory@oracle.com","roman.kab@oracle.com"]
        }
    }

    # Merge all groups
    identity_domain_groups_configuration = {
        groups: merge(local.cloud_engineers_group)
    }
        
    # Define the created group name
    #cloud_engineering_group_name = module.cislz_identity_domains.identity_domain_groups[local.cloud_engineering_group_key].display_name

}
