locals {
    network_configuration = {
        default_compartment_id = "ocid1.tenancy.oc1..aaaaaaaaonqlfuxbai2t677fopst4vowm5axun74bmowkxtcqvbx6liagciq",
        network_configuration_categories = {
            production = {
                non_vcn_specific_gateways = {
                    dynamic_routing_gateways = {
                        TENANCY-DRG = {
                            display_name = "CloudEngineering-DRG"
                            remote_peering_connections = {
                                ACCEPTOR-RPC = {
                                    display_name = "acceptor-rpc",
                                    peer_key = "INTEGRATION01-PHX",
                                    peer_region_name = "us-phoenix-1",
                                    peer_id = "ocid1.remotepeeringconnection.oc1.phx.aaaaaaaamy2v5kagfpfbllp3dbrwljro6yc4kbpvd3v6ehi4iwh4dklgnhua"
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}