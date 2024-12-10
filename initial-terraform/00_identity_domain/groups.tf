# CISLZ Groups
# Groups
locals {

  # Keys
  cloud_engineering_group_key         = "CLOUD-ENGINEERS-GROUP"
  cloud_engineering_group_description = "Group for all users that are Cloud Engineers (CE) in group ${var.domain_name}-users"
  oic_admin_group_key         = "OCI-ADMIN-GROUP"
  oic_admin_group_name        = "OIC-Administrators"
  oic_admin_group_description = "Group for use with OIC Administration"

  cloud_engineers_group = {
    (local.cloud_engineering_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = "${var.domain_name}-users"
      description        = local.cloud_engineering_group_description
    }
  }

  oic_admins_group = {
    (local.oic_admin_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = local.oic_admin_group_name
      description        = local.oic_admin_group_description
    }
  }

  # Merge all groups
  identity_domain_groups_configuration = {
    groups : merge(local.cloud_engineers_group, local.oic_admins_group)
  }
}
