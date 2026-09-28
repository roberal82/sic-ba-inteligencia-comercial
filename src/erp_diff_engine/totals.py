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


def _numeric_sum(sheet: SheetSnapshot, column_index: int) -> Decimal:
    total = Decimal(0)
    for row in sheet.rows:
        amount = try_parse_pyg_amount(row.values.get(column_index))
        if amount is not None:
            total += amount
    return total


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
            continue

        base_total = _numeric_sum(base_sheet, base_idx)
        current_total = _numeric_sum(current_sheet, current_idx)
        matches = base_total == current_total
        results[column] = {
            "status": "MATCH" if matches else "MISMATCH",
            "base_total": str(base_total),
            "current_total": str(current_total),
        }
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
