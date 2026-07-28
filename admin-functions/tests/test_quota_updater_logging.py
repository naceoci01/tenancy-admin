import io
import logging
import unittest

from functions.engineer_quota_updater.func import configure_logging, log_summary


class FunctionLoggingTests(unittest.TestCase):
    def test_configure_logging_suppresses_dependency_debug_by_default(self):
        configure_logging({"LOG_LEVEL": "INFO"}, {})
        self.assertEqual(logging.getLogger("engineer_quota_updater").getEffectiveLevel(), logging.INFO)
        self.assertEqual(logging.getLogger("urllib3.connectionpool").getEffectiveLevel(), logging.WARNING)
        self.assertEqual(logging.getLogger("oci.circuit_breaker").getEffectiveLevel(), logging.WARNING)

    def test_log_summary_emits_quota_lines(self):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("test_summary_logger")
        logger.handlers = [handler]
        logger.setLevel(logging.INFO)
        logger.propagate = False
        result = {
            "dry_run": True,
            "exclude_delete_marked_compartments": True,
            "quota_config_source": "payload_override",
            "quota_policy_count": 1,
            "discovered_compartment_count": 2,
            "quota_compartment_count": 1,
            "excluded_delete_marked_compartments": ["marked.user"],
            "quotas": [{"area": "network", "name": "network-quota", "action": "update", "statement_count": 5}],
        }
        log_summary(logger, result)
        output = stream.getvalue()
        self.assertIn("Summary dry_run=True", output)
        self.assertIn("Excluded delete-marked compartments: marked.user", output)
        self.assertIn("Quota network-quota area=network action=update", output)


if __name__ == "__main__":
    unittest.main()
