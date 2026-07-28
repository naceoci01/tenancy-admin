import importlib.util
import pathlib
import unittest


FUNCTION_PATH = pathlib.Path(__file__).parents[1] / "functions" / "engineer_compartment_lifecycle" / "func.py"
SPEC = importlib.util.spec_from_file_location("engineer_compartment_lifecycle_func", FUNCTION_PATH)
LIFECYCLE_FUNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LIFECYCLE_FUNC)

CompartmentInfo = LIFECYCLE_FUNC.CompartmentInfo
LifecycleConfig = LIFECYCLE_FUNC.LifecycleConfig
UserInfo = LIFECYCLE_FUNC.UserInfo
load_config = LIFECYCLE_FUNC.load_config
process_event = LIFECYCLE_FUNC.process_event


class FakeGateway:
    def __init__(self, user=None, compartments=None):
        self.user = user
        self.compartments = {item.name: item for item in compartments or []}
        self.created = []
        self.tag_updates = []

    def get_user(self, user_id):
        return self.user

    def find_child_compartment(self, parent_ocid, name):
        return self.compartments.get(name)

    def create_compartment(self, parent_ocid, name, description):
        created = CompartmentInfo(f"comp.{name}", name, {"Oracle-Tags": {"AllowCompartmentCreation": "true"}})
        self.created.append((parent_ocid, name, description))
        self.compartments[name] = created
        return created

    def update_defined_tags(self, compartment_ocid, defined_tags):
        self.tag_updates.append((compartment_ocid, defined_tags))


def settings(dry_run=False, grace_hours=72):
    return LifecycleConfig("domain", "root", grace_hours, dry_run)


class LifecycleTests(unittest.TestCase):
    def test_create_active_user_creates_missing_compartment(self):
        gateway = FakeGateway(user=UserInfo("jane@example.com", True))

        result = process_event(
            {"eventType": "User - Create", "data": {"resourceId": "user-1"}},
            settings(),
            gateway,
        )

        self.assertEqual(result["action"], "created")
        self.assertEqual(gateway.created[0][1], "jane")

    def test_deactivate_sets_deadline_from_event_time(self):
        compartment = CompartmentInfo("comp.1", "jane", {"Other": {"Key": "value"}})
        gateway = FakeGateway(user=UserInfo("jane@example.com", False), compartments=[compartment])

        result = process_event(
            {
                "eventType": "User - Deactivate",
                "eventTime": "2026-07-27T12:00:00Z",
                "data": {"resourceId": "user-1", "resourceName": "jane@example.com"},
            },
            settings(grace_hours=72),
            gateway,
        )

        self.assertEqual(result["action"], "marked")
        self.assertEqual(result["delete_after"], "2026-07-30T12:00:00Z")
        self.assertEqual(
            gateway.tag_updates,
            [("comp.1", {"Other": {"Key": "value"}, "Oracle-Tags": {"DeleteCompartmentAfter": "2026-07-30T12:00:00Z"}})],
        )

    def test_duplicate_delete_does_not_extend_deadline(self):
        tags = {"Oracle-Tags": {"DeleteCompartmentAfter": "2026-07-30T12:00:00Z"}}
        gateway = FakeGateway(
            user=None,
            compartments=[CompartmentInfo("comp.1", "jane", tags)],
        )

        result = process_event(
            {
                "eventType": "User - Delete",
                "eventTime": "2026-07-28T12:00:00Z",
                "data": {"resourceName": "jane@example.com"},
            },
            settings(),
            gateway,
        )

        self.assertEqual(result["action"], "unchanged")
        self.assertEqual(result["delete_after"], "2026-07-30T12:00:00Z")
        self.assertEqual(gateway.tag_updates, [])

    def test_active_user_removes_deletion_tag(self):
        tags = {"Oracle-Tags": {"DeleteCompartmentAfter": "2026-07-30T12:00:00Z"}, "Other": {"Key": "value"}}
        gateway = FakeGateway(
            user=UserInfo("jane@example.com", True),
            compartments=[CompartmentInfo("comp.1", "jane", tags)],
        )

        result = process_event(
            {"eventType": "User - Activate", "data": {"resourceId": "user-1"}},
            settings(),
            gateway,
        )

        self.assertEqual(result["action"], "unmarked")
        self.assertEqual(gateway.tag_updates, [("comp.1", {"Other": {"Key": "value"}})])

    def test_delete_uses_event_username_when_user_is_gone(self):
        gateway = FakeGateway(compartments=[CompartmentInfo("comp.1", "jane", {})])

        result = process_event(
            {
                "eventType": "com.oraclecloud.identityControlPlane.DeleteUser",
                "eventTime": "2026-07-27T12:00:00Z",
                "data": {"resourceId": "deleted-user", "resourceName": "jane@example.com"},
            },
            settings(),
            gateway,
        )

        self.assertEqual(result["action"], "marked")
        self.assertEqual(gateway.tag_updates[0][0], "comp.1")

    def test_missing_compartment_on_delete_is_noop(self):
        result = process_event(
            {"eventType": "User - Delete", "data": {"resourceName": "jane@example.com"}},
            settings(),
            FakeGateway(),
        )

        self.assertEqual(result["reason"], "compartment_not_found_under_engineer_root")

    def test_dry_run_does_not_mutate(self):
        gateway = FakeGateway(
            user=UserInfo("jane@example.com", False),
            compartments=[CompartmentInfo("comp.1", "jane", {})],
        )

        result = process_event(
            {"eventType": "User - Deactivate", "eventTime": "2026-07-27T12:00:00Z", "data": {"resourceId": "user-1"}},
            settings(dry_run=True),
            gateway,
        )

        self.assertEqual(result["action"], "dry_run")
        self.assertEqual(gateway.created, [])
        self.assertEqual(gateway.tag_updates, [])

    def test_unsupported_event_is_ignored(self):
        result = process_event({"eventType": "User - PasswordChanged"}, settings(), FakeGateway())
        self.assertEqual(result["action"], "ignored")

    def test_config_defaults_and_validation(self):
        config = load_config({"DOMAIN_ID": "domain", "ENGINEER_ROOT_COMPARTMENT_OCID": "root"}, {})
        self.assertEqual(config.delete_grace_period_hours, 72)
        self.assertTrue(config.dry_run)

        with self.assertRaisesRegex(ValueError, "greater than zero"):
            load_config(
                {"DOMAIN_ID": "domain", "ENGINEER_ROOT_COMPARTMENT_OCID": "root", "DELETE_GRACE_PERIOD_HOURS": "0"},
                {},
            )


if __name__ == "__main__":
    unittest.main()
