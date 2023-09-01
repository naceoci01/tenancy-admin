from oci import config
from oci import identity
from oci import loggingingestion
from oci.auth.signers import InstancePrincipalsSecurityTokenSigner
from oci.loggingingestion.models import PutLogsDetails,LogEntry,LogEntryBatch

import argparse
import json
import os
import datetime
import uuid

# Lists
dynamic_group_statements = []
service_statements = []
regular_statements = []
special_statements = []

# Helper

def log_message(loggingingestion_client, log_ocid, message):
    put_logs_response = loggingingestion_client.put_logs(
        log_id=log_ocid,
        put_logs_details=PutLogsDetails(
            specversion="1.0",
            log_entry_batches=LogEntryBatch(
                defaultlogentrytime=datetime.datetime.now(),
                source="oci-policy-analysis",
                type="output",
                entries=[LogEntry(id=uuid.uuid1(),data=message)]
            )
        )
    )

def print_statement(statement_tuple):
    a,b,c,d,e = statement_tuple
    print(f"Subject: {a}, Verb: {b}, Resource: {c}, Location: {d}, Condition: {e}")

def parse_statement(statement, comp_string, policy):
    # Play with tuple and partition
    # (subject, verb, resource, location, condition)
    # Pass 1 - where condition
    # Pass 2 - group subject
    # Pass 3 - location
    # Pass 4 - verb and resource
    pass1 = statement.casefold().partition(" where ")
    condition = pass1[2]
    pass2a = pass1[0].partition("allow ")
    pass2b = pass2a[2].partition(" to ")
    subject = pass2b[0]
    pass3 = pass2b[2].partition(" in ")
    location = pass3[2]
    pass4 = pass3[0].partition(" ")
    verb = pass4[0]
    resource = pass4[2]

    # Location Update
    # If compartment name, use hierarchy, if id then leave alone
    if "compartment id" in location:
        pass
    elif "tenancy" in location:
        pass
    else:
        sub_comp = location.partition("compartment ")[2]
        if comp_string == "":
            # if root, then leave compartment alone
            #location = f"compartment {comp_name}"
            pass
        else:
            location = f"compartment {comp_string}:{sub_comp}"

    # Build tuple based on modified location
    statement_tuple = (subject,verb,resource,location,condition,f"{comp_string}", policy.name, policy.id, policy.compartment_id, statement)
    return statement_tuple
    
# Recursive Compartments / Policies
def getNestedCompartment(identity_client, comp_ocid, level, max_level, comp_string, verbose):

    # Print something if not verbose
    if not verbose:
        print("c",end='',flush=True)

    # Level Printer
    level_string = ""
    for i in range(level):
        level_string += "|  "

    # Print with level
    get_compartment_response = identity_client.get_compartment(compartment_id=comp_ocid)
    comp = get_compartment_response.data
    if verbose:
        print(f"{level_string}| Compartment Name: {comp.name} ID: {comp_ocid} Hierarchy: {comp_string}")

    # Get policies First
    list_policies_response = identity_client.list_policies(
        compartment_id=comp_ocid,
        limit=1000
    )
    for policy in list_policies_response.data:
        if not verbose:
            print("p",end='',flush=True)
        else:
                print(f"{level_string}| > Policy: {policy.name} ID: {policy.id}")
        for index,statement in enumerate(policy.statements, start=1):
            if not verbose:
                print("s",end='',flush=True)
            else:
                print(f"{level_string}| > -- Statement {index}: {statement}", flush=True)
            
            # Root out "special" statements (endorse / define / as)
            if str.startswith(statement,"endorse") or str.startswith(statement,"admit") or str.startswith(statement,"define"):
                special_statements.append(statement)
                continue

            # Helper returns tuple with policy statement and lineage
            statement_tuple = parse_statement(
                statement=statement, 
                comp_string=comp_string, 
                policy=policy
            )

            if statement_tuple[0] is None or statement_tuple[0] == "":
                if verbose:
                    print(f"****Statement {statement} resulted in bad tuple: {statement_tuple}")

            if "dynamic-group " in statement_tuple[0]:
                dynamic_group_statements.append(statement_tuple)
            elif "service " in statement_tuple[0]:
                service_statements.append(statement_tuple)
            else:
                regular_statements.append(statement_tuple)

    if level == max_level:
        # return, stop
        return
    
    # Where are we? Do we need to recurse?
    list_compartments_response = identity_client.list_compartments(
        compartment_id=comp_ocid,
        limit=1000,
        access_level="ACCESSIBLE",
        compartment_id_in_subtree=False,
        sort_by="NAME",
        sort_order="ASC",
        lifecycle_state="ACTIVE")
    comp_list = list_compartments_response.data
    
    # Iterate and if any have sub-compartments, call recursive until none left
    if len(comp_list) == 0:
        # print(f"fall back level {level}")
        return
    for comp in comp_list:
       
        # Recurse
        if comp_string == "":
            getNestedCompartment(identity_client=identity_client, comp_ocid=comp.id, level=level+1, max_level=max_level, comp_string=comp_string + comp.name, verbose=verbose)
        else:
            getNestedCompartment(identity_client=identity_client, comp_ocid=comp.id, level=level+1, max_level=max_level, comp_string=comp_string + ":" + comp.name, verbose=verbose)

