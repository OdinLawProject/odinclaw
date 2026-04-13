from __future__ import annotations

from odinclaw.contracts.audit import CanonApprovalContext, CanonAttentionGroup, CanonAttentionItem, CanonAttentionPage, CanonAttentionPreset, CanonAuditPreset, CanonBoundedLinkedView, CanonBoundedLinkedViewPage, CanonConflictContext, CanonFollowUpGroup, CanonFollowUpItem, CanonFollowUpPage, CanonFollowUpPreset, CanonFollowUpType, CanonGovernanceReceiptContext, CanonHistoryQuery, CanonLinkedContext, CanonPressureType, CanonResolutionGroup, CanonResolutionItem, CanonResolutionPage, CanonResolutionPreset, CanonResolutionType, CanonSemanticDiff, CanonStateSummary, CanonSummaryPage, CanonTransitionExplanation, CanonTransitionSummary, CanonTrustContext
from odinclaw.contracts.memory import CanonTransitionRecord, DurableMemoryRecord, MemoryKind
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.odin.governance.approvals import ApprovalStore
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.conflict_store import ConflictMemoryStore
from odinclaw.odin.memory.history import CanonHistoryStore


class CanonExplanationService:
    def __init__(
        self,
        *,
        authority: DurableMemoryAuthority,
        history_store: CanonHistoryStore,
        continuity_store: ContinuityEvidenceStore,
        approvals: ApprovalStore | None = None,
        conflict_store: ConflictMemoryStore | None = None,
        receipt_chain: ReceiptChain | None = None,
    ) -> None:
        self.authority = authority
        self.history_store = history_store
        self.continuity_store = continuity_store
        self.approvals = approvals
        self.conflict_store = conflict_store
        self.receipt_chain = receipt_chain

    def ancestry_for_memory(self, memory_id: str) -> tuple[CanonTransitionRecord, ...]:
        history = self.history_store.list_for_memory(memory_id)
        return tuple(sorted(history, key=lambda item: item.requested_at))

    def ancestry_by_approval(self, approval_id: str) -> tuple[CanonTransitionRecord, ...]:
        return tuple(record for record in self.history_store.iter_records() if record.approval_id == approval_id)

    def ancestry_by_prior_state(self, prior_state_id: str) -> tuple[CanonTransitionRecord, ...]:
        return tuple(record for record in self.history_store.iter_records() if record.prior_state_id == prior_state_id)

    def prior_state(self, transition_id: str) -> CanonStateSummary | None:
        transition = self.history_store.get(transition_id)
        if transition.prior_state_id is None:
            return None
        return self._state_summary_from_transition(
            memory_id=transition.prior_state_id,
            content=transition.prior_content,
        )

    def explain_transition(self, transition_id: str) -> CanonTransitionExplanation:
        transition = self.history_store.get(transition_id)
        prior_state = self.prior_state(transition_id)
        resulting_state = (
            None
            if transition.resulting_state_id is None
            else self._state_summary_from_transition(
                memory_id=transition.resulting_state_id,
                content=transition.resulting_content,
            )
        )
        diff = self._diff(prior_state, resulting_state, transition)
        linked = self.linked_context(transition_id)
        lineage = tuple(record.transition_id for record in self.ancestry_for_memory(transition.memory_id))
        return CanonTransitionExplanation(
            transition_id=transition.transition_id,
            transition_summary=f"{transition.transition_type}:{transition.status}:{transition.reason}",
            approval_reference=transition.approval_id,
            prior_state=prior_state,
            resulting_state=resulting_state,
            semantic_delta=diff,
            continuity_summary=linked.continuity_summary,
            lineage=lineage,
        )

    def linked_context(self, transition_id: str) -> CanonLinkedContext:
        transition = self.history_store.get(transition_id)
        approval = self._approval_context(transition)
        trust = self._trust_context(transition)
        conflict = self._conflict_context(transition)
        continuity = tuple(
            link.reason
            for link in self.continuity_store.iter_links()
            if link.prior_state_id == transition.prior_state_id
            or link.resulting_state_id == transition.resulting_state_id
            or link.approval_id == transition.approval_id
        )
        return CanonLinkedContext(
            transition_id=transition.transition_id,
            approval=approval,
            trust=trust,
            conflict=conflict,
            continuity_summary=continuity,
        )

    def query_transition_summaries(self, query: CanonHistoryQuery) -> tuple[CanonTransitionSummary, ...]:
        return self.page_transition_summaries(query).items

    def page_transition_summaries(self, query: CanonHistoryQuery) -> CanonSummaryPage:
        records = self.history_store.iter_records()
        filtered = [record for record in records if self._matches(record, query)]
        ordered = sorted(filtered, key=lambda record: self._sort_key(record, query))
        start = 0
        if query.cursor is not None:
            for index, record in enumerate(ordered):
                if self._cursor_for(record) == query.cursor:
                    start = index + 1
                    break
        page_records = ordered[start : start + query.limit]
        next_cursor = None
        if start + query.limit < len(ordered) and page_records:
            next_cursor = self._cursor_for(page_records[-1])
        return CanonSummaryPage(
            items=tuple(self._summary(record) for record in page_records),
            next_cursor=next_cursor,
        )

    def preset_transition_summaries(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
    ) -> CanonSummaryPage:
        query = self._query_for_preset(
            preset=preset,
            topic=topic,
            lineage_id=lineage_id,
            cursor=cursor,
            limit=limit,
        )
        page = self.page_transition_summaries(query)
        return CanonSummaryPage(items=page.items, next_cursor=page.next_cursor, preset=preset.value)

    def preset_bounded_views(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
    ) -> CanonBoundedLinkedViewPage:
        page = self.preset_transition_summaries(
            preset=preset,
            topic=topic,
            lineage_id=lineage_id,
            cursor=cursor,
            limit=limit,
        )
        return CanonBoundedLinkedViewPage(
            items=tuple(self.bounded_view(item.transition_id) for item in page.items),
            next_cursor=page.next_cursor,
            preset=preset.value,
        )

    def bounded_view(self, transition_id: str) -> CanonBoundedLinkedView:
        transition = self.history_store.get(transition_id)
        summary = self._summary(transition)
        linked = self.linked_context(transition_id)
        governance_receipt = self._governance_receipt_context(transition)
        return CanonBoundedLinkedView(
            summary=summary,
            governance_receipt=governance_receipt,
            linked_context=linked,
            why_this_matters_now=self._why_this_matters_now(
                transition=transition,
                summary=summary,
                linked=linked,
                governance_receipt=governance_receipt,
            ),
        )

    def attention_preset_page(
        self,
        *,
        preset: CanonAttentionPreset,
        limit_per_group: int = 3,
    ) -> CanonAttentionPage:
        records = self._records_for_attention_preset(preset)
        grouped = self._group_attention_items(records, limit_per_group=limit_per_group)
        return CanonAttentionPage(groups=grouped, preset=preset.value)

    def attention_group_page(
        self,
        *,
        preset: CanonAttentionPreset,
        pressure_type: CanonPressureType,
        cursor: str | None = None,
        limit: int = 5,
    ) -> CanonAttentionGroup:
        records = [
            record
            for record in self._records_for_attention_preset(preset)
            if self._pressure_type(record) == pressure_type
        ]
        ordered = sorted(records, key=self._attention_sort_key)
        start = 0
        if cursor is not None:
            for index, record in enumerate(ordered):
                if self._cursor_for(record) == cursor:
                    start = index + 1
                    break
        page_records = ordered[start : start + limit]
        next_cursor = None
        if start + limit < len(ordered) and page_records:
            next_cursor = self._cursor_for(page_records[-1])
        return CanonAttentionGroup(
            pressure_type=pressure_type.value,
            items=tuple(self._attention_item(record) for record in page_records),
            next_cursor=next_cursor,
        )

    def follow_up_preset_page(
        self,
        *,
        preset: CanonFollowUpPreset,
        limit_per_group: int = 3,
    ) -> CanonFollowUpPage:
        records = self._records_for_follow_up_preset(preset)
        grouped = self._group_follow_up_items(records, limit_per_group=limit_per_group)
        return CanonFollowUpPage(groups=grouped, preset=preset.value)

    def follow_up_group_page(
        self,
        *,
        preset: CanonFollowUpPreset,
        follow_up_type: CanonFollowUpType,
        cursor: str | None = None,
        limit: int = 5,
    ) -> CanonFollowUpGroup:
        records = [
            record
            for record in self._records_for_follow_up_preset(preset)
            if self._follow_up_type(record) == follow_up_type
        ]
        ordered = sorted(records, key=self._follow_up_sort_key)
        start = 0
        if cursor is not None:
            for index, record in enumerate(ordered):
                if self._cursor_for(record) == cursor:
                    start = index + 1
                    break
        page_records = ordered[start : start + limit]
        next_cursor = None
        if start + limit < len(ordered) and page_records:
            next_cursor = self._cursor_for(page_records[-1])
        return CanonFollowUpGroup(
            follow_up_type=follow_up_type.value,
            items=tuple(self._follow_up_item(record) for record in page_records),
            next_cursor=next_cursor,
        )

    def resolution_preset_page(
        self,
        *,
        preset: CanonResolutionPreset,
        limit_per_group: int = 3,
    ) -> CanonResolutionPage:
        records = self._records_for_resolution_preset(preset)
        grouped = self._group_resolution_items(records, limit_per_group=limit_per_group)
        return CanonResolutionPage(groups=grouped, preset=preset.value)

    def resolution_group_page(
        self,
        *,
        preset: CanonResolutionPreset,
        resolution_type: CanonResolutionType,
        cursor: str | None = None,
        limit: int = 5,
    ) -> CanonResolutionGroup:
        records = [
            record
            for record in self._records_for_resolution_preset(preset)
            if self._resolution_type(record) == resolution_type
        ]
        ordered = sorted(records, key=self._resolution_sort_key)
        start = 0
        if cursor is not None:
            for index, record in enumerate(ordered):
                if self._cursor_for(record) == cursor:
                    start = index + 1
                    break
        page_records = ordered[start : start + limit]
        next_cursor = None
        if start + limit < len(ordered) and page_records:
            next_cursor = self._cursor_for(page_records[-1])
        return CanonResolutionGroup(
            resolution_type=resolution_type.value,
            items=tuple(self._resolution_item(record) for record in page_records),
            next_cursor=next_cursor,
        )

    def summary_to_explanation(self, transition_id: str) -> CanonTransitionExplanation:
        return self.explain_transition(transition_id)

    def _matches(self, record: CanonTransitionRecord, query: CanonHistoryQuery) -> bool:
        if query.topic is not None and query.topic.lower() not in record.metadata.get("topic", "").lower():
            return False
        if query.mutation_class is not None and query.mutation_class != record.transition_type:
            return False
        if query.transition_types and record.transition_type not in query.transition_types:
            return False
        if query.approval_id is not None and record.approval_id != query.approval_id:
            return False
        if query.lineage_id is not None and record.lineage_id != query.lineage_id:
            return False
        if query.outcome_type is not None and query.outcome_type not in record.status:
            return False
        if query.require_linked_approval and self._approval_context(record) is None:
            return False
        if query.require_linked_trust and self._trust_context(record) is None:
            return False
        if query.require_linked_conflict and self._conflict_context(record) is None:
            return False
        return True

    def _query_for_preset(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None,
        lineage_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> CanonHistoryQuery:
        if preset == CanonAuditPreset.RECENT_CHANGES:
            return CanonHistoryQuery(limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.TOPIC_CHANGES:
            return CanonHistoryQuery(topic=topic, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.RECENT_APPROVED:
            return CanonHistoryQuery(outcome_type="approved", limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.REJECTED_CANCELLED:
            return CanonHistoryQuery(outcome_type="rejected", limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.LINEAGE_FOCUS:
            return CanonHistoryQuery(lineage_id=lineage_id, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.HIGH_SIGNIFICANCE:
            return CanonHistoryQuery(mutation_class="mutation", limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.WITH_APPROVAL_CONTEXT:
            return CanonHistoryQuery(require_linked_approval=True, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.WITH_TRUST_CONTEXT:
            return CanonHistoryQuery(require_linked_trust=True, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.WITH_CONFLICT_CONTEXT:
            return CanonHistoryQuery(require_linked_conflict=True, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.HIGH_SIGNIFICANCE_GOVERNED:
            return CanonHistoryQuery(
                require_linked_approval=True,
                transition_types=("promotion", "mutation", "demotion"),
                limit=limit,
                cursor=cursor,
            )
        if preset == CanonAuditPreset.RELEVANCE_NOW_APPROVAL:
            return CanonHistoryQuery(require_linked_approval=True, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.RELEVANCE_NOW_TRUST:
            return CanonHistoryQuery(require_linked_trust=True, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.RELEVANCE_NOW_CONFLICT:
            return CanonHistoryQuery(require_linked_conflict=True, limit=limit, cursor=cursor)
        if preset == CanonAuditPreset.RELEVANCE_NOW_GOVERNED:
            return CanonHistoryQuery(
                require_linked_approval=True,
                transition_types=("promotion", "mutation", "demotion"),
                limit=limit,
                cursor=cursor,
            )
        return CanonHistoryQuery(limit=limit, cursor=cursor)

    def _sort_key(self, record: CanonTransitionRecord, query: CanonHistoryQuery) -> tuple[int, int, str]:
        topic_score = 0
        if query.topic is not None and query.topic.lower() in record.metadata.get("topic", "").lower():
            topic_score = -3
        approval_score = -2 if query.approval_id is not None and record.approval_id == query.approval_id else 0
        lineage_score = -1 if query.lineage_id is not None and record.lineage_id == query.lineage_id else 0
        linked_governance_score = -2 if self._approval_context(record) is not None else 0
        linked_conflict_score = -1 if self._conflict_context(record) is not None else 0
        return (
            topic_score + approval_score + lineage_score + linked_governance_score + linked_conflict_score,
            -int(record.requested_at.timestamp()),
            record.transition_id,
        )

    def _summary(self, record: CanonTransitionRecord) -> CanonTransitionSummary:
        linked = self.linked_context(record.transition_id)
        diff = self._diff(
            self._state_summary_from_transition(memory_id=record.prior_state_id, content=record.prior_content)
            if record.prior_state_id is not None
            else None,
            self._state_summary_from_transition(memory_id=record.resulting_state_id, content=record.resulting_content)
            if record.resulting_state_id is not None
            else None,
            record,
        )
        topic = record.metadata.get("topic") or self._topic_for_record(record)
        return CanonTransitionSummary(
            transition_id=record.transition_id,
            topic=topic,
            mutation_class=record.transition_type,
            approval_reference=record.approval_id,
            approval_status=record.status,
            lineage_cue=record.lineage_id or record.memory_id,
            semantic_delta_cue=self._semantic_delta_cue(diff),
            ordering_marker=record.requested_at.isoformat(),
            trust_cue=None if linked.trust is None else linked.trust.summary,
            conflict_cue=None if linked.conflict is None else linked.conflict.summary,
            continuity_cue=None if not linked.continuity_summary else linked.continuity_summary[0],
        )

    def _cursor_for(self, record: CanonTransitionRecord) -> str:
        return f"{record.requested_at.isoformat()}|{record.transition_id}"

    def _topic_for_record(self, record: CanonTransitionRecord) -> str:
        try:
            durable = self.authority.get(record.memory_id)
            return durable.topic
        except KeyError:
            return "unknown"

    def _semantic_delta_cue(self, diff: CanonSemanticDiff) -> str:
        if diff.changed_fields:
            return f"changed:{','.join(sorted(diff.changed_fields.keys()))}"
        if diff.added_fields:
            return f"added:{','.join(sorted(diff.added_fields.keys()))}"
        if diff.removed_fields:
            return f"removed:{','.join(sorted(diff.removed_fields.keys()))}"
        return "no-field-delta"

    def _state_summary_from_transition(self, *, memory_id: str, content: str | None) -> CanonStateSummary | None:
        try:
            record = self.authority.get(memory_id)
        except KeyError:
            return None
        return CanonStateSummary(
            memory_id=record.memory_id,
            topic=record.topic,
            tier=record.tier.value,
            kind=record.kind.value,
            content=content if content is not None else record.content,
            receipt_id=record.linked_receipt_id,
            run_id=record.linked_run_id,
        )

    def _diff(
        self,
        prior: CanonStateSummary | None,
        resulting: CanonStateSummary | None,
        transition: CanonTransitionRecord,
    ) -> CanonSemanticDiff:
        prior_data = {} if prior is None else {"topic": prior.topic, "tier": prior.tier, "kind": prior.kind, "content": prior.content}
        resulting_data = {} if resulting is None else {"topic": resulting.topic, "tier": resulting.tier, "kind": resulting.kind, "content": resulting.content}
        added = {key: value for key, value in resulting_data.items() if key not in prior_data}
        removed = {key: value for key, value in prior_data.items() if key not in resulting_data}
        changed = {
            key: (prior_data[key], resulting_data[key])
            for key in prior_data.keys() & resulting_data.keys()
            if prior_data[key] != resulting_data[key]
        }
        annotations: list[str] = []
        if transition.metadata.get("approval_receipt_id"):
            annotations.append("approval receipt linked")
        return CanonSemanticDiff(
            added_fields=added,
            removed_fields=removed,
            changed_fields=changed,
            transition_reason=transition.reason,
            transition_type=transition.transition_type,
            annotations=tuple(annotations),
        )

    def _approval_context(self, transition: CanonTransitionRecord) -> CanonApprovalContext | None:
        if transition.approval_id is None or self.approvals is None:
            return None
        approval = self.approvals.get(transition.approval_id)
        return CanonApprovalContext(
            approval_id=approval.approval_id,
            status=approval.status.value,
            requested_action=approval.requested_action,
            reason=approval.reason,
        )

    def _trust_context(self, transition: CanonTransitionRecord) -> CanonTrustContext | None:
        source_label = self._source_label_for_transition(transition)
        if source_label is None:
            return None
        records = [
            record
            for record in self.authority.snapshot().records
            if record.kind == MemoryKind.TRUST and record.metadata.get("source_label") == source_label
        ]
        if not records:
            return None
        latest = records[-1]
        state = latest.metadata.get("current", latest.content)
        return CanonTrustContext(
            source_label=source_label,
            trust_state=state,
            summary=f"{source_label}:{state}",
        )

    def _conflict_context(self, transition: CanonTransitionRecord) -> CanonConflictContext | None:
        if self.conflict_store is None:
            return None
        topic = transition.metadata.get("topic") or self._topic_for_record(transition)
        conflicts = self.conflict_store.relevant(topic=topic, limit=1)
        if not conflicts:
            return None
        conflict = conflicts[-1]
        return CanonConflictContext(
            topic=conflict.topic,
            severity=conflict.severity,
            summary=f"{conflict.severity}:{conflict.claim[:32]}",
        )

    def _source_label_for_transition(self, transition: CanonTransitionRecord) -> str | None:
        try:
            record = self.authority.get(transition.memory_id)
        except KeyError:
            return None
        if record.provenance is None:
            return None
        return record.provenance.source_label

    def _governance_receipt_context(self, transition: CanonTransitionRecord) -> CanonGovernanceReceiptContext | None:
        if self.receipt_chain is None:
            return None
        receipts = list(self.receipt_chain.iter_receipts())
        chosen = self._select_best_governance_receipt(transition, receipts)
        if chosen is None:
            return None
        return CanonGovernanceReceiptContext(
            receipt_id=chosen.receipt_id,
            receipt_type=chosen.receipt_type,
            action_name=chosen.action_name,
            ordering_marker=chosen.created_at.isoformat(),
            summary=f"{chosen.receipt_type}:{chosen.action_name}",
        )

    def _select_best_governance_receipt(
        self,
        transition: CanonTransitionRecord,
        receipts: list[ReceiptRecord],
    ) -> ReceiptRecord | None:
        candidates: list[tuple[int, ReceiptRecord]] = []
        for receipt in receipts:
            score = self._receipt_relevance_score(transition, receipt)
            if score is None:
                continue
            candidates.append((score, receipt))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], -int(item[1].created_at.timestamp()), item[1].receipt_id))
        return candidates[0][1]

    def _receipt_relevance_score(
        self,
        transition: CanonTransitionRecord,
        receipt: ReceiptRecord,
    ) -> int | None:
        if transition.receipt_id is not None and receipt.receipt_id == transition.receipt_id:
            return 0
        approval_receipt_id = transition.metadata.get("approval_receipt_id")
        if approval_receipt_id is not None and receipt.receipt_id == approval_receipt_id:
            return 1
        if transition.approval_id is not None and receipt.data.get("approval_id") == transition.approval_id:
            if receipt.receipt_type in {"canon_promotion_approved", "canon_promotion", "canon_mutation"}:
                return 2
            return 3
        if receipt.data.get("memory_id") == transition.memory_id and receipt.receipt_type.startswith("canon_"):
            return 4
        return None

    def _why_this_matters_now(
        self,
        *,
        transition: CanonTransitionRecord,
        summary: CanonTransitionSummary,
        linked: CanonLinkedContext,
        governance_receipt: CanonGovernanceReceiptContext | None,
    ) -> str:
        if linked.conflict is not None and transition.status in {"requested", "rejected", "cancelled"}:
            return "currently conflict-blocked canon candidate"
        if linked.trust is not None and linked.trust.trust_state in {
            TrustClass.AMBIGUOUS_EXTERNAL.value,
            TrustClass.UNTRUSTED_EXTERNAL.value,
            TrustClass.KNOWN_BAD_OR_BLOCKED.value,
        }:
            return "trust-downgraded canon transition"
        if governance_receipt is not None and transition.status.startswith("approved"):
            return f"recently approved durable {transition.transition_type}"
        if transition.transition_type == "mutation":
            return "lineage-near high-significance mutation"
        if linked.conflict is not None:
            return "canon transition with current conflict note"
        return f"recent canon {summary.mutation_class}"

    def _records_for_attention_preset(self, preset: CanonAttentionPreset) -> tuple[CanonTransitionRecord, ...]:
        records = self.history_store.iter_records()
        if preset == CanonAttentionPreset.NEEDS_APPROVAL:
            return tuple(record for record in records if self._pressure_type(record) == CanonPressureType.APPROVAL_PRESSURE)
        if preset == CanonAttentionPreset.CONFLICT_BLOCKED:
            return tuple(record for record in records if self._pressure_type(record) == CanonPressureType.CONFLICT_PRESSURE)
        if preset == CanonAttentionPreset.TRUST_DOWNGRADED:
            return tuple(record for record in records if self._pressure_type(record) == CanonPressureType.TRUST_PRESSURE)
        if preset == CanonAttentionPreset.RECENT_HIGH_SIGNIFICANCE:
            return tuple(
                record
                for record in records
                if record.transition_type in {"promotion", "mutation", "demotion"}
                and record.status.startswith("approved")
            )
        if preset == CanonAttentionPreset.UNRESOLVED_GOVERNED_MUTATIONS:
            return tuple(
                record
                for record in records
                if record.transition_type in {"promotion", "mutation", "demotion"}
                and not record.status.startswith("approved")
            )
        if preset == CanonAttentionPreset.REVIEW_NOW:
            return tuple(
                record
                for record in records
                if self._pressure_type(record) in {
                    CanonPressureType.APPROVAL_PRESSURE,
                    CanonPressureType.CONFLICT_PRESSURE,
                    CanonPressureType.TRUST_PRESSURE,
                    CanonPressureType.GOVERNED_MUTATION_PRESSURE,
                }
            )
        return records

    def _group_attention_items(
        self,
        records: tuple[CanonTransitionRecord, ...],
        *,
        limit_per_group: int,
    ) -> tuple[CanonAttentionGroup, ...]:
        grouped: dict[CanonPressureType, list[CanonTransitionRecord]] = {}
        for record in records:
            pressure = self._pressure_type(record)
            grouped.setdefault(pressure, []).append(record)
        ordered_groups: list[CanonAttentionGroup] = []
        for pressure in (
            CanonPressureType.APPROVAL_PRESSURE,
            CanonPressureType.CONFLICT_PRESSURE,
            CanonPressureType.TRUST_PRESSURE,
            CanonPressureType.GOVERNED_MUTATION_PRESSURE,
            CanonPressureType.REVIEW_ONLY,
        ):
            items = grouped.get(pressure, [])
            if not items:
                continue
            ordered = sorted(items, key=self._attention_sort_key)
            page_items = ordered[:limit_per_group]
            next_cursor = None
            if len(ordered) > limit_per_group:
                next_cursor = self._cursor_for(page_items[-1])
            ordered_groups.append(
                CanonAttentionGroup(
                    pressure_type=pressure.value,
                    items=tuple(self._attention_item(record) for record in page_items),
                    next_cursor=next_cursor,
                )
            )
        return tuple(ordered_groups)

    def _attention_item(self, record: CanonTransitionRecord) -> CanonAttentionItem:
        view = self.bounded_view(record.transition_id)
        linked_cue = None
        if view.linked_context is not None:
            if view.linked_context.approval is not None:
                linked_cue = f"approval:{view.linked_context.approval.status}"
            elif view.linked_context.conflict is not None:
                linked_cue = view.linked_context.conflict.summary
            elif view.linked_context.trust is not None:
                linked_cue = view.linked_context.trust.summary
        return CanonAttentionItem(
            summary=view.summary,
            pressure_type=self._pressure_type(record).value,
            why_this_matters_now=view.why_this_matters_now,
            linked_cue=linked_cue,
            transition_id=record.transition_id,
        )

    def _pressure_type(self, record: CanonTransitionRecord) -> CanonPressureType:
        linked = self.linked_context(record.transition_id)
        if record.status == "requested":
            return CanonPressureType.APPROVAL_PRESSURE
        if linked.conflict is not None and record.status in {"requested", "rejected", "cancelled"}:
            return CanonPressureType.CONFLICT_PRESSURE
        if linked.trust is not None and linked.trust.trust_state in {
            TrustClass.AMBIGUOUS_EXTERNAL.value,
            TrustClass.UNTRUSTED_EXTERNAL.value,
            TrustClass.KNOWN_BAD_OR_BLOCKED.value,
        }:
            return CanonPressureType.TRUST_PRESSURE
        if record.transition_type in {"mutation", "demotion"} or (
            record.transition_type == "promotion" and not record.status.startswith("approved")
        ):
            return CanonPressureType.GOVERNED_MUTATION_PRESSURE
        return CanonPressureType.REVIEW_ONLY

    def _attention_sort_key(self, record: CanonTransitionRecord) -> tuple[int, int, str]:
        pressure_rank = {
            CanonPressureType.APPROVAL_PRESSURE: 0,
            CanonPressureType.CONFLICT_PRESSURE: 1,
            CanonPressureType.TRUST_PRESSURE: 2,
            CanonPressureType.GOVERNED_MUTATION_PRESSURE: 3,
            CanonPressureType.REVIEW_ONLY: 4,
        }[self._pressure_type(record)]
        return (pressure_rank, -int(record.requested_at.timestamp()), record.transition_id)

    def _records_for_follow_up_preset(self, preset: CanonFollowUpPreset) -> tuple[CanonTransitionRecord, ...]:
        records = self.history_store.iter_records()
        if preset == CanonFollowUpPreset.CANON_SIGNIFICANCE_CHANGED:
            return tuple(record for record in records if self._follow_up_type(record) == CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP)
        if preset == CanonFollowUpPreset.TRUST_POSTURE_CHANGED_AFTER_RESOLUTION:
            return tuple(record for record in records if self._follow_up_type(record) == CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP)
        if preset == CanonFollowUpPreset.CONTINUITY_LINEAGE_MATERIALLY_SHIFTED:
            return tuple(record for record in records if self._follow_up_type(record) == CanonFollowUpType.CONTINUITY_LINEAGE_FOLLOW_UP)
        if preset == CanonFollowUpPreset.RESOLVED_BUT_REVIEW_WORTHY:
            return tuple(record for record in records if self._follow_up_type(record) == CanonFollowUpType.REVIEW_FOLLOW_UP)
        if preset == CanonFollowUpPreset.POST_RESOLUTION_GOVERNANCE_RELEVANCE:
            return tuple(record for record in records if self._follow_up_type(record) == CanonFollowUpType.GOVERNANCE_AFTERCARE)
        if preset == CanonFollowUpPreset.AFTERCARE_NEEDED_NOW:
            return tuple(
                record
                for record in records
                if self._follow_up_type(record) in {
                    CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP,
                    CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP,
                    CanonFollowUpType.CONTINUITY_LINEAGE_FOLLOW_UP,
                    CanonFollowUpType.GOVERNANCE_AFTERCARE,
                }
            )
        return ()

    def _records_for_resolution_preset(self, preset: CanonResolutionPreset) -> tuple[CanonTransitionRecord, ...]:
        records = self.history_store.iter_records()
        if preset == CanonResolutionPreset.RECENTLY_APPROVED:
            return tuple(record for record in records if record.status == "approved_applied")
        if preset == CanonResolutionPreset.RECENTLY_REJECTED:
            return tuple(record for record in records if record.status == "rejected")
        if preset == CanonResolutionPreset.RECENTLY_CANCELLED:
            return tuple(record for record in records if record.status == "cancelled")
        if preset == CanonResolutionPreset.CONFLICT_CLEARED:
            return tuple(
                record
                for record in records
                if record.status == "approved_applied" and self._conflict_context(record) is None
            )
        if preset == CanonResolutionPreset.TRUST_RESTORED:
            return tuple(
                record
                for record in records
                if self._resolution_type(record) == CanonResolutionType.TRUST_RECOVERED
            )
        if preset == CanonResolutionPreset.RECENTLY_COMPLETED_GOVERNED_MUTATIONS:
            return tuple(
                record
                for record in records
                if record.transition_type in {"promotion", "mutation", "demotion"}
                and record.status == "approved_applied"
            )
        return ()

    def _group_follow_up_items(
        self,
        records: tuple[CanonTransitionRecord, ...],
        *,
        limit_per_group: int,
    ) -> tuple[CanonFollowUpGroup, ...]:
        grouped: dict[CanonFollowUpType, list[CanonTransitionRecord]] = {}
        for record in records:
            follow_up = self._follow_up_type(record)
            grouped.setdefault(follow_up, []).append(record)
        ordered_groups: list[CanonFollowUpGroup] = []
        for follow_up in (
            CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP,
            CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP,
            CanonFollowUpType.CONTINUITY_LINEAGE_FOLLOW_UP,
            CanonFollowUpType.GOVERNANCE_AFTERCARE,
            CanonFollowUpType.REVIEW_FOLLOW_UP,
        ):
            items = grouped.get(follow_up, [])
            if not items:
                continue
            ordered = sorted(items, key=self._follow_up_sort_key)
            page_items = ordered[:limit_per_group]
            next_cursor = None
            if len(ordered) > limit_per_group:
                next_cursor = self._cursor_for(page_items[-1])
            ordered_groups.append(
                CanonFollowUpGroup(
                    follow_up_type=follow_up.value,
                    items=tuple(self._follow_up_item(record) for record in page_items),
                    next_cursor=next_cursor,
                )
            )
        return tuple(ordered_groups)

    def _group_resolution_items(
        self,
        records: tuple[CanonTransitionRecord, ...],
        *,
        limit_per_group: int,
    ) -> tuple[CanonResolutionGroup, ...]:
        grouped: dict[CanonResolutionType, list[CanonTransitionRecord]] = {}
        for record in records:
            resolution = self._resolution_type(record)
            grouped.setdefault(resolution, []).append(record)
        ordered_groups: list[CanonResolutionGroup] = []
        for resolution in (
            CanonResolutionType.APPROVAL_RESOLVED,
            CanonResolutionType.CONFLICT_RESOLVED,
            CanonResolutionType.TRUST_RECOVERED,
            CanonResolutionType.GOVERNED_MUTATION_COMPLETED,
            CanonResolutionType.REVIEW_CLOSED,
        ):
            items = grouped.get(resolution, [])
            if not items:
                continue
            ordered = sorted(items, key=self._resolution_sort_key)
            page_items = ordered[:limit_per_group]
            next_cursor = None
            if len(ordered) > limit_per_group:
                next_cursor = self._cursor_for(page_items[-1])
            ordered_groups.append(
                CanonResolutionGroup(
                    resolution_type=resolution.value,
                    items=tuple(self._resolution_item(record) for record in page_items),
                    next_cursor=next_cursor,
                )
            )
        return tuple(ordered_groups)

    def _follow_up_item(self, record: CanonTransitionRecord) -> CanonFollowUpItem:
        view = self.bounded_view(record.transition_id)
        linked_cue = None
        if view.linked_context is not None:
            if view.linked_context.trust is not None:
                linked_cue = view.linked_context.trust.summary
            elif view.linked_context.approval is not None:
                linked_cue = f"approval:{view.linked_context.approval.status}"
            elif view.linked_context.conflict is not None:
                linked_cue = view.linked_context.conflict.summary
            elif view.linked_context.continuity_summary:
                linked_cue = view.linked_context.continuity_summary[0]
        return CanonFollowUpItem(
            summary=view.summary,
            follow_up_type=self._follow_up_type(record).value,
            why_follow_up_now=self._why_follow_up_now(record, view),
            linked_cue=linked_cue,
            transition_id=record.transition_id,
        )

    def _resolution_item(self, record: CanonTransitionRecord) -> CanonResolutionItem:
        view = self.bounded_view(record.transition_id)
        linked_cue = None
        if view.linked_context is not None:
            if view.linked_context.approval is not None:
                linked_cue = f"approval:{view.linked_context.approval.status}"
            elif view.linked_context.trust is not None:
                linked_cue = view.linked_context.trust.summary
            elif view.linked_context.conflict is not None:
                linked_cue = view.linked_context.conflict.summary
        return CanonResolutionItem(
            summary=view.summary,
            resolution_type=self._resolution_type(record).value,
            why_resolved_now=self._why_resolved_now(record, view),
            linked_cue=linked_cue,
            transition_id=record.transition_id,
        )

    def _follow_up_type(self, record: CanonTransitionRecord) -> CanonFollowUpType:
        linked = self.linked_context(record.transition_id)
        if record.status not in {"approved_applied", "rejected", "cancelled"}:
            return CanonFollowUpType.REVIEW_FOLLOW_UP
        if linked.trust is not None:
            return CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP
        if record.transition_type in {"promotion", "demotion"} and record.status == "approved_applied":
            return CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP
        if linked.continuity_summary and len(self.ancestry_for_memory(record.memory_id)) > 1:
            return CanonFollowUpType.CONTINUITY_LINEAGE_FOLLOW_UP
        if record.approval_id is not None:
            return CanonFollowUpType.GOVERNANCE_AFTERCARE
        return CanonFollowUpType.REVIEW_FOLLOW_UP

    def _why_follow_up_now(self, record: CanonTransitionRecord, view: CanonBoundedLinkedView) -> str:
        follow_up = self._follow_up_type(record)
        if follow_up == CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP:
            return "canon tier significance changed after resolution"
        if follow_up == CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP:
            return "trust posture remains materially relevant after resolution"
        if follow_up == CanonFollowUpType.CONTINUITY_LINEAGE_FOLLOW_UP:
            return "continuity lineage shifted across resolved transition chain"
        if follow_up == CanonFollowUpType.GOVERNANCE_AFTERCARE:
            return "resolved transition still carries governance aftercare relevance"
        return f"resolved transition remains review-worthy via {record.status}"

    def _follow_up_sort_key(self, record: CanonTransitionRecord) -> tuple[int, int, str]:
        follow_up_rank = {
            CanonFollowUpType.CANON_SIGNIFICANCE_FOLLOW_UP: 0,
            CanonFollowUpType.TRUST_POSTURE_FOLLOW_UP: 1,
            CanonFollowUpType.CONTINUITY_LINEAGE_FOLLOW_UP: 2,
            CanonFollowUpType.GOVERNANCE_AFTERCARE: 3,
            CanonFollowUpType.REVIEW_FOLLOW_UP: 4,
        }[self._follow_up_type(record)]
        return (follow_up_rank, -int(record.requested_at.timestamp()), record.transition_id)

    def _resolution_type(self, record: CanonTransitionRecord) -> CanonResolutionType:
        linked = self.linked_context(record.transition_id)
        if record.status in {"rejected", "cancelled", "approved_applied"}:
            if record.transition_type in {"mutation", "demotion"} and record.status == "approved_applied":
                return CanonResolutionType.GOVERNED_MUTATION_COMPLETED
            if record.status == "approved_applied" and linked.trust is not None and linked.trust.trust_state in {
                TrustClass.TRUSTED_OPERATOR.value,
                TrustClass.TRUSTED_SELF.value,
                TrustClass.TRUSTED_INTERNAL_KNOWLEDGE.value,
                TrustClass.APPROVED_PROVIDER.value,
                TrustClass.APPROVED_TOOL.value,
            }:
                return CanonResolutionType.TRUST_RECOVERED
            if record.status == "approved_applied" and linked.conflict is None:
                return CanonResolutionType.CONFLICT_RESOLVED
            if record.approval_id is not None:
                return CanonResolutionType.APPROVAL_RESOLVED
        return CanonResolutionType.REVIEW_CLOSED

    def _why_resolved_now(self, record: CanonTransitionRecord, view: CanonBoundedLinkedView) -> str:
        resolution = self._resolution_type(record)
        if resolution == CanonResolutionType.APPROVAL_RESOLVED:
            return f"approval resolved as {record.status}"
        if resolution == CanonResolutionType.CONFLICT_RESOLVED:
            return "no current conflict on transition topic"
        if resolution == CanonResolutionType.TRUST_RECOVERED:
            return "transition source now within trusted threshold"
        if resolution == CanonResolutionType.GOVERNED_MUTATION_COMPLETED:
            return "governed mutation completed and applied"
        return f"review closed via {record.status}"

    def _resolution_sort_key(self, record: CanonTransitionRecord) -> tuple[int, int, str]:
        resolution_rank = {
            CanonResolutionType.APPROVAL_RESOLVED: 0,
            CanonResolutionType.CONFLICT_RESOLVED: 1,
            CanonResolutionType.TRUST_RECOVERED: 2,
            CanonResolutionType.GOVERNED_MUTATION_COMPLETED: 3,
            CanonResolutionType.REVIEW_CLOSED: 4,
        }[self._resolution_type(record)]
        return (resolution_rank, -int(record.requested_at.timestamp()), record.transition_id)
