import importlib.util
from datetime import datetime, timezone
import io
import logging
import pathlib
import unittest


FUNCTION_PATH = pathlib.Path(__file__).parents[1] / "functions" / "engineer_compartment_delete_staging" / "func.py"
SPEC = importlib.util.spec_from_file_location("engineer_compartment_delete_staging_func", FUNCTION_PATH)
DELETE_STAGING_FUNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DELETE_STAGING_FUNC)

CompartmentInfo = DELETE_STAGING_FUNC.CompartmentInfo
LOGGER = DELETE_STAGING_FUNC.LOGGER
load_config = DELETE_STAGING_FUNC.load_config
stage_expired_compartments = DELETE_STAGING_FUNC.stage_expired_compartments


class FakeGateway:
    def __init__(self, compartments):
        self.compartments = compartments
        self.moves = []

    def list_child_compartments(self, parent_compartment_ocid):
        self.parent_compartment_ocid = parent_compartment_ocid
        return self.compartments

    def move_compartment(self, compartment_ocid, destination_compartment_ocid):
        self.moves.append((compartment_ocid, destination_compartment_ocid))


def config(dry_run=True):
    return {
        "ENGINEER_ROOT_COMPARTMENT_OCID": "engineer-root",
        "DELETE_STAGING_COMPARTMENT_OCID": "delete-staging",
        "DRY_RUN": str(dry_run).lower(),
    }


def tagged_compartment(ocid, name, delete_after):
    return CompartmentInfo(ocid, name, {"Oracle-Tags": {"DeleteCompartmentAfter": delete_after}})


class DeleteStagingTests(unittest.TestCase):
    def test_dry_run_reports_only_expired_compartments(self):
        gateway = FakeGateway(
            [
                tagged_compartment("comp.future", "future", "2026-07-30T00:00:00Z"),
                tagged_compartment("comp.expired", "expired", "2026-07-27T00:00:00Z"),
                CompartmentInfo("comp.untagged", "untagged", {}),
            ]
        )

        result = stage_expired_compartments(config(), {}, gateway, datetime(2026, 7, 28, tzinfo=timezone.utc))

        self.assertEqual(result["action_counts"], {"dry_run": 1, "not_due": 1})
        self.assertEqual(gateway.moves, [])

    def test_live_run_moves_expired_compartment_to_staging(self):
        gateway = FakeGateway(
            [
                tagged_compartment("comp.future", "future", "2026-07-30T00:00:00Z"),
                tagged_compartment("comp.expired", "expired", "2026-07-27T00:00:00Z"),
            ]
        )

        result = stage_expired_compartments(config(dry_run=False), {}, gateway, datetime(2026, 7, 28, tzinfo=timezone.utc))

        expired_action = next(action for action in result["actions"] if action["name"] == "expired")
        self.assertEqual(expired_action["action"], "moved")
        self.assertEqual(gateway.moves, [("comp.expired", "delete-staging")])

    def test_dry_run_logs_the_staging_candidates(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        LOGGER.handlers = [handler]
        LOGGER.setLevel(logging.INFO)
        LOGGER.propagate = False
        gateway = FakeGateway([tagged_compartment("comp.expired", "expired", "2026-07-27T00:00:00Z")])

        stage_expired_compartments(config(), {}, gateway, datetime(2026, 7, 28, tzinfo=timezone.utc))

        self.assertIn("Delete-staging candidates dry_run=True count=1 compartments=expired", stream.getvalue())

    def test_invalid_deadline_is_reported_without_a_move(self):
        gateway = FakeGateway([tagged_compartment("comp.invalid", "invalid", "not-a-date")])

        result = stage_expired_compartments(config(dry_run=False), {}, gateway, datetime(2026, 7, 28, tzinfo=timezone.utc))

        self.assertEqual(result["actions"][0]["action"], "invalid_delete_after")
        self.assertEqual(gateway.moves, [])

    def test_config_requires_both_compartment_ocids(self):
        with self.assertRaisesRegex(ValueError, "DELETE_STAGING_COMPARTMENT_OCID"):
            load_config({"ENGINEER_ROOT_COMPARTMENT_OCID": "root"}, {})


if __name__ == "__main__":
    unittest.main()