# Main Code

# Parse Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="increase output verbosity", action="store_true")
parser.add_argument("-pr", "--profile", help="Config Profile, named", default="DEFAULT")
parser.add_argument("-o", "--ocid", help="OCID of compartment (if not passed, will use tenancy OCID from profile)", default="TENANCY")
parser.add_argument("-sf", "--subjectfilter", help="Filter all statement subjects by this text")
parser.add_argument("-vf", "--verbfilter", help="Filter all verbs (inspect,read,use,manage) by this text")
parser.add_argument("-rf", "--resourcefilter", help="Filter all resource (eg database or stream-family etc) subjects by this text")
parser.add_argument("-lf", "--locationfilter", help="Filter all location (eg compartment name) subjects by this text")
parser.add_argument("-m", "--maxlevel", help="Max recursion level (0 is root only)",type=int,default=6)
parser.add_argument("-c", "--usecache", help="Load from local cache (if it exists)", action="store_true")
parser.add_argument("-w", "--writejson", help="Write filtered output to JSON", action="store_true")
parser.add_argument("-ip", "--instanceprincipal", help="Use Instance Principal Auth - negates --profile", action="store_true")
parser.add_argument("-lo", "--logocid", help="Use an OCI Log - provide OCID")
args = parser.parse_args()
verbose = args.verbose
use_cache = args.usecache
ocid = args.ocid
profile = args.profile
sub_filter = args.subjectfilter
verb_filter = args.verbfilter
resource_filter = args.resourcefilter
location_filter = args.locationfilter
max_level = args.maxlevel
write_json_output = args.writejson
use_instance_principals = args.instanceprincipal
log_ocid = None if not args.logocid else args.logocid

if use_instance_principals:
    print(f"Using Instance Principal Authentication")
    signer = InstancePrincipalsSecurityTokenSigner()
    identity_client = identity.IdentityClient(config={}, signer=signer)
    logging_client = loggingingestion.LoggingClient(config={}, signer=signer)
    if ocid == "TENANCY":
        ocid = signer.tenancy_id
else:
    # Use a profile (must be defined)
    print(f"Using Profile Authentication: {profile}")
    config = config.from_file(profile_name=profile)
    if ocid == "TENANCY":
        print(f'Using tenancy OCID from profile: {config["tenancy"]}')
        ocid = config["tenancy"]

    # Create the OCI Client to use
    identity_client = identity.IdentityClient(config)
    logging_client = loggingingestion.LoggingClient(config)

# Test Log
log_message(logging_client,"test message")

# Load from cache (if exists)
if use_cache:
    print("Loading Policy statements from cache")

    if os.path.isfile(f'./.policy-special-cache-{ocid}.dat'):
        with open(f'./.policy-special-cache-{ocid}.dat', 'r') as filehandle:
            special_statements = json.load(filehandle)
    if os.path.isfile(f'./.policy-dg-cache-{ocid}.dat'):
        with open(f'./.policy-dg-cache-{ocid}.dat', 'r') as filehandle:
            dynamic_group_statements = json.load(filehandle)
    if os.path.isfile(f'.policy-svc-cache-{ocid}.dat'):
        with open(f'./.policy-svc-cache-{ocid}.dat', 'r') as filehandle:
            service_statements = json.load(filehandle)
    if os.path.isfile(f'.policy-statement-cache-{ocid}.dat'):
        with open(f'./.policy-statement-cache-{ocid}.dat', 'r') as filehandle:
            regular_statements = json.load(filehandle)
else:        
    # Run Recursion
    level = 0
    print("========Enter Recursion==============")
    getNestedCompartment(identity_client=identity_client, comp_ocid=ocid, level=level, max_level=max_level, comp_string="", verbose=verbose)
    print("\n========Exit Recursion==============")

# Write to local cache (per type)
with open(f'.policy-special-cache-{ocid}.dat', 'w') as filehandle:
    json.dump(special_statements, filehandle)
with open(f'.policy-dg-cache-{ocid}.dat', 'w') as filehandle:
    json.dump(dynamic_group_statements, filehandle)
with open(f'.policy-svc-cache-{ocid}.dat', 'w') as filehandle:
    json.dump(service_statements, filehandle)
with open(f'.policy-statement-cache-{ocid}.dat', 'w') as filehandle:
    json.dump(regular_statements, filehandle)

