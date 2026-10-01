"""Totales de control numéricos configurables por hoja/columna.

No se infiere qué columnas son "totales de control": deben declararse
explícitamente en la configuración (`control_totals: {hoja: [columna, ...]}`).
Sin declaración explícita, no se genera ningún chequeo de totales.
"""

from __future__ import annotations

from decimal import Decimal

from .columns import named_column_index
from .models import Difference, DiffKind, SheetSnapshot
from .normalize import try_parse_pyg_amount


def _numeric_sum(sheet: SheetSnapshot, column_index: int) -> tuple[Decimal, list[int]]:
    total = Decimal(0)
    invalid_rows: list[int] = []
    for row in sheet.rows:
        value = row.values.get(column_index)
        amount = try_parse_pyg_amount(value)
        if amount is not None:
            total += amount
        elif value not in (None, "") or column_index in row.formulas:
            invalid_rows.append(row.row_number)
    return total, invalid_rows


def diff_control_totals(
    sheet_name: str,
    base_sheet: SheetSnapshot,
    current_sheet: SheetSnapshot,
    columns: list[str],
) -> tuple[list[Difference], dict]:
    base_cols = named_column_index(base_sheet)
    current_cols = named_column_index(current_sheet)

    diffs: list[Difference] = []
    results: dict[str, dict] = {}

    for column in columns:
        base_idx = base_cols.get(column)
        current_idx = current_cols.get(column)
        if base_idx is None or current_idx is None:
            results[column] = {
                "status": "COLUMN_NOT_FOUND",
                "base_total": None,
                "current_total": None,
            }
            missing_in = []
            if base_idx is None:
                missing_in.append("BASE")
            if current_idx is None:
                missing_in.append("CURRENT")
            diffs.append(
                Difference(
                    kind=DiffKind.CONTROL_TOTAL_COLUMN_MISSING,
                    sheet=sheet_name,
                    column=column,
                    location=(
                        f"Hoja '{sheet_name}', columna de total configurada no encontrada: "
                        f"'{column}'"
                    ),
                    detail=f"Columna ausente en {', '.join(missing_in)}.",
                )
            )
            continue

        base_total, invalid_base = _numeric_sum(base_sheet, base_idx)
        current_total, invalid_current = _numeric_sum(current_sheet, current_idx)
        matches = base_total == current_total
        results[column] = {
            "status": (
                "INVALID_VALUES"
                if invalid_base or invalid_current
                else "MATCH"
                if matches
                else "MISMATCH"
            ),
            "base_total": str(base_total),
            "current_total": str(current_total),
            "invalid_rows_base": invalid_base,
            "invalid_rows_current": invalid_current,
        }
        if invalid_base or invalid_current:
            diffs.append(
                Difference(
                    kind=DiffKind.CONTROL_TOTAL_INVALID_VALUE,
                    sheet=sheet_name,
                    column=column,
                    location=(
                        f"Hoja '{sheet_name}', total de control no confiable en columna "
                        f"'{column}'"
                    ),
                    detail=(
                        f"Filas no numéricas/cache ausente en BASE: {invalid_base or 'ninguna'}; "
                        f"CURRENT: {invalid_current or 'ninguna'}."
                    ),
                )
            )
        if not matches:
            diffs.append(
                Difference(
                    kind=DiffKind.CONTROL_TOTAL_MISMATCH,
                    sheet=sheet_name,
                    column=column,
                    location=f"Hoja '{sheet_name}', total de control columna '{column}'",
                    base_value=str(base_total),
                    current_value=str(current_total),
                    detail=f"Diferencia: {current_total - base_total}",
                )
            )

    return diffs, results
