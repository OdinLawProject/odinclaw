from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ContinuityLink:
    session_id: str
    run_id: str
    parent_session_id: str | None
    parent_run_id: str | None
    reason: str
    recorded_at: datetime
    prior_state_id: str | None = None
    resulting_state_id: str | None = None
    approval_id: str | None = None
