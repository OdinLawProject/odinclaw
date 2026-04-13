from pathlib import Path

from odinclaw.contracts.audit import CanonAttentionPreset, CanonAuditPreset, CanonFollowUpPreset, CanonFollowUpType, CanonHistoryQuery, CanonPressureType, CanonResolutionPreset, CanonResolutionType
from odinclaw.contracts.action_ids import new_trace_ids
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.odin.governance.approvals import ApprovalStore
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.conflict_store import ConflictMemoryStore
from odinclaw.odin.memory.explanations import CanonExplanationService
from odinclaw.odin.memory.governed_mutations import GovernedMemoryMutations
from odinclaw.odin.memory.history import CanonHistoryStore


def test_explanations_provide_ancestry_prior_state_and_diff(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=ConflictMemoryStore(authority),
    )
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = authority.remember(
        topic="workflow",
        content="v1 stable lesson",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    approval = governed.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="stable")
    promoted = governed.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=operator,
        trace_ids=new_trace_ids(),
    )
    updated = governed.mutate_canon_with_approval(
        memory_id=promoted.memory_id,
        new_content="v2 stable lesson",
        requested_by=operator,
        approver=operator,
        reason="clarified wording",
        trace_ids=new_trace_ids(),
    )
    chain = explainer.ancestry_for_memory(updated.memory_id)
    explanation = explainer.explain_transition(chain[-1].transition_id)
    assert len(chain) >= 2
    assert explanation.prior_state is not None
    assert explanation.resulting_state is not None
    assert explanation.semantic_delta.changed_fields["content"] == ("v1 stable lesson", "v2 stable lesson")
    assert explanation.approval_reference is not None


def test_explanations_filter_and_rank_compact_summaries_deterministically(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=ConflictMemoryStore(authority),
    )
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    first = authority.remember(topic="workflow", content="first", provenance=operator, kind=MemoryKind.OBSERVATION)
    second = authority.remember(topic="identity", content="second", provenance=operator, kind=MemoryKind.OBSERVATION)
    approval_one = governed.request_canon_promotion(memory_id=first.memory_id, requested_by=operator, reason="workflow stable")
    governed.approve_canon_promotion(approval_id=approval_one.approval_id, approver=operator, trace_ids=new_trace_ids())
    approval_two = governed.request_canon_promotion(memory_id=second.memory_id, requested_by=operator, reason="identity stable")
    governed.reject_canon_promotion(approval_id=approval_two.approval_id, rejected_by=operator, trace_ids=new_trace_ids(), reason="not ready")
    summaries = explainer.query_transition_summaries(CanonHistoryQuery(topic="workflow", limit=5))
    assert summaries
    assert all(summary.topic == "workflow" for summary in summaries)
    assert summaries[0].semantic_delta_cue
    full = explainer.summary_to_explanation(summaries[0].transition_id)
    assert full.transition_id == summaries[0].transition_id


def test_explanations_support_presets_and_bounded_pagination(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    conflict_store = ConflictMemoryStore(authority)
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=conflict_store,
    )
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    first = authority.remember(topic="workflow", content="a", provenance=operator, kind=MemoryKind.OBSERVATION)
    second = authority.remember(topic="workflow", content="b", provenance=operator, kind=MemoryKind.OBSERVATION)
    third = authority.remember(topic="identity", content="c", provenance=operator, kind=MemoryKind.OBSERVATION)
    for record in (first, second, third):
        approval = governed.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason=f"{record.topic} stable")
        governed.approve_canon_promotion(approval_id=approval.approval_id, approver=operator, trace_ids=new_trace_ids())
    page_one = explainer.preset_transition_summaries(
        preset=CanonAuditPreset.TOPIC_CHANGES,
        topic="workflow",
        limit=1,
    )
    assert len(page_one.items) == 1
    assert page_one.next_cursor is not None
    page_two = explainer.preset_transition_summaries(
        preset=CanonAuditPreset.TOPIC_CHANGES,
        topic="workflow",
        limit=1,
        cursor=page_one.next_cursor,
    )
    assert len(page_two.items) == 1
    assert page_one.items[0].transition_id != page_two.items[0].transition_id


