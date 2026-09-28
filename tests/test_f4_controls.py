import unittest

from f4.config import Gates, Mode
from f4.contracts import JobContext, JobResult
from f4.jobs import JOB_SPECS, validate_catalog
from f4.runner import GateError, simulate_job


class F4ControlTests(unittest.TestCase):
    def setUp(self):
        self.ctx = JobContext(
            run_id="TEST-F4-001",
            mode=Mode.DRY_RUN.value,
            source_id="TEST_SOURCE",
            target="STAGING",
            cutoff="2026-09-26T23:59:00-03:00",
            actor="unittest",
            ruleset_version="F4-test",
        )

    def test_catalog_has_j01_to_j10(self):
        validate_catalog()
        self.assertEqual([j.job_id for j in JOB_SPECS], [f"J{i:02d}" for i in range(1, 11)])

    def test_apply_is_blocked_by_default(self):
        ctx = JobContext(**{**self.ctx.__dict__, "mode": Mode.APPLY.value})
        with self.assertRaises(GateError):
            simulate_job("J01", ctx, Gates())

    def test_j09_blocks_without_l4(self):
        result = simulate_job("J09", self.ctx, Gates())
        self.assertEqual(result.status, "BLOCKED_EXPECTED_L4")

    def test_j10_blocks_without_l4_l7(self):
        result = simulate_job("J10", self.ctx, Gates())
        self.assertTrue(result.status.startswith("BLOCKED_EXPECTED"))

    def test_j07_never_infers_cost(self):
        result = simulate_job("J07", self.ctx, Gates())
        self.assertEqual(result.status, "NO_ASIGNABLE")

    def test_balanced_contract(self):
        result = JobResult(
            job_id="J01",
            status="PASS",
            input_count=10,
            output_count=8,
            quarantined_count=1,
            rejected_count=1,
        )
        self.assertTrue(result.balanced)


if __name__ == "__main__":
    unittest.main()
