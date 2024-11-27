
resource "oci_limits_quota" "global-super-restrict" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Global Restrictions"
    name = "global-super-restrict-regions-quota"
    statements = [
        "zero analytics quota in tenancy where all {request.region = us-sanjose-1, request.region = sa-saopaulo-1,request.region = ca-toronto-1,request.region = eu-frankfurt-1,request.region = ap-mumbai-1,request.region = me-dubai-1,request.region = uk-london-1}",
        "zero big-data quota in tenancy where all {request.region = us-sanjose-1, request.region = sa-saopaulo-1,request.region = ca-toronto-1,request.region = eu-frankfurt-1,request.region = ap-mumbai-1,request.region = me-dubai-1,request.region = uk-london-1}"
    ] 
}