from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FinancialGate:
    l4_pass: bool = False
    cutoff: str = ''
    approved_by: str = ''
    evidence_ref: str = ''
    reason: str = 'L4 NO-GO o gate financiero no documentado'

    @property
    def official(self) -> bool:
        return all([
            self.l4_pass,
            bool(self.cutoff.strip()),
            bool(self.approved_by.strip()),
            bool(self.evidence_ref.strip()),
        ])


def load_financial_gate(data_clean: Path) -> FinancialGate:
    """Carga `financial_gate.json`; ante cualquier duda devuelve gate cerrado.

    El archivo no debe versionarse con datos reales. Sirve como interlock local
    después de un cierre L4 documentado y aprobado.
    """
    path = data_clean / 'financial_gate.json'
    if not path.is_file():
        return FinancialGate(reason='financial_gate.json ausente; L4 se considera NO-GO')

    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return FinancialGate(reason='financial_gate.json inválido; fail-closed')

    if not isinstance(payload, dict):
        return FinancialGate(reason='financial_gate.json debe ser un objeto; fail-closed')

    gate = FinancialGate(
        l4_pass=bool(payload.get('l4_pass', False)),
        cutoff=str(payload.get('cutoff', '') or ''),
        approved_by=str(payload.get('approved_by', '') or ''),
        evidence_ref=str(payload.get('evidence_ref', '') or ''),
        reason=str(payload.get('reason', '') or ''),
    )
    if not gate.official:
        return FinancialGate(
            l4_pass=gate.l4_pass,
            cutoff=gate.cutoff,
            approved_by=gate.approved_by,
            evidence_ref=gate.evidence_ref,
            reason='Gate incompleto: requiere L4 PASS + cutoff + approved_by + evidence_ref',
        )
    return gate
