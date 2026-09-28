from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class StepOutcome(str, Enum):
    PASS = "PASS"
    PASS_PARTIAL = "PASS_PARTIAL"
    NOT_EXECUTED = "NOT_EXECUTED"
    NOT_STARTED = "NOT_STARTED"
    BLOCKED_PRECONDITION = "BLOCKED_PRECONDITION"
    BLOCKED_L4 = "BLOCKED_L4"
    BLOCKED_L7 = "BLOCKED_L7"
    BLOCKED_APPROVAL = "BLOCKED_APPROVAL"
    BLOCKED_ROLLBACK = "BLOCKED_ROLLBACK"
    BLOCKED_WINDOW = "BLOCKED_WINDOW"
    BLOCKED_LEGACY = "BLOCKED_LEGACY"
    FAIL = "FAIL"

    @property
    def blocked(self) -> bool:
        return self.value.startswith("BLOCKED_")


@dataclass(frozen=True)
class CutoverContext:
    snapshot_ready: bool = False
    cutover_window_authorized: bool = False
    nonfinancial_ready: bool = False
    cardinality_validated: bool = False
    l4_pass: bool = False
    smoke_nonfinancial_pass: bool = False
    uat_accepted: bool = False
    l7_go: bool = False
    rollback_real_proven: bool = False
    human_approval: bool = False
    go_live_executed: bool = False
    coexistence_stable: bool = False


@dataclass(frozen=True)
class StepResult:
    step: int
    activity: str
    outcome: StepOutcome
    detail: str
    rollback_point: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "activity": self.activity,
            "outcome": self.outcome.value,
            "detail": self.detail,
            "rollback_point": self.rollback_point,
        }
