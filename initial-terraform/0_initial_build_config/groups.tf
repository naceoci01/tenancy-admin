# # Create the Cloud Engineering group
# # Use variable    (engineer_group_name)
# # Use variable    (domain_id)

# locals {

#     # Keys
#     cloud_engineering_group_key = "CLOUD-ENGINEERS-GROUP"
#     cloud_engineering_group_description = "Group for all users that are Cloud Engineers (CE) in group ${var.engineer_group_name}"

#     # Groups
#     cloud_engineers_group = {
#         (local.cloud_engineering_group_key) = {
#             identity_domain_id        = var.domain_id
#             name                      = var.engineer_group_name
#             description               = local.cloud_engineering_group_description
#         }
#     }

#     # Merge all groups
#     identity_domain_groups_configuration = {
#         groups: merge(local.cloud_engineers_group)
#     }
        
# }
