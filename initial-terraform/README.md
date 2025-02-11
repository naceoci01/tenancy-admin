# Terraform to configure tenancy

(doc in progress - 02/11/2025)

To set up a "Cloud Engineer" tenancy, there are several main steps to getting set up.  The scripts here will do some of them.

- Parent Tenancy Steps
- Github Repo for these stacks
- Create Identity Domain and initial Groups (Stack 00)
- Configure SSO (with optional JIT)
- Create main compartments, policies and dynamic groups (Stack 0)
- Ongoing (via cron or function) Compartment and quota policy per engineer (Stack 1)
- Create admin compartment, server, and dynamic group (Stack 2)
- Create advanced services (TBD)

## Parent Tenancy
Subscribe all needed regions
Tenancy govenance rules 
Subscribe child to governance rules
...

## Github Repo

Stacks in this repo are in subfolders, so they can be pulled from single GitHub repo.

Configure a Configuration Source Provider in home region, using an Org-based repo and a Personal Access Token.

From this, you then can create the stacks

## Create Identity domain (Stack 00)

Strategy is to avoid using default identity domain for anything other than admin user, some dynamic groups.

Use Stack 00 to create a basic Identity domain and note the name and OCID.  There is some functionality to create groups for main cloud engineer community and other purposes later on.  

NOTE - this one CANNOT be re-run over and over as re-creation of the main `cloud-engineering` group will remove all members.

## Enable SSO for Domain (no stack)

Set up SSO and JIT, using Oracle's production SSO configuration

Screen shots TBD

## Compartments, Policies, Dynamic Groups (Stack 1)

This should create a majority of policies and Dynamic Groups needed for various services.  At the moment, it set up policies for:

- CORE (compute, network, storage)
- SERVICES (OCI
- EXACS
- GG
- OSMH
- DB
- ADB
- FUNC
- OIC
- more

TODO: set up resource manager schema.yaml to enable or disable (DG, compartment, policy) by service.  For example, if Data Science is not needed, don't create the shared compartment and policies for it.

**NOTE - this one can be re-run over and over as policies are added.  It will overwrite manual changes**

## Admin Compartment (Stack 2)

VCN, server for admins to use, along with Dynamic Group allowing instance principal execution of scripts.

## Ongoing Engineer Compartments (Stack 1)

This one can be set via cron to run every so often (20 min currently) and checks the membership of the main `cloud-engineering group`, and then for each user, adds or updates a compartment for them (using first half of email name minus @oracle.com), then updates a set of compartment quotas to allow each engineer to have a set of resources.

**NOTE - this one can be updated and pushed to repo, then will automatically pick up changes next run.  Or run it manually**

## Advanced Services

TBD for this section.  Ech service must be set up, but these could all be scripted. 

What has been done manually

- Regional DRG and RPC connection for all regions (all in `cloud-engineering-shared`)


