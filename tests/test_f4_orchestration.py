import unittest

from src.orchestration.jobs import JOBS, evaluate_job
from src.orchestration.models import ExecutionContext, Mode, Outcome
from src.orchestration.runner import run_manifest


def job(job_id: str):
    return next(spec for spec in JOBS if spec.job_id == job_id)


class F4GuardrailTests(unittest.TestCase):
    def test_cost_job_blocks_without_item_or_oc_evidence(self):
        ctx = ExecutionContext(mode=Mode.DRY_RUN)
        result = evaluate_job(job("J07"), ctx, {"cost_evidence_ready": False})
        self.assertEqual(result.outcome, Outcome.BLOCKED_INPUT)
        self.assertIn("NO_ASIGNABLE", result.detail)

    def test_cost_job_accepts_partial_evidence_without_total_margin(self):
        ctx = ExecutionContext(mode=Mode.DRY_RUN)
        result = evaluate_job(
            job("J07"),
            ctx,
            {"cost_evidence_ready": False, "cost_evidence_partial": True},
        )
        self.assertEqual(result.outcome, Outcome.PASS_WITH_EXCEPTIONS)
        self.assertIn("evidencia parcial", result.detail.lower())
        self.assertIn("NO_ASIGNABLE", result.detail)
        self.assertIn("no se publica margen total", result.detail.lower())

    def test_cost_job_passes_only_when_complete_scope_is_documented(self):
        ctx = ExecutionContext(mode=Mode.DRY_RUN)
        result = evaluate_job(
            job("J07"),
            ctx,
            {"cost_evidence_ready": True, "cost_evidence_partial": True},
        )
        self.assertEqual(result.outcome, Outcome.PASS)

    def test_financial_precheck_blocks_without_l4(self):
        ctx = ExecutionContext(mode=Mode.DRY_RUN, l4_pass=False)
        result = evaluate_job(job("J09"), ctx, {})
        self.assertEqual(result.outcome, Outcome.BLOCKED_L4)

    def test_cutover_blocks_on_l4_before_l7(self):
        ctx = ExecutionContext(mode=Mode.DRY_RUN, l4_pass=False, l7_go=False)
        result = evaluate_job(job("J10"), ctx, {})
        self.assertEqual(result.outcome, Outcome.BLOCKED_L4)

    def test_cutover_blocks_without_l7(self):
        ctx = ExecutionContext(mode=Mode.DRY_RUN, l4_pass=True, l7_go=False)
        result = evaluate_job(job("J10"), ctx, {})
        self.assertEqual(result.outcome, Outcome.BLOCKED_L7)

    def test_apply_requires_explicit_production_interlock(self):
        ctx = ExecutionContext(
            mode=Mode.APPLY,
            l4_pass=True,
            l7_go=True,
            rollback_real_proven=True,
            human_approval=True,
            production_write_enabled=False,
        )
        result = evaluate_job(job("J10"), ctx, {})
        self.assertEqual(result.outcome, Outcome.BLOCKED_PROD_INTERLOCK)

    def test_dry_run_accepts_expected_blocks(self):
        manifest = {
            "run_id": "TEST-DRYRUN",
            "inputs": {
                "sales_ready": True,
                "purchases_ready": True,
                "purchases_incomplete_period": True,
                "pipeline_ready": True,
                "pipeline_has_conflicts": True,
                "documents_ready": True,
                "master_resolution_ready": True,
                "relation_candidates_ready": True,
                "cost_evidence_ready": False,
                "cost_evidence_partial": False,
                "bi_ready": True,
            },
            "gates": {
                "l4_pass": False,
                "l7_go": False,
                "rollback_real_proven": False,
                "human_approval": False,
            },
        }
        result = run_manifest(manifest, Mode.DRY_RUN)
        self.assertEqual(result["overall"], "PASS_WITH_EXPECTED_BLOCKS")
        outcomes = {row["job_id"]: row["outcome"] for row in result["results"]}
        self.assertEqual(outcomes["J07"], Outcome.BLOCKED_INPUT.value)
        self.assertEqual(outcomes["J09"], Outcome.BLOCKED_L4.value)
        self.assertEqual(outcomes["J10"], Outcome.BLOCKED_L4.value)

    def test_dry_run_preserves_partial_cost_as_exception(self):
        manifest = {
            "run_id": "TEST-PARTIAL-COST",
            "inputs": {
                "sales_ready": True,
                "purchases_ready": True,
                "pipeline_ready": True,
                "documents_ready": True,
                "master_resolution_ready": True,
                "relation_candidates_ready": True,
                "cost_evidence_ready": False,
                "cost_evidence_partial": True,
                "bi_ready": True,
            },
            "gates": {"l4_pass": False, "l7_go": False},
        }
        result = run_manifest(manifest, Mode.DRY_RUN)
        outcomes = {row["job_id"]: row["outcome"] for row in result["results"]}
        self.assertEqual(outcomes["J07"], Outcome.PASS_WITH_EXCEPTIONS.value)
        self.assertEqual(outcomes["J09"], Outcome.BLOCKED_L4.value)
        self.assertEqual(outcomes["J10"], Outcome.BLOCKED_L4.value)

    def test_stage_does_not_treat_blocks_as_success(self):
        manifest = {
            "inputs": {},
            "gates": {"l4_pass": False, "l7_go": False},
        }
        result = run_manifest(manifest, Mode.STAGE)
        self.assertEqual(result["overall"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
