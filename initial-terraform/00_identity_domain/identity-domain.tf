# CISLZ Identity Domain and Group

locals {

  # Keys
  cloud_engineering_domain_key         = "CLOUD-ENGINEERS-DOMAIN"

  identity_domains_configuration = {
    default_defined_tags : null
    default_freeform_tags : null,
    identity_domains : {
      (local.cloud_engineering_domain_key) : {
        # compartment_id = "TENANCY-ROOT"
        description                      = var.ce_domain_desc
        display_name                     = var.ce_domain_name
        license_type                     = "oracle-apps"
        admin_email                      = var.ce_domain_admin_email
        admin_first_name                 = var.ce_domain_admin_first_name
        admin_last_name                  = var.ce_domain_admin_last_name
        admin_user_name                  = var.ce_domain_admin_email
        home_region                      = var.region
        is_hidden_on_login               = false
        is_notification_bypassed         = false
        is_primary_email_required        = false
        is_notification_bypassed         = false
        allow_signing_cert_public_access = true
        # license_type                     = "free"
      }
    }

  }
}
