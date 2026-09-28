"""Normalización de valores de celda para comparación semántica.

Objetivo: que "15/03/2024" (texto) y datetime(2024, 3, 15) se comparen como el
mismo valor, y que "1.234.567" (texto, formato PYG) y 1234567 (número) se
comparen como el mismo importe. La diferencia de *tipo* (texto vs número) se
reporta por separado (ver `classify.py`, DiffKind.TYPE_CHANGED); nunca se
descarta silenciosamente.
"""

from __future__ import annotations

import datetime as _dt
import re
from decimal import Decimal, InvalidOperation
from typing import Any

_DATE_FORMATS = ("%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%Y-%m-%d", "%Y/%m/%d")
_DATE_LIKE_RE = re.compile(r"^\d{1,4}[/-]\d{1,2}[/-]\d{1,4}$")
_PYG_CURRENCY_RE = re.compile(r"(?i)^\s*(gs\.?|₲)\s*")
_THOUSANDS_DOT_RE = re.compile(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$")
_PLAIN_NUMBER_RE = re.compile(r"^-?\d+(\.\d+)?$")


def try_parse_date(value: Any) -> _dt.date | None:
    if isinstance(value, _dt.datetime):
        return value.date()
    if isinstance(value, _dt.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text or not _DATE_LIKE_RE.match(text):
            return None
        for fmt in _DATE_FORMATS:
            try:
                return _dt.datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    return None


def try_parse_pyg_amount(value: Any) -> Decimal | None:
    """Interpreta importes en Guaraníes: sin decimales habituales, separador de
    miles con punto (ej. "1.234.567") y prefijos opcionales "Gs." o "₲"."""

    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        text = _PYG_CURRENCY_RE.sub("", text)
        text = text.replace(" ", "")
        if not text:
            return None
        if _THOUSANDS_DOT_RE.match(text):
            normalized = text.replace(".", "").replace(",", ".")
            try:
                return Decimal(normalized)
            except InvalidOperation:
                return None
        if _PLAIN_NUMBER_RE.match(text):
            try:
                return Decimal(text)
            except InvalidOperation:
                return None
    return None


def detect_type(value: Any) -> str:
    if value is None:
        return "empty"
    if isinstance(value, str) and value.strip() == "":
        return "empty"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (_dt.datetime, _dt.date)):
        return "date"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        if try_parse_date(value) is not None:
            return "date_text"
        if try_parse_pyg_amount(value) is not None:
            return "amount_text"
        return "text"
    return "other"


def normalize_for_compare(value: Any) -> Any:
    """Representación canónica usada solo para *comparar* BASE vs CURRENT."""

    kind = detect_type(value)
    if kind == "empty":
        return None
    if kind == "bool":
        return bool(value)
    if kind == "date":
        parsed = try_parse_date(value)
        return parsed.isoformat() if parsed else value
    if kind == "date_text":
        parsed = try_parse_date(value)
        return parsed.isoformat() if parsed else value
    if kind in ("int", "float"):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return value
    if kind == "amount_text":
        amount = try_parse_pyg_amount(value)
        return amount if amount is not None else value
    if kind == "text":
        return value.strip()
    return value


def raw_type_label(value: Any) -> str:
    if value is None:
        return "NoneType"
    return type(value).__name__
