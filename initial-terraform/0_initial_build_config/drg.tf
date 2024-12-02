locals {
    network_configuration = {
        default_compartment_id = "ocid1.tenancy.oc1..aaaaaaaaonqlfuxbai2t677fopst4vowm5axun74bmowkxtcqvbx6liagciq",
        network_configuration_categories = var.use_drg ? {
            production = {
                non_vcn_specific_gateways = {
                    dynamic_routing_gateways = {
                        TENANCY-DRG = {
                            display_name = "CloudEngineering-DRG"
                            remote_peering_connections = var.rpc_peer_ocid != null ? {
                                ACCEPTOR-RPC = {
                                    display_name = "acceptor-rpc",
                                    peer_key = "INTEGRATION01-PHX",
                                    peer_region_name = "${var.rpc_peer_region}",
                                    peer_id = "${var.rpc_peer_ocid}"
                                }
                            } : null
                        }
                    }
                }
            }
        } : null
    }
}