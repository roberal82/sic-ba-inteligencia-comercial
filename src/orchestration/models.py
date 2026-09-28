from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Mode(str, Enum):
    DRY_RUN = "dry-run"
    STAGE = "stage"
    APPLY = "apply"


class Outcome(str, Enum):
    PASS = "PASS"
    PASS_WITH_EXCEPTIONS = "PASS_WITH_EXCEPTIONS"
    BLOCKED_INPUT = "BLOCKED_INPUT"
    BLOCKED_L4 = "BLOCKED_L4"
    BLOCKED_L7 = "BLOCKED_L7"
    BLOCKED_PROD_INTERLOCK = "BLOCKED_PROD_INTERLOCK"
    FAIL = "FAIL"

    @property
    def is_blocked(self) -> bool:
        return self.value.startswith("BLOCKED_")


@dataclass(frozen=True)
class ExecutionContext:
    mode: Mode
    l4_pass: bool = False
    l7_go: bool = False
    rollback_real_proven: bool = False
    human_approval: bool = False
    production_write_enabled: bool = False

    @property
    def production_ready(self) -> bool:
        return all(
            [
                self.l4_pass,
                self.l7_go,
                self.rollback_real_proven,
                self.human_approval,
                self.production_write_enabled,
            ]
        )


@dataclass(frozen=True)
class JobSpec:
    job_id: str
    name: str
    input_key: str | None = None
    financial: bool = False
    requires_cost_evidence: bool = False


@dataclass(frozen=True)
class JobResult:
    job_id: str
    name: str
    outcome: Outcome
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "name": self.name,
            "outcome": self.outcome.value,
            "detail": self.detail,
        }
