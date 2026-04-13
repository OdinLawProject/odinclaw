from pathlib import Path

from odinclaw.contracts.audit import CanonAuditPreset
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_preset_pages_and_drill_down_across_pages(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    for content in ("one", "two", "three"):
        record = bridge.lifecycle.services.memory_authority.remember(
            topic="workflow",
            content=content,
            provenance=operator,
            kind=MemoryKind.OBSERVATION,
        )
        approval = bridge.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="approved")
        bridge.approve_canon_promotion(approval_id=approval.approval_id, approver=operator)
    page_one = bridge.canon_preset_page(preset=CanonAuditPreset.RECENT_CHANGES, limit=2)
    assert len(page_one.items) == 2
    assert page_one.next_cursor is not None
    page_two = bridge.canon_preset_page(
        preset=CanonAuditPreset.RECENT_CHANGES,
        limit=2,
        cursor=page_one.next_cursor,
    )
    assert page_two.items
    linked_page = bridge.canon_linked_preset_page(
        preset=CanonAuditPreset.WITH_APPROVAL_CONTEXT,
        limit=2,
    )
    assert linked_page.items
    assert linked_page.items[0].approval_reference is not None
    explanation = bridge.explain_canon_transition(page_two.items[0].transition_id)
    assert explanation.transition_id == page_two.items[0].transition_id
