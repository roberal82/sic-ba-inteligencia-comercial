"""Gate L4 — evidencia financiera oficial requerida antes de cualquier escritura productiva.

Este gate es deliberadamente más estricto que ``src.financial_governance.FinancialGate``
(que solo bloquea inferencias comerciales). ``L4`` aquí es el interlock que autoriza
al writer productivo (Fase C) y al motor de cutover (Fase G) a considerar datos
financieros como oficiales. Fail-closed: cualquier campo ausente, vacío o con un
estado que no sea ``CONFIRMED`` produce ``FAIL_CLOSED``, nunca una inferencia.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class EvidenceStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    CANDIDATE = "CANDIDATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REQUIRES_HUMAN_REVIEW = "REQUIRES_HUMAN_REVIEW"


_REQUIRED_STATUS_FIELDS = (
    "cxc_status",
    "cxp_status",
    "checks_status",
    "bank_status",
    "nominal_reconciliation_status",
)


@dataclass(frozen=True)
class FinancialGateEvidence:
    """Documento de evidencia L4. Ningún campo tiene un default que apruebe el gate."""

    cutoff: str = ""
    cxc_status: EvidenceStatus | None = None
    cxp_status: EvidenceStatus | None = None
    checks_status: EvidenceStatus | None = None
    bank_status: EvidenceStatus | None = None
    nominal_reconciliation_status: EvidenceStatus | None = None
    approved_by: str = ""
    approval_timestamp: str = ""
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)
    source_hashes: Mapping[str, str] = field(default_factory=dict)

    @staticmethod
    def from_mapping(payload: Mapping[str, object]) -> "FinancialGateEvidence":
        def _status(value: object) -> EvidenceStatus | None:
            if value is None:
                return None
            try:
                return EvidenceStatus(str(value))
            except ValueError:
                return None

        raw_refs = payload.get("evidence_refs", ())
        refs = tuple(str(item) for item in raw_refs) if isinstance(raw_refs, (list, tuple)) else ()
        raw_hashes = payload.get("source_hashes", {})
        hashes = (
            {str(k): str(v) for k, v in raw_hashes.items()}
            if isinstance(raw_hashes, dict)
            else {}
        )
        return FinancialGateEvidence(
            cutoff=str(payload.get("cutoff", "") or ""),
            cxc_status=_status(payload.get("cxc_status")),
            cxp_status=_status(payload.get("cxp_status")),
            checks_status=_status(payload.get("checks_status")),
            bank_status=_status(payload.get("bank_status")),
            nominal_reconciliation_status=_status(payload.get("nominal_reconciliation_status")),
            approved_by=str(payload.get("approved_by", "") or ""),
            approval_timestamp=str(payload.get("approval_timestamp", "") or ""),
            evidence_refs=refs,
            source_hashes=hashes,
        )


@dataclass(frozen=True)
class L4Result:
    gate_result: str  # "PASS" | "FAIL_CLOSED"
    reasons: tuple[str, ...]

    @property
    def l4_pass(self) -> bool:
        return self.gate_result == "PASS"


def evaluate_l4(
    evidence: FinancialGateEvidence,
    *,
    expected_cutoff: str | None = None,
) -> L4Result:
    """Evalúa evidencia L4. Nunca aprueba por ausencia de datos ni por un solo flag.

    ``expected_cutoff``, si se provee, debe coincidir exactamente con
    ``evidence.cutoff`` (referencia de corte controlada, ver Sección 6 del mandato).
    """

    reasons: list[str] = []

    if not evidence.cutoff.strip():
        reasons.append("cutoff ausente")
    elif expected_cutoff is not None and evidence.cutoff != expected_cutoff:
        reasons.append(
            f"cutoff {evidence.cutoff!r} no coincide con la referencia controlada {expected_cutoff!r}"
        )

    for field_name in _REQUIRED_STATUS_FIELDS:
        status = getattr(evidence, field_name)
        if status is None:
            reasons.append(f"{field_name} ausente")
        elif status is not EvidenceStatus.CONFIRMED:
            reasons.append(f"{field_name}={status.value} (requiere CONFIRMED)")

    if not evidence.approved_by.strip():
        reasons.append("approved_by ausente")
    if not evidence.approval_timestamp.strip():
        reasons.append("approval_timestamp ausente")
    if not evidence.evidence_refs:
        reasons.append("evidence_refs vacío")
    if not evidence.source_hashes:
        reasons.append("source_hashes vacío")

    if reasons:
        return L4Result(gate_result="FAIL_CLOSED", reasons=tuple(reasons))
    return L4Result(gate_result="PASS", reasons=())
