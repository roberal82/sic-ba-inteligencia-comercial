"""Constructores de workbooks Excel sintéticos para tests de ERP_DIFF_ENGINE.

Todos los datos son inventados exclusivamente para pruebas. Ningún nombre,
importe o fecha proviene de Blanco & Asociados ni de ninguna copia real del
ERP (ver AGENTS.md).
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import openpyxl
import xlsxwriter

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


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


def _sheet_part_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    """Resuelve el nombre de hoja al part XML real (xl/worksheets/sheetN.xml)
    siguiendo xl/workbook.xml -> xl/_rels/workbook.xml.rels, en vez de asumir
    un nombre de archivo fijo."""

    wb_root = ET.fromstring(zf.read("xl/workbook.xml"))
    sheets_el = wb_root.find(f"{{{_MAIN_NS}}}sheets")
    rid = None
    for sheet_el in sheets_el.findall(f"{{{_MAIN_NS}}}sheet"):
        if sheet_el.get("name") == sheet_name:
            rid = sheet_el.get(f"{{{_REL_NS}}}id")
            break
    if rid is None:
        raise ValueError(f"hoja no encontrada en workbook.xml: {sheet_name}")

    rels_root = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    for rel_el in rels_root.findall(f"{{{_PKG_REL_NS}}}Relationship"):
        if rel_el.get("Id") == rid:
            target = rel_el.get("Target", "")
            if target.startswith("/"):
                return target.lstrip("/")
            if target.startswith("xl/"):
                return target
            return f"xl/{target}"
    raise ValueError(f"relationship no encontrado para rid: {rid}")


def corrupt_sheet_dimension(
    path: Path,
    sheet_name: str,
    *,
    dimension: str,
    trailing_empty_rows_to: int | None = None,
    empty_row_spans: str = "1:16",
) -> None:
    """Reescribe el ``<dimension ref="...">`` de una hoja ya guardada para
    reproducir el bug real reportado (openpyxl ``read_only=True`` confía
    ciegamente en ese tag; ver docstring de ``loader.py``). Nunca toca el
    contenido real de ``<sheetData>`` salvo, opcionalmente, para agregar
    filas físicamente vacías (``trailing_empty_rows_to``), replicando el
    padding de filas vacías que algunos exportadores (Google Sheets) dejan
    hasta un límite declarado.

    Usado solo para construir fixtures de test; nunca se usa contra archivos
    de entrada reales del motor.
    """

    with zipfile.ZipFile(path, "r") as zf:
        names = zf.namelist()
        sheet_part = _sheet_part_path(zf, sheet_name)
        original = zf.read(sheet_part).decode("utf-8")
        others = {n: zf.read(n) for n in names if n != sheet_part}

    updated, count = re.subn(
        r'<dimension ref="[^"]*"\s*/>', f'<dimension ref="{dimension}"/>', original, count=1
    )
    if count == 0:
        raise ValueError(f"no se encontró <dimension> en el XML de la hoja '{sheet_name}'")

    if trailing_empty_rows_to is not None:
        row_numbers = [int(m.group(1)) for m in re.finditer(r'<row r="(\d+)"', updated)]
        last_row = max(row_numbers) if row_numbers else 0
        stub_rows = "".join(
            f'<row r="{r}" spans="{empty_row_spans}"/>'
            for r in range(last_row + 1, trailing_empty_rows_to + 1)
        )
        updated = updated.replace("</sheetData>", stub_rows + "</sheetData>", 1)

    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in others.items():
            zf.writestr(name, data)
        zf.writestr(sheet_part, updated)
