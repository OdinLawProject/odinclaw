from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.provenance import ProvenanceRecord


class GovernanceOutcome(StrEnum):
    ALLOW = "allow"
    HOLD = "hold"
    ESCALATE = "escalate"
    DENY = "deny"


@dataclass(frozen=True)
class ActionRequest:
    action_name: str
    action_class: ActionClass
    provenance: ProvenanceRecord
    payload: dict[str, object] = field(default_factory=dict)
    meaningful: bool = True


@dataclass(frozen=True)
class GovernanceDecision:
    outcome: GovernanceOutcome
    reason: str
    risk_notes: tuple[str, ...] = ()
