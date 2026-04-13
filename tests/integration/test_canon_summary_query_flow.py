from pathlib import Path

from odinclaw.contracts.audit import CanonAuditPreset, CanonHistoryQuery
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_filtered_compact_canon_summaries_with_drill_down(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = bridge.lifecycle.services.memory_authority.remember(
        topic="workflow",
        content="stable",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    approval = bridge.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="approved")
    bridge.approve_canon_promotion(approval_id=approval.approval_id, approver=operator)
    summaries = bridge.canon_transition_summaries(CanonHistoryQuery(topic="workflow", limit=3))
    assert len(summaries) >= 1
    assert summaries[0].approval_reference == approval.approval_id
    explanation = bridge.explain_canon_transition(summaries[0].transition_id)
    assert explanation.transition_id == summaries[0].transition_id
    preset_page = bridge.canon_preset_page(preset=CanonAuditPreset.RECENT_CHANGES, limit=2)
    assert preset_page.items
