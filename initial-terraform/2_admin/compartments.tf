locals {

    # Place any created compartments in the defined top compartment
    compartments_configuration = {
        default_parent_id : "TENANCY-ROOT"
        enable_delete : false
        compartments : {
            ADMIN : {
                name = "admin",
                description = "admin compartment",
            }
        }
    }
}
