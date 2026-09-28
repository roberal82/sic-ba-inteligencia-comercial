"""Contratos mínimos de ejecución y auditoría de Fase 4."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List


@dataclass
class JobContext:
    run_id: str
    mode: str
    source_id: str
    target: str
    cutoff: str
    actor: str
    ruleset_version: str


@dataclass
class JobResult:
    job_id: str
    status: str
    input_count: int = 0
    output_count: int = 0
    quarantined_count: int = 0
    rejected_count: int = 0
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def balanced(self) -> bool:
        return self.input_count == (
            self.output_count + self.quarantined_count + self.rejected_count
        )

    def as_audit_event(self, context: JobContext) -> Dict[str, Any]:
        return {
            "run_id": context.run_id,
            "timestamp": self.timestamp,
            "job_id": self.job_id,
            "source_id": context.source_id,
            "target": context.target,
            "mode": context.mode,
            "cutoff": context.cutoff,
            "actor": context.actor,
            "ruleset_version": context.ruleset_version,
            "status": self.status,
            "input_count": self.input_count,
            "output_count": self.output_count,
            "quarantined_count": self.quarantined_count,
            "rejected_count": self.rejected_count,
            "details": self.details,
            "errors": self.errors,
        }
