from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

from ..gates.l4_evidence import FinancialGateEvidence, L4Result, evaluate_l4
from ..gates.l7_decision import L7Decision, L7Inputs, evaluate_l7


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
    l4_status: str = "FAIL_CLOSED"
    l7_status: str = "NO_GO"

    def as_dict(self) -> dict[str, Any]:
        return {
            "technical_status": self.technical_status,
            "production_status": self.production_status,
            "technical_ready": self.technical_ready,
            "production_ready": self.production_ready,
            "gates_ready": self.gates_ready,
            "writer_present": self.writer_present,
            "production_adapter_configured": self.production_adapter_configured,
            "l4_status": self.l4_status,
            "l7_status": self.l7_status,
            "failed_checks": list(self.failed_checks),
        }


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def _evaluate_formal_l4(evidence: Mapping[str, object]) -> L4Result:
    payload = _mapping(evidence.get("l4_evidence"))
    if not payload:
        return L4Result(
            gate_result="FAIL_CLOSED",
            reasons=("l4_evidence formal ausente",),
        )
    expected_cutoff = str(evidence.get("expected_financial_cutoff", "") or "")
    return evaluate_l4(
        FinancialGateEvidence.from_mapping(payload),
        expected_cutoff=expected_cutoff or None,
    )


def _evaluate_formal_l7(
    evidence: Mapping[str, object], l4_pass: bool
) -> tuple[L7Decision, L7Inputs]:
    payload = _mapping(evidence.get("l7_inputs"))
    if not payload:
        inputs = L7Inputs(l4_pass=l4_pass)
        return evaluate_l7(inputs), inputs

    inputs = L7Inputs(
        # El caller NO puede autocertificar L4 dentro de L7.
        l4_pass=l4_pass,
        integrity_pass=bool(payload.get("integrity_pass", False)),
        rollback_pass=bool(payload.get("rollback_pass", False)),
        smoke_pass=bool(payload.get("smoke_pass", False)),
        uat_pass=bool(payload.get("uat_pass", False)),
        manifest_complete=bool(payload.get("manifest_complete", False)),
        human_approval=bool(payload.get("human_approval", False)),
        approved_by=str(payload.get("approved_by", "") or ""),
        approval_timestamp=str(payload.get("approval_timestamp", "") or ""),
    )
    return evaluate_l7(inputs), inputs


def evaluate_release_candidate(evidence: dict[str, Any]) -> ReleaseGateResult:
    """Evalúa readiness técnica y productiva en modo fail-closed.

    Los flags heredados l4_pass/l7_go se ignoran deliberadamente. L4 se deriva
    de FinancialGateEvidence mediante evaluate_l4 y L7 se deriva de L7Inputs
    mediante evaluate_l7, forzando el resultado formal de L4 dentro de L7.
    """

    if not isinstance(evidence, dict):
        raise ValueError("La evidencia de release debe ser un objeto JSON.")

    failed = tuple(
        check for check in TECHNICAL_CHECKS if not bool(evidence.get(check, False))
    )
    technical_ready = not failed
    technical_status = "RC_READY" if technical_ready else "RC_BLOCKED_TECHNICAL"

    l4_result = _evaluate_formal_l4(evidence)
    l4_pass = l4_result.l4_pass

    l7_decision, l7_inputs = _evaluate_formal_l7(evidence, l4_pass)
    l7_go = l7_decision.l7_go

    rollback_real_proven = l7_inputs.rollback_pass
    human_approval = (
        l7_inputs.human_approval
        and bool(l7_inputs.approved_by.strip())
        and bool(l7_inputs.approval_timestamp.strip())
    )
    writer_present = bool(evidence.get("writer_module_present", False))
    production_adapter_configured = bool(
        evidence.get("production_adapter_configured", False)
    )
    interlock = (
        os.getenv("SIC_BA_PRODUCTION_WRITE", "").strip().upper()
        == PRODUCTION_INTERLOCK_VALUE
    )

    gates_ready = all(
        [
            l4_pass,
            l7_go,
            rollback_real_proven,
            human_approval,
            interlock,
        ]
    )
    production_ready = (
        gates_ready and writer_present and production_adapter_configured
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
        l4_status=l4_result.gate_result,
        l7_status=l7_decision.result,
        failed_checks=failed,
    )
