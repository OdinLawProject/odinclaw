from __future__ import annotations

from dataclasses import dataclass

from odinclaw.contracts.action_ids import TraceIds


@dataclass(frozen=True)
class RollbackEvidence:
    """Durable record of what was rolled back and why."""

    trace_ids: TraceIds
    reason: str
    rolled_back_action_id: str | None = None
    rolled_back_action_name: str | None = None
    restored_to_checkpoint: str | None = None


@dataclass(frozen=True)
class RepairReceiptRecord:
    """Receipt emitted when a repair or rollback event occurs."""

    trace_ids: TraceIds
    repair_type: str  # "enter_degraded_mode" | "exit_degraded_mode" | "rollback"
    reason: str
    rollback_evidence: RollbackEvidence | None = None
