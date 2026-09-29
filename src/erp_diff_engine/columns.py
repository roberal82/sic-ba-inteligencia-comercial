"""Utilidad compartida: mapa encabezado -> índice de columna (0-based)."""

from __future__ import annotations

from .models import SheetSnapshot


def named_column_index(sheet: SheetSnapshot) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, header in enumerate(sheet.headers):
        if header is None:
            continue
        key = str(header).strip()
        if key and key not in mapping:
            mapping[key] = idx
    return mapping


def common_headers(base_sheet: SheetSnapshot, current_sheet: SheetSnapshot) -> list[str]:
    base_cols = named_column_index(base_sheet)
    current_cols = named_column_index(current_sheet)
    return [h for h in base_cols if h in current_cols]
