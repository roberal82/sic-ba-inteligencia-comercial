"""Motor del writer productivo.

APPLY permanece fail-closed. Antes de invocar al adaptador se persiste una
operación APPLY_IN_PROGRESS. Si el proceso cae en una zona donde el resultado
de la escritura es desconocido, el mismo run_id no se reintenta a ciegas:
queda en REQUIRES_HUMAN_REVIEW y debe reconciliarse/rollbackearse.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..orchestration.stage_store import sha256_json
from .adapters import ProductionAdapter, WriterPermanentError, WriterTransientError
from .models import OperationRecord, OperationSpec, RunResult, RunStatus, WriteMode, WriterInterlock
from .store import WriterRunConflict, WriterRunStore


class WriterValidationError(RuntimeError):
    pass


class WriterTimeoutError(RuntimeError):
    pass


def _fingerprint(state: Mapping[str, object] | None) -> str | None:
    if state is None:
        return None
    return sha256_json(state)


@dataclass
class ProductionWriter:
    store_root: Path
    adapter: ProductionAdapter
    interlock: WriterInterlock
    batch_limit: int = 500
    max_retries: int = 3
    timeout_s: float = 30.0
    sleep_fn: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.monotonic

    def execute(
        self,
        run_id: str,
        operations: Sequence[OperationSpec],
        mode: WriteMode,
    ) -> RunResult:
        if not run_id.strip():
            raise WriterValidationError("run_id es obligatorio.")
        if len(operations) > self.batch_limit:
            raise WriterValidationError(
                f"batch_limit excedido: {len(operations)} > {self.batch_limit}."
            )
        op_ids = [op.op_id for op in operations]
        if len(set(op_ids)) != len(op_ids):
            raise WriterValidationError("op_id duplicado dentro del mismo run.")

        fingerprint = sha256_json(
            {
                "run_id": run_id,
                "mode": mode.value,
                "operations": [
                    {
                        "op_id": op.op_id,
                        "target": op.target,
                        "key": dict(op.key),
                        "payload": dict(op.payload),
                    }
                    for op in operations
                ],
            }
        )

        store = WriterRunStore(self.store_root)
        try:
            _, created = store.begin(
                run_id,
                fingerprint,
                {"mode": mode.value, "operation_count": len(operations)},
            )
        except WriterRunConflict:
            raise

        if not created:
            cached = store.read_result(run_id)
            if cached is not None:
                result = RunResult.from_dict(cached)
                store.append_audit(
                    run_id,
                    {"event": "RUN_REPLAYED_IDEMPOTENT", "status": result.status},
                )
                return result

            if mode is WriteMode.APPLY:
                persisted = tuple(store.read_operations(run_id))
                result = RunResult(
                    run_id=run_id,
                    mode=WriteMode.APPLY.value,
                    status=RunStatus.REQUIRES_HUMAN_REVIEW.value,
                    created=False,
                    operations=persisted,
                    reasons=(
                        "Run APPLY incompleto sin resultado final; no se reintenta una escritura de resultado desconocido.",
                    ),
                )
                store.set_status(run_id, RunStatus.REQUIRES_HUMAN_REVIEW.value)
                store.write_result(run_id, result.as_dict())
                store.append_audit(
                    run_id,
                    {
                        "event": "RUN_REPLAY_BLOCKED_INCOMPLETE_APPLY",
                        "persisted_operations": len(persisted),
                    },
                )
                return result

        store.append_audit(
            run_id,
            {
                "event": "RUN_STARTED",
                "mode": mode.value,
                "operation_count": len(operations),
            },
        )

        if mode is WriteMode.DRY_RUN:
            return self._run_dry(run_id, operations, store)
        if mode is WriteMode.STAGE:
            return self._run_stage(run_id, operations, store)
        return self._run_apply(run_id, operations, store)

    def _run_dry(
        self, run_id: str, operations: Sequence[OperationSpec], store: WriterRunStore
    ) -> RunResult:
        records = tuple(
            OperationRecord(
                op_id=op.op_id,
                target=op.target,
                key=dict(op.key),
                payload_sha256=sha256_json(op.payload),
                before_state=None,
                before_fingerprint=None,
                after_state=None,
                after_fingerprint=None,
                status="SIMULATED",
                attempts=0,
            )
            for op in operations
        )
        result = RunResult(
            run_id=run_id,
            mode=WriteMode.DRY_RUN.value,
            status=RunStatus.SIMULATED.value,
            created=True,
            operations=records,
        )
        store.set_status(run_id, RunStatus.SIMULATED.value)
        store.write_result(run_id, result.as_dict())
        store.append_audit(run_id, {"event": "RUN_COMPLETED", "status": result.status})
        return result

    def _run_stage(
        self, run_id: str, operations: Sequence[OperationSpec], store: WriterRunStore
    ) -> RunResult:
        records = tuple(
            OperationRecord(
                op_id=op.op_id,
                target=op.target,
                key=dict(op.key),
                payload_sha256=sha256_json(op.payload),
                before_state=None,
                before_fingerprint=None,
                after_state=None,
                after_fingerprint=None,
                status="STAGED",
                attempts=0,
            )
            for op in operations
        )
        for record in records:
            store.record_operation(run_id, record)
        result = RunResult(
            run_id=run_id,
            mode=WriteMode.STAGE.value,
            status=RunStatus.STAGED.value,
            created=True,
            operations=records,
        )
        store.set_status(run_id, RunStatus.STAGED.value)
        store.write_result(run_id, result.as_dict())
        store.append_audit(run_id, {"event": "RUN_COMPLETED", "status": result.status})
        return result

    def _run_apply(
        self, run_id: str, operations: Sequence[OperationSpec], store: WriterRunStore
    ) -> RunResult:
        if not self.interlock.apply_authorized:
            reasons = self.interlock.blocking_reasons
            result = RunResult(
                run_id=run_id,
                mode=WriteMode.APPLY.value,
                status=RunStatus.BLOCKED.value,
                created=True,
                reasons=reasons,
            )
            store.set_status(run_id, RunStatus.BLOCKED.value)
            store.write_result(run_id, result.as_dict())
            store.append_audit(
                run_id, {"event": "RUN_BLOCKED", "reasons": list(reasons)}
            )
            return result

        records: list[OperationRecord] = []
        for op in operations:
            try:
                before_state = self._read_with_retry(op)
            except WriterPermanentError as exc:
                return self._finish_partial(run_id, store, records, str(exc))

            before_fp = _fingerprint(before_state)
            pending = OperationRecord(
                op_id=op.op_id,
                target=op.target,
                key=dict(op.key),
                payload_sha256=sha256_json(op.payload),
                before_state=before_state,
                before_fingerprint=before_fp,
                after_state=None,
                after_fingerprint=None,
                status=RunStatus.APPLY_IN_PROGRESS.value,
                attempts=0,
            )
            store.record_operation(run_id, pending)
            store.set_status(
                run_id,
                RunStatus.APPLY_IN_PROGRESS.value,
                active_op_id=op.op_id,
            )
            store.append_audit(
                run_id,
                {
                    "event": "OPERATION_APPLY_IN_PROGRESS",
                    "op_id": op.op_id,
                    "target": op.target,
                },
            )

            try:
                after_state, attempts = self._apply_with_retry(op)
            except (WriterPermanentError, WriterTimeoutError) as exc:
                return self._finish_partial(run_id, store, records, str(exc))

            record = OperationRecord(
                op_id=op.op_id,
                target=op.target,
                key=dict(op.key),
                payload_sha256=sha256_json(op.payload),
                before_state=before_state,
                before_fingerprint=before_fp,
                after_state=after_state,
                after_fingerprint=_fingerprint(after_state),
                status="APPLIED",
                attempts=attempts,
            )
            store.record_operation(run_id, record)
            store.append_audit(
                run_id,
                {
                    "event": "OPERATION_APPLIED",
                    "op_id": op.op_id,
                    "target": op.target,
                    "attempts": attempts,
                },
            )
            records.append(record)

        result = RunResult(
            run_id=run_id,
            mode=WriteMode.APPLY.value,
            status=RunStatus.SUCCESS.value,
            created=True,
            operations=tuple(records),
        )
        store.set_status(run_id, RunStatus.SUCCESS.value, active_op_id=None)
        store.write_result(run_id, result.as_dict())
        store.append_audit(run_id, {"event": "RUN_COMPLETED", "status": result.status})
        return result

    def _finish_partial(
        self,
        run_id: str,
        store: WriterRunStore,
        records: list[OperationRecord],
        error: str,
    ) -> RunResult:
        status = RunStatus.PARTIAL.value if records else RunStatus.FAILED.value
        result = RunResult(
            run_id=run_id,
            mode=WriteMode.APPLY.value,
            status=status,
            created=True,
            operations=tuple(records),
            reasons=(error,),
        )
        store.set_status(run_id, status)
        store.write_result(run_id, result.as_dict())
        store.append_audit(
            run_id,
            {
                "event": "RUN_PARTIAL_FAILURE",
                "status": status,
                "error": error,
                "completed_operations": len(records),
            },
        )
        return result

    def _read_with_retry(self, op: OperationSpec) -> Mapping[str, object] | None:
        attempts = 0
        last_exc: Exception | None = None
        while attempts <= self.max_retries:
            attempts += 1
            try:
                return self.adapter.read(op.target, op.key)
            except WriterTransientError as exc:
                last_exc = exc
                if attempts <= self.max_retries:
                    self.sleep_fn(min(2 ** attempts, 10))
                    continue
                raise WriterPermanentError(
                    f"Lectura falló tras {attempts} intentos: {exc}"
                ) from exc
            except WriterPermanentError:
                raise
            except Exception as exc:
                raise WriterPermanentError(f"Lectura falló: {exc}") from exc
        raise WriterPermanentError(str(last_exc))

    def _apply_with_retry(
        self, op: OperationSpec
    ) -> tuple[Mapping[str, object], int]:
        attempts = 0
        last_exc: Exception | None = None
        while attempts <= self.max_retries:
            attempts += 1
            start = self.clock()
            try:
                after_state = self.adapter.apply(op.target, op.key, op.payload)
            except WriterTransientError as exc:
                last_exc = exc
                if attempts <= self.max_retries:
                    self.sleep_fn(min(2 ** attempts, 10))
                    continue
                raise WriterPermanentError(
                    f"Operación {op.op_id} falló tras {attempts} intentos: {exc}"
                ) from exc
            except WriterPermanentError:
                raise
            except Exception as exc:
                raise WriterPermanentError(
                    f"Operación {op.op_id} falló: {exc}"
                ) from exc
            elapsed = self.clock() - start
            if elapsed > self.timeout_s:
                raise WriterTimeoutError(
                    f"Operación {op.op_id} excedió timeout_s={self.timeout_s} ({elapsed:.2f}s)."
                )
            return after_state, attempts
        raise WriterPermanentError(str(last_exc))
