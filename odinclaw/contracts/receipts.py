from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from odinclaw.contracts.action_ids import TraceIds
from odinclaw.contracts.provenance import ProvenanceRecord


@dataclass(frozen=True)
class ReceiptRecord:
    receipt_id: str
    receipt_type: str
    trace_ids: TraceIds
    action_name: str
    created_at: datetime
    provenance: ProvenanceRecord
    data: dict[str, Any] = field(default_factory=dict)
    parent_receipt_hash: str | None = None
    receipt_hash: str = ""


@dataclass(frozen=True)
class ReceiptQuery:
    run_id: str | None = None
    action_id: str | None = None
    receipt_type: str | None = None
    session_id: str | None = None
    action_name: str | None = None
