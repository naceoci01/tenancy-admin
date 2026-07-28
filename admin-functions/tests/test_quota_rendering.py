import json
import pathlib
import unittest

from functions.engineer_quota_updater.func import render_quota_policies, render_statement


class QuotaRenderingTests(unittest.TestCase):
    def test_render_set_per_engineer_statement(self):
        statement = {
            "scope": "per_engineer",
            "operation": "set",
            "service": "compute-memory",
            "quota": "standard-e5-memory-count",
            "value": 200,
        }
        rendered = render_statement(statement, "cloud-engineering", "andrew.gregory")
        self.assertEqual(
            rendered,
            "set compute-memory quota standard-e5-memory-count to 200 in compartment cloud-engineering:andrew.gregory",
        )

    def test_render_zero_root_statement_with_specific_quota(self):
        statement = {
            "scope": "root",
            "operation": "zero",
            "service": "block-storage",
            "quota": "total-storage-gb",
        }
        rendered = render_statement(statement, "cloud-engineering", None)
        self.assertEqual(rendered, "zero block-storage quota total-storage-gb in compartment cloud-engineering")

    def test_sample_config_renders_expected_policies(self):
        sample_path = pathlib.Path(__file__).parents[1] / "samples" / "engineer-quota-config.json"
        policies = render_quota_policies(json.loads(sample_path.read_text()), "cloud-engineering", ["b.user", "a.user"])
        self.assertEqual(len(policies), 7)
        nosql = next(policy for policy in policies if policy["area"] == "nosql")
        self.assertIn("zero nosql quota in compartment cloud-engineering", nosql["statements"])
        self.assertIn("set nosql quota read-unit-count to 100 in compartment cloud-engineering:a.user", nosql["statements"])

    def test_compute_memory_root_and_per_engineer_counts(self):
        sample_path = pathlib.Path(__file__).parents[1] / "samples" / "engineer-quota-config.json"
        policies = render_quota_policies(json.loads(sample_path.read_text()), "cloud-engineering", ["a.user", "b.user"])
        compute_memory = next(policy for policy in policies if policy["area"] == "compute-memory")
        self.assertEqual(len(compute_memory["statements"]), 12)
        self.assertIn("compute-memory standard-e4-memory-count=200", compute_memory["summary"]["per_engineer"])


if __name__ == "__main__":
    unittest.main()
