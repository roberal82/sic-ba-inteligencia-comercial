"""Tests de data_start_rows explícito por hoja (hotfix Sprint 001, DATA_START_ROWS).

Contexto (ver AGENTS.md y el prompt operativo "HOTFIX 3 / DATA_START_ROWS"):
la hoja SOLICITUDES usa header_row = 3 y la fila 4 es una fila plantilla (sin
ID_Solicitud real, con una fórmula en la columna Dias_Habiles) que no debe
tratarse como registro real ni producir NULL_IN_KEY. Estos tests cubren
``data_start_rows`` explícito por hoja, con compatibilidad hacia atrás
(header_row + 1 por defecto, sin inferencia automática de filas plantilla) y
fallo cerrado si la fila configurada no existe físicamente en el workbook.

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
from src.erp_diff_engine.security import EngineInputError


class DataStartRowsEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    def _write_solicitudes(self, path: Path, n_records: int) -> None:
        # Fila 4 (primera tras el header en fila 3): plantilla real de
        # SOLICITUDES -> ID_Solicitud nulo + fórmula en Dias_Habiles.
        rows: list[list[object]] = [[None, ("=1+1", 2)]]
        rows += [[f"SOL-{i:04d}", i] for i in range(1, n_records + 1)]
        fx.write_formula_workbook(
            path,
            "SOLICITUDES",
            ["ID_Solicitud", "Dias_Habiles"],
            rows=rows,
            leading_rows=[["TITULO SOLICITUDES"], ["SUBTITULO"]],
        )

    def _run(self, base_records: int, current_records: int, **config_kwargs):
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        self._write_solicitudes(base_path, base_records)
        self._write_solicitudes(current_path, current_records)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            **config_kwargs,
        )
        return run(config)

    # A. header fila 3 + data_start fila 5: SOL-0001..0096 -> +SOL-0097/0098.
    def test_a_header_row_3_data_start_row_5_detects_two_row_added(self) -> None:
        self._run(
            96,
            98,
            primary_keys={"SOLICITUDES": ["ID_Solicitud"]},
            header_rows={"SOLICITUDES": 3},
            data_start_rows={"SOLICITUDES": 5},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["SOLICITUDES"]["rows_added"], 2)
        self.assertEqual(structure["sheets"]["SOLICITUDES"]["rows_removed"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 2)
        self.assertNotIn("ROW_REMOVED", summary["counts_by_kind"])

    # B. fila 4 plantilla con fórmula no debe convertirse en registro: con
    # BASE/CURRENT idénticos salvo la plantilla, 0 diferencias esperadas.
    def test_b_template_row_4_not_treated_as_record(self) -> None:
        result = self._run(
            10,
            10,
            primary_keys={"SOLICITUDES": ["ID_Solicitud"]},
            header_rows={"SOLICITUDES": 3},
            data_start_rows={"SOLICITUDES": 5},
        )
        self.assertEqual(result.total_differences, 0)
        summary = self._summary()
        self.assertEqual(summary["total_differences"], 0)
        self.assertNotIn("NULL_IN_KEY", summary["counts_by_kind"])
        self.assertNotIn("FORMULA_CHANGED", summary["counts_by_kind"])

    # C. PK sin NULL_IN_KEY cuando la única fila nula es la plantilla excluida.
    def test_c_no_null_in_key_when_template_row_excluded(self) -> None:
        self._run(
            10,
            12,
            primary_keys={"SOLICITUDES": ["ID_Solicitud"]},
            header_rows={"SOLICITUDES": 3},
            data_start_rows={"SOLICITUDES": 5},
        )
        summary = self._summary()
        self.assertNotIn("NULL_IN_KEY", summary["counts_by_kind"])
        structure = self._structure()
        self.assertEqual(
            structure["sheets"]["SOLICITUDES"]["row_matching_evidence"], "CONFIRMED"
        )

    # D. default: sin data_start_rows declarado, data_start = header_row + 1.
    # La fila plantilla 4 (= header_row(3) + 1) SÍ se carga como registro y
    # produce NULL_IN_KEY: esto documenta el comportamiento por defecto
    # (compatibilidad hacia atrás) que motiva declarar data_start_rows.
    def test_d_default_data_start_is_header_row_plus_one(self) -> None:
        self._run(
            10,
            10,
            primary_keys={"SOLICITUDES": ["ID_Solicitud"]},
            header_rows={"SOLICITUDES": 3},
        )
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("NULL_IN_KEY"), 2)  # BASE y CURRENT

    # E. data_start_rows <= header_row debe fallar (validación de configuración).
    def test_e_data_start_equal_to_header_row_is_rejected(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "header_rows": {"SOLICITUDES": 3},
                    "data_start_rows": {"SOLICITUDES": 3},
                },
            )

    def test_e_bis_data_start_below_header_row_is_rejected(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "header_rows": {"SOLICITUDES": 3},
                    "data_start_rows": {"SOLICITUDES": 2},
                },
            )

    def test_e_ter_data_start_equal_to_default_header_row_1_is_rejected(self) -> None:
        # Sin header_rows declarado, header_row efectivo = 1: data_start >= 2.
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "data_start_rows": {"HOJA": 1},
                },
            )

    # F. data_start_rows fuera del workbook debe fallar cerrado (en tiempo de
    # carga, cuando ya se conoce el contenido físico real del archivo).
    def test_f_data_start_beyond_workbook_fails_closed(self) -> None:
        with self.assertRaises(EngineInputError):
            self._run(
                1,
                1,
                primary_keys={"SOLICITUDES": ["ID_Solicitud"]},
                header_rows={"SOLICITUDES": 3},
                data_start_rows={"SOLICITUDES": 1000},
            )

    # G. compatibilidad hacia atrás total: hoja con header_row implícito (1)
    # y sin data_start_rows sigue comportándose exactamente igual que antes.
    def test_g_full_backward_compatibility_no_header_rows_no_data_start_rows(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        sheets = {"HOJA": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        fx.write_workbook_with_offset_header(base_path, sheets)
        fx.write_workbook_with_offset_header(current_path, sheets)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"HOJA": ["ID"]},
        )
        result = run(config)
        self.assertEqual(result.total_differences, 0)


if __name__ == "__main__":
    unittest.main()
