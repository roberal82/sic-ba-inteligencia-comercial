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
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import RowRecord, SheetSnapshot, WorkbookSnapshot
from .security import EngineInputError, require_existing_file, sha256_file

logger = logging.getLogger("erp_diff_engine")


def load_workbook_snapshot(
    path: Path, label: str, header_rows: dict[str, int] | None = None
) -> WorkbookSnapshot:
    """Carga un workbook.

    ``header_rows`` es opcional: {hoja: fila_encabezado (1-based)}. Una hoja
    no declarada usa fila 1 (compatibilidad hacia atrás).
    """

    resolved = require_existing_file(path, label)
    digest = sha256_file(resolved)
    header_rows = header_rows or {}

    try:
        wb_formulas = load_workbook(resolved, data_only=False, read_only=True)
    except InvalidFileException as exc:
        raise EngineInputError(f"{label} no es un archivo Excel válido: {resolved} ({exc})") from exc
    except (OSError, KeyError, ValueError, BadZipFile, EOFError) as exc:
        raise EngineInputError(f"No se pudo abrir {label} ({resolved}): {exc}") from exc

    try:
        try:
            wb_values = load_workbook(resolved, data_only=True, read_only=True)
        except (
            InvalidFileException,
            OSError,
            KeyError,
            ValueError,
            BadZipFile,
            EOFError,
        ) as exc:
            raise EngineInputError(
                f"No se pudo abrir {label} en modo valores ({resolved}): {exc}"
            ) from exc

        try:
            sheet_names = list(wb_formulas.sheetnames)
            sheets: dict[str, SheetSnapshot] = {}
            for index, name in enumerate(sheet_names):
                sheets[name] = _load_sheet(
                    wb_formulas[name],
                    wb_values[name],
                    name=name,
                    index=index,
                    header_row=header_rows.get(name, 1),
                )
        finally:
            wb_values.close()
    finally:
        wb_formulas.close()

    logger.info("Workbook cargado (%s): %d hoja(s) desde %s", label, len(sheet_names), resolved.name)
    return WorkbookSnapshot(path=resolved, sha256=digest, sheet_names=sheet_names, sheets=sheets)


def _load_sheet(
    ws_formulas, ws_values, *, name: str, index: int, header_row: int = 1
) -> SheetSnapshot:
    if header_row < 1:
        raise EngineInputError(
            f"header_row inválido para la hoja '{name}': {header_row} (debe ser un entero >= 1)."
        )

    max_row = ws_formulas.max_row or 0
    max_col = ws_formulas.max_column or 0

    if max_row == 0 or max_col == 0:
        return SheetSnapshot(name=name, index=index, headers=[], rows=[])

    if header_row > max_row:
        raise EngineInputError(
            f"header_row configurado ({header_row}) para la hoja '{name}' supera "
            f"el máximo de filas de la hoja ({max_row})."
        )

    header_row_formulas = next(
        ws_formulas.iter_rows(min_row=header_row, max_row=header_row, max_col=max_col), ()
    )
    headers = [cell.value for cell in header_row_formulas]

    rows: list[RowRecord] = []
    data_start = header_row + 1
    if max_row >= data_start:
        value_rows = ws_values.iter_rows(min_row=data_start, max_row=max_row, max_col=max_col)
        formula_rows = ws_formulas.iter_rows(min_row=data_start, max_row=max_row, max_col=max_col)
        for row_number, (value_cells, formula_cells) in enumerate(
            zip(value_rows, formula_rows), start=data_start
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
