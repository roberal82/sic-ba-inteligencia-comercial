import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.orchestration.models import Mode
from src.orchestration.operational import (
    OperationalRunError,
    rollback_operational_run,
    run_operational_stage,
)


def write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + "\n" + "\n".join(rows) + "\n", encoding="utf-8")


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_manifest(run_id: str = "S2-TEST") -> dict:
    return {
        "run_id": run_id,
        "sources": {
            "sales": {
                "path": "sales.csv",
                "required_columns": ["ID", "CLIENTE"],
                "key_fields": ["ID"],
                "sets_input": "sales_ready",
            }
        },
        "inputs": {
            "purchases_ready": False,
            "pipeline_ready": False,
            "documents_ready": False,
            "master_resolution_ready": False,
            "relation_candidates_ready": False,
            "cost_evidence_ready": False,
            "bi_ready": False,
        },
        "gates": {
            "l4_pass": False,
            "l7_go": False,
            "rollback_real_proven": False,
            "human_approval": False,
        },
    }


class Sprint002OperationalTests(unittest.TestCase):
    def test_source_is_read_only_and_stage_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "sources"
            stage_root = root / "stage"
            source = source_root / "sales.csv"
            write_csv(source, "ID,CLIENTE", ["1,SECRET-CUSTOMER", "2,CLIENT-B"])
            before = file_sha(source)

            result = run_operational_stage(
                base_manifest(), Mode.DRY_RUN, source_root, stage_root
            )

            self.assertEqual(file_sha(source), before)
            self.assertFalse(result["external_writes"])
            self.assertFalse(result["production_adapter_present"])
            self.assertEqual(result["source_stats"]["sales"]["staged_rows"], 2)
            self.assertTrue((stage_root / "S2-TEST" / "staged" / "sales.jsonl").is_file())

            audit = (stage_root / "S2-TEST" / "audit" / "events.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("SECRET-CUSTOMER", audit)

    def test_quarantine_missing_and_conflicting_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "sources"
            stage_root = root / "stage"
            write_csv(
                source_root / "sales.csv",
                "ID,CLIENTE",
                ["1,A", "1,A", "1,B", ",C", "2,D"],
            )

            result = run_operational_stage(
                base_manifest(), Mode.DRY_RUN, source_root, stage_root
            )
            stats = result["source_stats"]["sales"]
            self.assertEqual(stats["source_rows"], 5)
            self.assertEqual(stats["staged_rows"], 2)
            self.assertEqual(stats["quarantined_rows"], 2)
            self.assertEqual(stats["exact_duplicates"], 1)

            rows = [
                json.loads(line)
                for line in (stage_root / "S2-TEST" / "quarantine" / "sales.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            self.assertEqual(
                {row["reason"] for row in rows},
                {"MISSING_KEY", "DUPLICATE_KEY_CONFLICT"},
            )

    def test_rerun_same_fingerprint_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "sources"
            stage_root = root / "stage"
            write_csv(source_root / "sales.csv", "ID,CLIENTE", ["1,A", "2,B"])
            manifest = base_manifest()

            first = run_operational_stage(manifest, Mode.DRY_RUN, source_root, stage_root)
            staged_path = stage_root / "S2-TEST" / "staged" / "sales.jsonl"
            first_bytes = staged_path.read_bytes()
            second = run_operational_stage(manifest, Mode.DRY_RUN, source_root, stage_root)

            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["execution_fingerprint"], second["execution_fingerprint"])
            self.assertEqual(staged_path.read_bytes(), first_bytes)

    def test_same_run_id_with_changed_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "sources"
            stage_root = root / "stage"
            source = source_root / "sales.csv"
            write_csv(source, "ID,CLIENTE", ["1,A"])
            manifest = base_manifest()
            run_operational_stage(manifest, Mode.DRY_RUN, source_root, stage_root)

            write_csv(source, "ID,CLIENTE", ["1,A", "2,B"])
            with self.assertRaises(OperationalRunError):
                run_operational_stage(manifest, Mode.DRY_RUN, source_root, stage_root)

    def test_source_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "sources"
            source_root.mkdir()
            write_csv(root / "outside.csv", "ID,CLIENTE", ["1,A"])
            manifest = base_manifest()
            manifest["sources"]["sales"]["path"] = "../outside.csv"

            with self.assertRaises(OperationalRunError):
                run_operational_stage(manifest, Mode.DRY_RUN, source_root, root / "stage")

    def test_sensitive_readiness_cannot_be_derived_from_file_presence(self):
        manifest = base_manifest()
        manifest["sources"]["sales"]["sets_input"] = "cost_evidence_ready"
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_csv(root / "sources" / "sales.csv", "ID,CLIENTE", ["1,A"])
            with self.assertRaises(OperationalRunError):
                run_operational_stage(
                    manifest, Mode.DRY_RUN, root / "sources", root / "stage"
                )

    def test_financial_and_cutover_gates_remain_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_csv(root / "sources" / "sales.csv", "ID,CLIENTE", ["1,A"])
            result = run_operational_stage(
                base_manifest(), Mode.STAGE, root / "sources", root / "stage"
            )
            outcomes = {
                row["job_id"]: row["outcome"] for row in result["gate_result"]["results"]
            }
            self.assertEqual(result["overall"], "BLOCKED")
            self.assertEqual(outcomes["J09"], "BLOCKED_L4")
            self.assertEqual(outcomes["J10"], "BLOCKED_L4")

    def test_apply_never_becomes_production_writer(self):
        manifest = {
            "run_id": "S2-APPLY",
            "sources": {},
            "inputs": {
                "sales_ready": True,
                "purchases_ready": True,
                "pipeline_ready": True,
                "documents_ready": True,
                "master_resolution_ready": True,
                "relation_candidates_ready": True,
                "cost_evidence_ready": True,
                "bi_ready": True,
            },
            "gates": {
                "l4_pass": True,
                "l7_go": True,
                "rollback_real_proven": True,
                "human_approval": True,
            },
        }
        with tempfile.TemporaryDirectory() as td, patch.dict(
            os.environ, {"SIC_BA_PRODUCTION_WRITE": "ENABLED"}
        ):
            root = Path(td)
            result = run_operational_stage(
                manifest, Mode.APPLY, root / "sources", root / "stage"
            )
            self.assertTrue(result["gate_result"]["production_ready"])
            self.assertEqual(result["overall"], "BLOCKED_PRODUCTION_ADAPTER_MISSING")
            self.assertFalse(result["external_writes"])
            self.assertFalse(result["production_adapter_present"])

    def test_rollback_removes_only_selected_run(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_root = root / "sources"
            stage_root = root / "stage"
            write_csv(source_root / "sales.csv", "ID,CLIENTE", ["1,A"])
            run_operational_stage(
                base_manifest("S2-A"), Mode.DRY_RUN, source_root, stage_root
            )
            run_operational_stage(
                base_manifest("S2-B"), Mode.DRY_RUN, source_root, stage_root
            )

            self.assertTrue(rollback_operational_run(stage_root, "S2-A"))
            self.assertFalse((stage_root / "S2-A").exists())
            self.assertTrue((stage_root / "S2-B").exists())
            self.assertFalse(rollback_operational_run(stage_root, "S2-A"))


if __name__ == "__main__":
    unittest.main()
