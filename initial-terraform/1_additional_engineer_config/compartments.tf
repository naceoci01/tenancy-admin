locals {

    # Compartment

    engineer_compartment = { for cmp in var.compartment_names: "CMP-${cmp}" => {
        name : cmp,
        description : "${cmp} compartment"
    }}

    # Place any created compartments in the defined top compartment
    compartments_configuration = {
        default_parent_id : var.cloud_engineering_root_compartment_ocid
        enable_delete : true
        compartments : local.engineer_compartment
    }
}
