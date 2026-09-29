"""Tests del hotfix "openpyxl read_only dimensions" (Sprint 001, Hotfix 2).

Contexto: `openpyxl` en modo `read_only=True` NO calcula `max_row`/
`max_column` a partir de las celdas reales; confía ciegamente en el
atributo `<dimension ref="...">` declarado en el XML de la hoja (ver
docstring de `src/erp_diff_engine/loader.py`). Los XLSX exportados desde
Google Sheets pueden declarar ese atributo de forma inconsistente con el
contenido físico real, lo que producía falsos "hoja vacía"
(`headers=[]`, `rows=0`) o registros vacíos fantasma.

Estos tests construyen fixtures que deliberadamente corrompen el
`<dimension>` declarado (ver `tests.erp_diff_fixtures.corrupt_sheet_dimension`)
para reproducir el bug real de forma sintética y determinista, sin usar
ningún dato de Blanco & Asociados.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests import erp_diff_fixtures as fx

from src.erp_diff_engine.engine import run
from src.erp_diff_engine.loader import load_workbook_snapshot
from src.erp_diff_engine.models import EngineConfig
from src.erp_diff_engine.security import sha256_file


class LoaderDimensionTests(unittest.TestCase):
    """Tests directos sobre el loader (sin pasar por todo el motor)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # A. dimensión declarada A1:A1 pero contenido real más allá.
    def test_a_declared_dimension_a1_a1_with_real_content_beyond(self) -> None:
        path = self.base_dir / "A.xlsx"
        sheets = {"HOJA": {"headers": ["ID", "Valor"], "rows": [[i, i * 10] for i in range(1, 21)]}}
        fx.write_workbook_with_offset_header(path, sheets)
        fx.corrupt_sheet_dimension(path, "HOJA", dimension="A1:A1")

        snapshot = load_workbook_snapshot(path, "BASE")
        sheet = snapshot.sheets["HOJA"]
        self.assertEqual(sheet.headers, ["ID", "Valor"])
        self.assertEqual(sheet.n_rows, 20)
        self.assertEqual(sheet.rows[-1].values[0], 20)

    # B. dimensión declarada A1:P1000 pero solo ~100 filas reales.
    def test_b_declared_dimension_1000_rows_with_only_100_real(self) -> None:
        path = self.base_dir / "B.xlsx"
        sheets = {
            "HOJA": {"headers": ["ID", "Valor"], "rows": [[i, i * 10] for i in range(1, 101)]}
        }
        fx.write_workbook_with_offset_header(path, sheets)
        fx.corrupt_sheet_dimension(path, "HOJA", dimension="A1:P1000")

        snapshot = load_workbook_snapshot(path, "BASE")
        sheet = snapshot.sheets["HOJA"]
        self.assertEqual(sheet.n_rows, 100)
        self.assertEqual(sheet.rows[0].row_number, 2)
        self.assertEqual(sheet.rows[-1].row_number, 101)

    # E. filas físicamente vacías (stubs) hasta la fila 1000 declarada:
    #    no deben producir registros fantasma.
    def test_e_trailing_physically_empty_rows_produce_no_phantom_records(self) -> None:
        path = self.base_dir / "E.xlsx"
        sheets = {
            "HOJA": {"headers": ["ID", "Valor"], "rows": [[i, i * 10] for i in range(1, 51)]}
        }
        fx.write_workbook_with_offset_header(path, sheets)
        fx.corrupt_sheet_dimension(
            path, "HOJA", dimension="A1:B1000", trailing_empty_rows_to=1000
        )

        snapshot = load_workbook_snapshot(path, "BASE")
        sheet = snapshot.sheets["HOJA"]
        self.assertEqual(sheet.n_rows, 50)
        self.assertTrue(all(r.row_number <= 51 for r in sheet.rows))

    # F. contenido después de header desplazado, con dimensión corrompida.
    def test_f_content_after_offset_header_with_corrupt_dimension(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20], [3, 30]],
            }
        }
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
        fx.corrupt_sheet_dimension(base_path, "HOJA", dimension="A1:P1000")
        fx.corrupt_sheet_dimension(current_path, "HOJA", dimension="A1:P1000")

        base_snap = load_workbook_snapshot(base_path, "BASE", {"HOJA": 3})
        current_snap = load_workbook_snapshot(current_path, "CURRENT", {"HOJA": 3})
        self.assertEqual(base_snap.sheets["HOJA"].n_rows, 2)
        self.assertEqual(current_snap.sheets["HOJA"].n_rows, 3)
        self.assertEqual(current_snap.sheets["HOJA"].rows[-1].row_number, 6)

    # G. fórmulas después de header desplazado, con dimensión corrompida.
    def test_g_formula_after_offset_header_with_corrupt_dimension(self) -> None:
        path = self.base_dir / "G.xlsx"
        fx.write_formula_workbook(
            path,
            "HOJA",
            ["ID", "Total"],
            rows=[[1, ("=1+1", 2)]],
            leading_rows=[["TITULO"], ["SUBTITULO"]],
        )
        fx.corrupt_sheet_dimension(path, "HOJA", dimension="A1:P1000")

        snapshot = load_workbook_snapshot(path, "BASE", {"HOJA": 3})
        sheet = snapshot.sheets["HOJA"]
        self.assertEqual(sheet.n_rows, 1)
        self.assertEqual(sheet.rows[0].formulas[1], "=1+1")
        self.assertEqual(sheet.rows[0].values[1], 2)


