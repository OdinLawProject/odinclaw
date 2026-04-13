from __future__ import annotations

from odinclaw.contracts.action_ids import TraceIds
from odinclaw.contracts.approval import ApprovalRequest, ApprovalStatus
from odinclaw.contracts.continuity import ContinuityLink
from odinclaw.contracts.events import utc_now
from odinclaw.contracts.memory import CanonTransitionRecord, DurableMemoryRecord, DurableMutationClass, MemoryKind, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.odin.governance.approvals import ApprovalStore
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.history import CanonHistoryStore


class GovernedMemoryMutations:
    def __init__(
        self,
        *,
        authority: DurableMemoryAuthority,
        approvals: ApprovalStore,
        receipt_chain: ReceiptChain,
        continuity_store: ContinuityEvidenceStore,
        history_store: CanonHistoryStore,
    ) -> None:
        self.authority = authority
        self.approvals = approvals
        self.receipt_chain = receipt_chain
        self.continuity_store = continuity_store
        self.history_store = history_store

    def classify_mutation(
        self,
        *,
        record: DurableMemoryRecord | None = None,
        target_tier: MemoryTier | None = None,
        kind: MemoryKind | None = None,
    ) -> DurableMutationClass:
        resolved_kind = kind if kind is not None else (None if record is None else record.kind)
        resolved_tier = target_tier if target_tier is not None else (None if record is None else record.tier)
        if resolved_kind in {MemoryKind.GOVERNANCE, MemoryKind.TRUST}:
            return DurableMutationClass.TRUST_GOVERNANCE_SIGNIFICANT_UPDATE
        if record is not None and record.tier == MemoryTier.PROVISIONAL and resolved_tier == MemoryTier.CANON:
            return DurableMutationClass.PROMOTION_CANDIDATE
        if record is not None and record.tier == MemoryTier.CANON:
            return DurableMutationClass.CANON_MUTATION
        return DurableMutationClass.LOW_SIGNIFICANCE_PROVISIONAL_WRITE

    def request_canon_promotion(
        self,
        *,
        memory_id: str,
        requested_by: ProvenanceRecord,
        reason: str,
    ) -> ApprovalRequest:
        record = self.authority.get(memory_id)
        if self.classify_mutation(record=record, target_tier=MemoryTier.CANON) != DurableMutationClass.PROMOTION_CANDIDATE:
            raise ValueError("record is not a promotion candidate")
        approval = self.approvals.create(
            subject_type="memory",
            subject_id=memory_id,
            requested_action="promote_to_canon",
            requested_by=requested_by,
            reason=reason,
            metadata={"topic": record.topic, "kind": record.kind.value},
        )
        self.history_store.append(
            CanonTransitionRecord(
                transition_id=self.history_store.new_transition_id(),
                memory_id=memory_id,
                transition_type="promotion",
                status="requested",
                reason=reason,
                requested_at=utc_now(),
                requested_by=requested_by,
                approval_id=approval.approval_id,
                prior_state_id=record.memory_id,
                prior_content=record.content,
                lineage_id=record.memory_id,
                metadata={"topic": record.topic},
            )
        )
        return approval

    def reject_canon_promotion(
        self,
        *,
        approval_id: str,
        rejected_by: ProvenanceRecord,
        trace_ids: TraceIds,
        reason: str,
    ) -> ApprovalRequest:
        approval = self.approvals.reject(approval_id)
        record = self.authority.get(approval.subject_id)
        receipt = self.receipt_chain.append(
            ReceiptRecord(
                receipt_id=trace_ids.action_id,
                receipt_type="canon_promotion_rejected",
                trace_ids=trace_ids,
                action_name=f"reject:{record.topic}",
                created_at=utc_now(),
                provenance=rejected_by,
                data={"memory_id": record.memory_id, "approval_id": approval_id, "reason": reason},
            )
        )
        self.history_store.append(
            CanonTransitionRecord(
                transition_id=self.history_store.new_transition_id(),
                memory_id=record.memory_id,
                transition_type="promotion",
                status="rejected",
                reason=reason,
                requested_at=utc_now(),
                requested_by=approval.requested_by,
                approval_id=approval_id,
                approved_by=rejected_by.source_label,
                prior_state_id=record.memory_id,
                prior_content=record.content,
                receipt_id=receipt.receipt_id,
                lineage_id=record.memory_id,
            )
        )
        return approval

    def cancel_canon_promotion(
        self,
        *,
        approval_id: str,
        cancelled_by: ProvenanceRecord,
        trace_ids: TraceIds,
        reason: str,
    ) -> ApprovalRequest:
        approval = self.approvals.cancel(approval_id)
        record = self.authority.get(approval.subject_id)
        receipt = self.receipt_chain.append(
            ReceiptRecord(
                receipt_id=trace_ids.action_id,
                receipt_type="canon_promotion_cancelled",
                trace_ids=trace_ids,
                action_name=f"cancel:{record.topic}",
                created_at=utc_now(),
                provenance=cancelled_by,
                data={"memory_id": record.memory_id, "approval_id": approval_id, "reason": reason},
            )
        )
        self.history_store.append(
            CanonTransitionRecord(
                transition_id=self.history_store.new_transition_id(),
                memory_id=record.memory_id,
                transition_type="promotion",
                status="cancelled",
                reason=reason,
                requested_at=utc_now(),
                requested_by=approval.requested_by,
                approval_id=approval_id,
                approved_by=cancelled_by.source_label,
                prior_state_id=record.memory_id,
                prior_content=record.content,
                receipt_id=receipt.receipt_id,
                lineage_id=record.memory_id,
            )
        )
        return approval

    def approve_canon_promotion(
        self,
        *,
        approval_id: str,
        approver: ProvenanceRecord,
        trace_ids: TraceIds,
    ) -> DurableMemoryRecord:
        approval = self.approvals.approve(approval_id)
        if approval.status != ApprovalStatus.APPROVED:
            raise ValueError("approval is not approved")
        record = self.authority.get(approval.subject_id)
        if self.authority.has_blocking_conflicts(record.topic):
            raise ValueError("blocking conflicts prevent canon promotion")
        if record.provenance is not None and record.provenance.trust_class in {
            TrustClass.UNTRUSTED_EXTERNAL,
            TrustClass.KNOWN_BAD_OR_BLOCKED,
        }:
            raise ValueError("low-trust record cannot be promoted to canon")
        promoted = self.authority._promote_to_canon(
            record.memory_id,
            metadata={"approval_id": approval.approval_id, "approved_by": approver.source_label},
        )
        receipt = self.receipt_chain.append(
            ReceiptRecord(
                receipt_id=trace_ids.action_id,
                receipt_type="canon_promotion_approved",
                trace_ids=trace_ids,
                action_name=f"approve:{record.topic}",
                created_at=utc_now(),
                provenance=approver,
                data={"memory_id": record.memory_id, "approval_id": approval.approval_id},
            )
        )
        applied_receipt = self.receipt_chain.append(
            ReceiptRecord(
                receipt_id=trace_ids.action_id,
                receipt_type="canon_promotion",
                trace_ids=trace_ids,
                action_name=f"promote:{record.topic}",
                created_at=utc_now(),
                provenance=approver,
                data={"memory_id": record.memory_id, "approval_id": approval.approval_id},
            )
        )
        self.continuity_store.append(
            ContinuityLink(
                session_id=trace_ids.session_id,
                run_id=trace_ids.run_id,
                parent_session_id=None,
                parent_run_id=record.linked_run_id,
                reason=f"canon_promotion:{record.memory_id}",
                recorded_at=utc_now(),
                prior_state_id=record.memory_id,
                resulting_state_id=promoted.memory_id,
                approval_id=approval.approval_id,
            )
        )
        self.history_store.append(
            CanonTransitionRecord(
                transition_id=self.history_store.new_transition_id(),
                memory_id=record.memory_id,
                transition_type="promotion",
                status="approved_applied",
                reason=approval.reason,
                requested_at=utc_now(),
                requested_by=approval.requested_by,
                approval_id=approval.approval_id,
                approved_by=approver.source_label,
                prior_state_id=record.memory_id,
                prior_content=record.content,
                resulting_state_id=promoted.memory_id,
                resulting_content=promoted.content,
                receipt_id=applied_receipt.receipt_id,
                lineage_id=record.memory_id,
                metadata={"approval_receipt_id": receipt.receipt_id},
            )
        )
        self.authority.attach_receipt(promoted.memory_id, applied_receipt.receipt_id, trace_ids.run_id)
        return self.authority.get(promoted.memory_id)

    def demote_with_governance(
        self,
        *,
        memory_id: str,
        reason: str,
        provenance: ProvenanceRecord,
        trace_ids: TraceIds,
    ) -> DurableMemoryRecord:
        demoted = self.authority.demote_to_provisional(memory_id, reason=reason)
        receipt = self.receipt_chain.append(
            ReceiptRecord(
                receipt_id=trace_ids.action_id,
                receipt_type="canon_demotion",
                trace_ids=trace_ids,
                action_name=f"demote:{demoted.topic}",
                created_at=utc_now(),
                provenance=provenance,
                data={"memory_id": demoted.memory_id, "reason": reason},
            )
        )
        self.continuity_store.append(
            ContinuityLink(
                session_id=trace_ids.session_id,
                run_id=trace_ids.run_id,
                parent_session_id=None,
                parent_run_id=demoted.linked_run_id,
                reason=f"canon_demotion:{demoted.memory_id}",
                recorded_at=utc_now(),
                prior_state_id=memory_id,
                resulting_state_id=demoted.memory_id,
            )
        )
        self.history_store.append(
            CanonTransitionRecord(
                transition_id=self.history_store.new_transition_id(),
                memory_id=demoted.memory_id,
                transition_type="demotion",
                status="applied",
                reason=reason,
                requested_at=utc_now(),
                requested_by=provenance,
                prior_state_id=memory_id,
                prior_content=record.content if (record := self.authority.get(demoted.memory_id)) else None,
                resulting_state_id=demoted.memory_id,
                resulting_content=demoted.content,
                receipt_id=receipt.receipt_id,
                lineage_id=demoted.memory_id,
            )
        )
        self.authority.attach_receipt(demoted.memory_id, receipt.receipt_id, trace_ids.run_id)
        return self.authority.get(demoted.memory_id)

    def mutate_canon_with_approval(
        self,
        *,
        memory_id: str,
        new_content: str,
        requested_by: ProvenanceRecord,
        approver: ProvenanceRecord,
        reason: str,
        trace_ids: TraceIds,
    ) -> DurableMemoryRecord:
        request = self.approvals.create(
            subject_type="memory",
            subject_id=memory_id,
            requested_action="mutate_canon",
            requested_by=requested_by,
            reason=reason,
        )
        self.approvals.approve(request.approval_id)
        current = self.authority.get(memory_id)
        updated = self.authority._mutate_canon(
            memory_id,
            new_content=new_content,
            metadata={"approval_id": request.approval_id, "approved_by": approver.source_label},
        )
        receipt = self.receipt_chain.append(
            ReceiptRecord(
                receipt_id=trace_ids.action_id,
                receipt_type="canon_mutation",
                trace_ids=trace_ids,
                action_name=f"mutate:{updated.topic}",
                created_at=utc_now(),
                provenance=approver,
                data={"memory_id": updated.memory_id, "approval_id": request.approval_id},
            )
        )
        self.continuity_store.append(
            ContinuityLink(
                session_id=trace_ids.session_id,
                run_id=trace_ids.run_id,
                parent_session_id=None,
                parent_run_id=current.linked_run_id,
                reason=f"canon_mutation:{updated.memory_id}",
                recorded_at=utc_now(),
                prior_state_id=current.memory_id,
                resulting_state_id=updated.memory_id,
                approval_id=request.approval_id,
            )
        )
        self.history_store.append(
            CanonTransitionRecord(
                transition_id=self.history_store.new_transition_id(),
                memory_id=updated.memory_id,
                transition_type="mutation",
                status="approved_applied",
                reason=reason,
                requested_at=utc_now(),
                requested_by=requested_by,
                approval_id=request.approval_id,
                approved_by=approver.source_label,
                prior_state_id=current.memory_id,
                prior_content=current.content,
                resulting_state_id=updated.memory_id,
                resulting_content=updated.content,
                receipt_id=receipt.receipt_id,
                lineage_id=updated.memory_id,
            )
        )
        self.authority.attach_receipt(updated.memory_id, receipt.receipt_id, trace_ids.run_id)
        return self.authority.get(updated.memory_id)
