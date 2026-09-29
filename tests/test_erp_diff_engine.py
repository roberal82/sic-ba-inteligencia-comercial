"""Tests sintéticos obligatorios del ERP_DIFF_ENGINE (Sprint 001, Fase A).

Cada método cubre uno de los escenarios A-T pedidos en el prompt operativo del
Sprint. Todos los datos son inventados; ningún dato de Blanco & Asociados se
usa en fixtures ni en aserciones.
"""

from __future__ import annotations

import datetime
import json
import tempfile
import unittest
from pathlib import Path

from tests import erp_diff_fixtures as fx

from src.erp_diff_engine.cli import main as cli_main
from src.erp_diff_engine.engine import run
from src.erp_diff_engine.models import EngineConfig
from src.erp_diff_engine.security import EngineInputError


class ERPDiffEngineScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, base_sheets: dict, current_sheets: dict, **config_kwargs) -> object:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_openpyxl_workbook(base_path, base_sheets)
        fx.write_openpyxl_workbook(current_path, current_sheets)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            **config_kwargs,
        )
        return run(config)

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    def _rows_csv(self) -> str:
        return (self.output_dir / "diff_rows.csv").read_text(encoding="utf-8")

    def _formulas_csv(self) -> str:
        return (self.output_dir / "diff_formulas.csv").read_text(encoding="utf-8")

    # A. archivos idénticos
    def test_a_identical_files_produce_zero_differences(self) -> None:
        sheets = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 100], [2, 200]]}}
        result = self._run(sheets, sheets, primary_keys={"DATOS": ["ID"]})
        self.assertEqual(result.total_differences, 0)
        for filename in (
            "diff_summary.json",
            "diff_structure.json",
            "diff_rows.csv",
            "diff_formulas.csv",
            "risk_report.md",
        ):
            self.assertTrue((self.output_dir / filename).exists())

    # B. hoja agregada
    def test_b_sheet_added(self) -> None:
        base = {"UNO": {"headers": ["ID"], "rows": [[1]]}}
        current = {
            "UNO": {"headers": ["ID"], "rows": [[1]]},
            "DOS": {"headers": ["ID"], "rows": [[1]]},
        }
        self._run(base, current)
        structure = self._structure()
        self.assertIn("DOS", structure["sheets_added"])
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("SHEET_ADDED"), 1)

    # C. hoja eliminada
    def test_c_sheet_removed(self) -> None:
        base = {
            "UNO": {"headers": ["ID"], "rows": [[1]]},
            "DOS": {"headers": ["ID"], "rows": [[1]]},
        }
        current = {"UNO": {"headers": ["ID"], "rows": [[1]]}}
        self._run(base, current)
        structure = self._structure()
        self.assertIn("DOS", structure["sheets_removed"])
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("SHEET_REMOVED"), 1)
        self.assertEqual(summary["counts_by_classification"]["CRITICAL"], 1)

    def test_sheet_order_changed(self) -> None:
        base = {
            "UNO": {"headers": ["ID"], "rows": [[1]]},
            "DOS": {"headers": ["ID"], "rows": [[1]]},
        }
        current = {
            "DOS": {"headers": ["ID"], "rows": [[1]]},
            "UNO": {"headers": ["ID"], "rows": [[1]]},
        }
        self._run(base, current)
        structure = self._structure()
        self.assertTrue(structure["sheet_order_changed"])

    # D. fila agregada
    def test_d_row_added_keyed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["rows_added"], 1)

    # E. fila eliminada
    def test_e_row_removed_keyed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["rows_removed"], 1)

    # F. fila modificada
    def test_f_row_modified_keyed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 99]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["rows_modified"], 1)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("VALUE_MODIFIED"), 1)

    # G / H / (#11): fórmula modificada, misma fórmula sin cambio, y fórmula
    # distinta con mismo valor calculado.
    def test_g_h_formula_scenarios(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_formula_workbook(
            base_path,
            "DATOS",
            ["ID", "Total"],
            rows=[
                [1, ("=1+1", 2)],  # cambia la fórmula, el valor calculado se mantiene
                [2, ("=2+2", 4)],  # cambia fórmula y valor calculado
                [3, ("=3+3", 6)],  # sin cambios (H)
            ],
        )
        fx.write_formula_workbook(
            current_path,
            "DATOS",
            ["ID", "Total"],
            rows=[
                [1, ("=2", 2)],
                [2, ("=5+5", 10)],
                [3, ("=3+3", 6)],
            ],
        )
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"DATOS": ["ID"]},
        )
        run(config)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("FORMULA_CHANGED_SAME_VALUE"), 1)
        self.assertEqual(summary["counts_by_kind"].get("FORMULA_CHANGED"), 1)
        self.assertEqual(
            summary["counts_by_classification"]["REQUIRES_HUMAN_REVIEW"], 1
        )  # fila 1
        formulas_csv = self._formulas_csv()
        self.assertIn("FORMULA_CHANGED_SAME_VALUE", formulas_csv)
        self.assertIn("FORMULA_CHANGED", formulas_csv)

    # I. columna agregada
    def test_i_column_added(self) -> None:
        base = {"DATOS": {"headers": ["ID"], "rows": [[1]]}}
        current = {"DATOS": {"headers": ["ID", "Nueva"], "rows": [[1, "x"]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertIn("Nueva", structure["sheets"]["DATOS"]["columns_added"])

    # J. columna eliminada
    def test_j_column_removed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Vieja"], "rows": [[1, "x"]]}}
        current = {"DATOS": {"headers": ["ID"], "rows": [[1]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertIn("Vieja", structure["sheets"]["DATOS"]["columns_removed"])

    # K. duplicados (clave primaria duplicada en ambos archivos)
    def test_k_duplicate_primary_key(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [1, 10]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("DUPLICATE_KEY"), 2)  # BASE + CURRENT
        self.assertGreaterEqual(summary["counts_by_classification"]["CRITICAL"], 2)

    def test_k_duplicate_rows_without_primary_key(self) -> None:
        base = {"DATOS": {"headers": ["Valor"], "rows": [[10], [10]]}}
        current = {"DATOS": {"headers": ["Valor"], "rows": [[10], [10]]}}
        self._run(base, current)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("DUPLICATE_KEY"), 2)

    # L. valores nulos
    def test_l_null_values_tracked(self) -> None:
        sheets = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, None], [2, 5]]}}
        self._run(sheets, sheets, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["nulls_base"].get("Valor"), 1)
        self.assertEqual(structure["sheets"]["DATOS"]["nulls_current"].get("Valor"), 1)

    def test_l_null_in_primary_key_is_critical(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[None, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[None, 10]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("NULL_IN_KEY"), 2)

    # M. fechas dd/mm/yyyy vs objeto fecha
    def test_m_date_text_equals_date_object(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Fecha"], "rows": [[1, datetime.date(2024, 3, 15)]]}}
        current = {"DATOS": {"headers": ["ID", "Fecha"], "rows": [[1, "15/03/2024"]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("TYPE_CHANGED"), 1)
        self.assertNotIn("VALUE_MODIFIED", summary["counts_by_kind"])

    def test_m_date_value_actually_changed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Fecha"], "rows": [[1, "15/03/2024"]]}}
        current = {"DATOS": {"headers": ["ID", "Fecha"], "rows": [[1, "16/03/2024"]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("VALUE_MODIFIED"), 1)

    # N. importes PYG (texto con separador de miles vs número)
    def test_n_pyg_amount_text_equals_number(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, 1234567]]}}
        current = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, "1.234.567"]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("TYPE_CHANGED"), 1)
        self.assertNotIn("VALUE_MODIFIED", summary["counts_by_kind"])

    def test_n_pyg_amount_actually_changed(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, "1.234.567"]]}}
        current = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, "1.235.000"]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("VALUE_MODIFIED"), 1)

    # O. workbook vacío
    def test_o_empty_workbook(self) -> None:
        sheets = {"HOJA": {"headers": [], "rows": []}}
        result = self._run(sheets, sheets)
        self.assertEqual(result.total_differences, 0)

    # P. hoja vacía (con encabezados, cero filas de datos)
    def test_p_sheet_with_headers_and_no_data_rows(self) -> None:
        sheets = {"HOJA": {"headers": ["ID", "Valor"], "rows": []}}
        result = self._run(sheets, sheets, primary_keys={"HOJA": ["ID"]})
        self.assertEqual(result.total_differences, 0)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["base_row_count"], 0)
        self.assertEqual(structure["sheets"]["HOJA"]["current_row_count"], 0)

    # Q. encabezados incompletos
    def test_q_incomplete_headers(self) -> None:
        base = {"HOJA": {"headers": ["ID", None, "Valor"], "rows": [[1, "x", 10]]}}
        current = {"HOJA": {"headers": ["ID", "Nuevo", "Valor"], "rows": [[1, "x", 10]]}}
        self._run(base, current, primary_keys={"HOJA": ["ID"]})
        summary = self._summary()
        self.assertGreaterEqual(summary["counts_by_kind"].get("HEADER_CHANGED", 0), 1)

    # R. nombre de hoja con caracteres especiales
    def test_r_sheet_name_with_special_characters(self) -> None:
        name = "Ñandú (2024) - Ó"
        sheets = {name: {"headers": ["ID"], "rows": [[1]]}}
        result = self._run(sheets, sheets, primary_keys={name: ["ID"]})
        self.assertEqual(result.total_differences, 0)
        structure = self._structure()
        self.assertIn(name, structure["sheets_base"])

    # S. ejecución repetida / idempotencia
    def test_s_repeated_execution_is_idempotent(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 11], [3, 30]]}}
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_openpyxl_workbook(base_path, base)
        fx.write_openpyxl_workbook(current_path, current)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"DATOS": ["ID"]},
        )
        run(config)
        first = {
            name: (self.output_dir / name).read_bytes()
            for name in (
                "diff_summary.json",
                "diff_structure.json",
                "diff_rows.csv",
                "diff_formulas.csv",
                "risk_report.md",
            )
        }
        run(config)
        for name, content in first.items():
            self.assertEqual((self.output_dir / name).read_bytes(), content, msg=name)

    # T. ruta inválida
    def test_t_invalid_base_path_raises_controlled_error(self) -> None:
        config = EngineConfig(
            base_path=self.base_dir / "no_existe.xlsx",
            current_path=self.base_dir / "no_existe_2.xlsx",
            output_dir=self.output_dir,
        )
        with self.assertRaises(EngineInputError):
            run(config)
        self.assertFalse(self.output_dir.exists() and any(self.output_dir.iterdir()))

    def test_t_cli_reports_invalid_path_without_crashing(self) -> None:
        exit_code = cli_main(
            [
                "--base",
                str(self.base_dir / "missing.xlsx"),
                "--current",
                str(self.base_dir / "missing2.xlsx"),
                "--output",
                str(self.output_dir),
            ]
        )
        self.assertEqual(exit_code, 1)

    # Cobertura adicional: modo posicional (sin clave primaria) y totales de control.
    def test_positional_mode_detects_insertions_and_deletions(self) -> None:
        base = {
            "DATOS": {
                "headers": ["Nombre", "Valor"],
                "rows": [["a", 1], ["b", 2], ["c", 3]],
            }
        }
        current = {
            "DATOS": {
                "headers": ["Nombre", "Valor"],
                "rows": [["a", 1], ["x", 99], ["b", 2], ["c", 3]],
            }
        }
        self._run(base, current)
        structure = self._structure()
        self.assertGreaterEqual(structure["sheets"]["DATOS"]["rows_added"], 1)

    def test_control_totals_mismatch_is_critical(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, 100], [2, 200]]}}
        current = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, 100], [2, 250]]}}
        self._run(
            base,
            current,
            primary_keys={"DATOS": ["ID"]},
            control_totals={"DATOS": ["Monto"]},
        )
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("CONTROL_TOTAL_MISMATCH"), 1)

    def test_control_totals_match_produces_no_mismatch(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, 100], [2, 200]]}}
        current = {"DATOS": {"headers": ["ID", "Monto"], "rows": [[1, 200], [2, 100]]}}
        self._run(
            base,
            current,
            primary_keys={"DATOS": ["ID"]},
            control_totals={"DATOS": ["Monto"]},
        )
        summary = self._summary()
        self.assertNotIn("CONTROL_TOTAL_MISMATCH", summary["counts_by_kind"])


if __name__ == "__main__":
    unittest.main()
