
# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

locals {

    # Dynamic Groups - per compartment
    engineer_dg = { for k,v in module.cislz_compartments.compartments: "DG-${v.name}" => {
        identity_domain_id : var.domain_id
        name : "${v.name}-DG",
        description : "${v.name} compartment",
        matching_rule : "instance.compartment.id = '${v.id}'"
    } if try(v.freeform_tags["dg"],"") == "true" }

    # engineer_dg = { for k,v in module.cislz_compartments.compartments: "DG-${v.name}" => {
    #     # count = contains(keys(v.freeform_tags), "dg") ? 1 : 0
    #     count = 0
    #     identity_domain_id : var.domain_id
    #     name : "${v.name}-DG",
    #     description : "${v.name} compartment",
    #     matching_rule : "instance.compartment.id = '${v.id}'"
    # }}     

    
    # Merge all DGs into one config
    identity_domain_dynamic_groups_configuration = {
        dynamic_groups : local.engineer_dg
    }

    # # Build a string of rules
    # dg_rule = "all {resource.type='managementagent', resource.compartment.id='ocid1.compartment.oc1..aaaaaaaayaowlpwv7izl45sthscrfdzfofexswlgsbfsiyiwi6ytd73cn3ga'}"
}
