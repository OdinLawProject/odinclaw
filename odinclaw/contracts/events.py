from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.action_ids import TraceIds


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


class RunPhase(StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    SHUTTING_DOWN = "shutting_down"


@dataclass(frozen=True)
class RunTrace:
    session_name: str
    session_id: str
    run_id: str
    phase: RunPhase = RunPhase.ACTIVE
    started_at: datetime = field(default_factory=utc_now)
    parent_session_id: str | None = None
    parent_run_id: str | None = None


@dataclass(frozen=True)
class OdinClawEvent:
    event_type: str
    trace_ids: TraceIds
    action_name: str
    action_class: ActionClass
    occurred_at: datetime = field(default_factory=utc_now)
    meaningful: bool = True
    payload: dict[str, Any] = field(default_factory=dict)
