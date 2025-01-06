# Vault configuration
locals {
    vaults_configuration = {
        default_compartment_id = module.cislz_compartments.compartments.SHARED-CMP.id

        vaults = {
            CLOUD-ENGINEERING-VAULT = {
                name = "${var.engineer_compartment_base_name}-shared-vault-phx"
            }
        }
    } 
}