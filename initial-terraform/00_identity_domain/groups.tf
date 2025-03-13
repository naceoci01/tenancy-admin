# CISLZ Groups
# Groups
locals {

  # Keys
  cloud_engineering_group_key         = "CLOUD-ENGINEERS-GROUP"
  cloud_engineering_group_description = "Group for all users that are Cloud Engineers (CE) in group ${var.ce_domain_name}-users"
  oic_admin_group_key                 = "OIC-ADMIN-GROUP"
  exacs_admin_group_key               = "EXACS-ADMIN-GROUP"

  cloud_engineers_group = {
    (local.cloud_engineering_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = "${var.ce_domain_name}-users"
      description        = local.cloud_engineering_group_description
    }
  }

  oic_group = var.create_oic ? {
    (local.oic_admin_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = var.engineer_oic_group_name
      description        = var.engineer_oic_group_desc
    }
  } : {}

  exacs_group = var.create_exa ? {
    (local.exacs_admin_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = var.engineer_exacs_group_name
      description        = var.engineer_exacs_group_desc
    }
  } : {}

  # Merge all groups
  identity_domain_groups_configuration = {
    groups : merge(local.cloud_engineers_group, local.oic_group, local.exacs_group)
  }
}
