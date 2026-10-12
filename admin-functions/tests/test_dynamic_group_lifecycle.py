import importlib.util
from datetime import datetime, timezone
import pathlib
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch


FUNCTION_PATH = pathlib.Path(__file__).parents[1] / "functions" / "dynamic_group_lifecycle" / "func.py"
SPEC = importlib.util.spec_from_file_location("dynamic_group_lifecycle_func", FUNCTION_PATH)
FUNCTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FUNCTION)


class FakeGateway:
    def __init__(self, groups, unused_ocids):
        self.all_dynamic_groups = groups
        self.unused_ocids = set(unused_ocids)
        self.tags = {group["dynamic_group_ocid"]: dict(group.get("tags", {})) for group in groups}
        self.updated = []
        self.deleted = []

    def inventory(self):
        return [group for group in self.all_dynamic_groups if group["dynamic_group_ocid"] in self.unused_ocids]

    def get_freeform_tags(self, group):
        return dict(self.tags[group["dynamic_group_ocid"]])

    def update_freeform_tags(self, group, tags):
        ocid = group["dynamic_group_ocid"]
        self.tags[ocid] = dict(tags)
        self.updated.append((ocid, dict(tags)))

    def delete_dynamic_group(self, group):
        self.deleted.append(group["dynamic_group_ocid"])


def group(ocid, name, domain="Default", **tags):
    return {
        "dynamic_group_ocid": ocid,
        "dynamic_group_id": f"id-{ocid}",
        "dynamic_group_name": name,
        "domain_name": domain,
        "tags": tags,
    }


