# Terraform to configure tenancy

This is 2 stacks designed to create our initial tenancy.  It is broken into 2 parts:

1) Initial build of compartment structure, group, and initial users

2) Creation of individual users and dynamic groups

Each of these has a subdirectory with a Resource Manager config (terraform config).  To use either, create a stack and update the variables.

## Details (Part 1)
This stack requires an existing identity domain to exist and needs the OCID of it.  It may eventually be available to create the domain itself, along with enterprise required security (MFA), and then use the domain for the dynamic groups and shared group that get created.  

It also requires the name of the IAM group (to be created in Identity Domain), and the name of a top-level compartment for all users to (eventually be) exist under.

General policies are created for use by this group in this compartment, and thus it should be possible to enable new users simply by adding the user to the group and creating a compartment.

This stack also creates a basic quota policy to zero out the regions and services across the board, so as to prevent creation of resources in the top level compartment, such as `cloud-engineering`.

Finally, it creates a DRG at the root of the tenancy, for potential use with other tenancies or FastConnect/IPSec.

# Details (Part 2)

This stack defines a grouping (*not IAM*) of compartments to be created, and then creates the following:

- A compartment under the main `cloud-engineering` compartment
- A Dynamic Group for that compartment
- A quota policy, grouped by the name of the grouping, with statements allowing each compartment to contain a set number or size of resources.
