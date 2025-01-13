# Quota Policy

resource "oci_limits_quota" "global-super-restrict" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Global Restrictions"
    name = "global-super-restrict-regions-quota"
    statements = [
        "zero big-data quota in tenancy where any {request.region = us-phoenix-1, request.region = us-chicago-1}"
    ] 
}
