from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


TECHNICAL_CHECKS = (
    "full_regression_pass",
    "orchestration_ci_pass",
    "drift_gate_pass",
    "staging_ci_pass",
    "rollback_test_pass",
    "no_private_data",
)

PRODUCTION_INTERLOCK_VALUE = "ENABLED"


@dataclass(frozen=True)
class ReleaseGateResult:
    technical_status: str
    production_status: str
    technical_ready: bool
    production_ready: bool
    gates_ready: bool
    failed_checks: tuple[str, ...]
    writer_present: bool = False
    production_adapter_configured: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "technical_status": self.technical_status,
            "production_status": self.production_status,
            "technical_ready": self.technical_ready,
            "production_ready": self.production_ready,
            "gates_ready": self.gates_ready,
            "writer_present": self.writer_present,
            "production_adapter_configured": self.production_adapter_configured,
            "failed_checks": list(self.failed_checks),
        }


def evaluate_release_candidate(evidence: dict[str, Any]) -> ReleaseGateResult:
    """Evalúa readiness técnica sin autorizar producción.

    ``writer_present`` refleja si el módulo ``src.writer`` (Sprint 005) está
    integrado en el evidence del caller — nunca se deriva automáticamente de
    que los demás gates estén en verde. ``production_adapter_configured``
    refleja si existe un adaptador real contra el ERP productivo, algo que
    este repositorio no implementa: por lo tanto ``production_ready`` no
    puede ser verdadero hoy sin importar cuántos gates pasen.
    """

    if not isinstance(evidence, dict):
        raise ValueError("La evidencia de release debe ser un objeto JSON.")

    failed = tuple(check for check in TECHNICAL_CHECKS if not bool(evidence.get(check, False)))
    technical_ready = not failed
    technical_status = "RC_READY" if technical_ready else "RC_BLOCKED_TECHNICAL"

    l4_pass = bool(evidence.get("l4_pass", False))
    l7_go = bool(evidence.get("l7_go", False))
    rollback_real_proven = bool(evidence.get("rollback_real_proven", False))
    human_approval = bool(evidence.get("human_approval", False))
    writer_present = bool(evidence.get("writer_module_present", False))
    production_adapter_configured = bool(evidence.get("production_adapter_configured", False))
    interlock = (
        os.getenv("SIC_BA_PRODUCTION_WRITE", "").strip().upper()
        == PRODUCTION_INTERLOCK_VALUE
    )

    gates_ready = all(
        [l4_pass, l7_go, rollback_real_proven, human_approval, interlock]
    )
    production_ready = gates_ready and writer_present and production_adapter_configured

    if not technical_ready:
        production_status = "BLOCKED_TECHNICAL"
    elif not l4_pass:
        production_status = "BLOCKED_L4"
    elif not l7_go:
        production_status = "BLOCKED_L7"
    elif not rollback_real_proven or not human_approval:
        production_status = "BLOCKED_APPROVAL_OR_ROLLBACK"
    elif not interlock:
        production_status = "BLOCKED_PROD_INTERLOCK"
    elif not writer_present:
        production_status = "GATES_READY_WRITER_ABSENT"
    elif not production_adapter_configured:
        production_status = "GATES_READY_WRITER_PRESENT_NO_PRODUCTION_ADAPTER"
    else:
        production_status = "PRODUCTION_READY"

    return ReleaseGateResult(
        technical_status=technical_status,
        production_status=production_status,
        technical_ready=technical_ready,
        production_ready=production_ready,
        gates_ready=gates_ready,
        writer_present=writer_present,
        production_adapter_configured=production_adapter_configured,
        failed_checks=failed,
    )
