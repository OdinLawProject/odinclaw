from pathlib import Path

from odinclaw.contracts.action_ids import new_trace_ids
from odinclaw.contracts.approval import ApprovalStatus
from odinclaw.contracts.memory import DurableMutationClass, MemoryKind, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.odin.governance.approvals import ApprovalStore
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.governed_mutations import GovernedMemoryMutations
from odinclaw.odin.memory.history import CanonHistoryStore


def test_governed_mutation_classification_and_promotion_linkage(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=ApprovalStore(),
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=CanonHistoryStore(tmp_path / "canon_history.jsonl"),
    )
    requested_by = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = authority.remember(
        topic="workflow",
        content="This is a candidate durable lesson.",
        provenance=requested_by,
        kind=MemoryKind.OBSERVATION,
    )
    assert governed.classify_mutation(record=record, target_tier=MemoryTier.CANON) == DurableMutationClass.PROMOTION_CANDIDATE
    approval = governed.request_canon_promotion(
        memory_id=record.memory_id,
        requested_by=requested_by,
        reason="validated by operator",
    )
    promoted = governed.approve_canon_promotion(
        approval_id=approval.approval_id,
        approver=requested_by,
        trace_ids=new_trace_ids(),
    )
    assert promoted.tier == MemoryTier.CANON
    assert receipts.query(ReceiptQuery(receipt_type="canon_promotion"))
    links = continuity.iter_links()
    assert links[0].approval_id == approval.approval_id
    assert links[0].prior_state_id == record.memory_id
    history = governed.history_store.list_for_memory(record.memory_id)
    assert history[-1].prior_content == record.content
    assert history[-1].resulting_content == promoted.content


def test_governed_demotion_emits_receipt(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=ApprovalStore(),
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=CanonHistoryStore(tmp_path / "canon_history.jsonl"),
    )
    provenance = ProvenanceRecord(
        source_type="doctrine",
        source_label="odin-base",
        trust_class=TrustClass.TRUSTED_INTERNAL_KNOWLEDGE,
    )
    record = authority.remember(
        topic="identity",
        content="Stable canon item",
        provenance=provenance,
        kind=MemoryKind.DOCTRINE,
    )
    demoted = governed.demote_with_governance(
        memory_id=record.memory_id,
        reason="contradicted",
        provenance=provenance,
        trace_ids=new_trace_ids(),
    )
    assert demoted.tier == MemoryTier.PROVISIONAL
    assert receipts.query(ReceiptQuery(receipt_type="canon_demotion"))


def test_rejection_and_cancellation_are_explicit_and_receipted(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    history = CanonHistoryStore(tmp_path / "canon_history.jsonl")
    authority = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    authority.load()
    governed = GovernedMemoryMutations(
        authority=authority,
        approvals=ApprovalStore(),
        receipt_chain=receipts,
        continuity_store=continuity,
        history_store=history,
    )
    operator = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    record = authority.remember(
        topic="workflow",
        content="candidate",
        provenance=operator,
        kind=MemoryKind.OBSERVATION,
    )
    rejected = governed.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="not ready")
    rejected = governed.reject_canon_promotion(
        approval_id=rejected.approval_id,
        rejected_by=operator,
        trace_ids=new_trace_ids(),
        reason="insufficient validation",
    )
    assert rejected.status == ApprovalStatus.REJECTED
    cancelled = governed.request_canon_promotion(memory_id=record.memory_id, requested_by=operator, reason="later")
    cancelled = governed.cancel_canon_promotion(
        approval_id=cancelled.approval_id,
        cancelled_by=operator,
        trace_ids=new_trace_ids(),
        reason="operator withdrew",
    )
    assert cancelled.status == ApprovalStatus.CANCELLED
    assert receipts.query(ReceiptQuery(receipt_type="canon_promotion_rejected"))
    assert receipts.query(ReceiptQuery(receipt_type="canon_promotion_cancelled"))
