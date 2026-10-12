import unittest
import sys
from types import ModuleType, SimpleNamespace


def _install_oci_stub():
    oci = ModuleType("oci")
    oci.retry = SimpleNamespace(DEFAULT_RETRY_STRATEGY=None)
    oci.regions = SimpleNamespace(
        get_region_from_short_name=lambda region: {"phx": "us-phoenix-1"}.get(region, region)
    )
    oci.auth = ModuleType("oci.auth")
    oci.auth.signers = SimpleNamespace(get_resource_principals_signer=None)
    oci.database = ModuleType("oci.database")
    oci.database.DatabaseClient = object
    oci.database.models = ModuleType("oci.database.models")
    oci.database.models.UpdateAutonomousDatabaseDetails = object
    oci.exceptions = ModuleType("oci.exceptions")
    oci.exceptions.MaximumWaitTimeExceeded = type("MaximumWaitTimeExceeded", (Exception,), {})
    oci.exceptions.ServiceError = type("ServiceError", (Exception,), {})
    oci.resource_search = ModuleType("oci.resource_search")
    oci.resource_search.ResourceSearchClient = object
    oci.resource_search.models = ModuleType("oci.resource_search.models")
    oci.resource_search.models.StructuredSearchDetails = object
    sys.modules.update({
        "oci": oci,
        "oci.auth": oci.auth,
        "oci.database": oci.database,
        "oci.database.models": oci.database.models,
        "oci.exceptions": oci.exceptions,
        "oci.resource_search": oci.resource_search,
        "oci.resource_search.models": oci.resource_search.models,
    })


try:
    import oci  # noqa: F401
except ModuleNotFoundError:
    _install_oci_stub()

from func import (
    _format_notification,
    _notification_region,
    _reconcile_with_log,
    load_config,
    reconcile_database,
)


class NotificationFormatTests(unittest.TestCase):
    def test_notification_has_readable_summary_and_details(self):
        body = _format_notification({
            "mode": "DRY-RUN",
            "started_at": "2026-07-30T12:00:00+00:00",
            "completed_at": "2026-07-30T12:01:00+00:00",
            "duration_seconds": 60.0,
            "database_count": 3,
            "changed_count": 1,
            "no_op_count": 1,
            "error_count": 1,
            "actions": {"convert_to_ecpu": 1, "scale_storage_gb": 1},
            "results": [
                {
                    "detail": {"name": "changed-db", "workload": "OLTP", "compartment_id": "cmp", "ocid": "db1"},
                    "actions": ["convert_to_ecpu", {"scale_storage_gb": 20}],
                },
                {
                    "detail": {"name": "skipped-db", "workload": "DW", "compartment_id": "cmp", "ocid": "db2"},
                    "actions": [],
                    "no_op": "no configured changes required",
                },
                {
                    "detail": {"name": "failed-db", "workload": "JSON", "compartment_id": "cmp", "ocid": "db3"},
                    "actions": [],
                    "error": "request timed out",
                },
            ],
        })

        self.assertIn("SUMMARY", body)
        self.assertIn("DETAILS", body)
        self.assertIn("Outcome\tName\tWorkload", body)
        self.assertIn("DRY-RUN", body)
        self.assertIn("PLANNED\tchanged-db\tOLTP", body)
        self.assertIn("convert to ecpu, scale storage gb: 20 GB", body)
        self.assertIn("NO-OP\tskipped-db\tDW", body)
        self.assertIn("ERROR\tfailed-db\tJSON", body)


class ReconcileLogTests(unittest.TestCase):
    def test_reconcile_returns_one_ordered_log_block(self):
        database = SimpleNamespace(
            id="db1",
            display_name="skipped-db",
            db_workload="OLTP",
            lifecycle_state="AVAILABLE",
            is_dedicated=True,
            is_free_tier=False,
            is_dev_tier=False,
        )
        client = SimpleNamespace(
            get_autonomous_database=lambda _db_id: SimpleNamespace(data=database)
        )
        item = SimpleNamespace(identifier="db1", compartment_id="cmp")
        settings = {"dry_run": True}

        result, operation_log = _reconcile_with_log(client, item, settings)

        self.assertEqual("dedicated/free/developer tier", result["no_op"])
        self.assertEqual("RECONCILE start: database=db1", operation_log[0][1])
        self.assertIn("SKIP skipped-db", operation_log[1][1])
        self.assertEqual(
            "RECONCILE finish: database=skipped-db outcome=SKIP",
            operation_log[-1][1],
        )

    def test_adw_and_lakehouse_storage_updates_use_tbs(self):
        from unittest.mock import patch

        database = SimpleNamespace(
            id="db1",
            display_name="lakehouse-db",
            db_workload="ADW",
            lifecycle_state="AVAILABLE",
            is_dedicated=False,
            is_free_tier=False,
            is_dev_tier=False,
            role="PRIMARY",
            compute_model="ECPU",
            compute_count=2,
            backup_retention_period_in_days=14,
            allocated_storage_size_in_tbs=1,
            data_storage_size_in_tbs=4,
            license_model="BRING_YOUR_OWN_LICENSE",
        )
        client = SimpleNamespace(
            get_autonomous_database=lambda _db_id: SimpleNamespace(data=database)
        )
        settings = {
            "dry_run": True,
            "workloads": ["ADW"],
            "scale_storage": True,
            "minimum_storage_gb": 20,
            "storage_multiplier": 2,
            "convert_to_ecpu": False,
            "reduce_backup_retention": False,
            "reduce_ecpus": False,
            "convert_license": False,
        }

        with patch("func.UpdateAutonomousDatabaseDetails", side_effect=lambda **kwargs: kwargs) as details:
            result = reconcile_database(client, "db1", settings)

        self.assertEqual([{"scale_storage_tb": 2}], result["actions"])
        self.assertEqual(
            {
                "data_storage_size_in_tbs": 2,
                "is_auto_scaling_for_storage_enabled": True,
            },
            details.call_args.kwargs,
        )

        database.db_workload = "LH"
        settings["workloads"] = ["LH"]
        with patch("func.UpdateAutonomousDatabaseDetails", side_effect=lambda **kwargs: kwargs) as details:
            result = reconcile_database(client, "db1", settings)

        self.assertEqual([{"scale_storage_tb": 2}], result["actions"])
        self.assertEqual(
            {
                "data_storage_size_in_tbs": 2,
                "is_auto_scaling_for_storage_enabled": True,
            },
            details.call_args.kwargs,
        )


class RegionResolutionTests(unittest.TestCase):
    def test_notification_region_comes_from_topic_ocid(self):
        self.assertEqual(
            "us-phoenix-1",
            _notification_region(
                "ocid1.onstopic.oc1.phx.aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
            ),
        )

    def test_invalid_notification_topic_ocid_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "NOTIFICATION_TOPIC_ID"):
            _notification_region("not-a-topic-ocid")

    def test_blank_regions_uses_resource_principal_region(self):
        from unittest.mock import patch

        with patch(
            "func.signers.get_resource_principals_signer",
            return_value=SimpleNamespace(region="us-phoenix-1"),
        ):
            settings = load_config({}, {})

        self.assertEqual(["us-phoenix-1"], settings["regions"])


if __name__ == "__main__":
    unittest.main()
