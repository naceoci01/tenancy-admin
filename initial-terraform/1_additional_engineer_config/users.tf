
# # Import existing DG
# resource "oci_identity_domains_user" "ce-user" {
#     #Required
#     idcs_endpoint = data.oci_identity_domain.ce_domain.url
#     schemas = ["urn:ietf:params:scim:schemas:core:2.0:User"]
#     for_each = toset(var.compartment_names)
#     user_name = each.key
#     emails {
#         #Required
#         type = "work"
#         value = "${each.value}"
#         #Optional
#         primary = true
#         secondary = false
#         verified = true
#     } 
#     emails {
#         #Required
#         type = "recovery"
#         value = "${each.value}"
#     }
#     name {
#         family_name = split(".", split("@", each.key)[0])[1]
#         given_name = split(".", each.key)[0]
#         formatted = split("@", each.key)[0]
#     }

# }