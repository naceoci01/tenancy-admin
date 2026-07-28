from datetime import datetime, timezone
import sys
import types
import unittest
from unittest.mock import patch

from func import (
    CompartmentInfo,
    CompartmentMoveConflictError,
    OciDeleteStagingGateway,
    stage_expired_compartments,
)


class FakeGateway:
    def __init__(self):
        self.moves = []

    def list_child_compartments(self, parent_compartment_ocid):
        return [
            CompartmentInfo(
                ocid="ocid1.compartment.oc1..source",
                name="expired-engineer-compartment",
                defined_tags={"Oracle-Tags": {"DeleteCompartmentAfter": "2026-01-01T00:00:00Z"}},
            )
        ]

    def move_compartment(self, compartment_ocid, destination_compartment_ocid):
        self.moves.append((compartment_ocid, destination_compartment_ocid))
        return "ocid1.workrequest.oc1..example"


class ConflictGateway(FakeGateway):
    def move_compartment(self, compartment_ocid, destination_compartment_ocid):
        error = RuntimeError("A compartment with this name already exists")
        error.status = 409
        error.code = "Conflict"
        error.request_id = "request-id"
        raise CompartmentMoveConflictError(error)


class PartialFailureGateway(FakeGateway):
    def list_child_compartments(self, parent_compartment_ocid):
        return [
            CompartmentInfo(
                ocid="ocid1.compartment.oc1..failed",
                name="failed-compartment",
                defined_tags={"Oracle-Tags": {"DeleteCompartmentAfter": "2026-01-01T00:00:00Z"}},
            ),
            CompartmentInfo(
                ocid="ocid1.compartment.oc1..moved",
                name="moved-compartment",
                defined_tags={"Oracle-Tags": {"DeleteCompartmentAfter": "2026-01-01T00:00:00Z"}},
            ),
        ]

    def move_compartment(self, compartment_ocid, destination_compartment_ocid):
        if compartment_ocid.endswith("failed"):
            error = RuntimeError("OCI service temporarily unavailable")
            error.status = 503
            error.code = "ServiceUnavailable"
            error.request_id = "failed-request-id"
            raise error
        return super().move_compartment(compartment_ocid, destination_compartment_ocid)


class DeleteStagingTests(unittest.TestCase):
    def test_move_compartment_uses_target_compartment_id_and_returns_work_request(self):
        class MoveCompartmentDetails:
            def __init__(self, target_compartment_id):
                self.target_compartment_id = target_compartment_id

        models_module = types.ModuleType("oci.identity.models")
        models_module.MoveCompartmentDetails = MoveCompartmentDetails
        identity_module = types.ModuleType("oci.identity")
        identity_module.models = models_module
        oci_module = types.ModuleType("oci")
        oci_module.identity = identity_module

        class IdentityClient:
            def move_compartment(self, compartment_ocid, details):
                self.compartment_ocid = compartment_ocid
                self.details = details
                return types.SimpleNamespace(headers={"opc-work-request-id": "ocid1.workrequest.oc1..example"})

        identity_client = IdentityClient()
        with patch.dict(
            sys.modules,
            {"oci": oci_module, "oci.identity": identity_module, "oci.identity.models": models_module},
        ):
            work_request_id = OciDeleteStagingGateway(identity_client).move_compartment(
                "ocid1.compartment.oc1..source",
                "ocid1.compartment.oc1..staging",
            )

        self.assertEqual(work_request_id, "ocid1.workrequest.oc1..example")
        self.assertEqual(identity_client.compartment_ocid, "ocid1.compartment.oc1..source")
        self.assertEqual(identity_client.details.target_compartment_id, "ocid1.compartment.oc1..staging")

    def test_move_compartment_maps_oci_409_to_conflict(self):
        class MoveCompartmentDetails:
            def __init__(self, target_compartment_id):
                self.target_compartment_id = target_compartment_id

        models_module = types.ModuleType("oci.identity.models")
        models_module.MoveCompartmentDetails = MoveCompartmentDetails
        identity_module = types.ModuleType("oci.identity")
        identity_module.models = models_module
        oci_module = types.ModuleType("oci")
        oci_module.identity = identity_module

        class IdentityClient:
            def move_compartment(self, compartment_ocid, details):
                error = RuntimeError("A compartment with this name already exists")
                error.status = 409
                error.code = "Conflict"
                error.request_id = "request-id"
                raise error

        with patch.dict(
            sys.modules,
            {"oci": oci_module, "oci.identity": identity_module, "oci.identity.models": models_module},
        ):
            with self.assertRaises(CompartmentMoveConflictError) as raised:
                OciDeleteStagingGateway(IdentityClient()).move_compartment(
                    "ocid1.compartment.oc1..source",
                    "ocid1.compartment.oc1..staging",
                )

        self.assertEqual(raised.exception.status, 409)
        self.assertEqual(raised.exception.code, "Conflict")
        self.assertEqual(raised.exception.request_id, "request-id")

    def test_real_run_reports_submitted_move_work_request(self):
        gateway = FakeGateway()

        result = stage_expired_compartments(
            {
                "ENGINEER_ROOT_COMPARTMENT_OCID": "ocid1.compartment.oc1..root",
                "DELETE_STAGING_COMPARTMENT_OCID": "ocid1.compartment.oc1..staging",
                "DRY_RUN": "false",
            },
            {},
            gateway,
            now=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(
            gateway.moves,
            [("ocid1.compartment.oc1..source", "ocid1.compartment.oc1..staging")],
        )
        self.assertEqual(result["action_counts"], {"move_requested": 1})
        self.assertEqual(
            result["actions"],
            [
                {
                    "name": "expired-engineer-compartment",
                    "ocid": "ocid1.compartment.oc1..source",
                    "action": "move_requested",
                    "delete_after": "2026-01-01T00:00:00Z",
                    "work_request_id": "ocid1.workrequest.oc1..example",
                }
            ],
        )

    def test_real_run_reports_oci_conflict_without_raising(self):
        result = stage_expired_compartments(
            {
                "ENGINEER_ROOT_COMPARTMENT_OCID": "ocid1.compartment.oc1..root",
                "DELETE_STAGING_COMPARTMENT_OCID": "ocid1.compartment.oc1..staging",
                "DRY_RUN": "false",
            },
            {},
            ConflictGateway(),
            now=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(result["action_counts"], {"move_conflict": 1})
        self.assertEqual(result["actions"][0]["oci_status"], 409)
        self.assertEqual(result["actions"][0]["oci_code"], "Conflict")
        self.assertEqual(result["actions"][0]["oci_message"], "A compartment with this name already exists")
        self.assertEqual(result["actions"][0]["oci_request_id"], "request-id")

    def test_real_run_continues_after_a_move_failure(self):
        gateway = PartialFailureGateway()
        result = stage_expired_compartments(
            {
                "ENGINEER_ROOT_COMPARTMENT_OCID": "ocid1.compartment.oc1..root",
                "DELETE_STAGING_COMPARTMENT_OCID": "ocid1.compartment.oc1..staging",
                "DRY_RUN": "false",
            },
            {},
            gateway,
            now=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(result["action_counts"], {"move_failed": 1, "move_requested": 1})
        self.assertEqual(result["actions"][0]["action"], "move_failed")
        self.assertEqual(result["actions"][0]["error_message"], "OCI service temporarily unavailable")
        self.assertEqual(result["actions"][0]["oci_status"], 503)
        self.assertEqual(
            gateway.moves,
            [("ocid1.compartment.oc1..moved", "ocid1.compartment.oc1..staging")],
        )


if __name__ == "__main__":
    unittest.main()
