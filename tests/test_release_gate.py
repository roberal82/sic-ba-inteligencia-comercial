import os
import unittest
from unittest.mock import patch

from src.orchestration.release_gate import evaluate_release_candidate


def technical_pass() -> dict:
    return {
        "full_regression_pass": True,
        "orchestration_ci_pass": True,
        "drift_gate_pass": True,
        "staging_ci_pass": True,
        "rollback_test_pass": True,
        "no_private_data": True,
        "l4_pass": False,
        "l7_go": False,
        "rollback_real_proven": False,
        "human_approval": False,
    }


class ReleaseGateTests(unittest.TestCase):
    def test_technical_rc_can_be_ready_while_production_is_blocked_l4(self):
        result = evaluate_release_candidate(technical_pass())
        self.assertTrue(result.technical_ready)
        self.assertEqual(result.technical_status, "RC_READY")
        self.assertEqual(result.production_status, "BLOCKED_L4")
        self.assertFalse(result.production_ready)
        self.assertFalse(result.writer_present)

    def test_missing_technical_evidence_blocks_rc(self):
        evidence = technical_pass()
        evidence["staging_ci_pass"] = False
        result = evaluate_release_candidate(evidence)
        self.assertFalse(result.technical_ready)
        self.assertEqual(result.technical_status, "RC_BLOCKED_TECHNICAL")
        self.assertIn("staging_ci_pass", result.failed_checks)
        self.assertEqual(result.production_status, "BLOCKED_TECHNICAL")

    def test_l4_pass_without_l7_stays_blocked(self):
        evidence = technical_pass()
        evidence["l4_pass"] = True
        result = evaluate_release_candidate(evidence)
        self.assertEqual(result.production_status, "BLOCKED_L7")
        self.assertFalse(result.production_ready)

    def test_approval_or_real_rollback_is_required(self):
        evidence = technical_pass()
        evidence.update({"l4_pass": True, "l7_go": True})
        result = evaluate_release_candidate(evidence)
        self.assertEqual(result.production_status, "BLOCKED_APPROVAL_OR_ROLLBACK")

    def test_interlock_is_required_after_financial_and_human_gates(self):
        evidence = technical_pass()
        evidence.update(
            {
                "l4_pass": True,
                "l7_go": True,
                "rollback_real_proven": True,
                "human_approval": True,
            }
        )
        with patch.dict(os.environ, {}, clear=True):
            result = evaluate_release_candidate(evidence)
        self.assertEqual(result.production_status, "BLOCKED_PROD_INTERLOCK")
        self.assertFalse(result.gates_ready)

    def test_even_all_gates_do_not_create_production_writer(self):
        evidence = technical_pass()
        evidence.update(
            {
                "l4_pass": True,
                "l7_go": True,
                "rollback_real_proven": True,
                "human_approval": True,
            }
        )
        with patch.dict(os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}):
            result = evaluate_release_candidate(evidence)
        self.assertTrue(result.gates_ready)
        self.assertEqual(result.production_status, "GATES_READY_WRITER_ABSENT")
        self.assertFalse(result.production_ready)
        self.assertFalse(result.writer_present)

    def test_writer_present_without_production_adapter_still_blocks_production(self):
        evidence = technical_pass()
        evidence.update(
            {
                "l4_pass": True,
                "l7_go": True,
                "rollback_real_proven": True,
                "human_approval": True,
                "writer_module_present": True,
            }
        )
        with patch.dict(os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}):
            result = evaluate_release_candidate(evidence)
        self.assertTrue(result.writer_present)
        self.assertFalse(result.production_adapter_configured)
        self.assertFalse(result.production_ready)
        self.assertEqual(result.production_status, "GATES_READY_WRITER_PRESENT_NO_PRODUCTION_ADAPTER")

    def test_production_ready_requires_writer_and_real_adapter_and_all_gates(self):
        evidence = technical_pass()
        evidence.update(
            {
                "l4_pass": True,
                "l7_go": True,
                "rollback_real_proven": True,
                "human_approval": True,
                "writer_module_present": True,
                "production_adapter_configured": True,
            }
        )
        with patch.dict(os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}):
            result = evaluate_release_candidate(evidence)
        self.assertTrue(result.production_ready)
        self.assertEqual(result.production_status, "PRODUCTION_READY")

    def test_writer_present_alone_without_env_interlock_stays_blocked(self):
        evidence = technical_pass()
        evidence.update({"writer_module_present": True, "production_adapter_configured": True})
        with patch.dict(os.environ, {}, clear=True):
            result = evaluate_release_candidate(evidence)
        self.assertFalse(result.production_ready)
        self.assertEqual(result.production_status, "BLOCKED_L4")


if __name__ == "__main__":
    unittest.main()
