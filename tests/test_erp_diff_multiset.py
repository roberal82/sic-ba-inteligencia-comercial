"""Tests del modo MULTISET de emparejamiento de filas (Sprint 001, Hotfix 4).

Contexto (ver AGENTS.md y el prompt operativo del hotfix): hojas tipo
event/log (p.ej. una bitácora de alertas) no tienen una clave primaria
confiable, y contienen eventos idénticos repetidos legítimamente. El motor
no debe marcar esas repeticiones como ``DUPLICATE_KEY``. Este archivo cubre
los escenarios A-N pedidos en el hotfix: el modo ``multiset`` se activa solo
por configuración explícita (``row_match_modes`` + ``multiset_columns``),
nunca hardcodeando nombres de hoja empresariales en el motor.

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

_MULTISET_HEADERS = ["Fecha", "Tipo", "Modulo", "IDRegistro", "Detalle", "Estado"]


class MultisetRowMatchingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.base_dir = Path(self._tmp.name)
        self.output_dir = self.base_dir / "output"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, base_sheets: dict, current_sheets: dict, **config_kwargs):
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
        return run(config), base_path, current_path

    def _summary(self) -> dict:
        return json.loads((self.output_dir / "diff_summary.json").read_text(encoding="utf-8"))

    def _structure(self) -> dict:
        return json.loads((self.output_dir / "diff_structure.json").read_text(encoding="utf-8"))

    def _event(self, tag: str, extra: object = "d") -> list:
        return ["2024-01-01", tag, "M1", "R1", extra, "ABIERTO"]

    # A. multiset idéntico: mismas ocurrencias repetidas en BASE y CURRENT -> 0 drift.
    def test_a_multiset_identical_produces_zero_differences(self) -> None:
        rows = [self._event("X"), self._event("X")]
        sheets = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": rows}}
        result, _, _ = self._run(
            sheets,
            sheets,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        self.assertEqual(result.total_differences, 0)

    # B. BASE=2 ocurrencias, CURRENT=3 de la misma firma -> 1 ROW_ADDED (delta neto).
    def test_b_two_base_three_current_is_one_row_added(self) -> None:
        base = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [self._event("X"), self._event("X")]}}
        current = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("X"), self._event("X"), self._event("X")],
            }
        }
        self._run(
            base,
            current,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_added"], 1)
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_removed"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 1)
        self.assertNotIn("ROW_REMOVED", summary["counts_by_kind"])

    # C. BASE=3 ocurrencias, CURRENT=2 de la misma firma -> 1 ROW_REMOVED (delta neto).
    def test_c_three_base_two_current_is_one_row_removed(self) -> None:
        base = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("X"), self._event("X"), self._event("X")],
            }
        }
        current = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [self._event("X"), self._event("X")]}}
        self._run(
            base,
            current,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_removed"], 1)
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_added"], 0)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_REMOVED"), 1)
        self.assertNotIn("ROW_ADDED", summary["counts_by_kind"])

    # D. reordenar filas no produce drift.
    def test_d_reordered_rows_produce_zero_drift(self) -> None:
        base = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("A"), self._event("B"), self._event("C")],
            }
        }
        current = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("C"), self._event("A"), self._event("B")],
            }
        }
        result, _, _ = self._run(
            base,
            current,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        self.assertEqual(result.total_differences, 0)

    # E. dos eventos idénticos son válidos: nunca DUPLICATE_KEY en modo multiset.
    def test_e_identical_events_are_not_duplicate_key(self) -> None:
        rows = [self._event("X"), self._event("X"), self._event("X")]
        sheets = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": rows}}
        result, _, _ = self._run(
            sheets,
            sheets,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        summary = self._summary()
        self.assertNotIn("DUPLICATE_KEY", summary["counts_by_kind"])
        self.assertEqual(result.total_differences, 0)

    # F. None es un componente válido de la firma multiset.
    def test_f_none_value_inside_signature_is_valid(self) -> None:
        row_with_none = ["2024-01-01", "X", "M1", "R1", None, "ABIERTO"]
        base = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [row_with_none]}}
        current = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [row_with_none, row_with_none]}}
        self._run(
            base,
            current,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_added"], 1)
        summary = self._summary()
        self.assertEqual(summary["counts_by_kind"].get("ROW_ADDED"), 1)
        self.assertNotIn("NULL_IN_KEY", summary["counts_by_kind"])

    # G. columna multiset inexistente en el workbook real = fail closed.
    def test_g_missing_multiset_column_fails_closed(self) -> None:
        sheets = {"EVENTOS": {"headers": ["Fecha", "Tipo"], "rows": [["2024-01-01", "X"]]}}
        with self.assertRaises(EngineInputError):
            self._run(
                sheets,
                sheets,
                row_match_modes={"EVENTOS": "multiset"},
                multiset_columns={"EVENTOS": _MULTISET_HEADERS},
            )

    # H1. configuración parcial: multiset_columns declarado sin activar el modo
    # en row_match_modes -> se ignora, la hoja conserva su comportamiento por
    # defecto (keyed, porque hay primary_keys).
    def test_h1_multiset_columns_without_mode_is_ignored(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        self._run(
            base,
            current,
            primary_keys={"DATOS": ["ID"]},
            multiset_columns={"DATOS": ["ID", "Valor"]},
        )
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "keyed")
        self.assertEqual(structure["sheets"]["DATOS"]["rows_added"], 1)

    # H2. configuración parcial inversa: row_match_modes = multiset sin
    # multiset_columns declarado para esa hoja -> error de configuración
    # explícito (fail closed), tanto vía EngineConfig directo como vía
    # load_config (archivo de configuración).
    def test_h2_multiset_mode_without_columns_fails_closed(self) -> None:
        sheets = {"EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [self._event("X")]}}
        with self.assertRaises(EngineInputError):
            self._run(sheets, sheets, row_match_modes={"EVENTOS": "multiset"})

    def test_h2_load_config_rejects_multiset_mode_without_columns(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "row_match_modes": {"EVENTOS": "multiset"},
                },
            )

    def test_h2_load_config_accepts_multiset_mode_with_columns(self) -> None:
        config = load_config(
            None,
            {
                "base_path": "BASE.xlsx",
                "current_path": "CURRENT.xlsx",
                "output_dir": "out",
                "row_match_modes": {"EVENTOS": "multiset"},
                "multiset_columns": {"EVENTOS": _MULTISET_HEADERS},
            },
        )
        self.assertEqual(config.row_match_modes, {"EVENTOS": "multiset"})
        self.assertEqual(config.multiset_columns, {"EVENTOS": _MULTISET_HEADERS})

    def test_h2_load_config_rejects_invalid_row_match_mode_value(self) -> None:
        with self.assertRaises(EngineInputError):
            load_config(
                None,
                {
                    "base_path": "BASE.xlsx",
                    "current_path": "CURRENT.xlsx",
                    "output_dir": "out",
                    "row_match_modes": {"EVENTOS": "no_existe"},
                },
            )

    # I. modo keyed sigue funcionando sin cambios (regresión de compatibilidad).
    def test_i_keyed_mode_still_works(self) -> None:
        base = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10]]}}
        current = {"DATOS": {"headers": ["ID", "Valor"], "rows": [[1, 10], [2, 20]]}}
        self._run(base, current, primary_keys={"DATOS": ["ID"]})
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "keyed")
        self.assertEqual(structure["sheets"]["DATOS"]["rows_added"], 1)

    # J. modo positional sigue funcionando sin cambios (regresión de compatibilidad).
    def test_j_positional_mode_still_works(self) -> None:
        base = {"DATOS": {"headers": ["Nombre", "Valor"], "rows": [["a", 1], ["b", 2]]}}
        current = {"DATOS": {"headers": ["Nombre", "Valor"], "rows": [["a", 1], ["x", 99], ["b", 2]]}}
        self._run(base, current)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["DATOS"]["row_diff_mode"], "positional")
        self.assertGreaterEqual(structure["sheets"]["DATOS"]["rows_added"], 1)

    # K. header_rows sigue funcionando junto con multiset en otra hoja.
    def test_k_header_rows_still_works_alongside_multiset(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {
            "CON_OFFSET": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10]],
            },
            "EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [self._event("X"), self._event("X")]},
        }
        current = {
            "CON_OFFSET": {
                "leading_rows": [["TITULO"]],
                "headers": ["ID", "Valor"],
                "rows": [[1, 10], [2, 20]],
            },
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("X"), self._event("X"), self._event("X")],
            },
        }
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"CON_OFFSET": ["ID"]},
            header_rows={"CON_OFFSET": 2},
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        run(config)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["CON_OFFSET"]["rows_added"], 1)
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_added"], 1)
        self.assertEqual(structure["sheets"]["EVENTOS"]["row_diff_mode"], "multiset")

    # L. data_start_rows sigue funcionando junto con multiset en otra hoja.
    # La fila plantilla (ID nulo, justo después del encabezado) debe excluirse
    # vía data_start_rows y no producir NULL_IN_KEY, exactamente igual que sin
    # ninguna hoja multiset configurada en el resto del workbook.
    def test_l_data_start_rows_still_works_alongside_multiset(self) -> None:
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        base = {
            "CON_PLANTILLA": {
                "headers": ["ID", "Valor"],
                "rows": [[None, "PLANTILLA"], [1, 10]],
            },
            "EVENTOS": {"headers": _MULTISET_HEADERS, "rows": [self._event("X"), self._event("X")]},
        }
        current = {
            "CON_PLANTILLA": {
                "headers": ["ID", "Valor"],
                "rows": [[None, "PLANTILLA"], [1, 10], [2, 20]],
            },
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("X"), self._event("X"), self._event("X")],
            },
        }
        fx.write_workbook_with_offset_header(base_path, base)
        fx.write_workbook_with_offset_header(current_path, current)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            primary_keys={"CON_PLANTILLA": ["ID"]},
            data_start_rows={"CON_PLANTILLA": 3},
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        run(config)
        structure = self._structure()
        self.assertEqual(structure["sheets"]["CON_PLANTILLA"]["rows_added"], 1)
        self.assertNotIn("NULL_IN_KEY", self._summary()["counts_by_kind"])
        self.assertEqual(structure["sheets"]["EVENTOS"]["rows_added"], 1)

    # M. idempotencia: misma configuración + mismas entradas -> bytes idénticos.
    def test_m_repeated_execution_is_idempotent(self) -> None:
        base = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("A"), self._event("A"), self._event("B")],
            }
        }
        current = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("A"), self._event("B"), self._event("B"), self._event("C")],
            }
        }
        base_path = self.base_dir / "BASE.xlsx"
        current_path = self.base_dir / "CURRENT.xlsx"
        fx.write_openpyxl_workbook(base_path, base)
        fx.write_openpyxl_workbook(current_path, current)
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
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

    # N. inputs byte-identicos: el motor nunca escribe sobre BASE/CURRENT.
    def test_n_inputs_are_byte_identical_after_run(self) -> None:
        sheets = {
            "EVENTOS": {
                "headers": _MULTISET_HEADERS,
                "rows": [self._event("A"), self._event("A")],
            }
        }
        _, base_path, current_path = self._run(
            sheets,
            sheets,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        base_hash_before = sha256_file(base_path)
        current_hash_before = sha256_file(current_path)
        # Segunda corrida, sobre los mismos archivos ya usados en la primera.
        config = EngineConfig(
            base_path=base_path,
            current_path=current_path,
            output_dir=self.output_dir,
            row_match_modes={"EVENTOS": "multiset"},
            multiset_columns={"EVENTOS": _MULTISET_HEADERS},
        )
        run(config)
        self.assertEqual(sha256_file(base_path), base_hash_before)
        self.assertEqual(sha256_file(current_path), current_hash_before)


if __name__ == "__main__":
    unittest.main()
