# CISLZ Groups
# Groups
locals {

  # Keys
  cloud_engineering_group_key         = "CLOUD-ENGINEERS-GROUP"
  oic_admin_group_key                 = "OIC-ADMIN-GROUP"
  exacs_admin_group_key               = "EXACS-ADMIN-GROUP"
  oac_admin_group_key                 = "OAC-ADMIN-GROUP"
  datasci_admin_group_key             = "DATASCI-ADMIN-GROUP"
  mysql_admin_group_key               = "MYSQL-ADMIN-GROUP"
  postgres_admin_group_key            = "POSTGRES-ADMIN-GROUP"
  firewall_admin_group_key            = "FIREWALL-ADMIN-GROUP"

  # Always create the Cloud Engineers group
  # This group is used to assign policies to all Cloud Engineers in the tenancy
  # It is created in the non-Default Identity Domain specified by the user
  cloud_engineers_group = {
    (local.cloud_engineering_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = var.engineer_group_name
      description        = var.engineer_group_desc
    }
  }

  # Optional Groups - these groups are created only if the user has set the variable to true
  optional_groups = merge(
    # OIC Admin Group
    var.create_oic == true ?
    {
      (local.oic_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_oic_group_name
        description        = var.engineer_oic_group_desc
      }
    } : {},  

    # ExaCS Admin Group
    var.create_exa == true ?
    {
      (local.exacs_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_exacs_group_name
        description        = var.engineer_exacs_group_desc
      }
    } : {},

    # OAC Admin Group
    var.create_oac == true ?
    {
      (local.oac_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_oac_group_name
        description        = var.engineer_oac_group_desc
      }
    } : {},

    # Data Science Admin Group
    var.create_ds == true ?
    {
      (local.datasci_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_datascience_group_name
        description        = var.engineer_datascience_group_desc
      }
    } : {},

    # MySQL Admin Group
    var.create_mysql == true ?
    {
      (local.mysql_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_mysql_group_name
        description        = var.engineer_mysql_group_desc
      }
    } : {},

    # Postgres Admin Group
    var.create_postgres == true ?
    {
      (local.postgres_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_postgres_group_name
        description        = var.engineer_postgres_group_desc
      }
    } : {},

    # Firewall Admin Group
    var.create_firewall == true ?
    {
      (local.firewall_admin_group_key) = {
        identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
        name               = var.engineer_firewall_group_name
        description        = var.engineer_firewall_group_desc
      }
    } : {}
    
  )

  # Merge all groups
  identity_domain_groups_configuration = {
    # ignore_external_membership_updates : true
    groups : merge(local.cloud_engineers_group, local.optional_groups)
  }
}
