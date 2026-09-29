from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

from .adapters import CsvSnapshot, CsvSourceSpec, SourceAdapterError, read_csv_snapshot
from .models import Mode
from .runner import run_manifest
from .stage_store import StageRunStore, StageStoreError, canonical_json, sha256_json


# Solo disponibilidad física/estructural puede derivarse automáticamente de una
# fuente read-only. Evidencia de resolución, relaciones, costos, BI y finanzas
# requiere validación explícita y nunca se promueve por mera presencia de archivo.
SOURCE_DERIVED_INPUTS = frozenset(
    {
        "sales_ready",
        "purchases_ready",
        "pipeline_ready",
        "documents_ready",
    }
)


class OperationalRunError(RuntimeError):
    pass


def _parse_sources(manifest: dict[str, Any]) -> tuple[CsvSourceSpec, ...]:
    raw_sources = manifest.get("sources", {}) or {}
    if not isinstance(raw_sources, dict):
        raise OperationalRunError("manifest.sources debe ser un objeto JSON.")

    specs: list[CsvSourceSpec] = []
    for name in sorted(raw_sources):
        try:
            spec = CsvSourceSpec.from_mapping(name, raw_sources[name])
        except SourceAdapterError as exc:
            raise OperationalRunError(str(exc)) from exc
        if spec.sets_input and spec.sets_input not in SOURCE_DERIVED_INPUTS:
            raise OperationalRunError(
                f"sources.{name}.sets_input={spec.sets_input!r} no puede derivarse automáticamente."
            )
        specs.append(spec)
    return tuple(specs)


def _load_snapshots(
    source_root: Path,
    specs: tuple[CsvSourceSpec, ...],
) -> dict[str, CsvSnapshot | None]:
    snapshots: dict[str, CsvSnapshot | None] = {}
    for spec in specs:
        try:
            snapshots[spec.name] = read_csv_snapshot(source_root, spec)
        except SourceAdapterError as exc:
            raise OperationalRunError(str(exc)) from exc
    return snapshots


def _execution_fingerprint(
    manifest: dict[str, Any], snapshots: dict[str, CsvSnapshot | None]
) -> str:
    source_hashes = {
        name: None if snapshot is None else snapshot.sha256
        for name, snapshot in sorted(snapshots.items())
    }
    return sha256_json({"manifest": manifest, "source_hashes": source_hashes})


def _manifest_summary(manifest: dict[str, Any], specs: tuple[CsvSourceSpec, ...]) -> dict[str, Any]:
    """Resumen sin rutas ni datos de negocio para metadata del run."""
    return {
        "run_id": str(manifest.get("run_id", "")),
        "source_names": [spec.name for spec in specs],
        "declared_inputs": sorted((manifest.get("inputs", {}) or {}).keys()),
        "declared_gates": sorted((manifest.get("gates", {}) or {}).keys()),
    }


def run_operational_stage(
    manifest: dict[str, Any],
    mode: Mode,
    source_root: Path,
    stage_root: Path,
) -> dict[str, Any]:
    """Ejecuta Sprint 002 contra fuentes locales read-only y staging aislado.

    Esta función no contiene adaptadores productivos. Incluso en ``Mode.APPLY``
    solo lee fuentes y escribe en ``stage_root``. Si todos los gates productivos
    llegaran a PASS, el resultado queda bloqueado explícitamente porque el
    adaptador productivo no existe en este sprint.
    """

    if not isinstance(manifest, dict):
        raise OperationalRunError("El manifest debe ser un objeto JSON.")

    run_id = str(manifest.get("run_id", "")).strip()
    if not run_id:
        raise OperationalRunError("manifest.run_id es obligatorio para Sprint 002.")

    inputs = manifest.get("inputs", {}) or {}
    gates = manifest.get("gates", {}) or {}
    if not isinstance(inputs, dict):
        raise OperationalRunError("manifest.inputs debe ser un objeto JSON.")
    if not isinstance(gates, dict):
        raise OperationalRunError("manifest.gates debe ser un objeto JSON.")

    specs = _parse_sources(manifest)
    snapshots = _load_snapshots(source_root, specs)
    fingerprint = _execution_fingerprint(manifest, snapshots)

    store = StageRunStore(stage_root)
    try:
        run_dir, created = store.begin(
            run_id,
            fingerprint,
            _manifest_summary(manifest, specs),
        )
    except StageStoreError as exc:
        raise OperationalRunError(str(exc)) from exc

    effective_inputs = dict(inputs)
    stats_by_domain: dict[str, dict[str, Any]] = {}
    audit_events: list[dict[str, Any]] = [
        {"event": "RUN_STARTED", "run_id": run_id, "mode": mode.value}
    ]

    for spec in specs:
        snapshot = snapshots[spec.name]
        if snapshot is None:
            stats_by_domain[spec.name] = {
                "domain": spec.name,
                "source_rows": 0,
                "staged_rows": 0,
                "quarantined_rows": 0,
                "exact_duplicates": 0,
                "source_sha256": None,
                "missing_optional_source": True,
            }
            if spec.sets_input:
                effective_inputs[spec.sets_input] = False
            audit_events.append(
                {"event": "SOURCE_OPTIONAL_MISSING", "source": spec.name}
            )
            continue

        try:
            stats = store.stage_snapshot(run_id, spec.name, snapshot, spec.key_fields)
        except StageStoreError as exc:
            raise OperationalRunError(str(exc)) from exc

        stats_by_domain[spec.name] = stats.as_dict()
        if spec.sets_input:
            effective_inputs[spec.sets_input] = stats.staged_rows > 0

        audit_events.append(
            {
                "event": "SOURCE_STAGED",
                "source": spec.name,
                "source_rows": stats.source_rows,
                "staged_rows": stats.staged_rows,
                "quarantined_rows": stats.quarantined_rows,
                "exact_duplicates": stats.exact_duplicates,
                "source_sha256": stats.source_sha256,
            }
        )

    gate_manifest = deepcopy(manifest)
    gate_manifest.pop("sources", None)
    gate_manifest["inputs"] = effective_inputs
    gate_result = run_manifest(gate_manifest, mode)

    quarantine_total = sum(
        int(row.get("quarantined_rows", 0)) for row in stats_by_domain.values()
    )

    overall = gate_result["overall"]
    if mode is Mode.APPLY and gate_result.get("production_ready", False):
        overall = "BLOCKED_PRODUCTION_ADAPTER_MISSING"
    elif overall == "PASS" and quarantine_total:
        overall = "PASS_WITH_EXCEPTIONS"

    result = {
        "run_id": run_id,
        "mode": mode.value,
        "overall": overall,
        "created": created,
        "run_dir": str(run_dir),
        "execution_fingerprint": fingerprint,
        "external_writes": False,
        "production_adapter_present": False,
        "source_stats": stats_by_domain,
        "quarantine_total": quarantine_total,
        "effective_inputs": effective_inputs,
        "gate_result": gate_result,
    }

    audit_events.extend(
        [
            {
                "event": "GATES_EVALUATED",
                "overall": gate_result["overall"],
                "production_ready": bool(gate_result.get("production_ready", False)),
            },
            {
                "event": "RUN_COMPLETED",
                "overall": overall,
                "quarantine_total": quarantine_total,
                "external_writes": False,
            },
        ]
    )
    store.write_audit(run_id, audit_events)
    store.write_result(run_id, result)
    store.mark_completed(run_id, overall)
    return result


def rollback_operational_run(stage_root: Path, run_id: str) -> bool:
    try:
        return StageRunStore(stage_root).rollback(run_id)
    except StageStoreError as exc:
        raise OperationalRunError(str(exc)) from exc