class DynamicGroupLifecycleTests(unittest.TestCase):
    def test_publish_summary_uses_resource_principal_and_topic_region(self):
        client = unittest.mock.Mock()
        oci = ModuleType("oci")
        oci.regions = SimpleNamespace(get_region_from_short_name=lambda value: {"phx": "us-phoenix-1"}[value])
        oci.retry = SimpleNamespace(DEFAULT_RETRY_STRATEGY="retry")
        oci.ons = SimpleNamespace(
            NotificationDataPlaneClient=lambda *args, **kwargs: client,
            models=SimpleNamespace(MessageDetails=lambda **kwargs: kwargs),
        )
        oci_auth = ModuleType("oci.auth")
        oci_auth.signers = SimpleNamespace(get_resource_principals_signer=lambda: "resource-principal")
        result = {
            "evaluated_at": "2026-09-25T12:00:00Z",
            "delete_expired_dynamic_groups": False,
            "action_counts": {},
            "domain_counts": {},
            "actions": [],
        }

        with patch.dict("sys.modules", {"oci": oci, "oci.auth": oci_auth}):
            FUNCTION.publish_summary("ocid1.onstopic.oc1.phx.example", result)

        client.publish_message.assert_called_once()
        self.assertEqual(
            client.publish_message.call_args.kwargs["topic_id"],
            "ocid1.onstopic.oc1.phx.example",
        )
        self.assertEqual(
            client.publish_message.call_args.kwargs["message_details"]["title"],
            "Dynamic Group Lifecycle Summary",
        )

    def test_notification_has_summary_domain_counts_and_action_details(self):
        body = FUNCTION.format_notification(
            {
                "evaluated_at": "2026-09-25T12:00:00Z",
                "delete_expired_dynamic_groups": False,
                "action_counts": {"marked": 1, "unmarked": 1},
                "domain_counts": {
                    "Default": {"evaluated": 2, "unused": 1, "marked": 1, "unmarked": 1, "deleted": 0}
                },
                "actions": [
                    {"action": "marked", "domain": "Default", "name": "unused-dg", "ocid": "ocid-unused", "delete_after": "2026-10-09T12:00:00Z"},
                    {"action": "unmarked", "domain": "Default", "name": "used-dg", "ocid": "ocid-used"},
                ],
            }
        )

        self.assertIn("SUMMARY", body)
        self.assertIn("BY DOMAIN", body)
        self.assertIn("DETAILS", body)
        self.assertIn("Outcome\tDomain\tDynamic group", body)
        self.assertIn("marked\tDefault\tunused-dg\tocid-unused\t2026-10-09T12:00:00Z", body)
        self.assertIn("unmarked\tDefault\tused-dg\tocid-used\t-", body)

    def test_dependency_log_level_applies_to_policy_analysis_namespace(self):
        FUNCTION.configure_logging(
            {"LOG_LEVEL": "INFO", "DEPENDENCY_LOG_LEVEL": "WARNING"},
            {},
        )

        self.assertEqual(FUNCTION.logging.getLogger("oci-policy-analysis").level, FUNCTION.logging.WARNING)

    def test_gateway_reads_oci_extension_freeform_tags(self):
        dynamic_group = group("dg-1", "unused")
        dynamic_group["domain_ocid"] = "domain-1"
        client = SimpleNamespace(
            get_dynamic_resource_group=lambda **_: SimpleNamespace(
                data=SimpleNamespace(
                    urn_ietf_params_scim_schemas_oracle_idcs_extension_oci_tags=SimpleNamespace(
                        freeform_tags=[
                            SimpleNamespace(key="Owner", value="team-a"),
                            SimpleNamespace(key="DeleteDynamicGroupAfter", value="2026-10-09T00:00:00Z"),
                        ]
                    )
                )
            )
        )
        gateway = FUNCTION.OciDynamicGroupGateway()
        gateway._domain_clients = {"domain-1": client}

        self.assertEqual(
            gateway.get_freeform_tags(dynamic_group),
            {"Owner": "team-a", "DeleteDynamicGroupAfter": "2026-10-09T00:00:00Z"},
        )

    def test_gateway_patches_only_the_oci_freeform_tag_collection(self):
        class Model:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        class Operations(Model):
            OP_REPLACE = "REPLACE"

        dynamic_group = group("dg-1", "unused")
        dynamic_group["domain_ocid"] = "domain-1"
        client = unittest.mock.Mock()
        gateway = FUNCTION.OciDynamicGroupGateway()
        gateway._domain_clients = {"domain-1": client}
        modules = {
            "oci": SimpleNamespace(),
            "oci.identity_domains": SimpleNamespace(),
            "oci.identity_domains.models": SimpleNamespace(
                FreeformTags=Model,
                Operations=Operations,
                PatchOp=Model,
            ),
        }

        with patch.dict("sys.modules", modules):
            gateway.update_freeform_tags(
                dynamic_group,
                {"Owner": "team-a", "DeleteDynamicGroupAfter": "2026-10-09T00:00:00Z"},
            )

        patch_op = client.patch_dynamic_resource_group.call_args.kwargs["patch_op"]
        operation = patch_op.operations[0]
        self.assertEqual(patch_op.schemas, [FUNCTION.SCIM_PATCH_SCHEMA])
        self.assertEqual(operation.op, "REPLACE")
        self.assertEqual(operation.path, f"{FUNCTION.OCI_TAGS_SCHEMA}:freeformTags")
        self.assertEqual(
            [(tag.key, tag.value) for tag in operation.value],
            [("DeleteDynamicGroupAfter", "2026-10-09T00:00:00Z"), ("Owner", "team-a")],
        )

    def test_gateway_removes_the_tag_collection_when_the_lifecycle_tag_is_last(self):
        class Model:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        class Operations(Model):
            OP_REMOVE = "REMOVE"
            OP_REPLACE = "REPLACE"

        dynamic_group = group("dg-1", "unused")
        dynamic_group["domain_ocid"] = "domain-1"
        client = unittest.mock.Mock()
        gateway = FUNCTION.OciDynamicGroupGateway()
        gateway._domain_clients = {"domain-1": client}
        modules = {
            "oci": SimpleNamespace(),
            "oci.identity_domains": SimpleNamespace(),
            "oci.identity_domains.models": SimpleNamespace(
                FreeformTags=Model,
                Operations=Operations,
                PatchOp=Model,
            ),
        }

        with patch.dict("sys.modules", modules):
            gateway.update_freeform_tags(dynamic_group, {})

        operation = client.patch_dynamic_resource_group.call_args.kwargs["patch_op"].operations[0]
        self.assertEqual(operation.op, "REMOVE")
        self.assertEqual(operation.path, f"{FUNCTION.OCI_TAGS_SCHEMA}:freeformTags")
        self.assertFalse(hasattr(operation, "value"))

    def test_marks_unused_group_two_weeks_after_detection(self):
        gateway = FakeGateway([group("dg-unused", "unused", Owner="team-a")], {"dg-unused"})
        now = datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc)

        result = FUNCTION.reconcile_dynamic_groups({}, {}, gateway, now)

        self.assertEqual(result["action_counts"], {"marked": 1})
        self.assertEqual(
            gateway.tags["dg-unused"],
            {"Owner": "team-a", "DeleteDynamicGroupAfter": "2026-10-09T10:30:00Z"},
        )

    def test_keeps_existing_valid_deadline_on_repeated_unused_scan(self):
        gateway = FakeGateway(
            [group("dg-unused", "unused", DeleteDynamicGroupAfter="2026-10-01T00:00:00Z")],
            {"dg-unused"},
        )

        result = FUNCTION.reconcile_dynamic_groups({}, {}, gateway, datetime(2026, 9, 25, tzinfo=timezone.utc))

        self.assertEqual(result["action_counts"], {"marked_not_due": 1})
        self.assertEqual(gateway.updated, [])

    def test_unmarks_a_now_in_use_group(self):
        gateway = FakeGateway(
            [group("dg-used", "used", DeleteDynamicGroupAfter="2026-10-01T00:00:00Z", Owner="team-a")],
            set(),
        )

        result = FUNCTION.reconcile_dynamic_groups({}, {}, gateway, datetime(2026, 9, 25, tzinfo=timezone.utc))

        self.assertEqual(result["action_counts"], {"unmarked": 1})
        self.assertEqual(gateway.tags["dg-used"], {"Owner": "team-a"})

    def test_expired_group_is_not_deleted_without_explicit_configuration(self):
        gateway = FakeGateway(
            [group("dg-unused", "unused", DeleteDynamicGroupAfter="2026-09-01T00:00:00Z")],
            {"dg-unused"},
        )

        result = FUNCTION.reconcile_dynamic_groups({}, {}, gateway, datetime(2026, 9, 25, tzinfo=timezone.utc))

        self.assertEqual(result["action_counts"], {"marked_not_due": 1})
        self.assertEqual(gateway.deleted, [])

    def test_expired_group_is_deleted_only_when_enabled(self):
        gateway = FakeGateway(
            [group("dg-unused", "unused", DeleteDynamicGroupAfter="2026-09-01T00:00:00Z")],
            {"dg-unused"},
        )

        result = FUNCTION.reconcile_dynamic_groups(
            {"DELETE_EXPIRED_DYNAMIC_GROUPS": "true"}, {}, gateway, datetime(2026, 9, 25, tzinfo=timezone.utc)
        )

        self.assertEqual(result["action_counts"], {"deleted": 1})
        self.assertEqual(gateway.deleted, ["dg-unused"])

    def test_invalid_deadline_is_replaced_with_a_fresh_grace_period(self):
        gateway = FakeGateway(
            [group("dg-unused", "unused", DeleteDynamicGroupAfter="not-a-date")], {"dg-unused"}
        )

        result = FUNCTION.reconcile_dynamic_groups({}, {}, gateway, datetime(2026, 9, 25, tzinfo=timezone.utc))

        self.assertEqual(result["action_counts"], {"remarked_invalid_deadline": 1})
        self.assertEqual(gateway.tags["dg-unused"]["DeleteDynamicGroupAfter"], "2026-10-09T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
