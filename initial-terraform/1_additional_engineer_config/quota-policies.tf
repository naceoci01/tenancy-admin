# Define all quota policy statements
# Zero the type of quota
# Open for all compartments in our list
locals {
    comp_names = data.oci_identity_compartments.engineer-comps.compartments[*].name
    db_quota_statements = concat(
        [
            "zero database quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}"
        ],
        [
            "zero nosql quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}"
        ],
        [
            for comp in local.comp_names: "set database quota /*-total-storage-tb/ to 1 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set database quota /*-ecpu-count/ to 6 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set database quota vm-block-storage-gb to 512 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set database quota adb-developer-count to 2 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set database quota vm-standard-e5-ocpu-count to 2 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set nosql quota read-unit-count to 100 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set nosql quota write-unit-count to 10 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set nosql quota table-size-gb to 100 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ]
    )
    compute_quota_statements = concat(
        [
            "zero compute-core quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}",
            "zero compute-memory quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}"
        ],
        [
            for comp in local.comp_names: "set compute-memory quota standard-e5-memory-count to 120 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set compute-core quota standard-e5-core-count to 8 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set compute-memory quota standard3-memory-count to 120 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set compute-core quota standard3-core-count to 8 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set compute-memory quota standard-a1-memory-count to 120 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set compute-core quota standard-a1-core-count to 8 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set container-engine quota virtual-node-count to 3 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
    )
    #standard-a1-core-count
    storage_quota_statements = concat(
        [
            "zero block-storage quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}",
            "zero filesystem quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}"
        ],
        [
            for comp in local.comp_names: "set block-storage quota total-storage-gb to 4096 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set filesystem quota file-system-count to 1 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set filesystem quota mount-target-count to 1 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ]       
    )
    network_quota_statements = concat(
        [
            "zero vcn quota in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}"
        ],
        [
            for comp in local.comp_names: "set vcn quota vcn-count to 2 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ],
        [
            for comp in local.comp_names: "set vcn quota reserved-public-ip-count to 2 in compartment ${data.oci_identity_compartment.cloud-eng-comp.name}:${comp}"
        ]    
    )
}

resource "oci_limits_quota" "engineer-database" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota (Database)"
    name = "cloud-engineering-DATABASE-quota"
    statements = local.db_quota_statements
    depends_on = [ module.cislz_compartments ]
}

resource "oci_limits_quota" "engineer-compute" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota (Compute)"
    name = "cloud-engineering-COMPUTE-quota"
    statements = local.compute_quota_statements 
    depends_on = [ module.cislz_compartments ]
}

resource "oci_limits_quota" "engineer-storage" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota (Storage)"
    name = "cloud-engineering-STORAGE-quota"
    statements = local.storage_quota_statements
}

resource "oci_limits_quota" "engineer-network" {
    #Required
    compartment_id = var.tenancy_ocid
    description = "Engineer quota (VCN)"
    name = "cloud-engineering-NETWORK-quota"
    statements = local.network_quota_statements
}