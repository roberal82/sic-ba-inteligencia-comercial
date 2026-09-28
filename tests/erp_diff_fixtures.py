"""Constructores de workbooks Excel sintéticos para tests de ERP_DIFF_ENGINE.

Todos los datos son inventados exclusivamente para pruebas. Ningún nombre,
importe o fecha proviene de Blanco & Asociados ni de ninguna copia real del
ERP (ver AGENTS.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import openpyxl
import xlsxwriter


def write_openpyxl_workbook(path: Path, sheets: dict[str, dict[str, Any]]) -> None:
    """``sheets``: {nombre_hoja: {"headers": [...], "rows": [[...], ...]}}."""

    workbook = openpyxl.Workbook()
    names = list(sheets.keys())
    if not names:
        workbook.save(str(path))
        return

    default_ws = workbook.active
    for index, name in enumerate(names):
        ws = default_ws if index == 0 else workbook.create_sheet(title=name)
        if index == 0:
            ws.title = name
        spec = sheets[name]
        headers = spec.get("headers", [])
        if headers:
            ws.append(list(headers))
        for row in spec.get("rows", []):
            ws.append(list(row))
    workbook.save(str(path))


def write_workbook_with_offset_header(path: Path, sheets: dict[str, dict[str, Any]]) -> None:
    """``sheets``: {nombre_hoja: {"leading_rows": [[...], ...], "headers": [...], "rows": [[...], ...]}}.

    Simula layouts reales de ERP con filas de título/subtítulo antes del
    encabezado de datos (Fase B1-R2 / ``header_rows`` por hoja). Sin
    ``leading_rows`` se comporta igual que ``write_openpyxl_workbook``.
    """

    workbook = openpyxl.Workbook()
    names = list(sheets.keys())
    if not names:
        workbook.save(str(path))
        return

    default_ws = workbook.active
    for index, name in enumerate(names):
        ws = default_ws if index == 0 else workbook.create_sheet(title=name)
        if index == 0:
            ws.title = name
        spec = sheets[name]
        for leading_row in spec.get("leading_rows", []):
            ws.append(list(leading_row))
        headers = spec.get("headers", [])
        if headers:
            ws.append(list(headers))
        for row in spec.get("rows", []):
            ws.append(list(row))
    workbook.save(str(path))


def write_formula_workbook(
    path: Path,
    sheet_name: str,
    headers: list[str],
    rows: list[list[Any]],
    leading_rows: list[list[Any]] | None = None,
) -> None:
    """Escribe un workbook con fórmulas y su valor calculado (cacheado).

    ``rows``: cada celda es un valor literal, o una tupla ``(formula, cached_value)``
    para simular una celda con fórmula tal como la guardaría Excel (openpyxl no
    calcula fórmulas ni cachea su resultado, por eso se usa xlsxwriter aquí).

    ``leading_rows`` (opcional): filas de título/subtítulo antes del
    encabezado, para probar ``header_rows`` desplazado (Fase B1-R2).
    """

    workbook = xlsxwriter.Workbook(str(path))
    ws = workbook.add_worksheet(sheet_name)
    row_cursor = 0
    for leading_row in leading_rows or []:
        for col, value in enumerate(leading_row):
            ws.write(row_cursor, col, value)
        row_cursor += 1
    header_row_index = row_cursor
    for col, header in enumerate(headers):
        ws.write(header_row_index, col, header)
    row_cursor = header_row_index + 1
    for row in rows:
        for col, value in enumerate(row):
            if isinstance(value, tuple):
                formula, cached_value = value
                ws.write_formula(row_cursor, col, formula, None, cached_value)
            else:
                ws.write(row_cursor, col, value)
        row_cursor += 1
    workbook.close()
