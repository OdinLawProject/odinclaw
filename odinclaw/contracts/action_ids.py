from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass(frozen=True)
class TraceIds:
    session_id: str
    run_id: str
    action_id: str


def new_session_id() -> str:
    return f"session-{uuid4().hex}"


def new_run_id() -> str:
    return f"run-{uuid4().hex}"


def new_action_id() -> str:
    return f"action-{uuid4().hex}"


def new_trace_ids(
    *,
    session_id: str | None = None,
    run_id: str | None = None,
    action_id: str | None = None,
) -> TraceIds:
    return TraceIds(
        session_id=session_id or new_session_id(),
        run_id=run_id or new_run_id(),
        action_id=action_id or new_action_id(),
    )
