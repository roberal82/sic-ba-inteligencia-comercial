import unittest

from src.cutover.engine import CutoverEngine, CutoverEngineBlockedError, build_context_from_gates
from src.gates.l4_evidence import EvidenceStatus, FinancialGateEvidence, evaluate_l4
from src.gates.l7_decision import L7Inputs, evaluate_l7
from src.writer.models import WriterInterlock


def _l4_pass():
    evidence = FinancialGateEvidence(
        cutoff="2026-09-26T23:59:00-03:00",
        cxc_status=EvidenceStatus.CONFIRMED,
        cxp_status=EvidenceStatus.CONFIRMED,
        checks_status=EvidenceStatus.CONFIRMED,
        bank_status=EvidenceStatus.CONFIRMED,
        nominal_reconciliation_status=EvidenceStatus.CONFIRMED,
        approved_by="FINANZAS",
        approval_timestamp="2026-09-29T10:00:00-03:00",
        evidence_refs=("L4-REF",),
        source_hashes={"cxc.csv": "a" * 64},
    )
    return evaluate_l4(evidence)


def _l7_go():
    return evaluate_l7(
        L7Inputs(
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
    )


class CutoverEngineTests(unittest.TestCase):
    def test_context_reflects_real_gate_objects_not_raw_booleans(self):
        l4_fail = evaluate_l4(FinancialGateEvidence())
        l7_no_go = evaluate_l7(L7Inputs())
        ctx = build_context_from_gates(l4_fail, l7_no_go)
        self.assertFalse(ctx.l4_pass)
        self.assertFalse(ctx.l7_go)

    def test_evaluate_is_pure_and_matches_simulator_semantics(self):
        ctx = build_context_from_gates(
            _l4_pass(),
            _l7_go(),
            snapshot_ready=True,
            cutover_window_authorized=True,
            nonfinancial_ready=True,
            cardinality_validated=True,
            smoke_nonfinancial_pass=True,
            uat_accepted=True,
            rollback_real_proven=True,
            human_approval=True,
        )
        engine = CutoverEngine(ctx)
        result = engine.evaluate()
        # go-live simulado queda habilitado; legacy sigue bloqueado hasta
        # go-live real + convivencia estable, por eso overall sigue NO-GO.
        self.assertTrue(result["go_live_simulated"])
        self.assertEqual(result["overall"], "NO-GO")

    def test_execute_go_live_is_always_blocked_in_this_sprint(self):
        ctx = build_context_from_gates(
            _l4_pass(),
            _l7_go(),
            snapshot_ready=True,
            cutover_window_authorized=True,
            nonfinancial_ready=True,
            cardinality_validated=True,
            smoke_nonfinancial_pass=True,
            uat_accepted=True,
            rollback_real_proven=True,
            human_approval=True,
        )
        full_interlock = WriterInterlock(
            l4_pass=True,
            l7_go=True,
            rollback_real_proven=True,
            human_approval=True,
            cutover_window_authorized=True,
            snapshot_ready=True,
            production_write_env="ENABLED",
        )
        engine = CutoverEngine(ctx, writer_interlock=full_interlock)
        with self.assertRaises(CutoverEngineBlockedError) as ctxmgr:
            engine.execute_go_live()
        self.assertIn("adaptador productivo real", str(ctxmgr.exception))

    def test_execute_go_live_reports_all_blocking_reasons_when_nothing_ready(self):
        ctx = build_context_from_gates(evaluate_l4(FinancialGateEvidence()), evaluate_l7(L7Inputs()))
        engine = CutoverEngine(ctx)
        with self.assertRaises(CutoverEngineBlockedError) as ctxmgr:
            engine.execute_go_live()
        message = str(ctxmgr.exception)
        self.assertIn("NO-GO", message)
        self.assertIn("L4 no está en PASS", message)


if __name__ == "__main__":
    unittest.main()
