import json
import pathlib
import unittest

from functions.engineer_quota_updater.func import (
    CompartmentInfo,
    QuotaInfo,
    reconcile_quotas,
    render_quota_policies,
)


class FakeGateway:
    def __init__(self, compartments=None, quotas=None):
        self.compartments = compartments or []
        self.quotas = quotas or []
        self.created_quotas = []
        self.updated_quotas = []

    def get_compartment_name(self, compartment_ocid):
        self.last_root_ocid = compartment_ocid
        return "cloud-engineering"

    def list_child_compartments(self, parent_compartment_ocid):
        return self.compartments

    def list_quotas(self):
        return self.quotas

    def create_quota(self, name, description, statements):
        created = QuotaInfo(f"quota.{name}", name, description, tuple(statements))
        self.created_quotas.append(created)
        return created

    def update_quota(self, quota_id, description, statements):
        self.updated_quotas.append((quota_id, description, statements))


def load_sample_config():
    sample_path = pathlib.Path(__file__).parents[1] / "samples" / "engineer-quota-config.json"
    return json.loads(sample_path.read_text())


def base_config(quota_config):
    return {
        "ENGINEER_ROOT_COMPARTMENT_OCID": "root",
        "DRY_RUN": "true",
        "EXCLUDE_DELETE_MARKED_COMPARTMENTS": "false",
        "QUOTA_CONFIG_JSON": json.dumps(quota_config),
    }


class QuotaUpdaterTests(unittest.TestCase):
    def test_dry_run_updates_quotas_only(self):
        gateway = FakeGateway(compartments=[CompartmentInfo("ocid.active", "active.user", {})])

        result = reconcile_quotas(base_config(load_sample_config()), {}, gateway)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["quota_compartments"], ["active.user"])
        self.assertEqual(gateway.created_quotas, [])
        self.assertEqual(gateway.updated_quotas, [])
        self.assertTrue(all(quota["action"] == "create" for quota in result["quotas"]))

    def test_all_direct_child_compartments_are_targets(self):
        gateway = FakeGateway(
            compartments=[
                CompartmentInfo("ocid.b", "b.engineer", {}),
                CompartmentInfo("ocid.a", "a.engineer", {}),
                CompartmentInfo("ocid.duplicate", "a.engineer", {}),
            ]
        )

        result = reconcile_quotas(base_config(load_sample_config()), {}, gateway)

        self.assertEqual(result["discovered_compartment_count"], 3)
        self.assertEqual(result["quota_compartments"], ["a.engineer", "b.engineer"])

    def test_delete_marked_compartments_can_be_excluded(self):
        config = base_config(load_sample_config())
        config["EXCLUDE_DELETE_MARKED_COMPARTMENTS"] = "true"
        gateway = FakeGateway(
            compartments=[
                CompartmentInfo("ocid.active", "active.user", {}),
                CompartmentInfo("ocid.marked", "marked.user", {"Oracle-Tags": {"DeleteCompartmentAfter": "2026-07-30T00:00:00Z"}}),
            ],
        )

        result = reconcile_quotas(config, {}, gateway)

        self.assertEqual(result["quota_compartments"], ["active.user"])
        self.assertEqual(result["excluded_delete_marked_compartments"], ["marked.user"])

    def test_delete_marked_compartments_are_included_by_default(self):
        gateway = FakeGateway(
            compartments=[
                CompartmentInfo("ocid.active", "active.user", {}),
                CompartmentInfo("ocid.marked", "marked.user", {"Oracle-Tags": {"DeleteCompartmentAfter": "2026-07-30T00:00:00Z"}}),
            ]
        )

        result = reconcile_quotas(base_config(load_sample_config()), {}, gateway)

        self.assertEqual(result["quota_compartments"], ["active.user", "marked.user"])
        self.assertEqual(result["excluded_delete_marked_compartments"], [])

    def test_live_run_updates_changed_quota(self):
        quota_config = load_sample_config()
        rendered = render_quota_policies(quota_config, "cloud-engineering", ["active.user"])
        network = next(policy for policy in rendered if policy["area"] == "network")
        existing_network = QuotaInfo(network["name"], network["name"], network["description"], ("old statement",))
        config = base_config(quota_config)
        config["DRY_RUN"] = "false"
        gateway = FakeGateway(
            compartments=[CompartmentInfo("ocid.active", "active.user", {})],
            quotas=[existing_network],
        )

        result = reconcile_quotas(config, {}, gateway)

        actions = {quota["name"]: quota["action"] for quota in result["quotas"]}
        self.assertEqual(actions[network["name"]], "update")
        self.assertEqual(len(gateway.updated_quotas), 1)
        self.assertEqual(gateway.updated_quotas[0][0], network["name"])
        self.assertEqual(len(gateway.created_quotas), 6)


if __name__ == "__main__":
    unittest.main()
