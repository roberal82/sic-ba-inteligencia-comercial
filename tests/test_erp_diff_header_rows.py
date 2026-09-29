"""Tests de header_rows explícito por hoja (Fase B1-R2, hotfix Sprint 001).

Contexto (ver AGENTS.md y el hallazgo de Fase B1): el ERP real usa layouts
con títulos/subtítulos antes del encabezado real de datos. El motor asumía
siempre fila 1 = encabezado y producía un falso negativo (0 diferencias
reportadas donde en realidad había filas nuevas). Estos tests cubren la
corrección: ``header_rows`` explícito por hoja en la configuración, sin
inferencia automática y con compatibilidad hacia atrás (fila 1 por defecto
para hojas no declaradas).

Todos los datos son sintéticos; ningún nombre de hoja, ruta o valor proviene
de Blanco & Asociados ni de ninguna copia real del ERP.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tests import erp_diff_fixtures as fx

from src.erp_diff_engine.config import load_config
from src.erp_diff_engine.engine import run
from src.erp_diff_engine.models import EngineConfig
from src.erp_diff_engine.security import EngineInputError, sha256_file


class HeaderRowsEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_offset(self, base_sheets: dict, current_sheets: dict, **config_kwargs):
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_workbook_with_offset_header(base_path, base_sheets)
        fx.write_workbook_with_offset_header(current_path, current_sheets)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            **config_kwargs,
        )
        return run(config), base_path, current_path

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    def _rows_csv(self) -> str:
        return (self.output_dir / "diff_rows.csv").read_text(encoding="utf-8")

    # A. header en fila 1 (compatibilidad hacia atrás, sin header_rows)
    def test_a_default_header_row_1_backward_compatible(self) -> None:
        sheets = {"HOJA": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        result, _, _ = self._run_offset(sheets, sheets, primary_keys={"HOJA": ["ID"]})
        self.assertEqual(result.total_differences, 0)

    # B. título fila 1 + header fila 2
    def test_b_title_row_then_header_row_2(self) -> None:
        base = {
            "HOJA": {
                "leading_rows": [["TITULO EJEMPLO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO EJEMPLO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            }
        }
        result, _, _ = self._run_offset(
            base, current, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 2}
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_added"], 1)
        self.assertEqual(structure["sheets"]["HOJA"]["columns_added"], [])
        self.assertEqual(structure["sheets"]["HOJA"]["base_col_count"], 2)

    # C. título + subtítulo + header fila 3
    def test_c_title_subtitle_then_header_row_3(self) -> None:
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
        self._run_offset(base, current, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 3})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_added"], 1)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 1)

    # D. filas nuevas después de header desplazado
    def test_d_rows_added_after_offset_header(self) -> None:
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
                "rows": [[1, 10], [2, 20], [3, 30]],
            }
        }
        self._run_offset(base, current, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 3})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_added"], 2)

    # E. filas eliminadas después de header desplazado
    def test_e_rows_removed_after_offset_header(self) -> None:
        base = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20], [3, 30]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO"], ["SUBTITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            }
        }
        self._run_offset(base, current, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 3})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_removed"], 2)

    # F. PK con header desplazado
    def test_f_primary_key_matching_with_offset_header(self) -> None:
        base = {
            "HOJA": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            }
        }
        current = {
            "HOJA": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 99]],
            }
        }
        self._run_offset(base, current, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 2})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA"]["rows_modified"], 1)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("VALUE_MODIFIED"), 1)

    # G. fórmulas con header desplazado
    def test_g_formula_change_detected_with_offset_header(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_formula_workbook(
            base_path,
            "HOJA",
            ["ID", "Total"],
            rows=[[1, ("=1+1", 2)]],
            leading_rows=[["TITULO"], ["SUBTITULO"]],
        )
        fx.write_formula_workbook(
            current_path,
            "HOJA",
            ["ID", "Total"],
            rows=[[1, ("=2", 2)]],
            leading_rows=[["TITULO"], ["SUBTITULO"]],
        )
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
            header_rows={"HOJA": 3},
        )
        run(config)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("FORMULA_CHANGED_SAME_VALUE"), 1)

    # H. header_row inválido = 0
    def test_h_header_row_zero_is_rejected(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "header_rows": {"HOJA": 0},
                },
            )

    # I. header_row negativo
    def test_i_header_row_negative_is_rejected(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "header_rows": {"HOJA": -3},
                },
            )

    # J. header_row superior al máximo de filas de la hoja
    def test_j_header_row_above_max_row_raises_controlled_error(self) -> None:
        sheets = {"HOJA": {"headers": ["ID"], "rows": [[1]]}}
        with self.assertRaises(EngineInputError):
            self._run_offset(sheets, sheets, header_rows={"HOJA": 50})

    # K. configuración parcial: una hoja declarada, otra usa default fila 1
    def test_k_partial_header_rows_configuration(self) -> None:
        base = {
            "CON_OFFSET": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            },
            "SIN_OFFSET": {"headers": ["ID", "Valor"], "rows": [[1, 10]]},
        }
        current = {
            "CON_OFFSET": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            },
            "SIN_OFFSET": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]},
        }
        self._run_offset(
            base,
            current,
            primary_keys={"CON_OFFSET": ["ID"], "SIN_OFFSET": ["ID"]},
            header_rows={"CON_OFFSET": 2},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["CON_OFFSET"]["rows_added"], 1)
        self.assertEqual(structure["sheets"]["SIN_OFFSET"]["rows_added"], 1)

    # L. idempotencia (ejecución repetida produce bytes idénticos)
    def test_l_repeated_execution_is_idempotent_with_offset_header(self) -> None:
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
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
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

    # M. hashes de inputs sin cambios: el loader no modifica BASE/CURRENT y el
    # SHA-256 reportado corresponde exactamente al archivo real en disco.
    def test_m_input_hashes_unchanged_and_reported_correctly(self) -> None:
        sheets = {
            "HOJA": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            }
        }
        _, base_path, current_path = self._run_offset(
            sheets, sheets, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 2}
        )
        summary = self._summary()
        self.assertEqual(summary["base_sha256"], sha256_file(base_path))
        self.assertEqual(summary["current_sha256"], sha256_file(current_path))

    # row_number conserva el número real de fila Excel con header desplazado.
    def test_row_number_preserved_with_offset_header(self) -> None:
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
        self._run_offset(base, current, primary_keys={"HOJA": ["ID"]}, header_rows={"HOJA": 3})
        rows_csv = self._rows_csv()
        # Header en fila 3 -> primera fila de datos es la 4; la fila agregada
        # (ID=2) es la fila real Excel 5.
        self.assertIn("fila CURRENT 5", rows_csv)


class HeaderRowsRegressionTests(unittest.TestCase):
    """Regresión crítica: reproduce el falso negativo real detectado en Fase B1.

    Fixtures puramente sintéticos, estructuralmente equivalentes al hallazgo
    (ver prompt operativo de Fase B1-R2): header desplazado + filas nuevas
    después de ese header, que antes del fix producían 0 diferencias.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run_offset(self, base_sheets: dict, current_sheets: dict, **config_kwargs):
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_workbook_with_offset_header(base_path, base_sheets)
        fx.write_workbook_with_offset_header(current_path, current_sheets)
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

    # Fixture equivalente a "header fila 3, 96 filas -> 98 filas" (patrón SOLICITUDES).
    def test_header_row_3_detects_exactly_two_row_added(self) -> None:
        base_rows = [[i, i * 10] for i in range(1, 97)]  # 96 filas de datos
        current_rows = [[i, i * 10] for i in range(1, 99)]  # 98 filas de datos
        base = {
            "HOJA_SINTETICA_1": {
                "leading_rows": [["TITULO SINTETICO"], ["SUBTITULO SINTETICO"]],
                "headers": ["ID", "Valor"],
                "rows": base_rows,
            }
        }
        current = {
            "HOJA_SINTETICA_1": {
                "leading_rows": [["TITULO SINTETICO"], ["SUBTITULO SINTETICO"]],
                "headers": ["ID", "Valor"],
                "rows": current_rows,
            }
        }
        self._run_offset(
            base,
            current,
            primary_keys={"HOJA_SINTETICA_1": ["ID"]},
            header_rows={"HOJA_SINTETICA_1": 3},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA_SINTETICA_1"]["rows_added"], 2)
        self.assertEqual(structure["sheets"]["HOJA_SINTETICA_1"]["rows_removed"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 2)
        self.assertNotIn("ROW_REMOVED", summary["counts_by_kind"])

    # Fixture equivalente a "header fila 2, 206 filas -> 209 filas" (patrón ALERTAS).
    def test_header_row_2_detects_exactly_three_row_added(self) -> None:
        base_rows = [[i, i * 10] for i in range(1, 207)]  # 206 filas de datos
        current_rows = [[i, i * 10] for i in range(1, 210)]  # 209 filas de datos
        base = {
            "HOJA_SINTETICA_2": {
                "leading_rows": [["TITULO SINTETICO"]],
                "headers": ["ID", "Valor"],
                "rows": base_rows,
            }
        }
        current = {
            "HOJA_SINTETICA_2": {
                "leading_rows": [["TITULO SINTETICO"]],
                "headers": ["ID", "Valor"],
                "rows": current_rows,
            }
        }
        self._run_offset(
            base,
            current,
            primary_keys={"HOJA_SINTETICA_2": ["ID"]},
            header_rows={"HOJA_SINTETICA_2": 2},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["HOJA_SINTETICA_2"]["rows_added"], 3)
        self.assertEqual(structure["sheets"]["HOJA_SINTETICA_2"]["rows_removed"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 3)
        self.assertNotIn("ROW_REMOVED", summary["counts_by_kind"])


if __name__ == "__main__":
    unittest.main()
