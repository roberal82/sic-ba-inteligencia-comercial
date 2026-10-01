"""Panel de operación SIC-BA (Fase M).

Interfaz de solo lectura: agrega el resultado de los gates existentes
(release gate, L4, L7, cutover) en una sola vista de estado. No ejecuta
ninguna mutación, no llama al writer productivo y no requiere credenciales.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.cutover.engine import CutoverEngine, build_context_from_gates
from src.gates.l4_evidence import FinancialGateEvidence, evaluate_l4
from src.gates.l7_decision import L7Inputs, evaluate_l7
from src.orchestration.release_gate import evaluate_release_candidate


@dataclass(frozen=True)
class PanelRow:
    label: str
    value: str
    detail: str = ""


def _writer_row(release_result) -> PanelRow:
    if not release_result.writer_present:
        return PanelRow("WRITER", "NOT_PRESENT", "Módulo src.writer no declarado en el release evidence.")
    if release_result.production_adapter_configured:
        return PanelRow("WRITER", "READY / ENABLED_PENDING_INTERLOCK", "Adaptador productivo configurado; sigue sujeto a WriterInterlock.")
    return PanelRow("WRITER", "READY / DISABLED", "Módulo presente; sin adaptador productivo real (NullProductionAdapter).")


def build_panel(config: dict[str, Any]) -> list[PanelRow]:
    release_result = evaluate_release_candidate(config.get("release_candidate", {}))
    l4_result = evaluate_l4(FinancialGateEvidence.from_mapping(config.get("l4_evidence", {})))
    l7_decision = evaluate_l7(L7Inputs(**config.get("l7_inputs", {})))

    cutover_extra = dict(config.get("cutover_extra", {}))
    ctx = build_context_from_gates(l4_result, l7_decision, **cutover_extra)
    cutover_result = CutoverEngine(ctx).evaluate()

    rows = [
        PanelRow(
            "TECHNICAL",
            "READY" if release_result.technical_ready else "BLOCKED",
            release_result.technical_status,
        ),
        PanelRow(
            "L4",
            l4_result.gate_result,
            "; ".join(l4_result.reasons) if l4_result.reasons else "Evidencia completa.",
        ),
        PanelRow(
            "L7",
            l7_decision.result,
            "; ".join(l7_decision.reasons) if l7_decision.reasons else "Todos los prerequisitos GO.",
        ),
        _writer_row(release_result),
        PanelRow(
            "ROLLBACK",
            "READY" if config.get("release_candidate", {}).get("rollback_test_pass") else "NOT_PROVEN",
            "Evidencia técnica rollback_test_pass del release gate.",
        ),
        PanelRow(
            "CUTOVER",
            "READY" if cutover_result["go_live_simulated"] else "BLOCKED",
            f"F5 overall={cutover_result['overall']}",
        ),
        PanelRow(
            "PRODUCTION",
            "UNLOCKED" if release_result.production_ready else "LOCKED",
            release_result.production_status,
        ),
        PanelRow(
            "ADMIN 2026",
            "ELIGIBLE_FOR_ARCHIVE" if cutover_result["legacy_archive_simulated"] else "ACTIVE",
            "Legacy solo puede marcarse elegible; el archivado sigue siendo manual.",
        ),
    ]
    return rows


def render_text(rows: list[PanelRow]) -> str:
    width = max(len(row.label) for row in rows) + 2
    lines = ["SIC-BA — SYSTEM STATUS", "=" * 40]
    for row in rows:
        lines.append(f"{row.label.ljust(width)}{row.value}")
        if row.detail:
            lines.append(f"{' ' * width}  {row.detail}")
    return "\n".join(lines)
