"""Pruebas adversariales sintéticas para ERP_DIFF_ENGINE (Sprint 001).

Estos casos ejercitan ambigüedades y fronteras de seguridad que no estaban
cubiertas por la suite funcional original. Todos los nombres y valores son
inventados; no se utilizan datos ni identificadores de Blanco & Asociados.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import openpyxl

from tests import erp_diff_fixtures as fx

from src.erp_diff_engine.classify import classify_difference
from src.erp_diff_engine.cli import main as cli_main
from src.erp_diff_engine.engine import run
from src.erp_diff_engine.models import Classification, Difference, DiffKind, EngineConfig
from src.erp_diff_engine.normalize import normalize_for_compare, raw_type_label
from src.erp_diff_engine.security import EngineInputError, EngineSecurityError


REPORT_NAMES = (
    "diff_summary.json",
    "diff_structure.json",
    "diff_rows.csv",
    "diff_formulas.csv",
    "risk_report.md",
)


class AdversarialEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.base_path = self.root / "BASE.xlsx"
        self.current_path = self.root / "CURRENT.xlsx"
        self.output_dir = self.root / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_and_run(self, base: dict, current: dict, **kwargs):
        fx.write_openpyxl_workbook(self.base_path, base)
        fx.write_openpyxl_workbook(self.current_path, current)
        return run(
            EngineConfig(
                base_path=self.base_path,
                current_path=self.current_path,
                output_dir=self.output_dir,
                **kwargs,
            )
        )

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    def test_column_inserted_in_middle_is_not_misclassified_as_rename(self) -> None:
        base = {"TABLA": {"headers": ["ID", "A", "B"], "rows": [[1, "a", "b"]]}}
        current = {
            "TABLA": {"headers": ["ID", "NUEVA", "A", "B"], "rows": [[1, "n", "a", "b"]]}
        }
        self._write_and_run(base, current, primary_keys={"TABLA": ["ID"]})
        sheet = self._structure()["sheets"]["TABLA"]
        self.assertEqual(sheet["columns_added"], ["NUEVA"])
        self.assertEqual(sheet["headers_changed"], [])

    def test_column_removed_in_middle_is_not_misclassified_as_rename(self) -> None:
        base = {"TABLA": {"headers": ["ID", "VIEJA", "A", "B"], "rows": [[1, "v", "a", "b"]]}}
        current = {"TABLA": {"headers": ["ID", "A", "B"], "rows": [[1, "a", "b"]]}}
        self._write_and_run(base, current, primary_keys={"TABLA": ["ID"]})
        sheet = self._structure()["sheets"]["TABLA"]
        self.assertEqual(sheet["columns_removed"], ["VIEJA"])
        self.assertEqual(sheet["headers_changed"], [])

    def test_true_one_to_one_column_rename_is_reported_as_header_change(self) -> None:
        base = {"TABLA": {"headers": ["ID", "ANTES"], "rows": [[1, 7]]}}
        current = {"TABLA": {"headers": ["ID", "DESPUES"], "rows": [[1, 7]]}}
        self._write_and_run(base, current, primary_keys={"TABLA": ["ID"]})
        sheet = self._structure()["sheets"]["TABLA"]
        self.assertEqual(len(sheet["headers_changed"]), 1)
        self.assertEqual(sheet["columns_added"], [])
        self.assertEqual(sheet["columns_removed"], [])

    def test_duplicate_column_names_are_explicit_critical_findings(self) -> None:
        sheets = {"TABLA": {"headers": ["ID", "Monto", "Monto"], "rows": [[1, 10, 20]]}}
        self._write_and_run(sheets, sheets, primary_keys={"TABLA": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("DUPLICATE_HEADER"), 2)
        self.assertGreaterEqual(summary["counts_by_classification"]["CRITICAL"], 2)

    def test_empty_column_names_are_explicit_findings(self) -> None:
        sheets = {"TABLA": {"headers": ["ID", None, "Valor"], "rows": [[1, "x", 3]]}}
        self._write_and_run(sheets, sheets, primary_keys={"TABLA": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("EMPTY_HEADER"), 2)

    def test_reordered_rows_without_pk_are_marked_as_heuristic_not_documentary(self) -> None:
        base = {"TABLA": {"headers": ["Nombre", "Valor"], "rows": [["uno", 1], ["dos", 2]]}}
        current = {"TABLA": {"headers": ["Nombre", "Valor"], "rows": [["dos", 2], ["uno", 1]]}}
        self._write_and_run(base, current)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_MATCH_AMBIGUOUS"), 1)
        self.assertEqual(
            self._structure()["sheets"]["TABLA"]["row_matching_evidence"],
            "INSUFFICIENT_EVIDENCE",
        )

    def test_similar_inserted_rows_without_pk_are_marked_ambiguous(self) -> None:
        base = {
            "TABLA": {
                "headers": ["Concepto", "Monto"],
                "rows": [["Cuota", 100], ["Cuota", 101], ["Cuota", 102]],
            }
        }
        current = {
            "TABLA": {
                "headers": ["Concepto", "Monto"],
                "rows": [["Cuota", 100], ["Cuota", 100.5], ["Cuota", 101], ["Cuota", 102]],
            }
        }
        self._write_and_run(base, current)
        self.assertEqual(self._summary()["counts_by_kind"].get("ROW_MATCH_AMBIGUOUS"), 1)

    def test_reordered_rows_with_pk_produce_no_drift(self) -> None:
        base = {"TABLA": {"headers": ["ID", "Valor"], "rows": [["a", 1], ["b", 2]]}}
        current = {"TABLA": {"headers": ["ID", "Valor"], "rows": [["b", 2], ["a", 1]]}}
        result = self._write_and_run(base, current, primary_keys={"TABLA": ["ID"]})
        self.assertEqual(result.total_differences, 0)

    def test_missing_configured_pk_fails_closed(self) -> None:
        sheets = {"TABLA": {"headers": ["ID", "Valor"], "rows": [[1, 2]]}}
        fx.write_openpyxl_workbook(self.base_path, sheets)
        fx.write_openpyxl_workbook(self.current_path, sheets)
        with self.assertRaisesRegex(EngineInputError, "NO_EXISTE"):
            run(
                EngineConfig(
                    base_path=self.base_path,
                    current_path=self.current_path,
                    output_dir=self.output_dir,
                    primary_keys={"TABLA": ["NO_EXISTE"]},
                )
            )
        self.assertFalse((self.output_dir / "diff_summary.json").exists())

    def test_formula_change_without_cached_values_never_claims_same_value(self) -> None:
        fx.write_openpyxl_workbook(
            self.base_path,
            {"TABLA": {"headers": ["ID", "Total"], "rows": [[1, "=1+1"]]}},
        )
        fx.write_openpyxl_workbook(
            self.current_path,
            {"TABLA": {"headers": ["ID", "Total"], "rows": [[1, "=2+2"]]}},
        )
        run(
            EngineConfig(
                base_path=self.base_path,
                current_path=self.current_path,
                output_dir=self.output_dir,
                primary_keys={"TABLA": ["ID"]},
            )
        )
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("FORMULA_CHANGED_NO_CACHED_VALUE"), 1)
        self.assertNotIn("FORMULA_CHANGED_SAME_VALUE", summary["counts_by_kind"])
        formulas = (self.output_dir / "diff_formulas.csv").read_text(encoding="utf-8")
        self.assertIn("CACHE_MISSING", formulas)
        self.assertNotIn("El valor calculado no cambió", formulas)

    def test_formula_report_distinguishes_formula_cached_value_and_cache_status(self) -> None:
        fx.write_formula_workbook(
            self.base_path, "TABLA", ["ID", "Total"], [[1, ("=1+1", 2)]]
        )
        fx.write_formula_workbook(
            self.current_path, "TABLA", ["ID", "Total"], [[1, ("=2", 2)]]
        )
        run(
            EngineConfig(
                base_path=self.base_path,
                current_path=self.current_path,
                output_dir=self.output_dir,
                primary_keys={"TABLA": ["ID"]},
            )
        )
        rows = list(
            csv.DictReader(io.StringIO((self.output_dir / "diff_formulas.csv").read_text(encoding="utf-8")))
        )
        changed = next(row for row in rows if row["kind"] == "FORMULA_CHANGED_SAME_VALUE")
        self.assertEqual(changed["base_formula"], "=1+1")
        self.assertEqual(changed["current_formula"], "=2")
        self.assertEqual(changed["base_cached_value"], "2")
        self.assertEqual(changed["current_cached_value"], "2")
        self.assertEqual(changed["base_cache_status"], "PRESENT")
        self.assertEqual(changed["current_cache_status"], "PRESENT")

    def test_excel_serial_with_date_format_equals_dd_mm_yyyy(self) -> None:
        for path, value in ((self.base_path, 45366), (self.current_path, "15/03/2024")):
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            sheet.title = "TABLA"
            sheet.append(["ID", "Fecha"])
            sheet.append([1, value])
            if path == self.base_path:
                sheet["B2"].number_format = "dd/mm/yyyy"
            workbook.save(path)
        run(
            EngineConfig(
                base_path=self.base_path,
                current_path=self.current_path,
                output_dir=self.output_dir,
                primary_keys={"TABLA": ["ID"]},
            )
        )
        summary = self._summary()
        self.assertNotIn("VALUE_MODIFIED", summary["counts_by_kind"])

    def test_int_and_float_normalize_equally_when_source_type_is_available(self) -> None:
        self.assertEqual(normalize_for_compare(7), normalize_for_compare(7.0))
        self.assertNotEqual(raw_type_label(7), raw_type_label(7.0))

    def test_none_and_empty_string_normalize_equally(self) -> None:
        self.assertEqual(normalize_for_compare(None), normalize_for_compare(""))
        self.assertEqual(normalize_for_compare(None), normalize_for_compare("   "))

    def test_unicode_and_accents_round_trip_in_reports(self) -> None:
        base = {"Ñandú": {"headers": ["ID", "Descripción"], "rows": [[1, "acción"]]}}
        current = {"Ñandú": {"headers": ["ID", "Descripción"], "rows": [[1, "canción"]]}}
        self._write_and_run(base, current, primary_keys={"Ñandú": ["ID"]})
        rows = (self.output_dir / "diff_rows.csv").read_text(encoding="utf-8")
        self.assertIn("Ñandú", rows)
        self.assertIn("acción", rows)
        self.assertIn("canción", rows)

    def test_corrupt_workbook_raises_controlled_input_error(self) -> None:
        self.base_path.write_bytes(b"PK\x03\x04contenido-corrupto")
        fx.write_openpyxl_workbook(
            self.current_path, {"TABLA": {"headers": ["ID"], "rows": [[1]]}}
        )
        with self.assertRaises(EngineInputError):
            run(
                EngineConfig(
                    base_path=self.base_path,
                    current_path=self.current_path,
                    output_dir=self.output_dir,
                )
            )

    def test_cli_valid_run_writes_only_the_five_required_reports(self) -> None:
        sheets = {"TABLA": {"headers": ["ID"], "rows": [[1]]}}
        fx.write_openpyxl_workbook(self.base_path, sheets)
        fx.write_openpyxl_workbook(self.current_path, sheets)
        exit_code = cli_main(
            [
                "--base",
                str(self.base_path),
                "--current",
                str(self.current_path),
                "--output",
                str(self.output_dir),
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertEqual(
            {path.name for path in self.output_dir.iterdir()}, set(REPORT_NAMES)
        )

    def test_log_path_traversal_cannot_write_outside_output(self) -> None:
        sheets = {"TABLA": {"headers": ["ID"], "rows": [[1]]}}
        fx.write_openpyxl_workbook(self.base_path, sheets)
        fx.write_openpyxl_workbook(self.current_path, sheets)
        escaped = self.root / "escape.log"
        with self.assertRaises(EngineSecurityError):
            run(
                EngineConfig(
                    base_path=self.base_path,
                    current_path=self.current_path,
                    output_dir=self.output_dir,
                    log_file=Path("..") / "escape.log",
                )
            )
        self.assertFalse(escaped.exists())

    def test_log_file_is_allowed_only_inside_output(self) -> None:
        sheets = {"TABLA": {"headers": ["ID"], "rows": [[1]]}}
        self._write_and_run(sheets, sheets, log_file=Path("logs") / "run.log")
        log_path = self.output_dir / "logs" / "run.log"
        self.assertTrue(log_path.exists())
        first = log_path.read_bytes()
        run(
            EngineConfig(
                base_path=self.base_path,
                current_path=self.current_path,
                output_dir=self.output_dir,
                log_file=Path("logs") / "run.log",
            )
        )
        self.assertEqual(log_path.read_bytes(), first)

    def test_existing_outputs_are_atomically_replaced(self) -> None:
        self.output_dir.mkdir()
        for name in REPORT_NAMES:
            (self.output_dir / name).write_text("contenido obsoleto", encoding="utf-8")
        sheets = {"TABLA": {"headers": ["ID"], "rows": [[1]]}}
        self._write_and_run(sheets, sheets, primary_keys={"TABLA": ["ID"]})
        for name in REPORT_NAMES:
            self.assertNotEqual((self.output_dir / name).read_text(encoding="utf-8"), "contenido obsoleto")
        self.assertFalse(list(self.output_dir.glob("*.tmp")))

    def test_input_files_are_not_modified_and_hashes_are_reported(self) -> None:
        base = {"TABLA": {"headers": ["ID", "Valor"], "rows": [[1, "base"]]}}
        current = {"TABLA": {"headers": ["ID", "Valor"], "rows": [[1, "actual"]]}}
        fx.write_openpyxl_workbook(self.base_path, base)
        fx.write_openpyxl_workbook(self.current_path, current)
        before = {path: path.read_bytes() for path in (self.base_path, self.current_path)}
        run(
            EngineConfig(
                base_path=self.base_path,
                current_path=self.current_path,
                output_dir=self.output_dir,
                primary_keys={"TABLA": ["ID"]},
            )
        )
        summary = self._summary()
        self.assertEqual(summary["base_sha256"], hashlib.sha256(before[self.base_path]).hexdigest())
        self.assertEqual(
            summary["current_sha256"], hashlib.sha256(before[self.current_path]).hexdigest()
        )
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_outputs_are_reproducible_across_hash_seeds(self) -> None:
        base = {"TABLA": {"headers": ["ID", "Valor"], "rows": [["z", 1], ["a", 2], ["m", 3]]}}
        current = {"TABLA": {"headers": ["ID", "Valor"], "rows": [["x", 4], ["b", 5], ["n", 6]]}}
        fx.write_openpyxl_workbook(self.base_path, base)
        fx.write_openpyxl_workbook(self.current_path, current)
        script = (
            "from pathlib import Path; "
            "from src.erp_diff_engine.engine import run; "
            "from src.erp_diff_engine.models import EngineConfig; "
            "run(EngineConfig(base_path=Path(r'%s'), current_path=Path(r'%s'), "
            "output_dir=Path(r'%%s'), primary_keys={'TABLA':['ID']}))"
            % (self.base_path, self.current_path)
        )
        snapshots = []
        for seed in ("1", "777"):
            output = self.root / f"seed-{seed}"
            env = dict(os.environ, PYTHONHASHSEED=seed)
            subprocess.run(
                [sys.executable, "-c", script % output],
                cwd=Path(__file__).resolve().parents[1],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            snapshots.append({name: (output / name).read_bytes() for name in REPORT_NAMES})
        self.assertEqual(snapshots[0], snapshots[1])

    def test_totals_are_never_inferred_without_configuration(self) -> None:
        base = {"TABLA": {"headers": ["ID", "Monto"], "rows": [[1, 100]]}}
        current = {"TABLA": {"headers": ["ID", "Monto"], "rows": [[1, 900]]}}
        self._write_and_run(base, current, primary_keys={"TABLA": ["ID"]})
        summary = self._summary()
        self.assertNotIn("CONTROL_TOTAL_MISMATCH", summary["counts_by_kind"])
        self.assertEqual(self._structure()["sheets"]["TABLA"]["control_totals"], {})

    def test_configured_missing_total_column_is_not_silently_ignored(self) -> None:
        sheets = {"TABLA": {"headers": ["ID", "Monto"], "rows": [[1, 100]]}}
        self._write_and_run(
            sheets,
            sheets,
            primary_keys={"TABLA": ["ID"]},
            control_totals={"TABLA": ["NO_EXISTE"]},
        )
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("CONTROL_TOTAL_COLUMN_MISSING"), 1)

    def test_configured_total_with_non_numeric_values_is_not_false_match(self) -> None:
        base = {"TABLA": {"headers": ["ID", "Monto"], "rows": [[1, "texto-a"]]}}
        current = {"TABLA": {"headers": ["ID", "Monto"], "rows": [[1, "texto-b"]]}}
        self._write_and_run(
            base,
            current,
            primary_keys={"TABLA": ["ID"]},
            control_totals={"TABLA": ["Monto"]},
        )
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("CONTROL_TOTAL_INVALID_VALUE"), 1)
        totals = self._structure()["sheets"]["TABLA"]["control_totals"]["Monto"]
        self.assertEqual(totals["status"], "INVALID_VALUES")

    def test_severity_override_cannot_create_expected_without_expected_rule(self) -> None:
        diff = Difference(kind=DiffKind.ROW_ADDED, sheet="TABLA", location="sintético")
        config = EngineConfig(
            base_path=self.base_path,
            current_path=self.current_path,
            output_dir=self.output_dir,
            severity_overrides={DiffKind.ROW_ADDED: Classification.EXPECTED},
        )
        with self.assertRaises(EngineInputError):
            classify_difference(diff, config)


if __name__ == "__main__":
    unittest.main()
