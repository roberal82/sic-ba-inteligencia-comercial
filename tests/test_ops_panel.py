import unittest

from src.ops_panel import build_panel, render_text


def _row(rows, label):
    return next(r for r in rows if r.label == label)


class OpsPanelTests(unittest.TestCase):
    def test_default_config_is_fully_blocked_and_writer_absent(self):
        rows = build_panel({})
        self.assertEqual(_row(rows, "L4").value, "FAIL_CLOSED")
        self.assertEqual(_row(rows, "L7").value, "NO_GO")
        self.assertEqual(_row(rows, "WRITER").value, "NOT_PRESENT")
        self.assertEqual(_row(rows, "PRODUCTION").value, "LOCKED")
        self.assertEqual(_row(rows, "ADMIN 2026").value, "ACTIVE")

    def test_writer_present_but_disabled_when_module_declared_without_adapter(self):
        config = {
            "release_candidate": {
                "full_regression_pass": True,
                "orchestration_ci_pass": True,
                "drift_gate_pass": True,
                "staging_ci_pass": True,
                "rollback_test_pass": True,
                "no_private_data": True,
                "writer_module_present": True,
            }
        }
        rows = build_panel(config)
        self.assertEqual(_row(rows, "TECHNICAL").value, "READY")
        self.assertEqual(_row(rows, "WRITER").value, "READY / DISABLED")
        self.assertEqual(_row(rows, "ROLLBACK").value, "READY")
        self.assertEqual(_row(rows, "PRODUCTION").value, "LOCKED")

    def test_render_text_includes_every_row_label(self):
        rows = build_panel({})
        text = render_text(rows)
        for label in ("TECHNICAL", "L4", "L7", "WRITER", "ROLLBACK", "CUTOVER", "PRODUCTION", "ADMIN 2026"):
            self.assertIn(label, text)


if __name__ == "__main__":
    unittest.main()
