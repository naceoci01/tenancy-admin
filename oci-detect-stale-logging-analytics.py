from oci.resource_search import ResourceSearchClient
from oci.resource_search.models import StructuredSearchDetails
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
from oci.database import DatabaseClient
from oci.resource_search import ResourceSearchClient
from oci.resource_search.models import StructuredSearchDetails
from oci import config, pagination
from oci.exceptions import ServiceError
from oci.log_analytics import LogAnalyticsClient
from oci.core import VirtualNetworkClient
import argparse
import logging
import json
import time


# Main Routine
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("-pr", "--profile", help="Config Profile, named", default="DEFAULT")
parser.add_argument("-dryrun", help="Don't actually do it, just show what you'd do", action="store_true")
parser.add_argument("-ip", "--instanceprincipal", help="Use Instance Principal Auth - negates --profile", action="store_true")
parser.add_argument("-o", "--ocid", help="OCID of compartment (if not passed, will use tenancy OCID from profile)", default="TENANCY")

args = parser.parse_args()
verbose = args.verbose
profile = args.profile
dryrun = args.dryrun
use_instance_principals = args.instanceprincipal
compartment_ocid = args.ocid

# First set the log level
if verbose:
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

# Set up Config
if use_instance_principals:
    print(f"Using Instance Principal Authentication")
    signer = InstancePrincipalsSecurityTokenSigner()
    vcn_client = VirtualNetworkClient(config={}, signer=signer)
    logan_client = LogAnalyticsClient(config={}, signer=signer)
    if compartment_ocid == "TENANCY":
        tenancy_ocid = signer.tenancy_id
        logging.info(f"Signer: {signer}")

else:
    # Use a profile (must be defined)
    print(f"Using Profile Authentication: {profile}")
    config = config.from_file(profile_name=profile)
    if compartment_ocid == "TENANCY":
        print(f'Using tenancy OCID from profile: {config["tenancy"]}')
        tenancy_ocid = config["tenancy"]
        logging.info(f"Config: {config}")
    # Create the OCI Client to use
    vcn_client = VirtualNetworkClient(config)
    logan_client = LogAnalyticsClient(config)

#########
# Per given compartment, query all Entity
logan_entity_resp = logan_client.list_log_analytics_entities(
    namespace_name="orasenatdpltintegration01",
    limit=1000,
    lifecycle_state="ACTIVE",
    compartment_id=compartment_ocid).data
logging.info(f"Found {len(logan_entity_resp.items)} entities in {compartment_ocid}")
deleted_items = 0
for ent in logan_entity_resp.items:
    # Check type - if VNIC
    logging.debug(f"Entity: {ent.entity_type_name} / {ent.cloud_resource_id}")
    time.sleep(.05)
    if ent.cloud_resource_id and "ocid1.vnic." in ent.cloud_resource_id:
        vnid = ent.cloud_resource_id
        # Get active VNICs in the compartment
        try:
            active_vnic_resp = vcn_client.get_vnic(vnic_id=vnid).data
            logging.info(f"Found VNIC {vnid} : {active_vnic_resp}")
        except ServiceError as e:
            if dryrun:
                logging.info(f"VNIC {vnid} doesn't exist. Would be deleting it.")
            else:    
                # Delete it
                logan_entity_resp = logan_client.delete_log_analytics_entity(
                    namespace_name="orasenatdpltintegration01",
                    log_analytics_entity_id=ent.id
                    ).data
                logging.info(f"Entity for {vnid} deleted")
                deleted_items += 1

logging.info(f"Summary: Deleted {deleted_items} Entities")
