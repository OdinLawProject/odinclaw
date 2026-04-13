from pathlib import Path

from odinclaw.contracts.audit import CanonResolutionPreset, CanonResolutionType
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_resolution_presets_and_group_drill_down(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = bridge.lifecycle.services.memory_authority.remember(
        topic="workflow",
        content="approved item",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    approval = bridge.request_canon_promotion(
        memory_id=record.memory_id,
        requested_by=operator,
        reason="approved",
    )
    bridge.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=operator,
    )
    preset_page = bridge.canon_resolution_preset_page(
        preset=CanonResolutionPreset.RECENTLY_APPROVED,
        limit_per_group=2,
    )
    assert preset_page.groups
    group = bridge.canon_resolution_group_page(
        preset=CanonResolutionPreset.RECENTLY_APPROVED,
        resolution_type=CanonResolutionType.CONFLICT_RESOLVED,
        limit=2,
    )
    if not group.items:
        group = bridge.canon_resolution_group_page(
            preset=CanonResolutionPreset.RECENTLY_APPROVED,
            resolution_type=CanonResolutionType.APPROVAL_RESOLVED,
            limit=2,
        )
    assert group.items
    explanation = bridge.explain_canon_transition(group.items[0].transition_id)
    assert explanation.transition_id == group.items[0].transition_id
