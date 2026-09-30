from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class WriteMode(str, Enum):
    DRY_RUN = "DRY_RUN"
    STAGE = "STAGE"
    APPLY = "APPLY"


class RunStatus(str, Enum):
    STARTED = "STARTED"
    SIMULATED = "SIMULATED"
    STAGED = "STAGED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    PARTIAL = "PARTIAL"
    ROLLED_BACK = "ROLLED_BACK"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


@dataclass(frozen=True)
class WriterInterlock:
    """Interlock de producción. Todo default es False/deshabilitado.

    ``APPLY`` solo queda autorizado cuando los siete elementos son verdaderos
    simultáneamente. Ninguna variable de entorno por sí sola habilita nada.
    """

    l4_pass: bool = False
    l7_go: bool = False
    rollback_real_proven: bool = False
    human_approval: bool = False
    cutover_window_authorized: bool = False
    snapshot_ready: bool = False
    production_write_env: str = ""

    @property
    def env_enabled(self) -> bool:
        return self.production_write_env == "ENABLED"

    @property
    def apply_authorized(self) -> bool:
        return not self.blocking_reasons

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        reasons = []
        if not self.l4_pass:
            reasons.append("L4 no está en PASS")
        if not self.l7_go:
            reasons.append("L7 no está en GO")
        if not self.rollback_real_proven:
            reasons.append("rollback_real_proven=false")
        if not self.human_approval:
            reasons.append("human_approval=false")
        if not self.cutover_window_authorized:
            reasons.append("cutover_window_authorized=false")
        if not self.snapshot_ready:
            reasons.append("snapshot_ready=false")
        if not self.env_enabled:
            reasons.append("SIC_BA_PRODUCTION_WRITE != ENABLED")
        return tuple(reasons)

    @staticmethod
    def from_env(
        *,
        l4_pass: bool,
        l7_go: bool,
        rollback_real_proven: bool,
        human_approval: bool,
        cutover_window_authorized: bool,
        snapshot_ready: bool,
        environ: Mapping[str, str] | None = None,
    ) -> "WriterInterlock":
        env = environ if environ is not None else os.environ
        return WriterInterlock(
            l4_pass=l4_pass,
            l7_go=l7_go,
            rollback_real_proven=rollback_real_proven,
            human_approval=human_approval,
            cutover_window_authorized=cutover_window_authorized,
            snapshot_ready=snapshot_ready,
            production_write_env=env.get("SIC_BA_PRODUCTION_WRITE", ""),
        )


@dataclass(frozen=True)
class OperationSpec:
    op_id: str
    target: str
    key: Mapping[str, str]
    payload: Mapping[str, object]


@dataclass(frozen=True)
class OperationRecord:
    op_id: str
    target: str
    key: Mapping[str, str]
    payload_sha256: str
    before_state: Mapping[str, object] | None
    before_fingerprint: str | None
    after_state: Mapping[str, object] | None
    after_fingerprint: str | None
    status: str
    attempts: int

    def as_dict(self) -> dict[str, object]:
        return {
            "op_id": self.op_id,
            "target": self.target,
            "key": dict(self.key),
            "payload_sha256": self.payload_sha256,
            "before_state": dict(self.before_state) if self.before_state is not None else None,
            "before_fingerprint": self.before_fingerprint,
            "after_state": dict(self.after_state) if self.after_state is not None else None,
            "after_fingerprint": self.after_fingerprint,
            "status": self.status,
            "attempts": self.attempts,
        }

    @staticmethod
    def from_dict(payload: Mapping[str, object]) -> "OperationRecord":
        return OperationRecord(
            op_id=str(payload["op_id"]),
            target=str(payload["target"]),
            key=dict(payload.get("key") or {}),
            payload_sha256=str(payload["payload_sha256"]),
            before_state=payload.get("before_state"),
            before_fingerprint=payload.get("before_fingerprint"),
            after_state=payload.get("after_state"),
            after_fingerprint=payload.get("after_fingerprint"),
            status=str(payload["status"]),
            attempts=int(payload.get("attempts", 1)),
        )


@dataclass(frozen=True)
class RunResult:
    run_id: str
    mode: str
    status: str
    created: bool
    operations: tuple[OperationRecord, ...] = field(default_factory=tuple)
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, object]:
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "status": self.status,
            "created": self.created,
            "operations": [op.as_dict() for op in self.operations],
            "reasons": list(self.reasons),
        }

    @staticmethod
    def from_dict(payload: Mapping[str, object]) -> "RunResult":
        return RunResult(
            run_id=str(payload["run_id"]),
            mode=str(payload["mode"]),
            status=str(payload["status"]),
            created=bool(payload.get("created", False)),
            operations=tuple(
                OperationRecord.from_dict(item) for item in payload.get("operations", [])
            ),
            reasons=tuple(str(item) for item in payload.get("reasons", [])),
        )
