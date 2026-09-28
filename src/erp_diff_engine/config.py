"""Carga y validación de la configuración del ERP_DIFF_ENGINE.

Fuentes admitidas (SPRINT_001_ERP_DRIFT.md): CLI o archivo de configuración
JSON. Ninguna ruta privada, credencial o dato empresarial se hardcodea aquí:
todo viene de lo que el usuario indique al ejecutar el motor.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Classification, DiffKind, EngineConfig, ExpectedRule
from .security import EngineInputError, require_existing_file


def _normalize_str_list_map(raw: Any, field_name: str) -> dict[str, list[str]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise EngineInputError(f"'{field_name}' debe ser un objeto {{hoja: [columnas]}}.")
    result: dict[str, list[str]] = {}
    for sheet, columns in raw.items():
        if not isinstance(columns, list):
            raise EngineInputError(f"'{field_name}.{sheet}' debe ser una lista de columnas.")
        result[str(sheet)] = [str(c) for c in columns]
    return result


def _parse_expected_rule(raw: Any) -> ExpectedRule:
    if not isinstance(raw, dict) or "kind" not in raw:
        raise EngineInputError(f"expected_rules: entrada inválida {raw!r} (falta 'kind').")
    try:
        kind = DiffKind(raw["kind"])
    except ValueError as exc:
        raise EngineInputError(f"expected_rules: kind inválido {raw.get('kind')!r}.") from exc
    return ExpectedRule(
        kind=kind,
        sheet=raw.get("sheet"),
        column=raw.get("column"),
        row_key=raw.get("row_key"),
        note=str(raw.get("note", "")),
    )


def _parse_header_rows(raw: Any) -> dict[str, int]:
    """Parsea 'header_rows': {hoja: fila_encabezado (1-based)}.

    Solo valida aquí lo que no depende del contenido del workbook (tipo entero
    y límite inferior). El límite superior (fila de encabezado <= máximo de
    filas de la hoja) se valida en loader.py, porque el máximo de filas solo
    se conoce al abrir el archivo. Ver AGENTS.md: sin inferencia silenciosa de
    encabezados, y sin hardcodear nombres de hoja en la lógica del motor.
    """

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise EngineInputError("'header_rows' debe ser un objeto {hoja: fila_encabezado}.")
    result: dict[str, int] = {}
    for sheet, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise EngineInputError(
                f"'header_rows.{sheet}' debe ser un entero >= 1 (recibido {value!r})."
            )
        if value < 1:
            raise EngineInputError(
                f"'header_rows.{sheet}' debe ser >= 1 (recibido {value})."
            )
        result[str(sheet)] = value
    return result


def _parse_data_start_rows(raw: Any, header_rows: dict[str, int]) -> dict[str, int]:
    """Parsea 'data_start_rows': {hoja: primera_fila_de_datos (1-based)}.

    Opcional por hoja (AGENTS.md: sin inferencia automática de filas
    plantilla). Si no está declarada, loader.py usa header_row + 1
    (compatibilidad hacia atrás). Aquí se valida el límite estructural
    (entero >= header_row + 1, usando header_rows.get(hoja, 1) como fila de
    encabezado efectiva para esa hoja). El límite superior (fuera del
    contenido físico real del workbook) se valida en loader.py, igual que
    header_rows, porque el contenido real solo se conoce al abrir el
    archivo.
    """

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise EngineInputError(
            "'data_start_rows' debe ser un objeto {hoja: fila_inicio_datos}."
        )
    result: dict[str, int] = {}
    for sheet, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise EngineInputError(
                f"'data_start_rows.{sheet}' debe ser un entero >= 1 (recibido {value!r})."
            )
        effective_header_row = header_rows.get(str(sheet), 1)
        min_allowed = effective_header_row + 1
        if value < min_allowed:
            raise EngineInputError(
                f"'data_start_rows.{sheet}' ({value}) debe ser >= header_row + 1 "
                f"({min_allowed})."
            )
        result[str(sheet)] = value
    return result


_VALID_ROW_MATCH_MODES = {"keyed", "positional", "multiset"}


def _parse_row_match_modes(raw: Any) -> dict[str, str]:
    """Parsea 'row_match_modes': {hoja: "keyed"|"positional"|"multiset"}.

    Opcional por hoja. Una hoja no declarada aquí conserva el comportamiento
    histórico (keyed si tiene primary_keys, positional si no). Solo "multiset"
    cambia el comportamiento por defecto, y únicamente si se declara aquí de
    forma explícita (hotfix Sprint 001, MULTISET_EVENT_MATCHING, regla #3: "no
    hardcodear nombres empresariales en el motor" y "multiset solo se activa
    explícitamente por configuración").
    """

    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise EngineInputError("'row_match_modes' debe ser un objeto {hoja: modo}.")
    result: dict[str, str] = {}
    for sheet, value in raw.items():
        if not isinstance(value, str) or value not in _VALID_ROW_MATCH_MODES:
            raise EngineInputError(
                f"'row_match_modes.{sheet}' inválido ({value!r}); valores permitidos: "
                f"{sorted(_VALID_ROW_MATCH_MODES)}."
            )
        result[str(sheet)] = value
    return result


def _parse_multiset_columns(
    raw: Any, row_match_modes: dict[str, str]
) -> dict[str, list[str]]:
    """Parsea 'multiset_columns': {hoja: [columnas]}.

    Requerida (no vacía) para toda hoja con row_match_modes[hoja] == "multiset"
    (fail closed: configuración parcial es un error de configuración, no un
    comportamiento inferido). Se ignora para cualquier otra hoja.
    """

    result = _normalize_str_list_map(raw, "multiset_columns")
    for sheet, mode in row_match_modes.items():
        if mode != "multiset":
            continue
        columns = result.get(sheet)
        if not columns:
            raise EngineInputError(
                f"'row_match_modes.{sheet}' = 'multiset' requiere 'multiset_columns.{sheet}' "
                "con al menos una columna."
            )
    return result


def _parse_severity_overrides(raw: Any) -> dict[DiffKind, Classification]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise EngineInputError("'severity_overrides' debe ser un objeto {DIFF_KIND: CLASIFICACION}.")
    result: dict[DiffKind, Classification] = {}
    for key, value in raw.items():
        try:
            kind = DiffKind(key)
            classification = Classification(value)
        except ValueError as exc:
            raise EngineInputError(
                f"severity_overrides inválido: {key!r} -> {value!r} ({exc})."
            ) from exc
        if classification is Classification.EXPECTED:
            raise EngineInputError(
                "severity_overrides no puede asignar EXPECTED; "
                "declare una regla específica en expected_rules."
            )
        result[kind] = classification
    return result


def load_config(config_path: Path | None, overrides: dict[str, Any]) -> EngineConfig:
    """Combina archivo de configuración (opcional) + overrides de CLI.

    Los overrides de CLI (valores no ``None``) tienen prioridad sobre el
    archivo de configuración.
    """

    payload: dict[str, Any] = {}
    if config_path is not None:
        resolved = require_existing_file(config_path, "Config")
        try:
            with resolved.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except json.JSONDecodeError as exc:
            raise EngineInputError(f"Config JSON inválido ({resolved}): {exc}") from exc
        if not isinstance(payload, dict):
            raise EngineInputError("El archivo de configuración debe ser un objeto JSON.")

    merged: dict[str, Any] = dict(payload)
    for key, value in overrides.items():
        if value is not None:
            merged[key] = value

    base_path = merged.get("base_path")
    current_path = merged.get("current_path")
    output_dir = merged.get("output_dir")
    if not base_path or not current_path or not output_dir:
        raise EngineInputError(
            "Se requieren base_path, current_path y output_dir "
            "(por CLI --base/--current/--output o por archivo de configuración)."
        )

    log_file = merged.get("log_file")

    header_rows = _parse_header_rows(merged.get("header_rows"))
    row_match_modes = _parse_row_match_modes(merged.get("row_match_modes"))

    return EngineConfig(
        base_path=Path(base_path),
        current_path=Path(current_path),
        output_dir=Path(output_dir),
        primary_keys=_normalize_str_list_map(merged.get("primary_keys"), "primary_keys"),
        control_totals=_normalize_str_list_map(merged.get("control_totals"), "control_totals"),
        sensitive_columns=_normalize_str_list_map(
            merged.get("sensitive_columns"), "sensitive_columns"
        ),
        row_match_modes=row_match_modes,
        multiset_columns=_parse_multiset_columns(merged.get("multiset_columns"), row_match_modes),
        expected_rules=tuple(
            _parse_expected_rule(r) for r in (merged.get("expected_rules") or [])
        ),
        severity_overrides=_parse_severity_overrides(merged.get("severity_overrides")),
        header_rows=header_rows,
        data_start_rows=_parse_data_start_rows(merged.get("data_start_rows"), header_rows),
        log_file=Path(log_file) if log_file else None,
    )
