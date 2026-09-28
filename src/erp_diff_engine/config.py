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

    return EngineConfig(
        base_path=Path(base_path),
        current_path=Path(current_path),
        output_dir=Path(output_dir),
        primary_keys=_normalize_str_list_map(merged.get("primary_keys"), "primary_keys"),
        control_totals=_normalize_str_list_map(merged.get("control_totals"), "control_totals"),
        sensitive_columns=_normalize_str_list_map(
            merged.get("sensitive_columns"), "sensitive_columns"
        ),
        expected_rules=tuple(
            _parse_expected_rule(r) for r in (merged.get("expected_rules") or [])
        ),
        severity_overrides=_parse_severity_overrides(merged.get("severity_overrides")),
        log_file=Path(log_file) if log_file else None,
    )
