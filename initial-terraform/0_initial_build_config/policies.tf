# Build variables for CISLZ Policies

locals {
  # Policies
  core_policy_group_name           = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_group_name}'"
  core_policy_engineer_compartment = module.cislz_compartments.compartments.CLOUD-ENG.name
  core_policy_shared_compartment   = module.cislz_compartments.compartments.SHARED-CMP.name

  policies = {
    "CE-IAM-ROOT-POLICY" : {
      name : "cloud-engineering-IAM-policy"
      description : "Cloud Engineers IAM permissions"
      compartment_id : "TENANCY-ROOT" # Instead of an OCID, you can replace it with the string "TENANCY-ROOT" for attaching the policy to the Root compartment.
      statements : [
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to manage dynamic-groups in tenancy where ALL { target.resource.domain.name='${local.cloud_engineering_domain_name}', request.permission != 'DYNAMIC_GROUP_DELETE' } //Allows Cloud Engineers only to modify DG within their domain",
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to manage policies in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers only to manage policies in CE hierarchy",
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to read policies in TENANCY //Allows Cloud Engineers only to read policies in entire tenancy",
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to read domains in TENANCY //Allows Cloud Engineers only to read domains in entire tenancy",
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to read dynamic-groups in TENANCY //Allows Cloud Engineers only to read DG in entire tenancy",
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to inspect compartments in TENANCY //Allows Cloud Engineers only to list compartments",
        "allow group '${local.cloud_engineering_domain_name}'/'${var.engineer_group_name}' to read quotas in TENANCY //Allows Cloud Engineers see quotas"
      ]
    },
    "CE-SERVICES-POLICY" : {
      name : "cloud-engineering-SERVICE-policy"
      description : "Cloud Engineers Service Enablement permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to use loganalytics-resources-family in tenancy //Allows Cloud Engineers to use Logging Analytics",
        "allow group ${local.core_policy_group_name} to use loganalytics-features-family in tenancy //Allows Cloud Engineers to use Logging Analytics",
        "allow group ${local.core_policy_group_name} to manage loganalytics-resources-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to work Logging Analytics",
        "allow group ${local.core_policy_group_name} to manage loganalytics-features-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to work Logging Analytics",
        "allow group ${local.core_policy_group_name} to manage serviceconnectors in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Service Connector Hub",
        "allow group ${local.core_policy_group_name} to manage stream-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use OCI Streaming",
        "allow group ${local.core_policy_group_name} to manage logging-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use OCI Logging",
        "allow group ${local.core_policy_group_name} to manage email-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use email",
        "allow group ${local.core_policy_group_name} to manage ons-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use notifications and topics",
        "allow group ${local.core_policy_group_name} to manage cloudevents-rules in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Event Rules",
        "allow group ${local.core_policy_group_name} to manage cloud-guard-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Cloud Guard",
        "allow group ${local.core_policy_group_name} to manage orm-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use ORM Stacks",
        "allow group ${local.core_policy_group_name} to read work-requests in tenancy //Required tenancy-level for KMS Vaults",
        "allow group ${local.core_policy_group_name} to use cloud-shell in tenancy //Required tenancy-level for Cloud Shell",
        "allow group ${local.core_policy_group_name} to use cloud-shell-public-network in tenancy //Required tenancy-level for Cloud Shell",
      ]
    },
    "CE-CORE-POLICY" : {
      name : "cloud-engineering-CORE-policy"
      description : "Cloud Engineers Core Service permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to read all-resources in compartment ${local.core_policy_engineer_compartment} //Allow CE to read everything main CE compartment",
        "allow group ${local.core_policy_group_name} to manage instance-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage compute-management-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage instance-agent-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage instance-agent-command-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
        "allow dynamic-group all-instances to use instance-agent-command-execution-family in compartment ${local.core_policy_engineer_compartment} where request.instance.id=target.instance.id // Allows any instance to run commands via cloud agent",
        "allow dynamic-group all-instances to read objects in compartment ${local.core_policy_engineer_compartment} // Allows any instance to read objects in OSS (Scripts)",
        "allow group ${local.core_policy_group_name} to manage management-agents in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage management-agent-install-keys in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage volume-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all block storage within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage virtual-network-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage networking within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage load-balancers in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Load Balancers within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage certificate-authority-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Certificate Service within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage leaf-certificate-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Certificate Service within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage dns in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage all DNS within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to work with all object storage within main CE compartment",
        "allow group ${local.core_policy_group_name} to manage file-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to manage FSS main CE compartment",
        "allow group ${local.core_policy_group_name} to use drgs in compartment ${local.core_policy_shared_compartment} //Allows Cloud Engineers to connect to DRG in shared CE compartment",
        "allow group ${local.core_policy_group_name} to read dns in compartment ${local.core_policy_shared_compartment} //Allows Cloud Engineers to see DNS Views in shared CE compartment",
      ]
    },
    "CE-DB-POLICY" : {
      name : "cloud-engineering-DATABASE-policy"
      description : "Cloud Engineers Database Service permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to manage autonomous-database-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Autonomous main CE compartment",
        "allow group ${local.core_policy_group_name} to read dbmgmt-family in tenancy //Allow CE to see all DBMgmt resources tenancy-wide",
        "allow group ${local.core_policy_group_name} to manage dbmgmt-family in compartment ${local.core_policy_engineer_compartment} where ALL { request.permission != 'DBMGMT_PRIVATE_ENDPOINT_DELETE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_CREATE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_UPDATE' } //Allow CE to use almost all DBMgmt in CE Compartment",
        "allow group ${local.core_policy_group_name} to manage dbmgmt-family in compartment ${local.core_policy_shared_compartment}:exacs where ALL { request.permission != 'DBMGMT_PRIVATE_ENDPOINT_DELETE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_CREATE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_UPDATE' } //Allow CE to use almost all DBMgmt in ExaCS Compartment",
        "allow group ${local.core_policy_group_name} to manage data-safe-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to use Data Safe in Main CE Compartment",
        "allow group ${local.core_policy_group_name} to manage data-safe-family in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to use Data Safe in ExaCS Compartment",
        "allow group ${local.core_policy_group_name} to manage database-tools-connections in compartment cloud-engineering //Allow CE to work with SQL worksheets in main CE compartment",
        "allow group ${local.core_policy_group_name} to manage database-tools-connections in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to work with SQL worksheets in ExaCS compartment",
        "Allow service dpd to read secret-family in compartment ${local.core_policy_shared_compartment} //Service Permission for Database management",
      ]
    },
    "CE-SEC-POLICY" : {
      name : "cloud-engineering-SECURITY-policy"
      description : "Cloud Engineers Security permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to use vaults in compartment ${local.core_policy_shared_compartment} //Allow CE to use vaults in shared CE compartment",
        "allow group ${local.core_policy_group_name} to manage keys in compartment ${local.core_policy_shared_compartment} //Allow CE to manage keys in shared CE compartment",
        "allow group ${local.core_policy_group_name} to manage secret-family in compartment ${local.core_policy_shared_compartment} //Allow CE to manage secrets in shared CE compartment",
        "allow group ${local.core_policy_group_name} to manage keys in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage keys in main CE compartment",
        "allow group ${local.core_policy_group_name} to manage secret-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage secrets in main CE compartment",
        "allow group ${local.core_policy_group_name} to use key-delegate in compartment ${local.core_policy_shared_compartment} //Allow CE to use key-delegate in shared CE compartment",
        "allow service keymanagementservice to manage vaults in tenancy //Required tenancy-level for KMS Vaults",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.certificate_dynamic_group_name}' to use keys in compartment ${local.core_policy_shared_compartment} //Allows certificate Service access to shared vault",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.certificate_dynamic_group_name}' to manage objects in compartment ${local.core_policy_shared_compartment} //Allows certificate Service access to shared vault and OSS",
      ]
    },
    "CE-OSMH-INST-POLICY" : {
      name : "cloud-engineering-OSMH-policy"
      description : "Cloud Engineers OS Management Hub permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to read osmh-family in tenancy //Allow CE to load OSMH data",
        "allow group ${local.core_policy_group_name} to manage osmh-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to operate OSMH",
        "allow group ${local.core_policy_group_name} to manage osmh-scheduled-jobs in compartment ${local.core_policy_engineer_compartment} //Allow CE to run OSMH jobs",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.osmh_dynamic_group_name}' to {OSMH_MANAGED_INSTANCE_ACCESS} in compartment ${module.cislz_compartments.compartments.CLOUD-ENG.name} where request.principal.id = target.managed-instance.id",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.osmh_dynamic_group_name}' to use metrics in compartment ${module.cislz_compartments.compartments.CLOUD-ENG.name} where target.metrics.namespace = 'oracle_appmgmt'",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.osmh_dynamic_group_name}' to {MGMT_AGENT_DEPLOY_PLUGIN_CREATE, MGMT_AGENT_INSPECT, MGMT_AGENT_READ} in compartment ${module.cislz_compartments.compartments.CLOUD-ENG.name} where target.metrics.namespace = 'oracle_appmgmt'",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.osmh_dynamic_group_name}' to {APPMGMT_MONITORED_INSTANCE_READ, APPMGMT_MONITORED_INSTANCE_ACTIVATE} in compartment ${module.cislz_compartments.compartments.CLOUD-ENG.name} where request.instance.id = target.monitored-instance.id",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.osmh_dynamic_group_name}' to {INSTANCE_READ, INSTANCE_UPDATE} in compartment ${module.cislz_compartments.compartments.CLOUD-ENG.name} where request.instance.id = target.instance.id",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.osmh_dynamic_group_name}' to {APPMGMT_WORK_REQUEST_READ, INSTANCE_AGENT_PLUGIN_INSPECT} in compartment ${module.cislz_compartments.compartments.CLOUD-ENG.name}",
      ]
    },
    "CE-WLS-INST-POLICY" : {
      name : "cloud-engineering-WLS-DG-policy"
      description : "Cloud Engineers WebLogic Stack permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow dynamic-group all-instances read secret-bundles in compartment ${local.core_policy_shared_compartment} //WLS Instances to read secrets",
        "allow dynamic-group all-instances manage instance-family in compartment ${local.core_policy_engineer_compartment} //WLS Instances to manage instances",
        "allow dynamic-group all-instances manage volume-family in compartment ${local.core_policy_engineer_compartment} //WLS Instances to manage volumes",
        "allow dynamic-group all-instances manage virtual-network-family in compartment ${local.core_policy_engineer_compartment} //WLS Instances to manage VCNs",
        "allow dynamic-group all-instances manage load-balancers in compartment ${local.core_policy_engineer_compartment} //WLS Instances to manage LB",
        "allow dynamic-group all-instances inspect database-family in compartment ${local.core_policy_engineer_compartment} //WLS Instances to see DB resources",
        "allow dynamic-group all-instances use autonomous-transaction-processing-family in compartment ${local.core_policy_engineer_compartment} //WLS Instances to use ATP",
        "allow dynamic-group all-instances use logging-family in compartment ${local.core_policy_engineer_compartment} //WLS Instances to use Logging",
      ]
    },
    "CE-ADB-POLICY" : {
      name : "cloud-engineering-ADB-DG-policy"
      description : "Cloud Engineers ADB Dynamic Group permissions"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.adb_dynamic_group_name}' to use vaults in compartment ${local.core_policy_shared_compartment} //Allow ADB access to vaults",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.adb_dynamic_group_name}' to use keys in compartment ${local.core_policy_shared_compartment} //Allow ADB access to keys",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.adb_dynamic_group_name}' to manage objects in compartment ${local.core_policy_shared_compartment} //Allow ADB access read/write objects in CE Shared",
        "allow dynamic-group '${local.cloud_engineering_domain_name}'/'${local.adb_dynamic_group_name}' to use buckets in compartment ${local.core_policy_shared_compartment} //Allow ADB access use buckets in CE Shared",
      ]
    },
    "CE-OIC-POLICY" : {
      name : "cloud-engineering-OIC-policy"
      description : "Permissions for Oracle Integration"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group '${local.cloud_engineering_domain_name}'/'OIC-Administrators' to manage integration-instance in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to manage all OIC",
        "allow group '${local.cloud_engineering_domain_name}'/'OIC-Administrators' to manage process-automation-instances in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to manage all Process Automation",
        "allow group '${local.cloud_engineering_domain_name}'/'OIC-Administrators' to read metrics in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to read all metrics in OIC",
        "allow group '${local.cloud_engineering_domain_name}'/'OIC-Administrators' to manage visualbuilder-instance in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to manage VBCS",
        "allow group ${local.core_policy_group_name} to read integration-instance in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to manage all OIC",
        "allow group ${local.core_policy_group_name} to read process-automation-instances in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to manage all Process Automation",
        "allow group ${local.core_policy_group_name} to read metrics in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to read all metrics in OIC",
        "allow group ${local.core_policy_group_name} to read visualbuilder-instance in compartment ${local.core_policy_shared_compartment}:OIC //Allow OIC Admins to manage VBCS",
      ]
    },
    "CE-EXACS-POLICY" : {
      name : "cloud-engineering-EXACS-policy"
      description : "Permissions for ExaCS"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to read database-family in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to see all ExaCS Resources",        
        "allow group ${local.core_policy_group_name} to manage autonomous-databases in compartment ${local.core_policy_shared_compartment}:exacs //ADB access for ADB-Dedicated",        
        "allow group ${local.core_policy_group_name} to read virtual-network-family in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to see all ExaCS VCN Resources",        
        "allow group ${local.core_policy_group_name} to manage databases in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to manage databases Resources",
        "allow group ${local.core_policy_group_name} to manage pluggable-databases in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to manage databases Resources",
        "allow group ${local.core_policy_group_name} to use db-homes in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to use database home Resources",
        "allow group ${local.core_policy_group_name} to use cloud-vmclusters in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to create databases in VM Cluster",
        "allow group ${local.core_policy_group_name} to manage backups in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to manage database backups for ExaCS",
        "allow group ${local.core_policy_group_name} to read metrics in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE see Metrics for ExaCS",
        "allow group ${local.core_policy_group_name} to read loganalytics-resources-family in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE see any Logging Analytics for ExaCS",
        "allow group ${local.core_policy_group_name} to manage vnics in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to use DBMGMT for ExaCS",
        "allow group ${local.core_policy_group_name} to use subnets in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to use DBMGMT for ExaCS",
        "allow group ${local.core_policy_group_name} to use network-security-groups in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to use DBMGMT for ExaCS",
        "Allow service dpd to read secret-family in compartment ${local.core_policy_engineer_compartment} //Service Permission for Database management"
        # move this
      ]
    },
    "CE-APM-POLICY" : {
      name : "cloud-engineering-APM-policy"
      description : "Service Permissions for APM and Stack Monitoring"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to manage appmgmt-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to run App Management and Resource Discovery",
        "allow group ${local.core_policy_group_name} to manage stack-monitoring-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to run Stack Monitoring",
        "Allow group ${local.core_policy_group_name} to manage apm-domains in compartment ${local.core_policy_engineer_compartment}",
        "Allow group ${local.core_policy_group_name} to manage management-dashboard in compartment ${local.core_policy_engineer_compartment}",
        "Allow group ${local.core_policy_group_name} to manage management-saved-search in compartment ${local.core_policy_engineer_compartment}",
        "Allow group ${local.core_policy_group_name} to manage metrics in compartment ${local.core_policy_engineer_compartment}",
        "Allow group ${local.core_policy_group_name} to manage alarms in compartment ${local.core_policy_engineer_compartment}",
        "ALLOW DYNAMIC-GROUP all-stackmon-instances TO USE METRICS IN COMPARTMENT ${local.core_policy_engineer_compartment} where target.metrics.namespace = 'oracle_appmgmt'",
        "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {STACK_MONITORING_DISCOVERY_JOB_RESULT_SUBMIT} IN COMPARTMENT ${local.core_policy_engineer_compartment}",
        "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {MGMT_AGENT_DEPLOY_PLUGIN_CREATE, MGMT_AGENT_INSPECT, MGMT_AGENT_READ, APPMGMT_WORK_REQUEST_READ, INSTANCE_AGENT_PLUGIN_INSPECT} IN COMPARTMENT ${local.core_policy_engineer_compartment}",
        "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {APPMGMT_MONITORED_INSTANCE_READ, APPMGMT_MONITORED_INSTANCE_ACTIVATE} IN COMPARTMENT ${local.core_policy_engineer_compartment} where request.instance.id = target.monitored-instance.id",
        "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {INSTANCE_UPDATE} IN COMPARTMENT ${local.core_policy_engineer_compartment} where request.instance.id = target.instance.id",
        "ALLOW GROUP ${local.core_policy_engineer_compartment} TO READ tag-namespaces IN TENANCY",
        "ALLOW GROUP ${local.core_policy_engineer_compartment} TO READ tag-defaults IN TENANCY"
      ]
    },
    "CE-GENAI-POLICY" : {
      name : "cloud-engineering-GENAI-policy"
      description : "Permissions for Generative AI"
      compartment_id : "TENANCY-ROOT"
      statements : [
        "allow group ${local.core_policy_group_name} to use generative-ai-chat in compartment ${local.core_policy_engineer_compartment} //Allow CE to Use GenAI Chat",        
        "allow group ${local.core_policy_group_name} to use generative-ai-text-generation in compartment ${local.core_policy_engineer_compartment} //Allow CE to Use GenAI Text",        
        "allow group ${local.core_policy_group_name} to use generative-ai-text-summarization in compartment ${local.core_policy_engineer_compartment} //Allow CE to Use GenAI Text Summarization",        
        "allow group ${local.core_policy_group_name} to use generative-ai-text-embedding in compartment ${local.core_policy_engineer_compartment} //Allow CE to Use GenAI Text Embedding",        
        "allow group ${local.core_policy_group_name} to read generative-ai-work-request in compartment ${local.core_policy_engineer_compartment} //Allow CE to read GenAI Work requests",        
      ]
    },
  }

  # Merge all policies
  policies_configuration = {
    enable_cis_benchmark_checks : true
    supplied_policies : merge(local.policies)
  }
}
