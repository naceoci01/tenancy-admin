from oci.exceptions import ServiceError
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
from oci.database import DatabaseClient
from oci.data_safe import DataSafeClient
from oci import config, pagination
from oci.exceptions import ServiceError
from oci.log_analytics import LogAnalyticsClient
from oci.core import VirtualNetworkClient
import argparse
import logging
import json
import datetime


# Main Routine
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("-pr", "--profile", help="Config Profile, named", default="DEFAULT")
parser.add_argument("-dryrun", help="Don't actually do it, just show what you'd do", action="store_true")
parser.add_argument("-ip", "--instanceprincipal", help="Use Instance Principal Auth - negates --profile", action="store_true")
parser.add_argument("-o", "--ocid", help="OCID of compartment (if not passed, will use tenancy OCID from profile)", default="TENANCY")
parser.add_argument("-d", "--days", help="Age in days to delete (older than X days). Default 90", type=int, default=90)

args = parser.parse_args()
verbose = args.verbose
profile = args.profile
dryrun = args.dryrun
use_instance_principals = args.instanceprincipal
compartment_ocid = args.ocid
days = args.days

# First set the log level
if verbose:
    logging.getLogger().setLevel(logging.DEBUG)
else:
    logging.getLogger().setLevel(logging.INFO)

# Only allow subtree if we are going to use tenancy
use_subtree = True if compartment_ocid == "TENANCY" else False

# Set up Config
if use_instance_principals:
    print(f"Using Instance Principal Authentication")
    signer = InstancePrincipalsSecurityTokenSigner()
    datasafe_client = DataSafeClient(config={}, signer=signer)
    if compartment_ocid == "TENANCY":
        compartment_ocid = signer.tenancy_id
        logging.info(f"Signer: {signer}")

else:
    # Use a profile (must be defined)
    print(f"Using Profile Authentication: {profile}")
    config = config.from_file(profile_name=profile)
    if compartment_ocid == "TENANCY":
        print(f'Using tenancy OCID from profile: {config["tenancy"]}')
        compartment_ocid = config["tenancy"]
        logging.info(f"Config: {config}")
    # Create the OCI Client to use
    datasafe_client = DataSafeClient(config)

#########
# Counts
sa_delete_count = 0
ua_delete_count = 0

# Security Assessments
data_safe_resp = datasafe_client.list_security_assessments(
    compartment_id=compartment_ocid,
    compartment_id_in_subtree=use_subtree,
    sort_order="ASC",
    sort_by="timeCreated",
    lifecycle_state="SUCCEEDED",
    type="SAVED",
    #time_created_less_than="2023-01-01T00:00:00Z"
    limit=500
)
logging.info(f"Summary: {len(data_safe_resp.data)} Next Page {data_safe_resp.next_page} ")

for i in data_safe_resp.data: 
    logging.debug(f"UA: {i}")
    logging.debug(f"SA Found {i.display_name} / {i.time_created} / {i.lifecycle_state} / {i.type} / {i.id}")

    # Check for age (older than XX)
    #obj_time = i.time_created.replace(tzinfo=datetime.timezone.utc)
    if (i.time_created + datetime.timedelta(days=days) < datetime.datetime.now(tz=datetime.timezone.utc)):
        logging.info(f"Deleting due to creation older than {days} days: {i.time_created}")

        try:
            datasafe_client.delete_security_assessment(i.id)
            logging.info(f"SA Deleted {i.display_name} / {i.time_created}")
            sa_delete_count += 1
        except ServiceError as e:
            logging.warning(f"Failed to delete {i}: {e}")
    logging.debug("--------------------------")


# User Assessments
data_safe_resp = datasafe_client.list_user_assessments(
    compartment_id=compartment_ocid,
    compartment_id_in_subtree=use_subtree,
    sort_order="ASC",
    sort_by="timeCreated",
    # lifecycle_state="SUCCEEDED",
    type="SAVED",
    #time_created_less_than="2023-01-01T00:00:00Z"
    limit=500
).data

for i in data_safe_resp: 
    logging.debug(f"UA: {i}")
    logging.debug(f"UA Found {i.display_name} / {i.time_created} / {i.lifecycle_state} / {i.type} / {i.id}")
    if (i.time_created + datetime.timedelta(days=days) < datetime.datetime.now(tz=datetime.timezone.utc)):
        logging.info(f"Deleting due to creation older than {days} days: {i.time_created}")
        try:
            datasafe_client.delete_user_assessment(i.id)
            logging.info(f"UA Deleted {i.display_name} / {i.time_created}")
            ua_delete_count += 1
        except ServiceError as e:
            logging.warning(f"Failed to delete {i}: {e}")
    logging.debug("--------------------------")

logging.info(f"Summary: {sa_delete_count} Security Assessments removed, {ua_delete_count} User Assessments removed")
