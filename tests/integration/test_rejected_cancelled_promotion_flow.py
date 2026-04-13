from pathlib import Path

from odinclaw.contracts.memory import MemoryKind, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_rejected_and_cancelled_promotion_flows_remain_auditable(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = bridge.lifecycle.services.memory_authority.remember(
        topic="workflow",
        content="candidate",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    rejected = bridge.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="not ready")
    bridge.reject_canon_promotion(
        approval_id=rejected.approval_id,
        rejected_by=operator,
        reason="insufficient evidence",
    )
    cancelled = bridge.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="later")
    bridge.cancel_canon_promotion(
        approval_id=cancelled.approval_id,
        cancelled_by=operator,
        reason="withdrawn",
    )
    current = bridge.lifecycle.services.memory_authority.get(record.memory_id)
    assert current.tier == MemoryTier.PROVISIONAL
    assert bridge.lifecycle.services.receipt_chain.query(ReceiptQuery(receipt_type="canon_promotion_rejected"))
    assert bridge.lifecycle.services.receipt_chain.query(ReceiptQuery(receipt_type="canon_promotion_cancelled"))