def test_explanations_assemble_compact_linked_context_and_presets(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    conflict_store = ConflictMemoryStore(authority)
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=conflict_store,
    )
    external = ProvenanceRecord(
        source_type="feed",
        source_label="partner-feed",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    authority.record_trust_state_change(
        source_label="partner-feed",
        previous=None,
        current=TrustClass.AMBIGUOUS_EXTERNAL,
        provenance=external,
    )
    record = authority.remember(
        topic="workflow",
        content="linked lesson",
        provenance=external,
        kind=MemoryKind.OBSERVATION,
    )
    conflict_store.record(
        topic="workflow",
        claim="linked lesson",
        conflicting_claim="old workflow",
        severity="medium",
        provenance=external,
    )
    approval = governed.request_canon_promotion(memory_id=record.memory_id, requested_by=external, reason="operator approved")
    promoted = governed.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
    )
    transition = explainer.ancestry_for_memory(promoted.memory_id)[-1]
    linked = explainer.linked_context(transition.transition_id)
    assert linked.approval is not None
    assert linked.approval.approval_id == approval.approval_id
    assert linked.trust is not None
    assert linked.trust.source_label == "partner-feed"
    assert linked.conflict is not None
    assert linked.conflict.topic == "workflow"
    preset = explainer.preset_transition_summaries(
        preset=CanonAuditPreset.WITH_APPROVAL_CONTEXT,
        limit=5,
    )
    assert preset.items
    assert preset.items[0].trust_cue is not None
    assert preset.items[0].conflict_cue is not None
    governed = explainer.preset_transition_summaries(
        preset=CanonAuditPreset.HIGH_SIGNIFICANCE_GOVERNED,
        limit=5,
    )
    assert governed.items
    assert all(item.approval_reference is not None for item in governed.items)


def test_explanations_build_bounded_relevance_views_with_receipt_and_now_cues(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    conflict_store = ConflictMemoryStore(authority)
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=conflict_store,
        receipt_chain=receipts,
    )
    external = ProvenanceRecord(
        source_type="feed",
        source_label="partner-feed",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    authority.record_trust_state_change(
        source_label="partner-feed",
        previous=None,
        current=TrustClass.AMBIGUOUS_EXTERNAL,
        provenance=external,
    )
    record = authority.remember(
        topic="workflow",
        content="new guidance",
        provenance=external,
        kind=MemoryKind.OBSERVATION,
    )
    approval = governed.request_canon_promotion(
        memory_id=record.memory_id,
        requested_by=external,
        reason="operator reviewed",
    )
    promoted = governed.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
    )
    conflict_store.record(
        topic="workflow",
        claim="new guidance",
        conflicting_claim="old guidance",
        severity="high",
        provenance=external,
    )
    transition = explainer.ancestry_for_memory(promoted.memory_id)[-1]
    bounded = explainer.bounded_view(transition.transition_id)
    assert bounded.governance_receipt is not None
    assert bounded.governance_receipt.receipt_type in {"canon_promotion", "canon_promotion_approved"}
    assert bounded.linked_context is not None
    assert bounded.linked_context.trust is not None
    assert bounded.linked_context.conflict is not None
    assert bounded.why_this_matters_now == "trust-downgraded canon transition"
    page = explainer.preset_bounded_views(
        preset=CanonAuditPreset.RELEVANCE_NOW_GOVERNED,
        limit=5,
    )
    assert page.items
    assert page.items[0].why_this_matters_now


