
# Copyright (c) 2023 Oracle and/or its affiliates.
# Licensed under the Universal Permissive License v 1.0 as shown at https://oss.oracle.com/licenses/upl.

locals {

  # Keys and names
  osmh_dynamic_group_key         = "OSMH-DYN-GROUP"
  osmh_dynamic_group_name        = "all-osmh-instances"
  adb_dynamic_group_key          = "ADB-DYN-GROUP"
  adb_dynamic_group_name         = "all-adb-instances"
  stackmon_dynamic_group_key     = "STACKMON-DYN-GROUP"
  stackmon_dynamic_group_name    = "all-stackmon-instances"
  certificate_dynamic_group_key  = "CERT-AUTH-DYN-GROUP"
  certificate_dynamic_group_name = "CertificateAuthority-DG"
  gg_dynamic_group_key         = "GG-DYN-GROUP"
  gg_dynamic_group_name        = "all-goldengate-deployments-DG"
  func_dynamic_group_key         = "FUNC-DYN-GROUP"
  func_dynamic_group_name        = "all-functions-DG"  
  genai_agent_dynamic_group_key  = "GENAI-DYN-GROUP"
  genai_agent_group_name        = "all-genai-agents-DG"
  datascience_dynamic_group_key  = "DS-DYN-GROUP"
  datascience_dynamic_group_name = "all-datascience-DG"
  datalabeling_dynamic_group_key  = "DL-DYN-GROUP"
  datalabeling_dynamic_group_name = "all-datalabeling-DG"
  oac_dynamic_group_key  = "OAC-DYN-GROUP"
  oac_dynamic_group_name = "all-oac-instance-DG"
  oda_dynamic_group_key  = "ODA-DYN-GROUP"
  oda_dynamic_group_name = "all-oda-instance-DG"

  # Dynamic Groups
  all_dynamic_groups = {
    (local.osmh_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.osmh_dynamic_group_name
      description        = "Allows any instance to be an OSMH instance"
      matching_rule      = "ANY {ALL {resource.type='managementagent', resource.compartment.id != 'xxxx'}, instance.compartment.id != 'xxxx'}"
    },
    (local.adb_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.adb_dynamic_group_name
      description        = "Allows any instance to be an ADB instance - Resource Principal"
      matching_rule      = "resource.type='autonomousdatabase'"
    },
    (local.stackmon_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.stackmon_dynamic_group_name
      description        = "Allows any Stackmon instance to be part of this DG"
      matching_rule      = "ANY {ALL {resource.type='managementagent', resource.compartment.id !='xxxx'}, ALL {instance.compartment.id != 'xxxx'} }"
    },
    (local.certificate_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.certificate_dynamic_group_name
      description        = "For use by Certificates Service - creating a CA"
      matching_rule      = "resource.type='certificateauthority'"
    },
    (local.gg_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.gg_dynamic_group_name
      description        = "Defines all GoldenGate Deployments"
      matching_rule      = "resource.type = 'goldengatedeployment'"
    },
    (local.func_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.func_dynamic_group_name
      description        = "Defines all OCI Functions"
      matching_rule      = "resource.type = 'fnfunc'"
    },
    (local.genai_agent_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.genai_agent_group_name
      description        = "Defines all OCI GenaAI Agents or Ingestion Jobs"
      matching_rule      = "ANY {resource.type = 'genaiagent', resource.type='genaiagentdataingestionjob'}"
    },
    (local.datascience_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.datascience_dynamic_group_name
      description        = "Defines all OCI Data Science"
      matching_rule      = "Any {resource.type='datasciencenotebooksession',resource.type='dataflow-family',resource.type='datasciencemodeldeployment',resource.type='datasciencejobrun'}"
    },
    (local.datalabeling_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.datalabeling_dynamic_group_name
      description        = "Defines all OCI Data Labeling"
      matching_rule      = "resource.type='datalabelingdataset'"
    },
    (local.oac_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.oac_dynamic_group_name
      description        = "Defines all OAC Instances"
      matching_rule      = "resource.type='xxxx'"
    },
    (local.oda_dynamic_group_key) = {
      identity_domain_id = var.default_domain_id
      name               = local.oda_dynamic_group_name
      description        = "Defines all ODA Instances"
      matching_rule      = "resource.type='odainstance'"
    }   
  }

#resource.type='odainstance'
  # Merge all DGs into one config
  identity_domain_dynamic_groups_configuration = {
    # dynamic_groups : merge(local.engineer_dg, local.osmh_dynamic_group)
    dynamic_groups : local.all_dynamic_groups
  }
}