class EngineDimensionRegressionTests(unittest.TestCase):
    """Tests de extremo a extremo (motor completo) con dimensión corrompida."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_corrupted(
        self, path: Path, sheets: dict, sheet_name: str, dimension: str
    ) -> None:
        fx.write_workbook_with_offset_header(path, sheets)
        fx.corrupt_sheet_dimension(path, sheet_name, dimension=dimension)

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    # C. header en fila 2, con dimensión declarada mayor a la real.
    def test_c_header_row_2_with_corrupt_dimension(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {
            "HOJA": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            }
        }
        self._write_corrupted(base_path, base, "HOJA", "A1:P1000")
        self._write_corrupted(current_path, current, "HOJA", "A1:P1000")
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
            header_rows={"HOJA": 2},
        )
        run(config)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_added"], 1)
        self.assertEqual(structure["sheets"]["HOJA"]["base_col_count"], 2)

    # D. header en fila 3, con dimensión declarada mayor a la real.
    def test_d_header_row_3_with_corrupt_dimension(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            }
        }
        self._write_corrupted(base_path, base, "HOJA", "A1:P1000")
        self._write_corrupted(current_path, current, "HOJA", "A1:P1000")
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
            header_rows={"HOJA": 3},
        )
        run(config)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_added"], 1)

    # H. los archivos de entrada siguen siendo byte-identicos (SHA-256 sin
    #    cambios) tras ejecutar el motor sobre inputs con dimensión corrupta.
    def test_h_input_files_remain_byte_identical(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        sheets = {
            "HOJA": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            }
        }
        self._write_corrupted(base_path, sheets, "HOJA", "A1:P1000")
        self._write_corrupted(current_path, sheets, "HOJA", "A1:P1000")
        before_base = sha256_file(base_path)
        before_current = sha256_file(current_path)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
            header_rows={"HOJA": 2},
        )
        run(config)
        self.assertEqual(sha256_file(base_path), before_base)
        self.assertEqual(sha256_file(current_path), before_current)
        summary = self._summary()
        self.assertEqual(summary["base_sha256"], before_base)
        self.assertEqual(summary["current_sha256"], before_current)

    # I. ejecución idempotente sobre inputs con dimensión corrupta.
    def test_i_repeated_execution_is_idempotent_with_corrupt_dimension(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 11], [3, 30]],
            }
        }
        self._write_corrupted(base_path, base, "HOJA", "A1:P1000")
        self._write_corrupted(current_path, current, "HOJA", "A1:P1000")
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
            header_rows={"HOJA": 3},
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

    # J. regresión: un workbook normal (dimensión correcta, sin corromper)
    #    sigue funcionando igual que antes del hotfix.
    def test_j_normal_workbook_regression(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {"HOJA": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        current = {"HOJA": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 25]]}}
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
        )
        result = run(config)
        self.assertEqual(result.total_differences, 1)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("VALUE_MODIFIED"), 1)


class MainRegressionFixturesTests(unittest.TestCase):
    """TEST DE REGRESIÓN PRINCIPAL del hotfix: reproduce los dos patrones
    reales (ALERTAS/SOLICITUDES) con la dimensión física/declarada
    extendida hasta la fila 1000, tal como reportó la inspección
    independiente."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    # Fixture 1: header fila 2, BASE 206 filas reales, CURRENT 209 filas
    # reales, dimensión física/declarada hasta la fila 1000.
    def test_fixture_1_header_row_2_206_to_209_exactly_three_row_added(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base_rows = [[i, i * 10] for i in range(1, 207)]  # 206 filas
        current_rows = [[i, i * 10] for i in range(1, 210)]  # 209 filas
        base = {
            "ALERTAS": {
                "leading_rows": [["TITULO SINTETICO"]],
                "headers": ["ID", "Valor"],
                "rows": base_rows,
            }
        }
        current = {
            "ALERTAS": {
                "leading_rows": [["TITULO SINTETICO"]],
                "headers": ["ID", "Valor"],
                "rows": current_rows,
            }
        }
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
        fx.corrupt_sheet_dimension(
            base_path, "ALERTAS", dimension="A1:F1000", trailing_empty_rows_to=1000
        )
        fx.corrupt_sheet_dimension(
            current_path, "ALERTAS", dimension="A1:F1000", trailing_empty_rows_to=1000
        )
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"ALERTAS": ["ID"]},
            header_rows={"ALERTAS": 2},
        )
        run(config)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["ALERTAS"]["rows_added"], 3)
        self.assertEqual(structure["sheets"]["ALERTAS"]["rows_removed"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 3)
        self.assertNotIn("ROW_REMOVED", summary["counts_by_kind"])

    # Fixture 2: header fila 3, BASE 96 filas reales, CURRENT 98 filas
    # reales, dimensión física/declarada hasta la fila 1000.
    def test_fixture_2_header_row_3_96_to_98_exactly_two_row_added(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base_rows = [[i, i * 10] for i in range(1, 97)]  # 96 filas
        current_rows = [[i, i * 10] for i in range(1, 99)]  # 98 filas
        base = {
            "SOLICITUDES": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": base_rows,
            }
        }
        current = {
            "SOLICITUDES": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": current_rows,
            }
        }
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
        fx.corrupt_sheet_dimension(
            base_path, "SOLICITUDES", dimension="A1:P1000", trailing_empty_rows_to=1000
        )
        fx.corrupt_sheet_dimension(
            current_path, "SOLICITUDES", dimension="A1:P1000", trailing_empty_rows_to=1000
        )
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"SOLICITUDES": ["ID"]},
            header_rows={"SOLICITUDES": 3},
        )
        run(config)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["SOLICITUDES"]["rows_added"], 2)
        self.assertEqual(structure["sheets"]["SOLICITUDES"]["rows_removed"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 2)
        self.assertNotIn("ROW_REMOVED", summary["counts_by_kind"])


if __name__ == "__main__":
    unittest.main()
