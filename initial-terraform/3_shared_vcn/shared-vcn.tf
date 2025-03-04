locals {

  network_configuration = {
    default_compartment_id = var.compartment_ocid

    network_configuration_categories = {
      shared = {
        category_freeform_tags = {
          "test-tag" = "shared"
        }

        non_vcn_specific_gateways = var.is_attach_drg ? {
          dynamic_routing_gateways = {
            DRG-KEY = {
              display_name = "region-drg"
              drg_attachments = {
                DRG-VCN-ATTACH-VISION-KEY = {
                  display_name = "drg-vcn-attach"
                  network_details = {
                    attached_resource_key = "VCN-KEY"
                    type                  = "VCN"
                  }
                }
              }
            }
          }
        } : {} # DRG

        vcns = {
          VCN-KEY = {
            display_name                     = "${var.vcn_name}-vcn"
            is_ipv6enabled                   = false
            is_oracle_gua_allocation_enabled = false
            cidr_blocks                      = [var.vcn_cidr_block],
            dns_label                        = "${var.vcn_name}"
            is_create_igw                    = false
            is_attach_drg                    = var.is_attach_drg
            block_nat_traffic                = false
            default_security_list = {
              display_name = "sl-lb"

              egress_rules = [
                {
                  description = "egress to 0.0.0.0/0 over ALL protocols"
                  stateless   = false
                  protocol    = "ALL"
                  dst         = "0.0.0.0/0"
                  dst_type    = "CIDR_BLOCK"
                }
              ]

              ingress_rules = [
                # REQUIRE BASTION for port 22 !!!
                # {
                #   description  = "ingress from 0.0.0.0/0 over TCP22"
                #   stateless    = false
                #   protocol     = "TCP"
                #   src          = "0.0.0.0/0"
                #   src_type     = "CIDR_BLOCK"
                #   dst_port_min = 22
                #   dst_port_max = 22
                # },
                {
                  description  = "ingress from 0.0.0.0/0 over TCP443"
                  stateless    = false
                  protocol     = "TCP"
                  src          = "0.0.0.0/0"
                  src_type     = "CIDR_BLOCK"
                  dst_port_min = 443
                  dst_port_max = 443
                }
              ]
            }


            subnets = {
              for i, s in var.subnet_names : "KEY-${s}" => {
                cidr_block                 = var.subnet_cidr_blocks[index(var.subnet_names, s)]
                dhcp_options_key           = "default_dhcp_options"
                display_name               = "subnet-${s}-${var.subnet_types[index(var.subnet_names, s)]}"
                dns_label                  = "${s}"
                ipv6cidr_blocks            = []
                prohibit_internet_ingress  = var.subnet_types[index(var.subnet_names, s)] == "private" ? true : false
                prohibit_public_ip_on_vnic = var.subnet_types[index(var.subnet_names, s)] == "private" ? true : false
                route_table_key            = var.subnet_types[index(var.subnet_names, s)] == "private" ? "PRIVATE-SUBNET-ROUTE-TABLE" : "PUBLIC-SUBNET-ROUTE-TABLE"
              }
            } # Subnets

            route_tables = {
              PUBLIC-SUBNET-ROUTE-TABLE = {
                display_name = "public-subnet-rtable"
                route_rules = {
                  RULE-1 = {
                    network_entity_key = "IGW-KEY"
                    description        = "To Internet Gateway."
                    destination        = "0.0.0.0/0"
                    destination_type   = "CIDR_BLOCK"
                  }
                  RULE-2 = {
                    network_entity_key = "SGW-KEY"
                    description        = "To Service Gateway."
                    destination        = "objectstorage"
                    destination_type   = "SERVICE_CIDR_BLOCK"
                  }
                }
              },
              PRIVATE-SUBNET-ROUTE-TABLE = {
                display_name = "private-subnet-rtable"
                route_rules = {
                  RULE-1 = {
                    network_entity_key = "NATGW-KEY"
                    description        = "To NAT Gateway."
                    destination        = "0.0.0.0/0"
                    destination_type   = "CIDR_BLOCK"
                  }
                  RULE-2 = {
                    network_entity_key = "SGW-KEY"
                    description        = "To Service Gateway."
                    destination        = "all-services"
                    destination_type   = "SERVICE_CIDR_BLOCK"
                  }
                }
              }
            } # Route Tables

            network_security_groups = {

              NSG-LB-KEY = {
                display_name = "nsg-lb"
                egress_rules = {
                  anywhere = {
                    description = "egress to 0.0.0.0/0 over TCP"
                    stateless   = false
                    protocol    = "TCP"
                    dst         = "0.0.0.0/0"
                    dst_type    = "CIDR_BLOCK"
                  }
                }

                ingress_rules = {
                  # Port 443 only
                  http_443 = {
                    description  = "ingress from 0.0.0.0/0 over https:443"
                    stateless    = false
                    protocol     = "TCP"
                    src          = "0.0.0.0/0"
                    src_type     = "CIDR_BLOCK"
                    dst_port_min = 443
                    dst_port_max = 443
                  }
                }
              },

              NSG-APP-KEY = {
                display_name = "nsg-app"
                egress_rules = {
                  anywhere = {
                    description = "egress to 0.0.0.0/0 over TCP"
                    stateless   = false
                    protocol    = "TCP"
                    dst         = "0.0.0.0/0"
                    dst_type    = "CIDR_BLOCK"
                  }
                }

                ingress_rules = {
                  ssh_22 = {
                    description  = "ingress from 0.0.0.0/0 over TCP22"
                    stateless    = false
                    protocol     = "TCP"
                    src          = "NSG-LB-KEY"
                    src_type     = "NETWORK_SECURITY_GROUP"
                    dst_port_min = 22
                    dst_port_max = 22
                  }

                }
              }

              NSG-DB-KEY = {
                display_name = "nsg-db"
                egress_rules = {
                  anywhere = {
                    description = "egress to 0.0.0.0/0 over TCP"
                    stateless   = false
                    protocol    = "TCP"
                    dst         = "0.0.0.0/0"
                    dst_type    = "CIDR_BLOCK"
                  }
                }

                ingress_rules = {
                  ssh_22 = {
                    description  = "ingress from 0.0.0.0/0 over TCP22"
                    stateless    = false
                    protocol     = "TCP"
                    src          = "NSG-APP-KEY"
                    src_type     = "NETWORK_SECURITY_GROUP"
                    dst_port_min = 22
                    dst_port_max = 22
                  }

                  db_1521 = {
                    description  = "ingress from 0.0.0.0/0 over TCP:1521-1522"
                    stateless    = false
                    protocol     = "TCP"
                    src          = "NSG-APP-KEY"
                    src_type     = "NETWORK_SECURITY_GROUP"
                    dst_port_min = 1521
                    dst_port_max = 1522
                  }
                }
              }
            } # NSGs

            vcn_specific_gateways = {
              internet_gateways = {
                IGW-KEY = {
                  enabled      = true
                  display_name = "igw-prod-vcn"
                }
              }
              nat_gateways = {
                NATGW-KEY = {
                  block_traffic = false
                  display_name  = "natgw-prod-vcn"
                }
              }
              service_gateways = {
                SGW-KEY = {
                  display_name = "sgw-prod-vcn"
                  services     = "objectstorage"
                }
              }
            } # Gateways

          }
        }
      }
    } # categories
  }   # network_comfiguration
}     # locals
