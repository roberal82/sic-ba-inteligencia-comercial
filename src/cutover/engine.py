"""Motor de cutover (Fase G).

Convierte el simulador F5 puro en un motor preparado para ejecución real, pero
bloqueado por defecto: ``execute_go_live`` nunca ejecuta nada en este sprint,
porque no existe ningún adaptador productivo real (ver ``src.writer``). Sirve
para que, cuando exista un adaptador real y todos los gates estén en GO, el
camino a producción sea corto y no requiera rediseño.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..gates.l4_evidence import L4Result
from ..gates.l7_decision import L7Decision
from ..writer.models import WriterInterlock
from .models import CutoverContext
from .simulator import simulate_cutover


class CutoverEngineBlockedError(RuntimeError):
    """Se intentó ejecutar go-live real sin todos los gates en GO o sin adaptador."""


def build_context_from_gates(
    l4: L4Result,
    l7: L7Decision,
    *,
    snapshot_ready: bool = False,
    cutover_window_authorized: bool = False,
    nonfinancial_ready: bool = False,
    cardinality_validated: bool = False,
    smoke_nonfinancial_pass: bool = False,
    uat_accepted: bool = False,
    rollback_real_proven: bool = False,
    human_approval: bool = False,
    go_live_executed: bool = False,
    coexistence_stable: bool = False,
) -> CutoverContext:
    """Construye el contexto F5 a partir de gates formales, nunca de flags sueltos."""

    return CutoverContext(
        snapshot_ready=snapshot_ready,
        cutover_window_authorized=cutover_window_authorized,
        nonfinancial_ready=nonfinancial_ready,
        cardinality_validated=cardinality_validated,
        l4_pass=l4.l4_pass,
        smoke_nonfinancial_pass=smoke_nonfinancial_pass,
        uat_accepted=uat_accepted,
        l7_go=l7.l7_go,
        rollback_real_proven=rollback_real_proven,
        human_approval=human_approval,
        go_live_executed=go_live_executed,
        coexistence_stable=coexistence_stable,
    )


@dataclass
class CutoverEngine:
    context: CutoverContext
    writer_interlock: WriterInterlock = WriterInterlock()

    def evaluate(self) -> dict:
        """Decisión pura GO/NO-GO por paso. Nunca muta estado externo."""
        return simulate_cutover(self.context)

    def execute_go_live(self) -> None:
        """Bloqueado por defecto: no existe adaptador productivo real todavía.

        Incluso si todos los gates de ``evaluate()`` estuvieran en GO simulado
        y el ``writer_interlock`` estuviera autorizado, esta versión del motor
        no ejecuta ninguna mutación productiva. El bloqueo es intencional y
        documenta que ``writer_present=false`` para el ERP real.
        """
        result = self.evaluate()
        reasons: list[str] = []
        if result["overall"] != "GO_SIMULATED":
            reasons.append(f"Simulación F5 en {result['overall']}, no GO_SIMULATED.")
        if not self.writer_interlock.apply_authorized:
            reasons.extend(self.writer_interlock.blocking_reasons)
        reasons.append(
            "No existe adaptador productivo real para el ERP; go-live real no implementado en este sprint."
        )
        raise CutoverEngineBlockedError("; ".join(reasons))
