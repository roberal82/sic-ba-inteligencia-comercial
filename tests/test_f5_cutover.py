import unittest

from src.cutover.models import CutoverContext, StepOutcome
from src.cutover.simulator import simulate_cutover


def step(result: dict, number: int) -> dict:
    return next(row for row in result["steps"] if row["step"] == number)


def ready_context(**overrides) -> CutoverContext:
    values = {
        "snapshot_ready": True,
        "cutover_window_authorized": True,
        "nonfinancial_ready": True,
        "cardinality_validated": True,
        "l4_pass": True,
        "smoke_nonfinancial_pass": True,
        "uat_accepted": True,
        "l7_go": True,
        "rollback_real_proven": True,
        "human_approval": True,
        "go_live_executed": False,
        "coexistence_stable": False,
    }
    values.update(overrides)
    return CutoverContext(**values)


class F5CutoverTests(unittest.TestCase):
    def test_current_state_blocks_finance_and_legacy_archive(self):
        ctx = CutoverContext(
            nonfinancial_ready=True,
            cardinality_validated=True,
            smoke_nonfinancial_pass=True,
            l4_pass=False,
            l7_go=False,
        )
        result = simulate_cutover(ctx)
        self.assertEqual(result["overall"], "NO-GO")
        self.assertEqual(step(result, 5)["outcome"], StepOutcome.BLOCKED_L4.value)
        self.assertEqual(step(result, 6)["outcome"], StepOutcome.PASS_PARTIAL.value)
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.BLOCKED_PRECONDITION.value)
        self.assertEqual(step(result, 10)["outcome"], StepOutcome.BLOCKED_LEGACY.value)
        self.assertFalse(result["go_live_simulated"])
        self.assertFalse(result["legacy_archive_simulated"])

    def test_snapshot_is_mandatory_before_other_go_live_gates(self):
        result = simulate_cutover(ready_context(snapshot_ready=False, l4_pass=False))
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.BLOCKED_PRECONDITION.value)

    def test_l4_blocks_after_operational_preconditions(self):
        result = simulate_cutover(ready_context(l4_pass=False, l7_go=False))
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.BLOCKED_L4.value)

    def test_l4_pass_is_not_enough_without_l7(self):
        result = simulate_cutover(ready_context(l7_go=False))
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.BLOCKED_L7.value)

    def test_l4_and_l7_are_not_enough_without_real_rollback(self):
        result = simulate_cutover(ready_context(rollback_real_proven=False))
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.BLOCKED_ROLLBACK.value)

    def test_approval_is_required_after_l4_l7_and_rollback(self):
        result = simulate_cutover(ready_context(uat_accepted=False, human_approval=False))
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.BLOCKED_APPROVAL.value)

    def test_all_pre_go_live_gates_can_reach_simulated_go_but_not_archive_without_real_execution(self):
        result = simulate_cutover(ready_context())
        self.assertEqual(step(result, 8)["outcome"], StepOutcome.PASS.value)
        self.assertTrue(result["go_live_simulated"])
        self.assertEqual(step(result, 10)["outcome"], StepOutcome.BLOCKED_LEGACY.value)
        self.assertFalse(result["legacy_archive_simulated"])

    def test_legacy_archive_requires_real_go_live_and_stability(self):
        result = simulate_cutover(
            ready_context(go_live_executed=True, coexistence_stable=True)
        )
        self.assertEqual(step(result, 10)["outcome"], StepOutcome.PASS.value)
        self.assertTrue(result["legacy_archive_simulated"])


if __name__ == "__main__":
    unittest.main()
