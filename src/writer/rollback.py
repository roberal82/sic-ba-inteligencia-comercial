"""Rollback real por run_id (Fase D).

Reglas duras:
- Identifica exactamente el ``run_id``; nunca toca operaciones de otro run.
- Antes de restaurar nada, verifica que el estado actual de CADA operación
  coincida con el ``after_fingerprint`` grabado. Si algo cambió externamente
  después del apply, el rollback completo falla cerrado (``REQUIRES_HUMAN_REVIEW``)
  y no se restaura ninguna operación, ni siquiera las que sí coinciden.
- Es idempotente: si el run ya está ``ROLLED_BACK``, repetir la llamada no
  vuelve a tocar el adaptador y devuelve el mismo resultado.
"""

from __future__ import annotations

from pathlib import Path

from ..orchestration.stage_store import sha256_json
from .adapters import ProductionAdapter
from .models import RunResult, RunStatus
from .store import WriterRunStore


class RollbackError(RuntimeError):
    pass


def _fingerprint(state) -> str | None:
    if state is None:
        return None
    return sha256_json(state)


def rollback_run(store_root: Path, run_id: str, adapter: ProductionAdapter) -> RunResult:
    store = WriterRunStore(store_root)
    meta = store.read_meta(run_id)
    if meta is None:
        raise RollbackError(f"run_id desconocido: {run_id!r}")

    if meta.get("status") == RunStatus.ROLLED_BACK.value:
        cached = store.read_result(run_id)
        result = RunResult.from_dict(cached) if cached else RunResult(
            run_id=run_id, mode="ROLLBACK", status=RunStatus.ROLLED_BACK.value, created=False
        )
        store.append_audit(run_id, {"event": "ROLLBACK_REPLAYED_IDEMPOTENT"})
        return result

    operations = store.read_operations(run_id)
    if not operations:
        result = RunResult(run_id=run_id, mode="ROLLBACK", status=RunStatus.ROLLED_BACK.value, created=True, operations=())
        store.set_status(run_id, RunStatus.ROLLED_BACK.value)
        store.write_result(run_id, result.as_dict())
        store.append_audit(run_id, {"event": "ROLLBACK_COMPLETED", "reason": "no_operations_to_revert"})
        return result

    mismatches: list[str] = []
    for record in operations:
        if record.after_fingerprint is None:
            continue
        current = adapter.read(record.target, record.key)
        if _fingerprint(current) != record.after_fingerprint:
            mismatches.append(record.op_id)

    if mismatches:
        result = RunResult(
            run_id=run_id,
            mode="ROLLBACK",
            status=RunStatus.REQUIRES_HUMAN_REVIEW.value,
            created=True,
            operations=tuple(operations),
            reasons=(f"Modificación externa detectada tras el apply en: {mismatches}",),
        )
        store.set_status(run_id, RunStatus.REQUIRES_HUMAN_REVIEW.value)
        store.write_result(run_id, result.as_dict())
        store.append_audit(
            run_id,
            {"event": "ROLLBACK_BLOCKED_CONCURRENT_MODIFICATION", "op_ids": mismatches},
        )
        return result

    for record in reversed(operations):
        adapter.restore(record.target, record.key, record.before_state)
        restored = adapter.read(record.target, record.key)
        if _fingerprint(restored) != record.before_fingerprint:
            result = RunResult(
                run_id=run_id,
                mode="ROLLBACK",
                status=RunStatus.REQUIRES_HUMAN_REVIEW.value,
                created=True,
                operations=tuple(operations),
                reasons=(f"Verificación de checksum falló al restaurar {record.op_id}.",),
            )
            store.set_status(run_id, RunStatus.REQUIRES_HUMAN_REVIEW.value)
            store.write_result(run_id, result.as_dict())
            store.append_audit(
                run_id,
                {"event": "ROLLBACK_CHECKSUM_MISMATCH", "op_id": record.op_id},
            )
            return result
        store.append_audit(run_id, {"event": "OPERATION_ROLLED_BACK", "op_id": record.op_id})

    result = RunResult(run_id=run_id, mode="ROLLBACK", status=RunStatus.ROLLED_BACK.value, created=True, operations=tuple(operations))
    store.set_status(run_id, RunStatus.ROLLED_BACK.value)
    store.write_result(run_id, result.as_dict())
    store.append_audit(run_id, {"event": "ROLLBACK_COMPLETED"})
    return result
