import importlib.util
import pathlib
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


FUNCTION_PATH = pathlib.Path(__file__).with_name("func.py")
SPEC = importlib.util.spec_from_file_location("policy_cleanup_report_func", FUNCTION_PATH)
FUNCTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FUNCTION)


class PolicyCleanupReportTests(unittest.TestCase):
    def test_groups_one_statement_under_each_validation_reason(self):
        grouped = FUNCTION._group_invalid_statements([
            {
                "policy_name": "bad-policy",
                "compartment_path": "ROOT/Engineering",
                "statement_text": "Allow group Missing to manage frobs in tenancy",
                "invalid_reasons": ["Unknown group", "Unknown resource type"],
            },
        ])

        self.assertEqual(list(grouped), ["Unknown group", "Unknown resource type"])
        self.assertEqual(grouped["Unknown group"][0]["policy"], "bad-policy")
        self.assertEqual(grouped["Unknown resource type"][0]["compartment"], "ROOT/Engineering")

    def test_missing_group_is_annotated_when_same_name_exists_in_other_domain(self):
        statements = [{
            "subject_type": "group",
            "subject": [("Finance", "Operators")],
            "invalid_reasons": ["Group Operators not found in tenancy"],
        }]

        FUNCTION._missing_principal_domain_matches(statements, [
            {"domain_name": "Engineering", "group_name": "operators"},
            {"domain_name": "Finance", "group_name": "Other"},
        ], [])

        self.assertEqual(statements[0]["identity_domain_matches"], [{
            "principal_type": "group", "principal_name": "Operators",
            "referenced_domain": "Finance", "other_domains": "Engineering",
        }])
        self.assertIn("other domain(s): Engineering", FUNCTION._identity_domain_evidence_text(statements[0]))

    def test_exact_domain_match_is_not_reported_as_cross_domain_evidence(self):
        statements = [{
            "subject_type": "dynamic-group",
            "subject": [("Default", "FunctionRunners")],
            "invalid_reasons": ["Dynamic Group FunctionRunners not found in tenancy"],
        }]

        FUNCTION._missing_principal_domain_matches(statements, [], [
            {"domain_name": "default", "dynamic_group_name": "FunctionRunners"},
        ])

        self.assertNotIn("identity_domain_matches", statements[0])

    def test_missing_dynamic_group_is_annotated_when_same_name_exists_in_other_domain(self):
        statements = [{
            "subject_type": "dynamic-group",
            "subject": [("Finance", "FunctionRunners")],
            "invalid_reasons": ["Dynamic Group FunctionRunners not found in tenancy"],
        }]

        FUNCTION._missing_principal_domain_matches(statements, [], [
            {"domain_name": "Engineering", "dynamic_group_name": "functionrunners"},
        ])

        self.assertEqual(statements[0]["identity_domain_matches"][0]["other_domains"], "Engineering")

    def test_genai_prompt_includes_identity_domain_candidate_evidence(self):
        prompt = FUNCTION._genai_prompt({
            "invalid_by_reason": {
                "Group Operators not found in tenancy": [{
                    "statement": "Allow group Finance/Operators to read buckets in tenancy",
                    "identity_domain_evidence": "Same-named group 'Operators' exists in other domain(s): Engineering",
                }],
            },
        })

        self.assertIn("same-name candidate", prompt)
        self.assertIn("other domain(s): Engineering", prompt)

    def test_notification_keeps_cleanup_findings(self):
        body = FUNCTION.format_notification(
            {
                "generated_at": "2026-09-25T12:00:00+00:00",
                "tenancy": {"tenancy_name": "example", "data_as_of": "2026-09-25T12:00:00Z"},
                "invalid_statement_count": 1,
                "invalid_by_reason": {
                    "Unknown group": [{"policy": "bad-policy", "compartment": "ROOT", "statement": "Allow group Missing to read buckets in tenancy"}],
                },
            }
        )

        self.assertIn("INVALID STATEMENTS BY REASON", body)
        self.assertIn("Unknown group\t(1)", body)
        self.assertIn("Allow group Missing to read buckets", body)
        self.assertIn("GROUPS WITH NO USER MEMBERS", body)
        self.assertIn("DYNAMIC GROUPS NOT REFERENCED BY SCANNED POLICIES", body)

    def test_genai_is_not_called_when_disabled(self):
        report = {"invalid_by_reason": {"Unknown group": []}}
        self.assertIsNone(FUNCTION.generate_ai_guidance(report, {}, {}))

    def test_enabled_genai_requires_model_and_compartment(self):
        report = {"invalid_by_reason": {"Unknown group": []}}
        message = FUNCTION.generate_ai_guidance(report, {"ENABLE_GENAI_ENRICHMENT": "true"}, {})
        self.assertIn("GENAI_MODEL_ID", message)

    def test_notification_is_disabled_by_default_even_with_an_inherited_topic(self):
        self.assertFalse(FUNCTION.should_publish_notification({"NOTIFICATION_TOPIC_ID": "topic"}, {}))
        self.assertTrue(FUNCTION.should_publish_notification({}, {"publish_notification": True}))

    def test_policy_analysis_runtime_uses_ephemeral_writable_home(self):
        with patch.dict("os.environ", {"HOME": "/home/fn"}, clear=False):
            FUNCTION.configure_policy_analysis_runtime()
            self.assertEqual(FUNCTION.os.environ["HOME"], "/tmp/oci-policy-analysis")

    def test_publish_summary_uses_resource_principal_and_topic_region(self):
        client = unittest.mock.Mock()
        oci = ModuleType("oci")
        oci.regions = SimpleNamespace(get_region_from_short_name=lambda value: {"phx": "us-phoenix-1"}[value])
        oci.retry = SimpleNamespace(DEFAULT_RETRY_STRATEGY="retry")
        oci.ons = SimpleNamespace(NotificationDataPlaneClient=lambda *args, **kwargs: client, models=SimpleNamespace(MessageDetails=lambda **kwargs: kwargs))
        oci_auth = ModuleType("oci.auth")
        oci_auth.signers = SimpleNamespace(get_resource_principals_signer=lambda: "resource-principal")
        report = {"generated_at": "now", "tenancy": {}, "invalid_statement_count": 0, "invalid_by_reason": {}}

        with patch.dict("sys.modules", {"oci": oci, "oci.auth": oci_auth}):
            FUNCTION.publish_summary("ocid1.onstopic.oc1.phx.example", report, None)

        self.assertEqual(client.publish_message.call_args.kwargs["topic_id"], "ocid1.onstopic.oc1.phx.example")
        self.assertEqual(client.publish_message.call_args.kwargs["message_details"]["title"], "OCI IAM Policy Cleanup Report")


if __name__ == "__main__":
    unittest.main()
