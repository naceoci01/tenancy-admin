

# # import group 
# import {
#   to = oci_identity_domains_group.ce-group
#   id = "idcsEndpoint/https://idcs-9c88fbba4c644a1ca2cec3c615a1bc6a.identity.oraclecloud.com/groups/fabb9c77b8634c90be6ff006fc3f8ec8"
# }

# $ terraform import oci_identity_domains_group.test_group "idcsEndpoint/{idcsEndpoint}/groups/{groupId}" 
# ocid1.group.oc1..aaaaaaaaewr5q7fqazb7y7fbtdocunwfk6xfl2dapjd5w3qvpnbgmqjaonnq or fabb9c77b8634c90be6ff006fc3f8ec8

# Existing Identity domain Group
data "oci_identity_domains_group" "ce-group" {
  group_id = var.cloud_engineering_groupid
  idcs_endpoint = data.oci_identity_domain.ce-domain.url
  attribute_sets = ["all"]
}

# Existing ID Domain
data "oci_identity_domain" "ce-domain" {
  domain_id = var.domain_id
}

# resource "oci_identity_domains_group" "ce-group" {
#   depends_on = [ oci_identity_domains_user.ce-user ]
#   idcs_endpoint = data.oci_identity_domains_group.ce-group.idcs_endpoint
#   display_name = data.oci_identity_domains_group.ce-group.display_name
#   schemas = data.oci_identity_domains_group.ce-group.schemas
#   urnietfparamsscimschemasoracleidcsextensionrequestable_group {
#     requestable = true
#   }

#   dynamic "members" {
#       for_each = oci_identity_domains_user.ce-user
#       content {
#         type = "User"
#         value = members.value.id
#       }
#   }
#   # dynamic "members" {
#   #     for_each = data.oci_identity_domains_group.ce-group.members
#   #     content {
#   #       type = "User"
#   #       value = members.name
#   #     }
#   # }
# }