def test_explanations_classify_attention_pressure_and_group_bounded_views(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    conflict_store = ConflictMemoryStore(authority)
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=conflict_store,
        receipt_chain=receipts,
    )
    external = ProvenanceRecord(
        source_type="feed",
        source_label="partner-feed",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    authority.record_trust_state_change(
        source_label="partner-feed",
        previous=None,
        current=TrustClass.AMBIGUOUS_EXTERNAL,
        provenance=external,
    )
    requested = authority.remember(
        topic="approval",
        content="needs operator",
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        kind=MemoryKind.OBSERVATION,
    )
    requested_approval = governed.request_canon_promotion(
        memory_id=requested.memory_id,
        requested_by=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        reason="awaiting approval",
    )
    trust_record = authority.remember(
        topic="trust",
        content="downgraded source canon",
        provenance=external,
        kind=MemoryKind.OBSERVATION,
    )
    trust_approval = governed.request_canon_promotion(
        memory_id=trust_record.memory_id,
        requested_by=external,
        reason="operator reviewed",
    )
    governed.approve_canon_promotion(
        approval_id=trust_approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
    )
    mutation_record = authority.remember(
        topic="mutation",
        content="stable canon",
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        kind=MemoryKind.OBSERVATION,
    )
    mutation_approval = governed.request_canon_promotion(
        memory_id=mutation_record.memory_id,
        requested_by=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        reason="promote then mutate",
    )
    promoted = governed.approve_canon_promotion(
        approval_id=mutation_approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
    )
    governed.mutate_canon_with_approval(
        memory_id=promoted.memory_id,
        new_content="stable canon v2",
        requested_by=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        reason="clarify",
        trace_ids=new_trace_ids(),
    )
    conflict_store.record(
        topic="approval",
        claim="needs operator",
        conflicting_claim="do not promote",
        severity="high",
        provenance=external,
    )
    requested_transition = explainer.ancestry_by_approval(requested_approval.approval_id)[0]
    trust_transition = explainer.ancestry_for_memory(trust_record.memory_id)[-1]
    mutation_transition = explainer.ancestry_for_memory(promoted.memory_id)[-1]
    assert explainer._pressure_type(requested_transition) == CanonPressureType.APPROVAL_PRESSURE
    assert explainer._pressure_type(trust_transition) == CanonPressureType.TRUST_PRESSURE
    assert explainer._pressure_type(mutation_transition) == CanonPressureType.GOVERNED_MUTATION_PRESSURE
    attention = explainer.attention_preset_page(
        preset=CanonAttentionPreset.REVIEW_NOW,
        limit_per_group=2,
    )
    assert attention.groups
    group_types = {group.pressure_type for group in attention.groups}
    assert CanonPressureType.APPROVAL_PRESSURE.value in group_types
    assert CanonPressureType.TRUST_PRESSURE.value in group_types
    assert CanonPressureType.GOVERNED_MUTATION_PRESSURE.value in group_types
    approval_group = explainer.attention_group_page(
        preset=CanonAttentionPreset.REVIEW_NOW,
        pressure_type=CanonPressureType.APPROVAL_PRESSURE,
        limit=2,
    )
    assert approval_group.items
    assert approval_group.items[0].transition_id


def test_explanations_classify_follow_up_and_group_bounded_pages(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    conflict_store = ConflictMemoryStore(authority)
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=conflict_store,
        receipt_chain=receipts,
    )
    external = ProvenanceRecord(
        source_type="feed",
        source_label="partner-feed",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    authority.record_trust_state_change(
        source_label="partner-feed",
        previous=None,
        current=TrustClass.AMBIGUOUS_EXTERNAL,
        provenance=external,
    )
    trust_record = authority.remember(
        topic="workflow",
        content="follow-up trust",
        provenance=external,
        kind=MemoryKind.OBSERVATION,
    )
    trust_approval = governed.request_canon_promotion(
        memory_id=trust_record.memory_id,
        requested_by=external,
        reason="approve trust case",
    )
    governed.approve_canon_promotion(
        approval_id=trust_approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
    )
    canon_record = authority.remember(
        topic="identity",
        content="canon significance",
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        kind=MemoryKind.OBSERVATION,
    )
    canon_approval = governed.request_canon_promotion(
        memory_id=canon_record.memory_id,
        requested_by=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        reason="promote canon",
    )
    governed.approve_canon_promotion(
        approval_id=canon_approval.approval_id,
        approver=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
    )
    governance_record = authority.remember(
        topic="governance",
        content="rejected but relevant",
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        kind=MemoryKind.OBSERVATION,
    )
    governance_approval = governed.request_canon_promotion(
        memory_id=governance_record.memory_id,
        requested_by=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        reason="reject later",
    )
    governed.reject_canon_promotion(
        approval_id=governance_approval.approval_id,
        rejected_by=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        trace_ids=new_trace_ids(),
        reason="not ready",
    )
    trust_transition = explainer.ancestry_for_memory(trust_record.memory_id)[-1]
    canon_transition = explainer.ancestry_for_memory(canon_record.memory_id)[-1]
    governance_transition = explainer.ancestry_by_approval(governance_approval.approval_id)[-1]
    assert explainer._follow_up_type(trust_transition) == CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP
    assert explainer._follow_up_type(canon_transition) == CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP
    assert explainer._follow_up_type(governance_transition) == CanonFollowUpType.GOVERNANCE_AFTERCARE
    page = explainer.follow_up_preset_page(
        preset=CanonFollowUpPreset.AFTERCARE_NEEDED_NOW,
        limit_per_group=2,
    )
    assert page.groups
    group = explainer.follow_up_group_page(
        preset=CanonFollowUpPreset.POST_RESOLUTION_GOVERNANCE_RELEVANCE,
        follow_up_type=CanonFollowUpType.GOVERNANCE_AFTERCARE,
        limit=2,
    )
    assert group.items
    assert group.items[0].transition_id


def test_explanations_classify_resolution_and_group_bounded_resolution_views(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    approvals = ApprovalStore()
    conflict_store = ConflictMemoryStore(authority)
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=approvals,
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    explainer = CanonExplanationService(
        authority=authority,
        history_store=history,
        continuity_store=continuity,
        approvals=approvals,
        conflict_store=conflict_store,
        receipt_chain=receipts,
    )
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    approved_record = authority.remember(
        topic="workflow",
        content="approved item",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    approved = governed.request_canon_promotion(
        memory_id=approved_record.memory_id,
        requested_by=operator,
        reason="approve this",
    )
    governed.approve_canon_promotion(
        approval_id=approved.approval_id,
        approver=operator,
        trace_ids=new_trace_ids(),
    )
    rejected_record = authority.remember(
        topic="identity",
        content="reject item",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    rejected = governed.request_canon_promotion(
        memory_id=rejected_record.memory_id,
        requested_by=operator,
        reason="reject this",
    )
    governed.reject_canon_promotion(
        approval_id=rejected.approval_id,
        rejected_by=operator,
        trace_ids=new_trace_ids(),
        reason="not ready",
    )
    cancelled_record = authority.remember(
        topic="cancel",
        content="cancel item",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    cancelled = governed.request_canon_promotion(
        memory_id=cancelled_record.memory_id,
        requested_by=operator,
        reason="cancel this",
    )
    governed.cancel_canon_promotion(
        approval_id=cancelled.approval_id,
        cancelled_by=operator,
        trace_ids=new_trace_ids(),
        reason="withdrawn",
    )
    mutation_record = authority.remember(
        topic="mutation",
        content="stable",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    mutation_approval = governed.request_canon_promotion(
        memory_id=mutation_record.memory_id,
        requested_by=operator,
        reason="promote",
    )
    promoted = governed.approve_canon_promotion(
        approval_id=mutation_approval.approval_id,
        approver=operator,
        trace_ids=new_trace_ids(),
    )
    governed.mutate_canon_with_approval(
        memory_id=promoted.memory_id,
        new_content="stable v2",
        requested_by=operator,
        approver=operator,
        reason="complete mutation",
        trace_ids=new_trace_ids(),
    )
    approved_transition = explainer.ancestry_by_approval(approved.approval_id)[-1]
    rejected_transition = explainer.ancestry_by_approval(rejected.approval_id)[-1]
    mutation_transition = explainer.ancestry_for_memory(promoted.memory_id)[-1]
    assert explainer._resolution_type(approved_transition) in {
        CanonResolutionType.APPROVAL_RESOLVED,
        CanonResolutionType.CONFLICT_RESOLVED,
    }
    assert explainer._resolution_type(rejected_transition) == CanonResolutionType.APPROVAL_RESOLVED
    assert explainer._resolution_type(mutation_transition) == CanonResolutionType.GOVERNED_MUTATION_COMPLETED
    resolution = explainer.resolution_preset_page(
        preset=CanonResolutionPreset.RECENTLY_COMPLETED_GOVERNED_MUTATIONS,
        limit_per_group=2,
    )
    assert resolution.groups
    group = explainer.resolution_group_page(
        preset=CanonResolutionPreset.RECENTLY_COMPLETED_GOVERNED_MUTATIONS,
        resolution_type=CanonResolutionType.GOVERNED_MUTATION_COMPLETED,
        limit=2,
    )
    assert group.items
    assert group.items[0].transition_id
