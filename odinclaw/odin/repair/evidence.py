from __future__ import annotations

from dataclasses import dataclass

from odinclaw.contracts.action_ids import TraceIds


@dataclass(frozen=True)
class RollbackEvidence:
    trace_ids: TraceIds
    reason: str
    rolled_back_action_id: str | None = None
    rolled_back_action_name: str | None = None
    restored_to_checkpoint: str | None = None


@dataclass(frozen=True)
class RepairReceiptRecord:
    trace_ids: TraceIds
    repair_type: str
    reason: str
    rollback_evidence: RollbackEvidence | None = None
