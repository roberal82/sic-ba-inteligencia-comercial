import unittest

from src.gates.l4_evidence import EvidenceStatus, FinancialGateEvidence, evaluate_l4
from src.gates.l7_decision import L7Inputs, evaluate_l7


def _complete_evidence(**overrides):
    base = dict(
        cutoff="2026-09-26T23:59:00-03:00",
        cxc_status=EvidenceStatus.CONFIRMED,
        cxp_status=EvidenceStatus.CONFIRMED,
        checks_status=EvidenceStatus.CONFIRMED,
        bank_status=EvidenceStatus.CONFIRMED,
        nominal_reconciliation_status=EvidenceStatus.CONFIRMED,
        approved_by="FINANZAS",
        approval_timestamp="2026-09-29T10:00:00-03:00",
        evidence_refs=("L4-CIERRE-2026-09",),
        source_hashes={"cxc.csv": "a" * 64},
    )
    base.update(overrides)
    return FinancialGateEvidence(**base)


class L4EvidenceGateTests(unittest.TestCase):
    def test_empty_evidence_fails_closed(self):
        result = evaluate_l4(FinancialGateEvidence())
        self.assertEqual(result.gate_result, "FAIL_CLOSED")
        self.assertFalse(result.l4_pass)
        self.assertGreaterEqual(len(result.reasons), 8)

    def test_l4_pass_only_flag_is_never_enough(self):
        # Ni siquiera con todos los status CONFIRMED, un solo flag l4_pass=True
        # existiría en payloads externos; aquí garantizamos que faltan otros
        # campos obligatorios siguen bloqueando el gate.
        evidence = FinancialGateEvidence(
            cxc_status=EvidenceStatus.CONFIRMED,
            cxp_status=EvidenceStatus.CONFIRMED,
            checks_status=EvidenceStatus.CONFIRMED,
            bank_status=EvidenceStatus.CONFIRMED,
            nominal_reconciliation_status=EvidenceStatus.CONFIRMED,
        )
        result = evaluate_l4(evidence)
        self.assertEqual(result.gate_result, "FAIL_CLOSED")
        self.assertTrue(any("cutoff" in r for r in result.reasons))
        self.assertTrue(any("approved_by" in r for r in result.reasons))

    def test_one_non_confirmed_status_blocks(self):
        evidence = _complete_evidence(cxc_status=EvidenceStatus.CANDIDATE)
        result = evaluate_l4(evidence)
        self.assertEqual(result.gate_result, "FAIL_CLOSED")
        self.assertTrue(any("cxc_status" in r for r in result.reasons))

    def test_complete_evidence_passes(self):
        result = evaluate_l4(_complete_evidence())
        self.assertEqual(result.gate_result, "PASS")
        self.assertTrue(result.l4_pass)
        self.assertEqual(result.reasons, ())

    def test_cutoff_mismatch_against_controlled_reference_blocks(self):
        evidence = _complete_evidence(cutoff="2026-08-31T23:59:00-03:00")
        result = evaluate_l4(evidence, expected_cutoff="2026-09-26T23:59:00-03:00")
        self.assertEqual(result.gate_result, "FAIL_CLOSED")
        self.assertTrue(any("no coincide" in r for r in result.reasons))

    def test_from_mapping_ignores_unknown_status_strings(self):
        evidence = FinancialGateEvidence.from_mapping({"cxc_status": "OFICIAL_A_MANO"})
        self.assertIsNone(evidence.cxc_status)


class L7DecisionGateTests(unittest.TestCase):
    def test_default_inputs_are_no_go(self):
        decision = evaluate_l7(L7Inputs())
        self.assertEqual(decision.result, "NO_GO")
        self.assertFalse(decision.l7_go)
        self.assertEqual(len(decision.reasons), 7)

    def test_go_requires_every_element(self):
        full = dict(
            l4_pass=True,
            integrity_pass=True,
            rollback_pass=True,
            smoke_pass=True,
            uat_pass=True,
            manifest_complete=True,
            human_approval=True,
            approved_by="DIRECCION",
            approval_timestamp="2026-09-29T12:00:00-03:00",
        )
        decision = evaluate_l7(L7Inputs(**full))
        self.assertEqual(decision.result, "GO")

        for missing_field in (
            "l4_pass",
            "integrity_pass",
            "rollback_pass",
            "smoke_pass",
            "uat_pass",
            "manifest_complete",
            "human_approval",
        ):
            degraded = dict(full)
            degraded[missing_field] = False
            decision = evaluate_l7(L7Inputs(**degraded))
            self.assertEqual(decision.result, "NO_GO", msg=f"{missing_field} debería bloquear L7")

    def test_human_approval_without_identity_is_rejected(self):
        decision = evaluate_l7(
            L7Inputs(
                l4_pass=True,
                integrity_pass=True,
                rollback_pass=True,
                smoke_pass=True,
                uat_pass=True,
                manifest_complete=True,
                human_approval=True,
                approved_by="",
                approval_timestamp="",
            )
        )
        self.assertEqual(decision.result, "NO_GO")
        self.assertTrue(any("approved_by" in r for r in decision.reasons))


if __name__ == "__main__":
    unittest.main()
