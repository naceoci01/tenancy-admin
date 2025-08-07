
# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

locals {

  # Keys and names
  osmh_dynamic_group_key          = "OSMH-DYN-GROUP"
  osmh_dynamic_group_name         = "all-osmh-instances"
  adb_dynamic_group_key           = "ADB-DYN-GROUP"
  adb_dynamic_group_name          = "all-adb-instances"
  stackmon_dynamic_group_key      = "STACKMON-DYN-GROUP"
  stackmon_dynamic_group_name     = "all-stackmon-instances"
  certificate_dynamic_group_key   = "CERT-AUTH-DYN-GROUP"
  certificate_dynamic_group_name  = "CertificateAuthority-DG"
  gg_dynamic_group_key            = "GG-DYN-GROUP"
  gg_dynamic_group_name           = "all-goldengate-deployments-DG"
  func_dynamic_group_key          = "FUNC-DYN-GROUP"
  func_dynamic_group_name         = "all-functions-DG"
  genai_agent_dynamic_group_key   = "GENAI-DYN-GROUP"
  genai_agent_group_name          = "all-genai-agents-DG"
  datascience_dynamic_group_key   = "DS-DYN-GROUP"
  datascience_dynamic_group_name  = "all-datascience-DG"
  datalabeling_dynamic_group_key  = "DL-DYN-GROUP"
  datalabeling_dynamic_group_name = "all-datalabeling-DG"
  oac_dynamic_group_key           = "OAC-DYN-GROUP"
  oac_dynamic_group_name          = "all-oac-instance-DG"
  oda_dynamic_group_key           = "ODA-DYN-GROUP"
  oda_dynamic_group_name          = "all-oda-instance-DG"
  mysql_dynamic_group_key         = "MYSQL-DYN-GROUP"
  mysql_dynamic_group_name        = "all-mysql-dbsystems-DG"
  exacs_dynamic_group_key         = "EXACS-DYN-GROUP"
  exacs_dynamic_group_name        = "all-exacs-DG"
  database_dynamic_group_key         = "DB-DYN-GROUP"
  database_dynamic_group_name        = "all-databases-DG"
  resource_dynamic_group_key         = "RESOURCE-DYN-GROUP"
  resource_dynamic_group_name        = "all-resourceschedules-DG"
  data_catalog_dynamic_group_key         = "DATACATALOG-DYN-GROUP"
  data_catalog_dynamic_group_name        = "all-data-catalog-DG"
  oic_rp_dynamic_group_key         = "OIC-RP-DYN-GROUP"
  oic_rp_dynamic_group_name        = "all-OIC-RP-DG"
  # Dynamic Groups
  all_dynamic_groups = merge(
    {
      (local.osmh_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.osmh_dynamic_group_name
        description        = "Allows any instance to be an OSMH instance"
        matching_rule      = "ANY {ALL {resource.type='managementagent', resource.compartment.id != 'xxxx'}, instance.compartment.id != 'xxxx'}"
      }
    },
    {
      (local.adb_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.adb_dynamic_group_name
        description        = "Allows any instance to be an ADB instance - Resource Principal"
        matching_rule      = "resource.type='autonomousdatabase'"
      }
    },
    {
      (local.stackmon_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.stackmon_dynamic_group_name
        description        = "Allows any Stackmon instance to be part of this DG"
        matching_rule      = "ANY {ALL {resource.type='managementagent', resource.compartment.id !='xxxx'}, ALL {instance.compartment.id != 'xxxx'} }"
      }
    },
    {
      (local.certificate_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.certificate_dynamic_group_name
        description        = "For use by Certificates Service - creating a CA"
        matching_rule      = "resource.type='certificateauthority'"
      }
    },
    {
      (local.func_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.func_dynamic_group_name
        description        = "Defines all OCI Functions"
        matching_rule      = "resource.type = 'fnfunc'"
      }
    },
    {
      (local.resource_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.resource_dynamic_group_name
        description        = "Defines all OCI Resource Schedules"
        matching_rule      = "resource.type = 'resourceschedule'"
      }
    },
    {
      (local.database_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.database_dynamic_group_name
        description        = "Defines all OCI Databases"
        matching_rule      = "ANY {resource.type = 'database', resource.type = 'dbsystem'}"
      }
    },

    # Optional
    var.create_oac == true ?
    {
      (local.oac_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.oac_dynamic_group_name
        description        = "Defines all OAC Instances"
        matching_rule      = "resource.type='xxxx'"
      }
    } : {},

    var.create_oda == true ?
    {
      (local.oda_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.oda_dynamic_group_name
        description        = "Defines all ODA Instances"
        matching_rule      = "resource.type='odainstance'"
      }
    } : {},
    var.create_ds == true ?
    {
      (local.datascience_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.datascience_dynamic_group_name
        description        = "Defines all OCI Data Science"
        matching_rule      = "Any {resource.type='datasciencenotebooksession',resource.type='dataflow-family',resource.type='datasciencemodeldeployment',resource.type='datasciencejobrun'}"
      },
      (local.datalabeling_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.datalabeling_dynamic_group_name
        description        = "Defines all OCI Data Labeling"
        matching_rule      = "resource.type='datalabelingdataset'"
      }
    } : {},
    var.create_ai == true ?
    {
      (local.genai_agent_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.genai_agent_group_name
        description        = "Defines all OCI GenaAI Agents or Ingestion Jobs"
        matching_rule      = "ANY {resource.type = 'genaiagent', resource.type='genaiagentdataingestionjob'}"
      }
    } : {},
    var.create_gg == true ?
    {
      (local.gg_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.gg_dynamic_group_name
        description        = "Defines all GoldenGate Deployments"
        matching_rule      = "resource.type = 'goldengatedeployment'"
      }
    } : {},
    var.create_mysql == true ?
    {
      (local.mysql_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.mysql_dynamic_group_name
        description        = "Defines all MySQL DB Systems for Lakehouse access"
        matching_rule      = "resource.type = 'mysqldbsystem'"
      }
    } : {},
    var.create_exa == true ?
    {
      (local.exacs_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.exacs_dynamic_group_name
        description        = "Defines all ExaCS via compartment ocid"
        matching_rule      = "resource.compartment.id = '${module.cislz_compartments.compartments.EXACS-CMP.id}'"
      }
    } : {},
    var.create_di == true ?
    {
      (local.data_catalog_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.data_catalog_dynamic_group_name
        description        = "Defines all Data Catalog via resource type"
        matching_rule      = "any {resource.type='datacatalog', resource.type='datacatalogprivateendpoint', resource.type='datacatalogmetastore'}"
      }
    } : {},
    var.create_oic == true ?
    {
      (local.oic_rp_dynamic_group_key) = {
        identity_domain_id = var.default_domain_ocid
        name               = local.oic_rp_dynamic_group_name
        description        = "Defines all OIC Instances by Resource ID (OAUTH APPID)"
        matching_rule      = "any {resource.id='xxx', resource.id='yyy', resource.id='zzz'}"
      }
    } : {},

  )

  # Merge all DGs into one config
  identity_domain_dynamic_groups_configuration = {
    dynamic_groups : local.all_dynamic_groups
  }
}
