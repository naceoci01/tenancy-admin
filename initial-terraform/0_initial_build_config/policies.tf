# Build variables for CISLZ Policies

locals {
  # Policies
  core_policy_group_name              = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_group_name}'"
  core_policy_ds_group_name           = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_datascience_group_name}'"
  core_policy_mysql_group_name        = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_mysql_group_name}'"
  core_policy_postgres_group_name     = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_postgres_group_name}'"
  core_policy_oac_group_name          = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_oac_group_name}'"
  core_policy_exacs_admin_group_name  = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_exacs_group_name}'"
  core_policy_gg_admin_group_name     = "'${data.oci_identity_domain.ce_domain.display_name}'/'GGS_Administrator'"
  core_policy_oic_admin_group_name    = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_oic_group_name}'"
  core_policy_fw_admin_group_name     = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_firewall_group_name}'"
  core_policy_di_user_group_name      = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_di_group_name}'"
  core_policy_idl_user_group_name     = "'${data.oci_identity_domain.ce_domain.display_name}'/'${var.engineer_idl_group_name}'"
  
  core_policy_engineer_compartment    = module.cislz_compartments.compartments.CLOUD-ENG.name
  core_policy_shared_compartment      = module.cislz_compartments.compartments.SHARED-CMP.name
  core_policy_datascience_compartment = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.DS-CMP.name}"
  core_policy_mysql_compartment       = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.MYSQL-CMP.name}"
  core_policy_postgres_compartment    = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.POSTGRES-CMP.name}"
  core_policy_oac_compartment         = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.OAC-CMP.name}"
  core_policy_oic_compartment         = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.OIC-CMP.name}"
  core_policy_exacs_compartment       = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.EXACS-CMP.name}"
  core_policy_oda_compartment         = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.ODA-CMP.name}"
  core_policy_gg_compartment          = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.GG-CMP.name}"
  core_policy_fw_compartment          = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.FW-CMP.name}"
  core_policy_di_compartment          = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.DI-CMP.name}"
  core_policy_idl_compartment         = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.IDL-CMP.name}"
  core_policy_fsdr_compartment        = "${local.core_policy_shared_compartment}:${module.cislz_compartments.compartments.FSDR-CMP.name}"
  core_policy_engineer_ocid           = module.cislz_compartments.compartments.CLOUD-ENG.id
  default_domain_name                 = "Default"

  policies = merge(
    {
      "CE-IAM-ROOT-POLICY" : {
        name : "cloud-engineering-IAM-policy"
        description : "Cloud Engineers IAM permissions"
        compartment_id : "TENANCY-ROOT" # Instead of an OCID, you can replace it with the string "TENANCY-ROOT" for attaching the policy to the Root compartment.
        statements : [
          "allow group ${local.core_policy_group_name} to manage dynamic-groups in TENANCY where ALL { target.resource.domain.name='${local.cloud_engineering_domain_name}', request.permission != 'DYNAMIC_GROUP_DELETE' } //Allows Cloud Engineers only to modify DG within their domain",
          "allow group ${local.core_policy_group_name} to manage policies in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers only to manage policies in CE hierarchy",
          "allow group ${local.core_policy_group_name} to manage compartments in compartment ${local.core_policy_engineer_compartment} where target.resource.compartment.tag.Oracle-Tags.AllowCompartmentCreation = 'true' //Allows Cloud Engineers manage compartments within main CE Compartment, but not main CE",
          "allow group ${local.core_policy_group_name} to manage tickets in TENANCY //Allows Cloud Engineers manipulate tickets",
          "allow group ${local.core_policy_group_name} to read all-resources in TENANCY //CE can read ALL - showoci",
          "allow group ${local.core_policy_group_name} to manage tag-defaults in compartment cloud-engineering //Allow Cloud Engineers to set compartment tag defaults",
          "allow group ${local.core_policy_group_name} to manage tag-namespaces in compartment cloud-engineering //Allow Cloud Engineers to manage tag namespaces in the CE Compartments",
        ]
      }
    },
    {
      "CE-COST-POLICY" : {
        name : "cloud-engineering-COST-policy"
        description : "Cloud Engineers Cost Policies"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "define tenancy usage-report as ocid1.tenancy.oc1..aaaaaaaamhmra7tjzxzaronywihwj4ibgnifs27nxr5nvemeemmwtrtatr2q",
          "endorse group ${local.core_policy_group_name} to read objects in tenancy usage-report",
          "allow group ${local.core_policy_group_name} to manage usage-report in tenancy //Allow CE to save cost reports",
        ]
      }
    },
    {
      "CE-SERVICES-POLICY" : {
        name : "cloud-engineering-SERVICE-policy"
        description : "Cloud Engineers Service Enablement permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to use loganalytics-resources-family in TENANCY //Allows Cloud Engineers to use Logging Analytics",
          "allow group ${local.core_policy_group_name} to use loganalytics-features-family in TENANCY //Allows Cloud Engineers to use Logging Analytics",
          "allow group ${local.core_policy_group_name} to manage loganalytics-resources-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to work Logging Analytics",
          "allow group ${local.core_policy_group_name} to manage loganalytics-features-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to work Logging Analytics",
          "allow group ${local.core_policy_group_name} to manage serviceconnectors in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Service Connector Hub",
          "allow group ${local.core_policy_group_name} to manage stream-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use OCI Streaming",
          "allow group ${local.core_policy_group_name} to manage logging-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use OCI Logging",
          "allow group ${local.core_policy_group_name} to manage email-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use email",
          "allow group ${local.core_policy_group_name} to manage ons-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use notifications and topics",
          "allow group ${local.core_policy_group_name} to manage api-gateway-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use notifications and topics",
          "allow group ${local.core_policy_group_name} to manage cloudevents-rules in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Event Rules",
          "allow group ${local.core_policy_group_name} to manage cloud-guard-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Cloud Guard",
          "allow group ${local.core_policy_group_name} to manage orm-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use ORM Stacks",
          "allow group ${local.core_policy_group_name} to use marketplace-listings in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use ORM Stacks (Marketplace)",
          "allow group ${local.core_policy_group_name} to manage waf-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Web App Firewall (WAF)",
          "allow group ${local.core_policy_group_name} to manage queues in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Queues Service",
          "allow group ${local.core_policy_group_name} to manage vcns in compartment ${local.core_policy_shared_compartment} where request.operation!='CreateVcn' //Allow CE to use shared bastion",
          "allow group ${local.core_policy_group_name} to use bastion in compartment ${local.core_policy_shared_compartment} //Allow CE to use shared bastion",
          "allow group ${local.core_policy_group_name} to manage bastion-session in compartment ${local.core_policy_shared_compartment} //Allow CE to manage bastion sessions",
          "allow group ${local.core_policy_group_name} to manage bastion-session in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage bastion sessions in CE Main",
          "allow group ${local.core_policy_group_name} to manage operator-control-family in compartment ${local.core_policy_shared_compartment} //Allow CE to manage Operator Access Control (demo)",
          "allow group ${local.core_policy_group_name} to use agcs-instance in compartment ${local.core_policy_shared_compartment} //Allow CE to use Organization Governance in Shared comp",
          "allow group ${local.core_policy_group_name} to use cloud-shell in TENANCY //Required tenancy-level for Cloud Shell",
          "allow group ${local.core_policy_group_name} to use cloud-shell-public-network in TENANCY //Required tenancy-level for Cloud Shell",
          "allow group ${local.core_policy_group_name} to manage resource-schedule-family in compartment ${local.core_policy_engineer_compartment} //Allow Cloud Engineers to control Vulnerability Scanning in CE Main compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.resource_dynamic_group_name}' to manage functions-family in compartment ${local.core_policy_engineer_compartment} //Allow Dynamic Group for Resource Scheduler to manipulate Functions in CE Main compartment",
        ]
      }
    },
    {
      "CE-FSDR-POLICY" : {
        name : "cloud-engineering-FSDR-policy"
        description : "Full Stack Disaster Recovery Service permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage disaster-recovery-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to use Full Stack DR Service in CE Compartment",
          "allow group ${local.core_policy_group_name} to {DISASTER_RECOVERY_PLAN_PRECHECK_CREATE, DISASTER_RECOVERY_PLAN_EXECUTION_CREATE, INSTANCE_POWER_ACTIONS, INSTANCE_UPDATE} in compartment ${local.core_policy_fsdr_compartment} //Allows Cloud Engineers to use Full Stack DR Service in limited fashion in Shared Comp",
          "allow group ${local.core_policy_group_name} to manage objects in compartment ${local.core_policy_fsdr_compartment} //Allows Cloud Engineers to use Full Stack DR Service in limited fashion in Shared Comp",
          "allow group ${local.core_policy_group_name} to manage instance-agent-command-family in compartment ${local.core_policy_fsdr_compartment} //Allows Cloud Engineers to use Full Stack DR Service in limited fashion in Shared Comp",
          "allow dynamic-group 'Default'/'all-instances' to manage instance-agent-command-family in compartment ${local.core_policy_engineer_compartment} // For FSDR to use DGs to run instance command in CE Main compartment",
          "allow dynamic-group 'Default'/'all-instances' to manage instance-agent-command-family in compartment ${local.core_policy_fsdr_compartment} // For FSDR to use DGs to run instance command",
          "allow dynamic-group 'Default'/'all-instances' to manage instance-agent-command-execution-family in compartment ${local.core_policy_engineer_compartment} // For FSDR to use DGs to see instance command output",
          "allow dynamic-group 'Default'/'all-instances' to manage instance-agent-command-execution-family in compartment ${local.core_policy_fsdr_compartment} // For FSDR to use DGs to see instance command output",
          "allow dynamic-group 'Default'/'all-instances' to manage objects in compartment ${local.core_policy_engineer_compartment} //Instances to record command output to OSS",
          "allow dynamic-group 'Default'/'all-instances' to manage objects in compartment ${local.core_policy_fsdr_compartment} //Instances to record command output to OSS",
        ]
      }
    },
    {
      "CE-VSS-POLICY" : {
        name : "cloud-engineering-VSS-policy"
        description : "Vulnerability Scanning Service permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage vss-family in compartment ${local.core_policy_engineer_compartment} //Allow Cloud Engineers to control Vulnerability Scanning in CE Main compartment",
          "allow service vulnerability-scanning-service to read compartments in tenancy //VSS to read compartments",
          "allow service vulnerability-scanning-service to read repos in tenancy //VSS Read OCIR Repos",
          "allow service vulnerability-scanning-service to manage instances in tenancy //VSS Instances",
          "allow service vulnerability-scanning-service to read vnics in tenancy //VSS VNICs",
          "allow service vulnerability-scanning-service to read vnic-attachments in tenancy //VSS VNICs",
        ]
      }
    },
    {
      "CE-VPNA-POLICY" : {
        name : "cloud-engineering-VPNA-policy"
        description : "Network Path Analyzer Service permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage vn-path-analyzer-test in compartment ${local.core_policy_engineer_compartment} //Allow Cloud Engineers to control Virtual Network Path Analyzer in CE Main compartment",
          "allow group ${local.core_policy_group_name} to manage vn-path-analyzer-test in compartment ${local.core_policy_shared_compartment} //Allow Cloud Engineers to control Virtual Network Path Analyzer in Shared compartment",
          "allow any-user to inspect compartments in TENANCY where all { request.principal.type = 'vnpa-service' }",
          "allow any-user to read instances in TENANCY where all { request.principal.type = 'vnpa-service' }",
          "allow any-user to read virtual-network-family in TENANCY where all { request.principal.type = 'vnpa-service' }",
          "allow any-user to read load-balancers in TENANCY where all { request.principal.type = 'vnpa-service' }",
          "allow any-user to read network-security-group in TENANCY where all { request.principal.type = 'vnpa-service' }",
        ]
      }
    },
    {
      "CE-CORE-POLICY" : {
        name : "cloud-engineering-CORE-policy"
        description : "Cloud Engineers Core Service permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage instance-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage compute-management-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage instance-agent-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage instance-agent-command-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
          "allow dynamic-group all-instances to use instance-agent-command-execution-family in compartment ${local.core_policy_engineer_compartment} where request.instance.id=target.instance.id // Allows any instance to run commands via cloud agent",
          "allow dynamic-group all-instances to read objects in compartment ${local.core_policy_engineer_compartment} // Allows any instance to read objects in OSS (Scripts)",
          "Allow group ${local.core_policy_group_name} to manage metrics in compartment ${local.core_policy_engineer_compartment} // All Metrics in main CE Compartment",
          "allow group ${local.core_policy_group_name} to manage management-agents in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage management-agent-install-keys in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all compute within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage volume-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all block storage within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage virtual-network-family in compartment ${local.core_policy_engineer_compartment} where request.permission!='DRG_CREATE' //Allow CE to manage networking within main CE compartment - not DRG",
          "allow group ${local.core_policy_group_name} to manage load-balancers in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Load Balancers within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage certificate-authority-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Certificate Service within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage leaf-certificate-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Certificate Service within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage dns in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage all DNS within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to work with all object storage within main CE compartment",
          "allow group ${local.core_policy_group_name} to manage file-family in compartment ${local.core_policy_engineer_compartment} //Allows Cloud Engineers to manage FSS main CE compartment",
          "allow group ${local.core_policy_group_name} to use drgs in compartment ${local.core_policy_shared_compartment} //Allows Cloud Engineers to connect to DRG in shared CE compartment",
          "allow group ${local.core_policy_group_name} to read dns in compartment ${local.core_policy_shared_compartment} //Allows Cloud Engineers to see DNS Views in shared CE compartment",
          "allow group ${local.core_policy_group_name} to inspect tenancies in TENANCY where request.operation='GetTenancy' //Allows Cloud Engineers to see tenancy and home region details"
        ]
      }
    },
    {
      "CE-DB-POLICY" : {
        name : "cloud-engineering-DATABASE-policy"
        description : "Cloud Engineers Database Service permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage autonomous-database-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Autonomous main CE compartment",
          "allow group ${local.core_policy_group_name} to manage db-systems in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Base DB main CE compartment",
          "allow group ${local.core_policy_group_name} to manage nosql-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all NOSQL in main CE compartment",
          "allow group ${local.core_policy_group_name} to manage db-nodes in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Base DB main CE compartment",
          "allow group ${local.core_policy_group_name} to manage db-homes in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Base DB main CE compartment",
          "allow group ${local.core_policy_group_name} to manage db-backups in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Base DB main CE compartment",
          "allow group ${local.core_policy_group_name} to manage databases in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Base DB main CE compartment",
          "allow group ${local.core_policy_group_name} to manage pluggable-databases in compartment ${local.core_policy_engineer_compartment} //Allow CE to work with all Base Pluggable DB main CE compartment",
          "allow group ${local.core_policy_group_name} to manage data-safe-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to use Data Safe in Main CE Compartment",
          "allow group ${local.core_policy_group_name} to manage database-tools-connections in compartment cloud-engineering //Allow CE to work with SQL worksheets in main CE compartment",
          "allow group ${local.core_policy_group_name} to manage database-tools-connections in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to work with SQL worksheets in ExaCS compartment",
          "allow group ${local.core_policy_group_name} to use database-tools-private-endpoints in compartment ${local.core_policy_shared_compartment}:exacs //Allow CE to work with PE in ExaCS compartment",
          "allow group ${local.core_policy_group_name} to use database-tools-private-endpoints in compartment ${local.core_policy_shared_compartment} //Allow CE to work with PE in Shared compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.database_dynamic_group_name}' to use vaults in compartment ${local.core_policy_shared_compartment} // For DB Systems to read vaults for Customer KMS",
          "allow dynamic-group '${local.default_domain_name}'/'${local.database_dynamic_group_name}' to use keys in compartment ${local.core_policy_shared_compartment} // For DB Systems to use keys for Customer KMS"
        ]
      }
    },
    {
      "CE-DBMGMT-POLICY" : {
        name : "cloud-engineering-DBMGMT-policy"
        description : "Cloud Engineers Database Management permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to {DATABASE_SERVICE_USAGE_INSPECT} in TENANCY //Allow CE to read DBMGMT Usage",
          "allow group ${local.core_policy_group_name} to manage dbmgmt-family in compartment ${local.core_policy_engineer_compartment} where ALL { request.permission != 'DBMGMT_PRIVATE_ENDPOINT_DELETE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_CREATE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_UPDATE' } //Allow CE to use almost all DBMgmt in CE Compartment",
          "allow group ${local.core_policy_group_name} to manage dbmgmt-family in compartment ${local.core_policy_exacs_compartment} where ALL { request.permission != 'DBMGMT_PRIVATE_ENDPOINT_DELETE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_CREATE', request.permission != 'DBMGMT_PRIVATE_ENDPOINT_UPDATE' } //Allow CE to use almost all DBMgmt in ExaCS Compartment",
          "Allow service dpd to read secret-family in compartment ${local.core_policy_engineer_compartment} //Service Permission for Database management into CE Paaswords",
          "Allow service dpd to read secret-family in compartment ${local.core_policy_exacs_compartment} //Service Permission for Database management into ExaCS Passwords",
        ]
      }
    },
    {
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
          "allow service keymanagementservice to manage vaults in TENANCY //Required tenancy-level for KMS Vaults",
          "allow dynamic-group '${local.default_domain_name}'/'${local.certificate_dynamic_group_name}' to use keys in compartment ${local.core_policy_shared_compartment} //Allows certificate Service access to shared vault",
          "allow dynamic-group '${local.default_domain_name}'/'${local.certificate_dynamic_group_name}' to manage objects in compartment ${local.core_policy_shared_compartment} //Allows certificate Service access to shared vault and OSS",
        ]
      }
    },
    {
      "CE-OSMH-INST-POLICY" : {
        name : "cloud-engineering-OSMH-policy"
        description : "Cloud Engineers OS Management Hub permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to read osmh-family in TENANCY //Allow CE to load OSMH data",
          "allow group ${local.core_policy_group_name} to manage osmh-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to operate OSMH",
          "allow group ${local.core_policy_group_name} to manage osmh-scheduled-jobs in compartment ${local.core_policy_engineer_compartment} //Allow CE to run OSMH jobs",
          "allow dynamic-group '${local.default_domain_name}'/'${local.osmh_dynamic_group_name}' to {OSMH_MANAGED_INSTANCE_ACCESS} in TENANCY where request.principal.id = target.managed-instance.id //Required OSMH",
          "allow dynamic-group '${local.default_domain_name}'/'${local.osmh_dynamic_group_name}' to use metrics in TENANCY where target.metrics.namespace = 'oracle_appmgmt' //Required OSMH",
          "allow dynamic-group '${local.default_domain_name}'/'${local.osmh_dynamic_group_name}' to {MGMT_AGENT_DEPLOY_PLUGIN_CREATE, MGMT_AGENT_INSPECT, MGMT_AGENT_READ} in TENANCY where target.metrics.namespace = 'oracle_appmgmt' //Required OSMH",
          "allow dynamic-group '${local.default_domain_name}'/'${local.osmh_dynamic_group_name}' to {APPMGMT_MONITORED_INSTANCE_READ, APPMGMT_MONITORED_INSTANCE_ACTIVATE} in TENANCY where request.instance.id = target.monitored-instance.id //Required OSMH",
          "allow dynamic-group '${local.default_domain_name}'/'${local.osmh_dynamic_group_name}' to {INSTANCE_READ, INSTANCE_UPDATE} in TENANCY where request.instance.id = target.instance.id //Required OSMH",
          "allow dynamic-group '${local.default_domain_name}'/'${local.osmh_dynamic_group_name}' to {APPMGMT_WORK_REQUEST_READ, INSTANCE_AGENT_PLUGIN_INSPECT} in TENANCY //Required OSMH",
        ]
      }
    },
    {
      "CE-ADB-POLICY" : {
        name : "cloud-engineering-ADB-DG-policy"
        description : "Cloud Engineers ADB Dynamic Group permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow dynamic-group '${local.default_domain_name}'/'${local.adb_dynamic_group_name}' to use vaults in compartment ${local.core_policy_shared_compartment} //Allow ADB access to vaults",
          "allow dynamic-group '${local.default_domain_name}'/'${local.adb_dynamic_group_name}' to use keys in compartment ${local.core_policy_shared_compartment} //Allow ADB access to keys",
          "allow dynamic-group '${local.default_domain_name}'/'${local.adb_dynamic_group_name}' to manage objects in compartment ${local.core_policy_shared_compartment} //Allow ADB access read/write objects in CE Shared",
          "allow dynamic-group '${local.default_domain_name}'/'${local.adb_dynamic_group_name}' to use buckets in compartment ${local.core_policy_shared_compartment} //Allow ADB access use buckets in CE Shared",
        ]
      }
    },
    {
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
          "Allow group ${local.core_policy_group_name} to manage alarms in compartment ${local.core_policy_engineer_compartment}",
          "ALLOW DYNAMIC-GROUP all-stackmon-instances TO USE METRICS IN COMPARTMENT ${local.core_policy_engineer_compartment} where target.metrics.namespace = 'oracle_appmgmt'",
          "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {STACK_MONITORING_DISCOVERY_JOB_RESULT_SUBMIT} IN COMPARTMENT ${local.core_policy_engineer_compartment}",
          "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {MGMT_AGENT_DEPLOY_PLUGIN_CREATE, MGMT_AGENT_INSPECT, MGMT_AGENT_READ, APPMGMT_WORK_REQUEST_READ, INSTANCE_AGENT_PLUGIN_INSPECT} IN COMPARTMENT ${local.core_policy_engineer_compartment}",
          "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {APPMGMT_MONITORED_INSTANCE_READ, APPMGMT_MONITORED_INSTANCE_ACTIVATE} IN COMPARTMENT ${local.core_policy_engineer_compartment} where request.instance.id = target.monitored-instance.id",
          "ALLOW DYNAMIC-GROUP all-stackmon-instances TO {INSTANCE_UPDATE} IN COMPARTMENT ${local.core_policy_engineer_compartment} where request.instance.id = target.instance.id",
          "ALLOW GROUP ${local.core_policy_engineer_compartment} TO READ tag-namespaces IN TENANCY",
          "ALLOW GROUP ${local.core_policy_engineer_compartment} TO READ tag-defaults IN TENANCY"
        ]
      }
    },
    {
      "CE-ARS-POLICY" : {
        name : "cloud-engineering-ARS-policy"
        description : "Permissions for Autonomous Recovery Service"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow service database to manage recovery-service-family in TENANCY",
          "allow service database to manage tagnamespace in TENANCY",
          "allow service rcs to manage recovery-service-family in TENANCY",
          "allow service rcs to manage virtual-network-family in TENANCY",
          "allow group ${local.core_policy_group_name} to manage recovery-service-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Recovery Subnets in CE Compartment",
          "allow group ${local.core_policy_group_name} to manage recovery-service-family in compartment ${local.core_policy_exacs_compartment} //Allow CE to manage Recovery Subnets in Exacs Compartment",
        ]
      }
    },
    # Optional Policies

    var.create_func == true ? {
      "CE-FUNC-POLICY" : {
        name : "cloud-engineering-FUNCTIONS-policy"
        description : "Cloud Engineers Functions permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage repos in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage all Container Repos in main CE compartment",
          "allow group ${local.core_policy_group_name} to manage functions-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Functions in main CE compartment",
          "allow service faas to use apm-domains in TENANCY //Allow FAAS to use APM Tenancy-wide",
          "allow service faas to read repos in TENANCY where request.operation='ListContainerImageSignatures' //Allow FAAS to read repos",
          "allow service faas to {KEY_READ} in TENANCY where request.operation='GetKeyVersion' //Allow FAAS to read keys",
          "allow service faas to {KEY_VERIFY} in TENANCY where request.operation='Verify' //Allow FAAS to verify keys",
          "allow dynamic-group '${local.default_domain_name}'/'${local.func_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allow Functions DG to manage OSS in main CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.func_dynamic_group_name}' to manage ons-family in compartment ${local.core_policy_engineer_compartment} //Allow Functions DG to manage OSS in main CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.func_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allow Functions DG to manage OSS in main CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.func_dynamic_group_name}' to use secret-family in compartment ${local.core_policy_engineer_compartment} //Allow Functions DG use keys OSS in main CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.func_dynamic_group_name}' to use secret-family in compartment ${local.core_policy_shared_compartment} //Allow Functions DG to use keys in shared CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.func_dynamic_group_name}' to read all-resources in TENANCY //Allow Functions DG to READ everything in tenancy"
        ]
      },
    } : {}, #No policy Functions
    var.create_gg == true ? {
      "CE-GG-POLICY" : {
        name : "cloud-engineering-GOLDENGATE-policy"
        description : "Cloud Engineers GOldenGate permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage goldengate-connections in compartment ${local.core_policy_gg_compartment} //Allow CE to manage GoldenGate connections in shared GG compartment",
          "allow group ${local.core_policy_group_name} to manage goldengate-connection-assignments in compartment ${local.core_policy_gg_compartment} //Allow CE to manage GoldenGate assignments in shared GG compartment",
          "allow group ${local.core_policy_group_name} to manage vcns in compartment ${local.core_policy_gg_compartment} where request.permission='VCN_UPDATE' //Allow CE to add private views to shared VCN, for DNS resolution",
          "allow group ${local.core_policy_group_name} to use goldengate-deployments in compartment ${local.core_policy_gg_compartment} //Allow CE to use all GoldenGate deployments in shared GG compartment",
          "allow group ${local.core_policy_group_name} to use ons-topics in compartment ${local.core_policy_gg_compartment} //Allow CE to view ONS Topics in shared GG compartment",
          "allow group ${local.core_policy_group_name} to manage ons-subscriptions in compartment ${local.core_policy_gg_compartment} //Allow CE to Subscribe to Notifications in shared GG compartment",
          "allow group ${local.core_policy_gg_admin_group_name} to manage goldengate-family in compartment ${local.core_policy_gg_compartment} //Allow GG Admin in shared GG compartment",
          "allow group ${local.core_policy_gg_admin_group_name} to manage load-balancers in compartment ${local.core_policy_gg_compartment} //Allow GG Admin in shared GG compartment",
          "allow group ${local.core_policy_gg_admin_group_name} to manage logging-family in compartment ${local.core_policy_gg_compartment} //Allow GG Admin in shared GG compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.gg_dynamic_group_name}' to use keys in compartment ${local.core_policy_shared_compartment} //Allow GG DG to use keys in shared CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.gg_dynamic_group_name}' to use vault in compartment ${local.core_policy_shared_compartment} //Allow GG DG to use vault in shared CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.gg_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allow GG DG to manage OSS in main CE compartment",
          "allow service goldengate to {idcs_user_viewer, domain_resources_viewer} in TENANCY //GG Service to see domains",
        ]
      },
    } : {}, #No policy GG
    var.create_oic == true ? {
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
    } : {}, #No policy WLS
    var.create_oic == true ? {
      "CE-OIC-POLICY" : {
        name : "cloud-engineering-OIC-policy"
        description : "Permissions for Oracle Integration"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_oic_admin_group_name} to manage integration-instance in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage all OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage process-automation-instances in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage all Process Automation",
          "allow group ${local.core_policy_oic_admin_group_name} to read metrics in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to read all metrics in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage logging-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to set up Logging in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage visualbuilder-instance in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage VBCS",
          "allow group ${local.core_policy_oic_admin_group_name} to manage autonomous-database-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage ADB instances in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage api-gateway-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage ADB instances in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage object-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage OSS in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage functions-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage Functions in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage virtual-network-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage VCN in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage stream-family in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage Streams in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage cloudevents-rules in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage Event Rules in OIC",
          "allow group ${local.core_policy_oic_admin_group_name} to manage queues in compartment ${local.core_policy_oic_compartment} //Allow OIC Admins to manage Queues in OIC",
        ]
      },
      "CE-OIC-RP-POLICY" : {
        name : "cloud-engineering-OIC-RP-policy"
        description : "Permissions for Oracle Integration Resource Principal and Service Invocation"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow any-user to read all-resources in tenancy where request.principal.type='integrationinstance' // Broad read access for OIC Resource Principal to read anything in tenancy",
          "allow any-user to manage object-family in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP in ce compartment for object storage",
          "allow any-user to manage object-family in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP in OIC compartment for object storage",
          "allow any-user to use functions-family in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Functions in CE compartment",
          "allow any-user to use functions-family in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Functions in OIC compartment",
          "allow any-user to use api-gateway-family in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI APIGW in CE compartment",
          "allow any-user to use api-gateway-family in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI APIGW in OIC compartment",
          "allow any-user to use queues in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Queues in CE compartment",
          "allow any-user to use queues in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Queues in OIC compartment",
          "allow any-user to use ai-service-document-family in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Doc in CE compartment",
          "allow any-user to use ai-service-document-family in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Doc in OIC compartment",
          "allow any-user to use ai-service-speech-family in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Speech in CE compartment",
          "allow any-user to use ai-service-speech-family in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Speech in OIC compartment",
          "allow any-user to use ai-service-vision-family in compartment ${local.core_policy_engineer_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Vision in CE compartment",
          "allow any-user to use ai-service-vision-family in compartment ${local.core_policy_oic_compartment} where request.principal.type='integrationinstance' // Allow OIC instances to use RP for OCI Vision in OIC compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oic_rp_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allows Resource Principal to manage object family in CE compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oic_rp_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_oic_compartment} //Allows Resource Principal to manage object family in OIC compartment",
          # "allow dynamic-group 'oic-resource-principal-DG'
        ]
      },
      //allow dynamic-group 'cloud-engineering-domain'/'oic-resource-principal-dg' to manage ai-service-document-family in compartment cloud-engineering-shared:oic //allow oic instances to use resource principal in oic compartment for document understanding
    } : {}, #No policy OIC
    var.create_exa == true ? {
      "CE-EXACS-POLICY" : {
        name : "cloud-engineering-EXACS-policy"
        description : "Permissions for ExaCS"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage autonomous-databases in compartment ${local.core_policy_exacs_compartment} //ADB access for ADB-Dedicated",
          "allow group ${local.core_policy_group_name} to manage autonomous-database-family in compartment ${local.core_policy_exacs_compartment} //Allow CE to work with all Autonomous in ExaCS compartment",
          "allow group ${local.core_policy_group_name} to manage databases in compartment ${local.core_policy_exacs_compartment} //Allow CE to manage databases Resources",
          "allow group ${local.core_policy_group_name} to manage pluggable-databases in compartment ${local.core_policy_exacs_compartment} //Allow CE to manage databases Resources",
          "allow group ${local.core_policy_group_name} to use db-homes in compartment ${local.core_policy_exacs_compartment} //Allow CE to use database home Resources",
          "allow group ${local.core_policy_group_name} to use cloud-vmclusters in compartment ${local.core_policy_exacs_compartment} where all { request.permission != 'CLOUD_VM_CLUSTER_UPDATE_SSH_KEY' , request.permission != 'CLOUD_VM_CLUSTER_UPDATE' } //Allow CE to create databases in VM Cluster without Adding SSH Key",
          "allow group ${local.core_policy_group_name} to manage dbnode-console-connection in compartment ${local.core_policy_exacs_compartment} //Allow CE to create databases in VM Cluster",
          "allow group ${local.core_policy_group_name} to manage db-backups in compartment ${local.core_policy_exacs_compartment} //Allow CE to manage database backups for ExaCS",
          "allow group ${local.core_policy_group_name} to manage vnics in compartment ${local.core_policy_exacs_compartment} //Allow CE to use DBMGMT for ExaCS",
          "allow group ${local.core_policy_group_name} to use subnets in compartment ${local.core_policy_exacs_compartment} //Allow CE to use DBMGMT for ExaCS",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage cloudevents-rules in compartment ${local.core_policy_exacs_compartment} //Allows Cloud Engineers to use Event Rules for ExaCS",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage leaf-certificate-family in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Cert Leaf",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage certificate-authority-family in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Cert CA",
          "allow group ${local.core_policy_group_name} to use network-security-groups in compartment ${local.core_policy_exacs_compartment} //Allow CE to use DBMGMT for ExaCS",
          "allow group ${local.core_policy_group_name} to use bastion in compartment ${local.core_policy_exacs_compartment} //Allow CE to use existing bastion for ExaCS",
          "allow group ${local.core_policy_group_name} to manage bastion-session in compartment ${local.core_policy_exacs_compartment} //Allow CE to manage bastion sessions for ExaCS",
          "allow group ${local.core_policy_group_name} to use data-safe-family in compartment ${local.core_policy_exacs_compartment} //Allow CE to use Data Safe in ExaCS Compartment",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage dbmgmt-family in compartment ${local.core_policy_exacs_compartment} //Allow Admins to use all DBMgmt in ExaCS Compartment",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage cloud-vmclusters in compartment ${local.core_policy_exacs_compartment} //Allow Admins for ExaCS VM Cluster",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage exadb-vm-clusters in compartment ${local.core_policy_exacs_compartment} //Allow Admins for ExaScale VM Cluster",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage cloud-exadata-infrastructures in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Infra",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage db-homes in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage DB Homes",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage scheduling-policies in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Schedules",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage scheduling-windows in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Schedules",
          "allow group ${local.core_policy_exacs_admin_group_name} to manage scheduling-plans in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Schedules",
          # "allow group ${local.core_policy_exacs_admin_group_name} to manage scheduled-action in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Schedules",
          # "allow group ${local.core_policy_exacs_admin_group_name} to manage execution-windows in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Schedules",
          # "allow group ${local.core_policy_exacs_admin_group_name} to manage execution-action in compartment ${local.core_policy_exacs_compartment} //Allow Admins to manage Schedules",
          "allow dynamic-group '${local.default_domain_name}'/'${local.exacs_dynamic_group_name}' to manage keys in compartment ${local.core_policy_shared_compartment} //Allows DG for ExaCS to work with customer-managed keys",
          "allow dynamic-group '${local.default_domain_name}'/'${local.exacs_dynamic_group_name}' to read vaults in tenancy //Allows DG for ExaCS to work with vaults",
          "allow dynamic-group 'Default'/'all-exacs-DG' to use secret-family in compartment cloud-engineering-shared // Used for OKV managed keys",
          "allow dynamic-group 'Default'/'all-exacs-DG' to use keystores in compartment cloud-engineering-shared // used for OKC managed keys",
          "allow service database to read secret-family in compartment cloud-engineering-shared // Service level access to keys"
        ]
      }
    } : {}, #No policy EXACS
    var.create_oda == true ? {
      "CE-ODA-POLICY" : {
        name : "cloud-engineering-ODA-policy"
        description : "Permissions for Oracle Digital Assistant"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to use oda-family in compartment ${local.core_policy_oda_compartment} //Allow CE to Use GenAI Chat",
          "allow group ${local.core_policy_group_name} to use metrics in compartment ${local.core_policy_oda_compartment} //Allow CE to See Metrics for ODA",
          "allow group ${local.core_policy_group_name} to manage oda-private-endpoints in compartment ${local.core_policy_engineer_compartment} //Allow CE to Manage PE for ODA",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to manage genai-agent-family in compartment ${local.core_policy_engineer_compartment} //DG Access to AI Agents in CE Compartment",
          "allow any-user to manage genai-agent-family in tenancy where request.principal.type='odainstance'//Allows ODA instances to use GenAI",
          "allow any-user to manage genai-agent-family in tenancy where request.principal.type='autonomousdatabase'//Allows all ADBs to use GenAI",
          "allow any-user to read object-family in tenancy where request.principal.type='autonomousdatabase'//Allows ADBs to read objects",
          "allow any-user to manage object-family in tenancy where ALL { request.principal.type='autonomousdatabase', request.permission = 'PAR_MANAGE' }//Allows ADBs to manage PARs",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to manage genai-agent-family in compartment ${local.core_policy_oda_compartment} //DG Access to AI Agents in ODA Compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_engineer_compartment} //DG Access to OSS in CE Coompartments",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_oda_compartment} //DG Access to OSS in ODA compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to manage agent-family in compartment ${local.core_policy_engineer_compartment} //DG Access to AI Agents in CE Compartments",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to manage agent-family in compartment ${local.core_policy_oda_compartment} //DG Access to AI Agents",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to use generative-ai-family in compartment ${local.core_policy_engineer_compartment} //DG Access to Generative AI in CE Compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to use generative-ai-family in compartment ${local.core_policy_oda_compartment} //DG Access to Generative AI in ODA Compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to use fn-invocation in compartment ${local.core_policy_engineer_compartment} //DG Access CE-written Functions",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oda_dynamic_group_name}' to use fn-invocation in compartment ${local.core_policy_oda_compartment} //DG Access Functions in ODA Compartment",
        ]
      },
    } : {}, #No policy ODA
    var.create_oac == true ? {
      "CE-OAC-POLICY" : {
        name : "cloud-engineering-OAC-policy"
        description : "Permissions for Oracle Analytics - please request admin access to group ${local.core_policy_oac_group_name}"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to use analytics-instances in compartment ${local.core_policy_oac_compartment} where request.operation!='StopAnalyticsInstance' // Allow CE to see and only start existing OAC in Shared OAC Compartment",
          "allow group ${local.core_policy_oac_group_name} to manage analytics-instances in compartment ${local.core_policy_oac_compartment} // Allow OAC Admin CE to use create OAC in Shared OAC Compartment",
          "allow group ${local.core_policy_oac_group_name} to manage analytics-instance-work-requests in compartment ${local.core_policy_oac_compartment} // Allow CE to use existing OAC in Shared OAC Compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to manage objects in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to manage OSS objects",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to read buckets in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to read OSS buckets",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to use ai-service-vision-family in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to use OCI Vision",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to use ai-service-document-family in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to use OCI Document Understanding",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to use ai-service-language-family in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to use OCI Language",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to use functions-family in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to use functions",
          "allow dynamic-group '${local.default_domain_name}'/'${local.oac_dynamic_group_name}' to use data-science-family in compartment ${local.core_policy_oac_compartment} //Allows OAC DG to use functions",
          "allow any-user to read buckets in compartment ${local.core_policy_oac_compartment} where request.principal.type='analyticsinstance' //Allow OAC to see buckets in OAC compartment",
          "allow any-user to read buckets in compartment ${local.core_policy_engineer_compartment} where request.principal.type='analyticsinstance' //Allow OAC to see buckets in CE compartment",
          "allow any-user to manage objects in compartment ${local.core_policy_oac_compartment} where request.principal.type='analyticsinstance' //Allow OAC to manage objects in OAC compartment",
          "allow any-user to manage objects in compartment ${local.core_policy_engineer_compartment} where request.principal.type='analyticsinstance' // OAC to manage objects in CE compartment",
        ]
      },
    } : {}, #No policy OAC
    var.create_ai == true ? {
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
          "allow any-user to use generative-ai-family in compartment ${local.core_policy_engineer_compartment} where any { request.principal.type = 'autonomousdatabase' } //Allow any ADB to use GenAI",
          "allow group ${local.core_policy_group_name} to manage genai-agent-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage GenAI Agents",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to inspect buckets in compartment ${local.core_policy_shared_compartment} //DG Access to object storage buckets in shared comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to inspect buckets in compartment ${local.core_policy_engineer_compartment} //DG Access to object storage buckets in engineer comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to {BUCKET_INSPECT, BUCKET_READ, OBJECT_INSPECT, OBJECT_READ, OBJECT_CREATE, OBJECT_OVERWRITE, PAR_MANAGE} in compartment ${local.core_policy_shared_compartment} //DG Access to object storage buckets in shared comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to {BUCKET_INSPECT, BUCKET_READ, OBJECT_INSPECT, OBJECT_READ, OBJECT_CREATE, OBJECT_OVERWRITE, PAR_MANAGE} in compartment ${local.core_policy_engineer_compartment} //DG Access to object storage buckets in engineer comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to read objects in compartment ${local.core_policy_engineer_compartment} //DG Access to object storage",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to use database-tools-family in compartment ${local.core_policy_shared_compartment} //DG Access to DB Tools in Shared Comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to use database-tools-family in compartment ${local.core_policy_engineer_compartment} //DG Access to DB Tools in Engineer Comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to read secret-family in compartment ${local.core_policy_shared_compartment} //DG access to Vault secrets in Shared Comp",
          "allow dynamic-group '${local.default_domain_name}'/'${local.genai_agent_group_name}' to read secret-family in compartment ${local.core_policy_engineer_compartment} //DG access to Vault secrets in Engineer Comp",
        ]
      },
      "CE-AI-POLICY" : {
        name : "cloud-engineering-AI-policy"
        description : "Permissions for AI Services"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to manage ai-service-vision-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Vision, including custom projects",
          "allow group ${local.core_policy_group_name} to manage ai-service-speech-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Speech",
          "allow group ${local.core_policy_group_name} to manage ai-service-language-family in compartment ${local.core_policy_engineer_compartment} where ALL {request.permission != 'AI_SERVICE_LANGUAGE_ENDPOINT_CREATE', request.permission != 'AI_SERVICE_LANGUAGE_MODEL_CREATE'}//Allow CE to manage Language (no endpoint)",
          "allow group ${local.core_policy_group_name} to manage ai-service-document-family in compartment ${local.core_policy_engineer_compartment} //Allow CE to manage Document Understanding",
        ]
      },
    } : {}, #No policy AI
    var.create_opensearch == true ? {
      "CE-OPENSEARCH-POLICY" : {
        name : "cloud-engineering-OPENSEARCH-policy"
        description : "Permissions for OpenSearch"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow dynamic-group '${local.default_domain_name}'/'all-functions-DG' to manage objects in compartment ${local.core_policy_shared_compartment}:OpenSearch //For Functions",
        ]
      }
    } : {}, #No policy Open Search
    var.create_ds == true ? {
      "CE-DS-POLICY" : {
        name : "cloud-engineering-DATASCIENCE-policy"
        description : "Permissions for Data Science - please request access to group cloud-engineering-datascience-users"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow service datascience to use virtual-network-family in TENANCY",
          "allow group ${local.core_policy_ds_group_name} to manage virtual-network-family in compartment ${local.core_policy_datascience_compartment} // Allow CE to set up Networking in DS Compartment",
          "allow group ${local.core_policy_ds_group_name} to manage data-science-family in compartment ${local.core_policy_datascience_compartment} // Allow CE to manage Data Science in DS Compartment",
          "allow group ${local.core_policy_ds_group_name} to manage object-family in compartment ${local.core_policy_datascience_compartment} // Allow CE to set up Object Storage in DS Compartment",
          "allow group ${local.core_policy_ds_group_name} to manage logging-family in compartment ${local.core_policy_datascience_compartment} // Allow CE to set up Logging in DS Compartment",
          "allow group ${local.core_policy_ds_group_name} to use metrics in compartment ${local.core_policy_datascience_compartment} // Allow CE to use metrics in DS Compartment",
          "allow group ${local.core_policy_group_name} to read data-science-family in compartment ${local.core_policy_datascience_compartment} //Allow CE to see Data Science and request access",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_datascience_compartment} //Allows DS DG to manage OSS",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to manage data-science-family in compartment ${local.core_policy_datascience_compartment} //Allows DS DG to use OSS",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to manage dataflow-family in compartment ${local.core_policy_datascience_compartment} //Allows DS DG to use OSS",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to use logging-family in compartment ${local.core_policy_datascience_compartment} //Allows DS DG to use Logging",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to read compartments in TENANCY //Required DG Policy Statement",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to read users in TENANCY //Required DG Policy Statement",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datascience_dynamic_group_name}' to read repos in TENANCY //Allows Data Science to Read and Pull Containers",
          "allow any-user to read objects in compartment ${local.core_policy_datascience_compartment} where request.principal.type='datasciencemodeldeployment' //Give DS Model Deployment Access to a Published Conda Bucket",
          "allow any-user to use log-content in compartment ${local.core_policy_datascience_compartment} where ALL {request.principal.type = 'datasciencemodeldeployment'} //Give Model Deployment Access to the Logging Service",
          "allow any-user to read objects in compartment ${local.core_policy_datascience_compartment} where request.principal.type='datasciencemodeldeployment' //Give Model Deployment Access to Object Storage Bucket in DS",
          "allow any-user to read objects in compartment ${local.core_policy_engineer_compartment} where request.principal.type='datasciencemodeldeployment' //Give Model Deployment Access to Object Storage Bucket in CE Main",
        ]
      },
      "CE-DL-POLICY" : {
        name : "cloud-engineering-DATALABEL-policy"
        description : "Permissions for Data Labeling"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_ds_group_name} to manage data-labeling-family in compartment ${local.core_policy_engineer_compartment} // Allow CE to set up Data Labeling in CE Compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datalabeling_dynamic_group_name}' to read objects in compartment ${local.core_policy_engineer_compartment} //Allows DL DG to read OSS",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datalabeling_dynamic_group_name}' to read buckets in compartment ${local.core_policy_engineer_compartment} //Allows DL DG to read OSS",
          "allow dynamic-group '${local.default_domain_name}'/'${local.datalabeling_dynamic_group_name}' to manage objects in compartment ${local.core_policy_engineer_compartment} //Allows DL DG to manage OSS objects",
        ]
      },
    } : {}, #No policy Data Science Data Labelling
    var.create_di == true ? {
      "CE-DI-POLICY" : {
        name : "cloud-engineering-DATAINTEGRATION-policy"
        description : "Permissions for Data Integration - please request access to group cloud-engineering-data-integration-users"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow service dataintegration to use virtual-network-family in compartment ${local.core_policy_engineer_compartment} // Allow DI Workspace to use a VCN in CE Compartment",
          "allow service dataintegration to use virtual-network-family in compartment ${local.core_policy_di_compartment} // Allow DI Workspace to use a VCN in Shared DI Compartment",
          "allow service dataintegration to use virtual-network-family in compartment ${local.core_policy_shared_compartment} // Allow DI Workspace to use a VCN in Shared Compartment",
          "allow group ${local.core_policy_di_user_group_name} to manage dis-workspaces in compartment ${local.core_policy_di_compartment} // DIS Workspaces in Shared Compartment",
          "allow group ${local.core_policy_di_user_group_name} to manage dis-work-requests in compartment ${local.core_policy_di_compartment} // DIS Workspaces in Shared Compartment",
          "allow any-user to use buckets in compartment ${local.core_policy_engineer_compartment} where request.principal.type='disworkspace' // DIS Workspace RP to access CE Buckets",
          "allow any-user to use buckets in compartment ${local.core_policy_di_compartment} where request.principal.type='disworkspace' // DIS Workspace RP to access Shared Buckets",
          "allow any-user to manage objects in compartment ${local.core_policy_engineer_compartment} where request.principal.type='disworkspace' // DIS Workspace RP to access CE Buckets",
          "allow any-user to manage objects in compartment ${local.core_policy_di_compartment} where request.principal.type='disworkspace' // DIS Workspace RP to access Shared Buckets",
          "allow any-user {PAR_MANAGE} in compartment ${local.core_policy_engineer_compartment} where request.principal.type='disworkspace' // ADB PAR Manage by DIS Workspace",
          "allow any-user {PAR_MANAGE} in compartment ${local.core_policy_di_compartment} where request.principal.type='disworkspace' // ADB PAR Manage by DIS Workspace",
          "allow any-user to read secret-bundles in compartment ${local.core_policy_shared_compartment} where request.principal.type = 'disworkspace' // DIS Workspace read Shared Vault",
          "allow any-user to manage dataflow-application in compartment ${local.core_policy_di_compartment} where request.principal.type = 'disworkspace' // DIS Workspace publish Data Flow",
          "allow any-user to read dataflow-private-endpoint in compartment ${local.core_policy_di_compartment} where request.principal.type = 'disworkspace' // DIS Workspace Read Data Flow Endpoint",
          "allow any-user to inspect compartments in tenancy where request.principal.type='disworkspace' //DIS Workspace inspect compartments",
          "allow any-user to read secret-bundles in compartment cloud-engineering where request.principal.type = 'disworkspace' // DIS Workspace read Shared Vault with secret in CE",
          "allow group ${local.core_policy_di_user_group_name} to manage dataflow-application in compartment ${local.core_policy_di_compartment} // Data Integration Users can create DF applications",
          "allow group ${local.core_policy_di_user_group_name} to manage dataflow-run in compartment ${local.core_policy_di_compartment} // Data Integration Users to manage Data Flow run",
          "allow group ${local.core_policy_di_user_group_name} to use dataflow-pool in compartment ${local.core_policy_di_compartment} // Data Integration Users to use Data Flow pool",
          # Add Data Flow RP-based "all-in-one" 
          "ALLOW ANY-USER TO {STREAM_INSPECT, STREAM_READ, STREAM_CONSUME} IN compartment ${local.core_policy_di_compartment} WHERE ALL {request.principal.type='dataflowrun'} //Data Flow Run use streams in DI compartment",
          "ALLOW ANY-USER TO MANAGE OBJECTS IN compartment ${local.core_policy_di_compartment} WHERE ALL {request.principal.type='dataflowrun'} //Data Flow Run use OSS in DI compartment",
          "ALLOW ANY-USER TO {STREAM_INSPECT, STREAM_READ, STREAM_CONSUME} IN compartment ${local.core_policy_engineer_compartment} WHERE ALL {request.principal.type='dataflowrun'} //Data Flow Run use streams in CE compartment",
          "ALLOW ANY-USER TO MANAGE OBJECTS IN compartment ${local.core_policy_engineer_compartment} WHERE ALL {request.principal.type='dataflowrun'} //Data Flow Run use OSS in CE compartment",
          # Data Catalog - all except manage
          "allow group ${local.core_policy_di_user_group_name} to manage data-catalog-family in compartment ${local.core_policy_di_compartment} where all {request.operation != 'CreateCatalog', request.operation != 'DeleteCatalog', request.operation != 'ChangeCatalogCompartment', request.operation != 'CreateMetastore', request.operation != 'DeleteMetastore', request.operation != 'ChangeMetastoreCompartment'} //Allow DI Engineers to manage data catalogs but not delete or create",
          "allow dynamic-group '${local.default_domain_name}'/'${local.data_catalog_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_di_compartment} //Allow Catalog and Metastore access to object storage in DI Compartment",
          "allow dynamic-group '${local.default_domain_name}'/'${local.data_catalog_dynamic_group_name}' to manage object-family in compartment ${local.core_policy_engineer_compartment} //Allow Catalog and Metastore access to object storage in CE Compartment",
        ]
      },
    } : {}, #No policy DI
    var.create_mysql == true ? {
      "CE-MYSQL-POLICY" : {
        name : "cloud-engineering-MYSQL-policy"
        description : "Permissions for MySQL Heatwave - please request access to group cloud-engineering-mysql-users"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow service mysql_dp_auth TO {AUTHENTICATION_INSPECT, GROUP_MEMBERSHIP_INSPECT, DYNAMIC_GROUP_INSPECT} IN TENANCY // Allow MySQL to use Mapped Proxy Users",
          "allow group ${local.core_policy_group_name} to use dbmgmt-mysql-family in compartment ${local.core_policy_mysql_compartment} // MySQL Management",
          "allow group ${local.core_policy_group_name} to use bastions in compartment ${local.core_policy_mysql_compartment} // MySQL Bastion Usage",
          "allow group ${local.core_policy_group_name} to manage bastion-sessions in compartment ${local.core_policy_mysql_compartment} // MySQL Bastion Usage",
          "allow group ${local.core_policy_mysql_group_name} to manage alarms in compartment ${local.core_policy_mysql_compartment} // Set up alarms for MySQL",
          "allow group ${local.core_policy_mysql_group_name} to manage virtual-network-family in compartment ${local.core_policy_mysql_compartment} // See Networking for MySQL",
          "allow group ${local.core_policy_mysql_group_name} to manage mysql-family in compartment ${local.core_policy_mysql_compartment} where request.operation != 'CreateDbSystem' // Start and Stop - no creation",
          "allow dynamic-group '${local.default_domain_name}'/'${local.mysql_dynamic_group_name}' to read buckets in compartment ${local.core_policy_mysql_compartment} //Allows MySQL DB Systems to read OSS buckets",
          "allow dynamic-group '${local.default_domain_name}'/'${local.mysql_dynamic_group_name}' to manage objects in compartment ${local.core_policy_mysql_compartment} //Allows MySQL DB Systems to read OSS buckets",
          "allow dynamic-group '${local.default_domain_name}'/'${local.mysql_dynamic_group_name}' to read buckets in compartment ${local.core_policy_engineer_compartment} //Allows MySQL DB Systems to read OSS buckets in CE Shared",
          "allow dynamic-group '${local.default_domain_name}'/'${local.mysql_dynamic_group_name}' to manage objects in compartment ${local.core_policy_engineer_compartment} //Allows MySQL DB Systems to read OSS buckets in CE Shared",
          "allow dynamic-group '${local.default_domain_name}'/'${local.mysql_dynamic_group_name}' to use generative-ai-chat in compartment ${local.core_policy_mysql_compartment} //Allows MySQL DB Systems to use GenAI",
          "allow dynamic-group '${local.default_domain_name}'/'${local.mysql_dynamic_group_name}' to use generative-ai-text-embedding in compartment ${local.core_policy_mysql_compartment} //Allows MySQL DB Systems to use GenAI",
        ]
      },
    } : {}, #No policy MYSQL
    var.create_postgres == true ? {
      "CE-POSTGRES-POLICY" : {
        name : "cloud-engineering-POSTGRES-policy"
        description : "Permissions for PostGres - please request access to group cloud-engineering-postgres-users"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to use bastions in compartment ${local.core_policy_postgres_compartment} // Postgres Bastion Usage",
          "allow group ${local.core_policy_group_name} to manage bastion-sessions in compartment ${local.core_policy_postgres_compartment} // Postgres Bastion Usage",
          "allow group ${local.core_policy_postgres_group_name} to manage postgres-db-systems in compartment ${local.core_policy_postgres_compartment} // Postgres Management",
          "allow group ${local.core_policy_postgres_group_name} to manage postgres-backups in compartment ${local.core_policy_postgres_compartment} // Postgres Management",
          "allow group ${local.core_policy_postgres_group_name} to manage postgres-configuration in compartment ${local.core_policy_postgres_compartment} // Postgres Management",
          "allow group ${local.core_policy_postgres_group_name} to manage virtual-network-family in compartment ${local.core_policy_postgres_compartment} // Postgres VCN Management",
        ]
      }
    } : {}, #No policy Postgres
    var.create_firewall == true ? {
      "CE-FIREWALL-POLICY" : {
        name : "cloud-engineering-FIREWALL-policy"
        description : "Cloud Engineers Network Firewall permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_fw_admin_group_name} to manage virtual-network-family in compartment ${local.core_policy_fw_compartment} //Allow CE to work with VCN in Firewall compartment",
          "allow group ${local.core_policy_fw_admin_group_name} to manage network-firewall-family in compartment ${local.core_policy_fw_compartment} //Allow CE to work with OCI FW in Firewall compartment",
          "allow group ${local.core_policy_group_name} to manage instance-family in compartment ${local.core_policy_fw_compartment} //Allow CE to create instances in Firewall compartment",
          "allow group ${local.core_policy_group_name} to use vnics in compartment ${local.core_policy_fw_compartment} //Allow CE to create instances with VNIC in Firewall compartment",
        ]
      }
    } : {}, #No policy FW
    var.create_idl == true ? {
      "CE-DATALAKE-POLICY" : {
        name : "cloud-engineering-DATALAKE-policy"
        description : "Cloud Engineers Intelligent Data Lake permissions"
        compartment_id : "TENANCY-ROOT"
        statements : [
          "allow group ${local.core_policy_group_name} to use datalakes in compartment ${local.core_policy_idl_compartment} //Allow CE to use existing Data Lakes in shared compartment",
          "allow any-user to {AUTHENTICATION_INSPECT, GROUP_MEMBERSHIP_INSPECT, DYNAMIC_GROUP_INSPECT, GROUP_INSPECT, USER_INSPECT, USER_READ,  DOMAIN_INSPECT, DOMAIN_READ} IN TENANCY where all {request.principal.type='datalake'} //Allow IDL to do basic IAM introspection",
          "allow any-user to manage log-groups in compartment ${local.core_policy_idl_compartment} where ALL { request.principal.type='datalake'} //Allow IDL to manage logs in shared compartment",
          "allow any-user to read log-content in compartment ${local.core_policy_idl_compartment} where ALL { request.principal.type='datalake'} //Allow IDL to manage logs in shared compartment",
          "allow any-user to use metrics in compartment ${local.core_policy_idl_compartment} where ALL { request.principal.type='datalake', target.metrics.namespace='oracle_datalake'} //Allow IDL to use metrics in shared compartment",
          "allow any-user to {TAG_NAMESPACE_CREATE, TAG_NAMESPACE_INSPECT, TAG_NAMESPACE_READ} in TENANCY where ALL { request.principal.type='datalake'} //Allow IDL to work with necessary tags in tenancy",
          "allow any-user to manage tag-namespaces in TENANCY where all { request.principal.type = 'datalake', target.tag-namespace.name = 'datalake-managed-resources' } //Allow IDL to work with its own tag namespace",
          "allow any-user to manage buckets in compartment ${local.core_policy_idl_compartment} where all { request.principal.type='datelake', any { request.permission = 'BUCKET_CREATE', request.permission = 'BUCKET_UPDATE', request.permission = 'BUCKET_INSPECT', request.permission = 'BUCKET_READ' }} //IDL OSS Permissions",
          "allow any-user to manage buckets in compartment ${local.core_policy_idl_compartment} where all { request.principal.id=target.bucket.tag.datalake-managed-resources.governingdatalakeId, any {request.permission='BUCKET_DELETE', request.permission='PAR_MANAGE', request.permission='RETENTION_RULE_LOCK', request.permission='RETENTION_RULE_MANAGE'} } //IDL OSS Permissions",
          "allow any-user to read objectstorage-namespaces in TENANCY where all { request.principal.type='datalake', any {request.permission = 'OBJECTSTORAGE_NAMESPACE_READ'}} //IDL OSS Permissions",
          "allow any-user to manage objects in compartment ${local.core_policy_idl_compartment} where all { request.principal.id=target.bucket.tag.datalake-managed-resources.governingdatalakeId } //IDL OSS Permissions",
          "allow any-user to manage vnics in compartment ${local.core_policy_idl_compartment} where all { request.principal.type='datalake'} //Allow IDL to work with its own VCN",
          "allow any-user to use subnets in compartment ${local.core_policy_idl_compartment} where all { request.principal.type='datalake'} //Allow IDL to work with its own VCN",
          "allow any-user to use network-security-groups in compartment ${local.core_policy_idl_compartment} where all { request.principal.type='datalake'} //Allow IDL to work with its own VCN",
          "allow any-user to manage vnics in compartment ${local.core_policy_engineer_compartment} where all { request.principal.type='datalake'} //Allow IDL to work CE VCN",
          "allow any-user to use subnets in compartment ${local.core_policy_engineer_compartment} where all { request.principal.type='datalake'} //Allow IDL to work with CE VCN",
          "allow any-user to use network-security-groups in compartment ${local.core_policy_engineer_compartment} where all { request.principal.type='datalake'} //Allow IDL to work with CE VCN",
          "allow service objectstorage-${var.region} to manage object-family in compartment ${local.core_policy_idl_compartment} //OSS Permission",
          "allow service objectstorage-us-ashburn-1 to manage object-family in compartment ${local.core_policy_idl_compartment} //OSS Permission"
        ]
      }
    } : {}, #No policy for Intelligent Data Lake
    # End of policies block
  )

  # Merge all policies
  policies_configuration = {
    enable_cis_benchmark_checks : true
    supplied_policies : merge(local.policies)
  }
}
