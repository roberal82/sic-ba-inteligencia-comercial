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

    def as_dict(self) -> dict[str, Any]:
        return {
            "technical_status": self.technical_status,
            "production_status": self.production_status,
            "technical_ready": self.technical_ready,
            "production_ready": self.production_ready,
            "gates_ready": self.gates_ready,
            "writer_present": self.writer_present,
            "failed_checks": list(self.failed_checks),
        }


def evaluate_release_candidate(evidence: dict[str, Any]) -> ReleaseGateResult:
    """Evalúa readiness técnica sin autorizar producción.

    Sprint 003 deliberadamente no contiene writer productivo. Aun con todos los
    gates habilitados, ``production_ready`` permanece False y el estado final
    indica que falta un adaptador de cutover explícito.
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
    interlock = (
        os.getenv("SIC_BA_PRODUCTION_WRITE", "").strip().upper()
        == PRODUCTION_INTERLOCK_VALUE
    )

    gates_ready = all(
        [l4_pass, l7_go, rollback_real_proven, human_approval, interlock]
    )

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
    else:
        production_status = "GATES_READY_WRITER_ABSENT"

    return ReleaseGateResult(
        technical_status=technical_status,
        production_status=production_status,
        technical_ready=technical_ready,
        production_ready=False,
        gates_ready=gates_ready,
        writer_present=False,
        failed_checks=failed,
    )
