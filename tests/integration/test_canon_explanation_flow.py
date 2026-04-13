from pathlib import Path

from odinclaw.contracts.audit import CanonHistoryQuery
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_canon_explanation_without_owning_logic(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = bridge.lifecycle.services.memory_authority.remember(
        topic="workflow",
        content="v1 lesson",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    approval = bridge.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="approved")
    bridge.approve_canon_promotion(approval_id=approval.approval_id, approver=operator)
    history = bridge.lifecycle.services.canon_history.list_for_memory(record.memory_id)
    explanation = bridge.explain_canon_transition(history[-1].transition_id)
    assert explanation.transition_summary
    assert explanation.continuity_summary
    assert explanation.lineage
    summaries = bridge.canon_transition_summaries(CanonHistoryQuery(topic="workflow"))
    assert summaries
