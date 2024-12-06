
# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

locals {

    # Keys and names
    osmh_dynamic_group_key = "OSMH-DYN-GROUP"
    osmh_dynamic_group_name = "all-osmh-instances"
    adb_dynamic_group_key = "ADB-DYN-GROUP"
    adb_dynamic_group_name = "all-adb-instances"

    # Dynamic Groups
    all_dynamic_groups = {
        (local.osmh_dynamic_group_key) = {
            identity_domain_id = var.domain_id
            name          = local.osmh_dynamic_group_name
            description   = "Allows any instance to be an OSMH instance"
            matching_rule = "resource.type='managementagent'"
            defined_tags  = {}
            freeform_tags = {}
        },
        (local.adb_dynamic_group_key) = {
            identity_domain_id = var.domain_id
            name          = local.adb_dynamic_group_name
            description   = "Allows any ADB instance to be part of this DG"
            matching_rule = "resource.type='autonomousdatabase'"
            defined_tags  = {}
            freeform_tags = {}
        }    }
    
    # Merge all DGs into one config
    identity_domain_dynamic_groups_configuration = {
        # dynamic_groups : merge(local.engineer_dg, local.osmh_dynamic_group)
        dynamic_groups : local.all_dynamic_groups
    }
}