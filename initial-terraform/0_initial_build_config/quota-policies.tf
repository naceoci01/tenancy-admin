# Quota Policy

resource "oci_limits_quota" "global-super-restrict" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Global Restrictions"
    name = "global-super-restrict-regions-quota"
    statements = [
        "zero big-data quota in tenancy",
        "zero ai-language quota /*count*/ in tenancy"
    ] 
}
