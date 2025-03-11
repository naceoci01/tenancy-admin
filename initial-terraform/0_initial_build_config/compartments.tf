# Create top-level compartments in ROOT compartment

locals {

  oac_comp = var.create_oac ? {
    OAC-CMP = {
      name        = "OAC",
      description = "Oracle Analytics Cloud"
    }
  } : {}
  oic_comp = var.create_oic ? {
    OIC-CMP = {
      name        = "OIC",
      description = "Oracle Integration Cloud"
    }
  } : {}
  oda_comp = var.create_oda ? {
    ODA-CMP = {
      name        = "ODA",
      description = "Oracle Digital Assistant"
    }
  } : {}
  mysql_comp = var.create_mysql ? {
    MYSQL-CMP = {
      name        = "MySQL",
      description = "Shared Heatwave"
    }
  } : {}
  exacs_comp = var.create_exa ? {
    EXACS-CMP = {
      name        = "ExaCS",
      description = "Oracle Exadata Cloud Service"
    }
  } : {}
  pg_comp = var.create_postgres ? {
    POSTGRES-CMP = {
      name        = "Postgres",
      description = "Shared Postgres"
    }
  } : {}
  ds_comp = var.create_ds ? {
    DS-CMP = {
      name        = "DataScience",
      description = "Shared Data Science"
    }
  } : {}
  opensearch_comp = var.create_opensearch ? {
    OS-CMP = {
      name        = "OpenSearch",
      description = "Shared OpenSearch"
    }
  } : {}
  di_comp = var.create_opensearch ? {
    DI-CMP = {
      name        = "DataIntegration",
      description = "Shared Data Integration"
    }
  } : {}
  firewall_comp = var.create_firewall ? {
    FW-CMP = {
      name        = "Firewall",
      description = "Shared Network Firewall"
    }
  } : {}
  gg_comp = var.create_gg ? {
    GG-CMP = {
      name        = "GoldenGate",
      description = "Shared GoldenGate"
    }
  } : {}


  children = merge(local.oac_comp, local.oic_comp, local.exacs_comp,
    local.pg_comp, local.ds_comp, local.mysql_comp,
    local.opensearch_comp, local.firewall_comp, local.gg_comp, local.oda_comp)

  all_comp = {
    CLOUD-ENG = {
      name        = "${var.engineer_compartment_base_name}",
      description = "Top level compartment for all cloud engineers",
    },
    SPECIAL-CMP = {
      name        = "${var.engineer_compartment_base_name}-specialprojects",
      description = "Special project compartments",
    },
    SHARED-CMP = {
      name        = "${var.engineer_compartment_base_name}-shared",
      description = "Shared compartment for all cloud engineers - limited access",
      children    = local.children
    }
  }

  # Place any created compartments in the defined top compartment
  compartments_configuration = {
    default_parent_id : var.tenancy_ocid
    enable_delete : false
    compartments : local.all_comp
  }

}
