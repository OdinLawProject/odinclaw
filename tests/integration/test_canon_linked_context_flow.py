from pathlib import Path

from odinclaw.contracts.audit import CanonAuditPreset
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_linked_context_for_transition_drill_down(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    external = ProvenanceRecord(
        source_type="feed",
        source_label="partner-feed",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    bridge.lifecycle.services.memory_authority.record_trust_state_change(
        source_label="partner-feed",
        previous=None,
        current=TrustClass.AMBIGUOUS_EXTERNAL,
        provenance=external,
    )
    record = bridge.lifecycle.services.memory_authority.remember(
        topic="workflow",
        content="new guidance",
        provenance=external,
        kind=MemoryKind.OBSERVATION,
    )
    approval = bridge.request_canon_promotion(
        memory_id=record.memory_id,
        requested_by=external,
        reason="operator reviewed",
    )
    bridge.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
    )
    bridge.lifecycle.services.conflict_store.record(
        topic="workflow",
        claim="new guidance",
        conflicting_claim="old guidance",
        severity="high",
        provenance=external,
    )
    page = bridge.canon_linked_preset_page(
        preset=CanonAuditPreset.WITH_CONFLICT_CONTEXT,
        limit=5,
    )
    assert page.items
    summary = page.items[0]
    linked = bridge.canon_linked_context(summary.transition_id)
    assert linked.approval is not None
    assert linked.approval.approval_id == approval.approval_id
    assert linked.trust is not None
    assert linked.trust.source_label == "partner-feed"
    assert linked.conflict is not None
    explanation = bridge.explain_canon_transition(summary.transition_id)
    assert explanation.transition_id == summary.transition_id
