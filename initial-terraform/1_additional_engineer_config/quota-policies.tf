
# resource "oci_limits_quota" "global-super-restrict" {
#     #Required
#     compartment_id = var.tenancy_ocid
#     description = "Global Restrictions"
#     name = "global-super-restrict-regions-quota"
#     statements = [
#         "zero analytics quota in tenancy where all {request.region = us-sanjose-1, request.region = sa-saopaulo-1,request.region = ca-toronto-1,request.region = eu-frankfurt-1,request.region = ap-mumbai-1,request.region = me-dubai-1,request.region = uk-london-1}",
#         "zero big-data quota in tenancy where all {request.region = us-sanjose-1, request.region = sa-saopaulo-1,request.region = ca-toronto-1,request.region = eu-frankfurt-1,request.region = ap-mumbai-1,request.region = me-dubai-1,request.region = uk-london-1}"
#     ] 
# }

locals {
    db_quota_statements = concat(
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "zero database quota /*-ocpu-count/ in compartment cloud-engineering:${comp.name}"
        ],
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set database quota /*-total-storage-tb/ to 1 in compartment cloud-engineering:${comp.name}"
        ],
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set database quota /*-ecpu-count/ to 4 in compartment cloud-engineering:${comp.name}"
        ],
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set database quota vm-block-storage-gb to 1024 in compartment cloud-engineering:${comp.name}"
        ]
    )
    compute_quota_statements = concat(
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set compute-memory quota /standard-*/ to 120 in compartment cloud-engineering:${comp.name}"
        ],
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set compute-core quota /standard-*/ to 8 in compartment cloud-engineering:${comp.name}"
        ],
    )
    storage_quota_statements = concat(
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set block-storage quota total-storage-gb to 1024 in compartment cloud-engineering:${comp.name}"
        ],
        [
            for comp in data.oci_identity_compartments.engineer_compartments.compartments: "set compute-core quota /standard-*/ to 8 in compartment cloud-engineering:${comp.name}"
        ]
    )
}

resource "oci_limits_quota" "engineer-database" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota"
    name = "cloud-engineering-${var.compartment_grouping}-DATABASE-quota"
    statements = local.db_quota_statements
    depends_on = [ module.cislz_compartments ]
}

resource "oci_limits_quota" "engineer-compute" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota"
    name = "cloud-engineering-${var.compartment_grouping}-COMPUTE-quota"
    statements = local.compute_quota_statements 
    depends_on = [ module.cislz_compartments ]
}

resource "oci_limits_quota" "engineer-storage" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota"
    name = "cloud-engineering-${var.compartment_grouping}-STORAGE-quota"
    statements = local.compute_quota_statements 
}

data "oci_identity_compartments" "engineer_compartments" {
    #Required
    compartment_id = var.cloud_engineering_root_compartment_ocid
    state = "ACTIVE"
    depends_on = [module.cislz_compartments]
}

