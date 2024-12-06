
# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

locals {

    # Dynamic Groups - per compartment
    engineer_dg = { for k,v in module.cislz_compartments.compartments: "DG-${v.name}" => {
        identity_domain_id : var.domain_id
        name : "${v.name}-DG",
        description : "${v.name} compartment",
        matching_rule : "instance.compartment.id = '${v.id}'"
    }}     

    
    # Merge all DGs into one config
    identity_domain_dynamic_groups_configuration = {
        dynamic_groups : local.engineer_dg
    }

    # Build a string of rules
    dg_rule = "all {resource.type='managementagent', resource.compartment.id='ocid1.compartment.oc1..aaaaaaaayaowlpwv7izl45sthscrfdzfofexswlgsbfsiyiwi6ytd73cn3ga'}"
}

# import {
#   to = oci_identity_dynamic_group.osmh-instances
#   id = "ocid1.dynamicgroup.oc1..aaaaaaaar6uyqcpropiaaew3lvpkrbaswmixfnpozvfb67dtw4rrrtiawx7q"
# }

# Import existing DG
resource "oci_identity_dynamic_group" "osmh-instances" {
  name = "osmh-instances"
  description = "Updated DG for engineers"
  compartment_id = "ocid1.tenancy.oc1..aaaaaaaaonqlfuxbai2t677fopst4vowm5axun74bmowkxtcqvbx6liagciq"
  matching_rule = "any {resource.type='managementagent', ${local.dg_rule} }"
}