# Perform Filtering
if sub_filter:
    print(f"Filtering subject: {sub_filter}. Before: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")
    dynamic_group_statements = list(filter(lambda statement: sub_filter.casefold() in statement[0].casefold(),dynamic_group_statements))
    service_statements = list(filter(lambda statement: sub_filter.casefold() in statement[0].casefold(),service_statements))
    regular_statements = list(filter(lambda statement: sub_filter.casefold() in statement[0].casefold(),regular_statements))
    print(f"After: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")

if verb_filter:
    print(f"Filtering verb: {verb_filter}. Before: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")
    dynamic_group_statements = list(filter(lambda statement: verb_filter.casefold() in statement[1].casefold(),dynamic_group_statements))
    service_statements = list(filter(lambda statement: verb_filter.casefold() in statement[1].casefold(),service_statements))
    regular_statements = list(filter(lambda statement: verb_filter.casefold() in statement[1].casefold(),regular_statements))
    print(f"After: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")

if resource_filter:
    print(f"Filtering resource: {resource_filter}. Before: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")
    dynamic_group_statements = list(filter(lambda statement: resource_filter.casefold() in statement[2].casefold(),dynamic_group_statements))
    service_statements = list(filter(lambda statement: resource_filter.casefold() in statement[2].casefold(),service_statements))
    regular_statements = list(filter(lambda statement: resource_filter.casefold() in statement[2].casefold(),regular_statements))
    print(f"After: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")

if location_filter:
    print(f"Filtering location: {location_filter}. Before: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")
    dynamic_group_statements = list(filter(lambda statement: location_filter.casefold() in statement[3].casefold(),dynamic_group_statements))
    service_statements = list(filter(lambda statement: location_filter.casefold() in statement[3].casefold(),service_statements))
    regular_statements = list(filter(lambda statement: location_filter.casefold() in statement[3].casefold(),regular_statements))
    print(f"After: {len(dynamic_group_statements)}/{len(service_statements)}/{len(regular_statements)} DG/SVC/Reg statements")


# Print Special 
print("========Summary Special==============")
for index, statement in enumerate(special_statements, start=1):
    print(f"Statement #{index}: {statement}")
print(f"Total Special statement in tenancy: {len(special_statements)}")

# Print Dynamic Groups
print("========Summary DG==============")
for index, statement in enumerate(dynamic_group_statements, start=1):
    print(f"Statement #{index}: {statement[9]} | Policy: {statement[5]}/{statement[6]}")
print(f"Total Service statement in tenancy: {len(dynamic_group_statements)}")

# Print Service
print("========Summary SVC==============")
for index, statement in enumerate(service_statements, start=1):
    print(f"Statement #{index}: {statement[9]} | Policy: {statement[5]}/{statement[6]}")
print(f"Total Service statement in tenancy: {len(service_statements)}")

# Print Regular
print("========Summary Reg==============")
for index, statement in enumerate(regular_statements, start=1):
    print(f"Statement #{index}: {statement[9]} | Policy: {statement[5]}/{statement[6]}")
print(f"Total Regular statement in tenancy: {len(regular_statements)}")

# To output file if required
if write_json_output:
    # Empty Dictionary
    statements_list = []
    for i,s in enumerate(special_statements):
        statements_list.append( {"type": "special", "subject": s[0], "verb": s[1], "resource": s[2], "location":s[3], "conditions": s[4], "lineage":{"policy-compartment-ocid": s[8], "policy-relative-hierarchy": s[5],"policy-name": s[6], "policy-ocid": s[7], "policy-text": s[9]}})
    for i,s in enumerate(dynamic_group_statements):
        statements_list.append( {"type": "dynamic-group", "subject": s[0], "verb": s[1], "resource": s[2], "location":s[3], "conditions": s[4], "lineage":{"policy-compartment-ocid": s[8], "policy-relative-hierarchy": s[5],"policy-name": s[6], "policy-ocid": s[7], "policy-text": s[9]}})
    for i,s in enumerate(service_statements):
        statements_list.append( {"type": "service", "subject": s[0], "verb": s[1], "resource": s[2], "location":s[3], "conditions": s[4], "lineage":{"policy-compartment-ocid": s[8], "policy-relative-hierarchy": s[5],"policy-name": s[6], "policy-ocid": s[7], "policy-text": s[9]}})
    for i,s in enumerate(regular_statements):
        statements_list.append( {"type": "regular", "subject": s[0], "verb": s[1], "resource": s[2], "location":s[3], "conditions": s[4], "lineage":{"policy-compartment-ocid": s[8], "policy-relative-hierarchy": s[5],"policy-name": s[6], "policy-ocid": s[7], "policy-text": s[9]}})
    # Serializing json
    json_object = json.dumps(statements_list, indent=2)
    
    # Writing to sample.json
    with open(f"policyoutput-{ocid}.json", "w") as outfile:
        outfile.write(json_object)