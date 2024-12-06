# CISLZ Identity Domain and Group

locals {

  # Keys
  cloud_engineering_domain_key         = "CLOUD-ENGINEERS-DOMAIN"
  cloud_engineering_group_key         = "CLOUD-ENGINEERS-GROUP"
  cloud_engineering_group_description = "Group for all users that are Cloud Engineers (CE) in group ${var.domain_name}-users"

  # Groups
  cloud_engineers_group = {
    (local.cloud_engineering_group_key) = {
      identity_domain_id = module.cislz_identity_domains.identity_domains.CLOUD-ENGINEERS-DOMAIN.id
      name               = "${var.domain_name}-users"
      description        = local.cloud_engineering_group_description
    }
  }

  # Merge all groups
  identity_domain_groups_configuration = {
    groups : merge(local.cloud_engineers_group)
  }

  identity_domains_configuration = {
    # default_compartment_id : "TENANCY-ROOT",
    # ocid1.tenancy.oc1..aaaaaaaaonqlfuxbai2t677fopst4vowm5axun74bmowkxtcqvbx6liagciq
    default_defined_tags : null
    default_freeform_tags : null,
    identity_domains : {
      (local.cloud_engineering_domain_key) : {
        # compartment_id = "TENANCY-ROOT"
        description                      = "${var.domain_name} Identity Domain"
        display_name                     = var.domain_name
        license_type                     = "free"
        admin_email                      = "orasenatdpltintegration01_us@oracle.com"
        admin_first_name                 = "Integration01"
        admin_last_name                  = "Administrator"
        admin_user_name                  = "orasenatdpltintegration01_us@oracle.com"
        home_region                      = var.region
        is_hidden_on_login               = false
        is_notification_bypassed         = false
        is_primary_email_required        = false
        is_notification_bypassed         = false
        allow_signing_cert_public_access = true
      }
    }

  }
}
