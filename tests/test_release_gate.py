import os
import unittest
from unittest.mock import patch

from src.orchestration.release_gate import evaluate_release_candidate


CUTOFF = "2026-09-26T23:59:00-03:00"


def technical_pass() -> dict:
    return {
        "full_regression_pass": True,
        "orchestration_ci_pass": True,
        "drift_gate_pass": True,
        "staging_ci_pass": True,
        "rollback_test_pass": True,
        "no_private_data": True,
        "expected_financial_cutoff": CUTOFF,
        "l4_evidence": {
            "cutoff": CUTOFF,
            "cxc_status": "INSUFFICIENT_EVIDENCE",
            "cxp_status": "INSUFFICIENT_EVIDENCE",
            "checks_status": "INSUFFICIENT_EVIDENCE",
            "bank_status": "INSUFFICIENT_EVIDENCE",
            "nominal_reconciliation_status": "INSUFFICIENT_EVIDENCE",
            "approved_by": "",
            "approval_timestamp": "",
            "evidence_refs": [],
            "source_hashes": {},
        },
        "l7_inputs": {},
        "writer_module_present": False,
        "production_adapter_configured": False,
    }


def confirm_l4(evidence: dict) -> None:
    evidence["l4_evidence"] = {
        "cutoff": CUTOFF,
        "cxc_status": "CONFIRMED",
        "cxp_status": "CONFIRMED",
        "checks_status": "CONFIRMED",
        "bank_status": "CONFIRMED",
        "nominal_reconciliation_status": "CONFIRMED",
        "approved_by": "FINANCE-APPROVER",
        "approval_timestamp": "2026-10-01T10:00:00-03:00",
        "evidence_refs": ["private:l4/manifest.json"],
        "source_hashes": {"manifest": "a" * 64},
    }


def confirm_l7(evidence: dict) -> None:
    evidence["l7_inputs"] = {
        "integrity_pass": True,
        "rollback_pass": True,
        "smoke_pass": True,
        "uat_pass": True,
        "manifest_complete": True,
        "human_approval": True,
        "approved_by": "CUTOVER-APPROVER",
        "approval_timestamp": "2026-10-01T10:05:00-03:00",
        # Incluso si alguien agrega l4_pass aquí, release_gate lo ignora.
        "l4_pass": True,
    }


class ReleaseGateTests(unittest.TestCase):
    def test_technical_rc_can_be_ready_while_production_is_blocked_l4(self):
        result = evaluate_release_candidate(technical_pass())
        self.assertTrue(result.technical_ready)
        self.assertEqual(result.technical_status, "RC_READY")
        self.assertEqual(result.production_status, "BLOCKED_L4")
        self.assertEqual(result.l4_status, "FAIL_CLOSED")
        self.assertEqual(result.l7_status, "NO_GO")
        self.assertFalse(result.production_ready)

    def test_missing_technical_evidence_blocks_rc(self):
        evidence = technical_pass()
        evidence["staging_ci_pass"] = False
        result = evaluate_release_candidate(evidence)
        self.assertFalse(result.technical_ready)
        self.assertEqual(result.technical_status, "RC_BLOCKED_TECHNICAL")
        self.assertIn("staging_ci_pass", result.failed_checks)
        self.assertEqual(result.production_status, "BLOCKED_TECHNICAL")

    def test_legacy_self_certified_flags_are_ignored(self):
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
        self.assertEqual(result.production_status, "BLOCKED_L4")
        self.assertFalse(result.gates_ready)

    def test_formal_l4_pass_without_l7_stays_blocked(self):
        evidence = technical_pass()
        confirm_l4(evidence)
        result = evaluate_release_candidate(evidence)
        self.assertEqual(result.l4_status, "PASS")
        self.assertEqual(result.production_status, "BLOCKED_L7")
        self.assertFalse(result.production_ready)

    def test_cutoff_mismatch_blocks_formal_l4(self):
        evidence = technical_pass()
        confirm_l4(evidence)
        evidence["l4_evidence"]["cutoff"] = "2026-09-27T23:59:00-03:00"
        result = evaluate_release_candidate(evidence)
        self.assertEqual(result.l4_status, "FAIL_CLOSED")
        self.assertEqual(result.production_status, "BLOCKED_L4")

    def test_interlock_is_required_after_formal_l4_l7(self):
        evidence = technical_pass()
        confirm_l4(evidence)
        confirm_l7(evidence)
        with patch.dict(os.environ, {}, clear=True):
            result = evaluate_release_candidate(evidence)
        self.assertEqual(result.l7_status, "GO")
        self.assertEqual(result.production_status, "BLOCKED_PROD_INTERLOCK")
        self.assertFalse(result.gates_ready)

    def test_all_formal_gates_do_not_create_writer(self):
        evidence = technical_pass()
        confirm_l4(evidence)
        confirm_l7(evidence)
        with patch.dict(os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}):
            result = evaluate_release_candidate(evidence)
        self.assertTrue(result.gates_ready)
        self.assertEqual(result.production_status, "GATES_READY_WRITER_ABSENT")
        self.assertFalse(result.production_ready)

    def test_writer_present_without_real_adapter_still_blocks(self):
        evidence = technical_pass()
        confirm_l4(evidence)
        confirm_l7(evidence)
        evidence["writer_module_present"] = True
        with patch.dict(os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}):
            result = evaluate_release_candidate(evidence)
        self.assertEqual(
            result.production_status,
            "GATES_READY_WRITER_PRESENT_NO_PRODUCTION_ADAPTER",
        )
        self.assertFalse(result.production_ready)

    def test_production_ready_requires_formal_gates_writer_and_adapter(self):
        evidence = technical_pass()
        confirm_l4(evidence)
        confirm_l7(evidence)
        evidence["writer_module_present"] = True
        evidence["production_adapter_configured"] = True
        with patch.dict(os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}):
            result = evaluate_release_candidate(evidence)
        self.assertTrue(result.production_ready)
        self.assertEqual(result.production_status, "PRODUCTION_READY")


if __name__ == "__main__":
    unittest.main()
