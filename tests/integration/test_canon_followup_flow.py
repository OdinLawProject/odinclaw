from pathlib import Path

from odinclaw.contracts.audit import CanonFollowUpPreset, CanonFollowUpType
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_follow_up_presets_and_group_drill_down(tmp_path: Path) -> None:
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
        content="follow-up case",
        provenance=external,
        kind=MemoryKind.OBSERVATION,
    )
    approval = bridge.request_canon_promotion(
        memory_id=record.memory_id,
        requested_by=external,
        reason="approved",
    )
    bridge.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
    )
    preset_page = bridge.canon_follow_up_preset_page(
        preset=CanonFollowUpPreset.AFTERCARE_NEEDED_NOW,
        limit_per_group=2,
    )
    assert preset_page.groups
    group = bridge.canon_follow_up_group_page(
        preset=CanonFollowUpPreset.TRUST_POSTURE_CHANGED_AFTER_RESOLUTION,
        follow_up_type=CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP,
        limit=2,
    )
    assert group.items
    explanation = bridge.explain_canon_transition(group.items[0].transition_id)
    assert explanation.transition_id == group.items[0].transition_id
