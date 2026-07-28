import json
import unittest

from functions.engineer_quota_updater.func import load_config, parse_bool


class ConfigTests(unittest.TestCase):
    def test_parse_bool(self):
        self.assertTrue(parse_bool("true", default=False))
        self.assertFalse(parse_bool("no", default=True))
        self.assertTrue(parse_bool(None, default=True))

    def test_load_config_accepts_payload_overrides(self):
        config = {
            "ENGINEER_ROOT_COMPARTMENT_OCID": "root",
            "DRY_RUN": "true",
            "EXCLUDE_DELETE_MARKED_COMPARTMENTS": "false",
            "QUOTA_CONFIG_JSON": json.dumps([{"area": "network"}]),
        }
        payload = {
            "dry_run": False,
            "exclude_delete_marked_compartments": True,
            "quota_config_json": [{"area": "payload"}],
        }

        loaded = load_config(config, payload)

        self.assertFalse(loaded.dry_run)
        self.assertTrue(loaded.exclude_delete_marked_compartments)
        self.assertEqual(loaded.quota_config_source, "payload_override")
        self.assertEqual(loaded.quota_config, [{"area": "payload"}])

    def test_load_config_uses_bundled_defaults(self):
        config = {
            "ENGINEER_ROOT_COMPARTMENT_OCID": "root",
        }

        loaded = load_config(config, {})

        self.assertEqual(len(loaded.quota_config), 8)
        self.assertEqual(loaded.quota_config[0]["area"], "database")
        self.assertFalse(loaded.exclude_delete_marked_compartments)
        self.assertEqual(loaded.quota_config_source, "bundled_default")


if __name__ == "__main__":
    unittest.main()
