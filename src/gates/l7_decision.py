"""Gate L7 — decisión GO/NO-GO de producción.

L7 nunca puede alcanzar GO por sí solo: depende técnicamente de L4 PASS más
integridad, rollback probado, smoke test, UAT y aprobación humana explícita.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class L7Inputs:
    l4_pass: bool = False
    integrity_pass: bool = False
    rollback_pass: bool = False
    smoke_pass: bool = False
    uat_pass: bool = False
    manifest_complete: bool = False
    human_approval: bool = False
    approved_by: str = ""
    approval_timestamp: str = ""


@dataclass(frozen=True)
class L7Decision:
    result: str  # "GO" | "NO_GO"
    reasons: tuple[str, ...]

    @property
    def l7_go(self) -> bool:
        return self.result == "GO"


_CHECKS: tuple[tuple[str, str], ...] = (
    ("l4_pass", "L4 no está en PASS"),
    ("integrity_pass", "Verificación de integridad no aprobada"),
    ("rollback_pass", "Rollback real no probado"),
    ("smoke_pass", "Smoke test no aprobado"),
    ("uat_pass", "UAT no aceptado"),
    ("manifest_complete", "Manifest de operación incompleto"),
    ("human_approval", "Falta aprobación humana explícita"),
)


def evaluate_l7(inputs: L7Inputs) -> L7Decision:
    reasons = [message for field_name, message in _CHECKS if not getattr(inputs, field_name)]

    if inputs.human_approval:
        if not inputs.approved_by.strip():
            reasons.append("human_approval=true sin approved_by")
        if not inputs.approval_timestamp.strip():
            reasons.append("human_approval=true sin approval_timestamp")

    if reasons:
        return L7Decision(result="NO_GO", reasons=tuple(reasons))
    return L7Decision(result="GO", reasons=())
