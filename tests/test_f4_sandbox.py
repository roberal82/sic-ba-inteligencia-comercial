import json
import tempfile
import unittest
from pathlib import Path

from src.orchestration.sandbox import (
    SandboxManifestConflict,
    SandboxRunStore,
    validate_run_id,
)


class F4SandboxTests(unittest.TestCase):
    def test_same_run_and_manifest_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SandboxRunStore(Path(tmp) / "sandbox")
            manifest = {"run_id": "RUN-001", "inputs": {"sales_ready": True}}

            first_dir, first_created = store.begin("RUN-001", manifest)
            second_dir, second_created = store.begin("RUN-001", manifest)

            self.assertTrue(first_created)
            self.assertFalse(second_created)
            self.assertEqual(first_dir, second_dir)
            self.assertEqual(len(list((Path(tmp) / "sandbox").iterdir())), 1)

    def test_same_run_with_different_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SandboxRunStore(Path(tmp) / "sandbox")
            store.begin("RUN-002", {"inputs": {"sales_ready": True}})

            with self.assertRaises(SandboxManifestConflict):
                store.begin("RUN-002", {"inputs": {"sales_ready": False}})

    def test_result_write_and_rollback_are_scoped_to_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "sandbox"
            store = SandboxRunStore(root)
            manifest = {"inputs": {}}

            run_a, _ = store.begin("RUN-A", manifest)
            run_b, _ = store.begin("RUN-B", manifest)
            result_path = store.write_result("RUN-A", {"overall": "PASS"})
            store.mark_completed("RUN-A", "PASS")

            self.assertTrue(result_path.exists())
            meta = json.loads((run_a / "run_meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["status"], "COMPLETED")
            self.assertTrue(store.rollback("RUN-A"))
            self.assertFalse(run_a.exists())
            self.assertTrue(run_b.exists())
            self.assertFalse(store.rollback("RUN-A"))

    def test_run_id_cannot_escape_sandbox(self):
        for run_id in ["../escape", "a/b", "", " space"]:
            with self.subTest(run_id=run_id):
                with self.assertRaises(ValueError):
                    validate_run_id(run_id)


if __name__ == "__main__":
    unittest.main()
