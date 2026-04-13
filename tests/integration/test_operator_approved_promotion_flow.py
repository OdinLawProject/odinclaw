from pathlib import Path

from odinclaw.contracts.memory import MemoryKind, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_operator_approved_canon_promotion_flows_through_shell_bridge(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = bridge.lifecycle.services.memory_authority.remember(
        topic="workflow",
        content="Validated stable lesson",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    approval = bridge.request_canon_promotion(
        memory_id=record.memory_id,
        requested_by=operator,
        reason="stable and approved",
    )
    promoted = bridge.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=operator,
    )
    assert promoted.tier == MemoryTier.CANON
    receipts = bridge.lifecycle.services.receipt_chain.query(ReceiptQuery(receipt_type="canon_promotion"))
    assert len(receipts) == 1
    history = bridge.lifecycle.services.canon_history.list_for_memory(record.memory_id)
    assert history[-1].status == "approved_applied"
    assert history[-1].approval_id == approval.approval_id
    explanation = bridge.explain_canon_transition(history[-1].transition_id)
    assert explanation.approval_reference == approval.approval_id
    assert explanation.prior_state is not None
    assert bridge.extension_state().startup_ready is True
