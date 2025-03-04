locals {

    # Compartment per existing user
    # engineer_compartment = { for cmp in var.compartment_names: "CMP-${cmp}" => {
    #     name : split(".", cmp)[0],
    #     description : "${cmp} compartment"
    # }}    
    engineer_compartment = { for cmp in data.oci_identity_domains_group.ce-group.members[*].name: "CMP-${cmp}" => {
        name : split("@", cmp)[0],
        description : "${cmp} compartment",
        defined_tags : {
            "Oracle-Tags.AllowCompartmentCreation"="true"
        }
    }}

    # Place any created compartments in the defined top compartment
    compartments_configuration = {
        default_parent_id : var.cloud_engineering_root_compartment_ocid
        enable_delete : false
        compartments : local.engineer_compartment
    }
}

# Root cloud-engineering
data "oci_identity_compartment" "cloud-eng-comp" {
    id = var.cloud_engineering_root_compartment_ocid
}

# All existing compartments, grab after creation
data "oci_identity_compartments" "engineer-comps" {
    compartment_id = data.oci_identity_compartment.cloud-eng-comp.id
    state = "ACTIVE"
    depends_on = [ module.cislz_compartments ]

}