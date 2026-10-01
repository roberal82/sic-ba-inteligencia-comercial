"""Rollback seguro por run_id.

Se hace un precheck global y, además, cada restauración usa compare-and-swap.
Así se cierra la carrera entre el precheck y el restore: si otro actor modifica
el registro en ese intervalo, el rollback no lo sobrescribe.

Runs STAGE/DRY_RUN no son rollbackeables contra el adaptador. Operaciones
APPLY_IN_PROGRESS con resultado desconocido solo se consideran seguras si el
estado actual todavía coincide con el estado anterior; de lo contrario quedan
en REQUIRES_HUMAN_REVIEW.
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


def _blocked_result(
    store: WriterRunStore,
    run_id: str,
    operations,
    reason: str,
    event: str,
    **audit,
) -> RunResult:
    result = RunResult(
        run_id=run_id,
        mode="ROLLBACK",
        status=RunStatus.REQUIRES_HUMAN_REVIEW.value,
        created=True,
        operations=tuple(operations),
        reasons=(reason,),
    )
    store.set_status(run_id, RunStatus.REQUIRES_HUMAN_REVIEW.value)
    store.write_result(run_id, result.as_dict())
    store.append_audit(run_id, {"event": event, **audit})
    return result


def rollback_run(
    store_root: Path, run_id: str, adapter: ProductionAdapter
) -> RunResult:
    store = WriterRunStore(store_root)
    meta = store.read_meta(run_id)
    if meta is None:
        raise RollbackError(f"run_id desconocido: {run_id!r}")

    if meta.get("status") == RunStatus.ROLLED_BACK.value:
        cached = store.read_result(run_id)
        result = (
            RunResult.from_dict(cached)
            if cached
            else RunResult(
                run_id=run_id,
                mode="ROLLBACK",
                status=RunStatus.ROLLED_BACK.value,
                created=False,
            )
        )
        store.append_audit(run_id, {"event": "ROLLBACK_REPLAYED_IDEMPOTENT"})
        return result

    manifest = meta.get("manifest_summary") or {}
    if manifest.get("mode") != "APPLY":
        operations = store.read_operations(run_id)
        return _blocked_result(
            store,
            run_id,
            operations,
            "Rollback contra adaptador solo está permitido para runs APPLY.",
            "ROLLBACK_BLOCKED_NON_APPLY_RUN",
            original_mode=manifest.get("mode"),
        )

    operations = store.read_operations(run_id)
    if not operations:
        result = RunResult(
            run_id=run_id,
            mode="ROLLBACK",
            status=RunStatus.ROLLED_BACK.value,
            created=True,
            operations=(),
        )
        store.set_status(run_id, RunStatus.ROLLED_BACK.value)
        store.write_result(run_id, result.as_dict())
        store.append_audit(
            run_id,
            {"event": "ROLLBACK_COMPLETED", "reason": "no_operations_to_revert"},
        )
        return result

    mismatches: list[str] = []
    unknown: list[str] = []
    no_change_in_progress: set[str] = set()

    # Precheck global: evita empezar un rollback cuando ya existe evidencia de
    # modificación externa. El CAS posterior cierra la carrera restante.
    for record in operations:
        current = adapter.read(record.target, record.key)
        current_fp = _fingerprint(current)

        if record.status == RunStatus.APPLY_IN_PROGRESS.value:
            if current_fp == record.before_fingerprint:
                no_change_in_progress.add(record.op_id)
            else:
                unknown.append(record.op_id)
            continue

        if record.status != "APPLIED" or record.after_fingerprint is None:
            unknown.append(record.op_id)
            continue

        if current_fp != record.after_fingerprint:
            mismatches.append(record.op_id)

    if mismatches or unknown:
        reason_parts = []
        if mismatches:
            reason_parts.append(f"modificación externa detectada: {mismatches}")
        if unknown:
            reason_parts.append(
                f"resultado APPLY desconocido/no reconciliable automáticamente: {unknown}"
            )
        return _blocked_result(
            store,
            run_id,
            operations,
            "; ".join(reason_parts),
            "ROLLBACK_BLOCKED_PRECHECK",
            mismatch_op_ids=mismatches,
            unknown_op_ids=unknown,
        )

    restored_ids: list[str] = []
    for record in reversed(operations):
        if record.op_id in no_change_in_progress:
            store.append_audit(
                run_id,
                {
                    "event": "APPLY_IN_PROGRESS_RECONCILED_NO_CHANGE",
                    "op_id": record.op_id,
                },
            )
            continue

        restored = adapter.compare_and_swap_restore(
            record.target,
            record.key,
            record.after_state,
            record.before_state,
        )
        if not restored:
            return _blocked_result(
                store,
                run_id,
                operations,
                (
                    f"CAS rechazó restore de {record.op_id}; el estado cambió entre "
                    f"precheck y restore. Operaciones ya restauradas: {restored_ids}"
                ),
                "ROLLBACK_BLOCKED_CAS_RACE",
                op_id=record.op_id,
                restored_op_ids=restored_ids,
            )

        verified = adapter.read(record.target, record.key)
        if _fingerprint(verified) != record.before_fingerprint:
            return _blocked_result(
                store,
                run_id,
                operations,
                f"Verificación de checksum falló al restaurar {record.op_id}.",
                "ROLLBACK_CHECKSUM_MISMATCH",
                op_id=record.op_id,
                restored_op_ids=restored_ids,
            )

        restored_ids.append(record.op_id)
        store.append_audit(
            run_id,
            {"event": "OPERATION_ROLLED_BACK", "op_id": record.op_id},
        )

    result = RunResult(
        run_id=run_id,
        mode="ROLLBACK",
        status=RunStatus.ROLLED_BACK.value,
        created=True,
        operations=tuple(operations),
    )
    store.set_status(run_id, RunStatus.ROLLED_BACK.value)
    store.write_result(run_id, result.as_dict())
    store.append_audit(
        run_id, {"event": "ROLLBACK_COMPLETED", "restored_op_ids": restored_ids}
    )
    return result
