"""Carga de workbooks Excel a `WorkbookSnapshot` (solo lectura).

Se abre el archivo dos veces en modo lectura (`read_only=True`):
  - una vez con `data_only=False` para capturar fórmulas;
  - una vez con `data_only=True` para capturar valores (calculados si Excel
    los cacheó al guardar, o el valor literal si la celda no es fórmula).

Nunca se llama a `save()` sobre un archivo de entrada.
"""

from __future__ import annotations

import logging
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import RowRecord, SheetSnapshot, WorkbookSnapshot
from .security import EngineInputError, require_existing_file, sha256_file

logger = logging.getLogger("erp_diff_engine")


def load_workbook_snapshot(path: Path, label: str) -> WorkbookSnapshot:
    resolved = require_existing_file(path, label)
    digest = sha256_file(resolved)

    try:
        wb_formulas = load_workbook(resolved, data_only=False, read_only=True)
    except InvalidFileException as exc:
        raise EngineInputError(f"{label} no es un archivo Excel válido: {resolved} ({exc})") from exc
    except (OSError, KeyError, ValueError) as exc:
        raise EngineInputError(f"No se pudo abrir {label} ({resolved}): {exc}") from exc

    try:
        try:
            wb_values = load_workbook(resolved, data_only=True, read_only=True)
        except (InvalidFileException, OSError, KeyError, ValueError) as exc:
            raise EngineInputError(
                f"No se pudo abrir {label} en modo valores ({resolved}): {exc}"
            ) from exc

        try:
            sheet_names = list(wb_formulas.sheetnames)
            sheets: dict[str, SheetSnapshot] = {}
            for index, name in enumerate(sheet_names):
                sheets[name] = _load_sheet(
                    wb_formulas[name], wb_values[name], name=name, index=index
                )
        finally:
            wb_values.close()
    finally:
        wb_formulas.close()

    logger.info("Workbook cargado (%s): %d hoja(s) desde %s", label, len(sheet_names), resolved.name)
    return WorkbookSnapshot(path=resolved, sha256=digest, sheet_names=sheet_names, sheets=sheets)


def _load_sheet(ws_formulas, ws_values, *, name: str, index: int) -> SheetSnapshot:
    max_row = ws_formulas.max_row or 0
    max_col = ws_formulas.max_column or 0

    if max_row == 0 or max_col == 0:
        return SheetSnapshot(name=name, index=index, headers=[], rows=[])

    header_row_formulas = next(
        ws_formulas.iter_rows(min_row=1, max_row=1, max_col=max_col), ()
    )
    headers = [cell.value for cell in header_row_formulas]

    rows: list[RowRecord] = []
    if max_row >= 2:
        value_rows = ws_values.iter_rows(min_row=2, max_row=max_row, max_col=max_col)
        formula_rows = ws_formulas.iter_rows(min_row=2, max_row=max_row, max_col=max_col)
        for row_number, (value_cells, formula_cells) in enumerate(
            zip(value_rows, formula_rows), start=2
        ):
            values: dict[int, object] = {}
            formulas: dict[int, str] = {}
            for col_index, (value_cell, formula_cell) in enumerate(
                zip(value_cells, formula_cells)
            ):
                raw_formula = formula_cell.value
                if isinstance(raw_formula, str) and raw_formula.startswith("="):
                    formulas[col_index] = raw_formula
                    values[col_index] = value_cell.value
                else:
                    values[col_index] = value_cell.value
            if any(v is not None for v in values.values()) or formulas:
                rows.append(RowRecord(row_number=row_number, values=values, formulas=formulas))

    return SheetSnapshot(name=name, index=index, headers=headers, rows=rows)
