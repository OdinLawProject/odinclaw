from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from odinclaw.contracts.governance import ActionRequest, GovernanceDecision, GovernanceOutcome
from odinclaw.contracts.audit import CanonAttentionGroup, CanonAttentionPage, CanonAttentionPreset, CanonAuditPreset, CanonBoundedLinkedViewPage, CanonFollowUpGroup, CanonFollowUpPage, CanonFollowUpPreset, CanonFollowUpType, CanonHistoryQuery, CanonLinkedContext, CanonPressureType, CanonResolutionGroup, CanonResolutionPage, CanonResolutionPreset, CanonResolutionType, CanonSummaryPage, CanonTransitionSummary
from odinclaw.contracts.reader import ReaderRequest, ReaderResult
from odinclaw.contracts.shell_state import AuditPanelState, GovernancePanelState, MemoryPanelState, OverloadPanelState, ShellExtensionState, TrustPanelState
from odinclaw.odin.state.signals import BurdenInputs, StabilityInputs, evaluate_burden, evaluate_stability
from odinclaw.odin.state.overload import OverloadSignal, evaluate_overload, concurrent_hold_cap_for, PACING_HOLD_NEW, PACING_ACTIVE
from odinclaw.odin.repair.evidence import RepairReceiptRecord, RollbackEvidence
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.odin.context.engine import OdinContextEngine
from odinclaw.odin.governance.approvals import ApprovalStore
from odinclaw.odin.governance.action_legality import preflight_action
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.explanations import CanonExplanationService
from odinclaw.odin.memory.conflict_store import ConflictMemoryStore
from odinclaw.odin.memory.history import CanonHistoryStore
from odinclaw.odin.memory.governed_mutations import GovernedMemoryMutations
from odinclaw.odin.trust.read_only_reader import read_external_content
from odinclaw.odin.trust.thresholds import evaluate_threshold


@dataclass
class GovernanceHookSet:
    pending_holds: int = 0
    approvals_required: int = 0
    escalations_required: int = 0


@dataclass
class TrustHookSet:
    enabled: bool = True
    blocked_sources: int = 0
    ambiguous_sources: int = 0


@dataclass
class RepairStateStore:
    degraded_mode: bool = False
    persisted: bool = False
    repair_receipts: list[RepairReceiptRecord] = field(default_factory=list)

    def persist(self) -> None:
        self.persisted = True


@dataclass
class LifecycleServices:
    receipt_chain: ReceiptChain
    continuity_store: ContinuityEvidenceStore
    memory_authority: DurableMemoryAuthority
    conflict_store: ConflictMemoryStore
    approvals: ApprovalStore
    canon_history: CanonHistoryStore
    canon_explanations: CanonExplanationService
    governed_memory: GovernedMemoryMutations
    governance_hooks: GovernanceHookSet
    trust_hooks: TrustHookSet
    context_engine: OdinContextEngine


@dataclass
class OdinClawLifecycle:
    services: LifecycleServices
    repair_state: RepairStateStore = field(default_factory=RepairStateStore)
    action_gate_open: bool = False
    startup_steps: list[str] = field(default_factory=list)
    shutdown_steps: list[str] = field(default_factory=list)
    # Phase 7: concurrent hold tracking for pacing
    concurrent_holds: int = 0

    def startup(self) -> ShellExtensionState:
        self.startup_steps.append("trace_receipt_services")
        self.startup_steps.append("continuity_services")
        self.startup_steps.append("durable_memory_authority")
        self.services.memory_authority.load()
        self.startup_steps.append("governance_trust_hooks")
        self.startup_steps.append("context_engine_readiness")
        self.services.context_engine.mark_ready()
        self.action_gate_open = True
        return self.shell_state()

    def shutdown(self) -> ShellExtensionState:
        self.shutdown_steps.append("stop_new_actions")
        self.action_gate_open = False
        self.shutdown_steps.append("flush_receipts")
        self.services.receipt_chain.flush()
        self.shutdown_steps.append("persist_continuity")
        self.services.continuity_store.flush()
        self.shutdown_steps.append("persist_durable_memory")
        self.services.memory_authority.flush()
        self.shutdown_steps.append("persist_repair_state")
        self.repair_state.persist()
        return self.shell_state(shutdown_ready=True)

    def _current_overload_signal(self) -> OverloadSignal:
        """Compute the current overload signal without building the full shell state."""
        receipt_count = self.services.receipt_chain.count()
        continuity_count = self.services.continuity_store.count()
        memory_snapshot = self.services.memory_authority.snapshot()
        burden = evaluate_burden(
            BurdenInputs(
                pending_holds=self.services.governance_hooks.pending_holds,
                approvals_required=self.services.governance_hooks.approvals_required,
                escalations_required=self.services.governance_hooks.escalations_required,
                blocked_sources=self.services.trust_hooks.blocked_sources,
                ambiguous_sources=self.services.trust_hooks.ambiguous_sources,
                active_conflicts=self.services.conflict_store.count(),
                memory_dirty=memory_snapshot.dirty,
                receipt_count=receipt_count,
                continuity_links=continuity_count,
            )
        )
        stability = evaluate_stability(
            StabilityInputs(
                startup_ready=self.services.context_engine.ready,
                shutdown_ready=False,
                accepting_actions=self.action_gate_open,
                degraded_mode=self.repair_state.degraded_mode,
                memory_dirty=memory_snapshot.dirty,
                active_conflicts=self.services.conflict_store.count(),
            )
        )
        return evaluate_overload(
            burden_level=burden.level,
            stability_status=stability.status,
            burden_reasons=burden.reasons,
        )

    def preflight(self, request: ActionRequest) -> GovernanceDecision:
        # Phase 7 — stability regulation: check overload before governance logic.
        overload = self._current_overload_signal()
        if overload.level == PACING_HOLD_NEW:
            # Stability is degraded or burden is critical — hold all new actions.
            return GovernanceDecision(
                outcome=GovernanceOutcome.HOLD,
                reason=f"overload_gate: {', '.join(overload.reasons) or overload.level}",
                risk_notes=tuple(overload.reasons),
            )

        # Phase 7 — pacing: at HIGH burden, enforce concurrent hold cap.
        if overload.level == PACING_ACTIVE:
            cap = concurrent_hold_cap_for(overload.burden_level)
            if self.concurrent_holds >= cap:
                return GovernanceDecision(
                    outcome=GovernanceOutcome.HOLD,
                    reason=f"pacing_cap_reached: concurrent_holds={self.concurrent_holds} cap={cap}",
                    risk_notes=("pacing_cap",),
                )

        decision = preflight_action(request)
        self.services.memory_authority.record_governance_decision(request=request, decision=decision)
        if decision.outcome == GovernanceOutcome.HOLD:
            self.services.governance_hooks.pending_holds += 1
            self.services.governance_hooks.approvals_required += 1
            self.concurrent_holds += 1
        elif decision.outcome == GovernanceOutcome.ESCALATE:
            self.services.governance_hooks.pending_holds += 1
            self.services.governance_hooks.escalations_required += 1
            self.concurrent_holds += 1
        return decision

    def release_hold(self) -> None:
        """Call when a held action is approved or denied to decrement the hold counter."""
        if self.concurrent_holds > 0:
            self.concurrent_holds -= 1

    # ------------------------------------------------------------------
    # Phase 6 — Repair: degraded mode transitions with repair receipts.
    # ------------------------------------------------------------------

    def enter_degraded_mode(self, *, reason: str) -> RepairReceiptRecord:
        """Enter degraded mode and emit a repair receipt."""
        from odinclaw.contracts.action_ids import new_action_id, new_run_id, new_session_id
        from odinclaw.contracts.action_ids import TraceIds
        trace_ids = TraceIds(
            session_id=new_session_id(),
            run_id=new_run_id(),
            action_id=new_action_id(),
        )
        self.repair_state.degraded_mode = True
        receipt = RepairReceiptRecord(
            trace_ids=trace_ids,
            repair_type="enter_degraded_mode",
            reason=reason,
        )
        self.repair_state.repair_receipts.append(receipt)
        return receipt

    def exit_degraded_mode(self, *, reason: str) -> RepairReceiptRecord:
        """Exit degraded mode and emit a repair receipt."""
        from odinclaw.contracts.action_ids import new_action_id, new_run_id, new_session_id
        from odinclaw.contracts.action_ids import TraceIds
        trace_ids = TraceIds(
            session_id=new_session_id(),
            run_id=new_run_id(),
            action_id=new_action_id(),
        )
        self.repair_state.degraded_mode = False
        receipt = RepairReceiptRecord(
            trace_ids=trace_ids,
            repair_type="exit_degraded_mode",
            reason=reason,
        )
        self.repair_state.repair_receipts.append(receipt)
        return receipt

    def record_rollback(
        self,
        *,
        reason: str,
        rolled_back_action_id: str | None = None,
        rolled_back_action_name: str | None = None,
        restored_to_checkpoint: str | None = None,
    ) -> RepairReceiptRecord:
        """Record a rollback event with evidence and emit a repair receipt."""
        from odinclaw.contracts.action_ids import new_action_id, new_run_id, new_session_id
        from odinclaw.contracts.action_ids import TraceIds
        trace_ids = TraceIds(
            session_id=new_session_id(),
            run_id=new_run_id(),
            action_id=new_action_id(),
        )
        evidence = RollbackEvidence(
            trace_ids=trace_ids,
            reason=reason,
            rolled_back_action_id=rolled_back_action_id,
            rolled_back_action_name=rolled_back_action_name,
            restored_to_checkpoint=restored_to_checkpoint,
        )
        receipt = RepairReceiptRecord(
            trace_ids=trace_ids,
            repair_type="rollback",
            reason=reason,
            rollback_evidence=evidence,
        )
        self.repair_state.repair_receipts.append(receipt)
        return receipt

    def ingest_read_only(self, request: ReaderRequest) -> ReaderResult:
        result = read_external_content(request)
        threshold = evaluate_threshold(result.trust_class)
        previous = None
        if result.trust_class == TrustClass.KNOWN_BAD_OR_BLOCKED:
            self.services.trust_hooks.blocked_sources += 1
        elif result.trust_class == TrustClass.AMBIGUOUS_EXTERNAL:
            self.services.trust_hooks.ambiguous_sources += 1
        self.services.memory_authority.record_trust_state_change(
            source_label=request.uri,
            previous=previous,
            current=result.trust_class,
            provenance=result.provenance,
        )
        self.services.memory_authority.remember(
            topic="reader_ingest",
            content=result.sanitized_text,
            provenance=result.provenance,
            kind=__import__("odinclaw.contracts.memory", fromlist=["MemoryKind"]).MemoryKind.OBSERVATION,
            metadata={"uri": request.uri, "reader_restricted": str(threshold.reader_restricted).lower()},
        )
        return result

    def shell_state(self, *, shutdown_ready: bool = False) -> ShellExtensionState:
        receipt_count = self.services.receipt_chain.count()
        continuity_count = self.services.continuity_store.count()
        memory_snapshot = self.services.memory_authority.snapshot()
        burden = evaluate_burden(
            BurdenInputs(
                pending_holds=self.services.governance_hooks.pending_holds,
                approvals_required=self.services.governance_hooks.approvals_required,
                escalations_required=self.services.governance_hooks.escalations_required,
                blocked_sources=self.services.trust_hooks.blocked_sources,
                ambiguous_sources=self.services.trust_hooks.ambiguous_sources,
                active_conflicts=self.services.conflict_store.count(),
                memory_dirty=memory_snapshot.dirty,
                receipt_count=receipt_count,
                continuity_links=continuity_count,
            )
        )
        stability = evaluate_stability(
            StabilityInputs(
                startup_ready=self.services.context_engine.ready,
                shutdown_ready=shutdown_ready,
                accepting_actions=self.action_gate_open,
                degraded_mode=self.repair_state.degraded_mode,
                memory_dirty=memory_snapshot.dirty,
                active_conflicts=self.services.conflict_store.count(),
            )
        )
        # Phase 7 — overload signal computed from burden + stability.
        overload_signal = evaluate_overload(
            burden_level=burden.level,
            stability_status=stability.status,
            burden_reasons=burden.reasons,
        )
        cap = concurrent_hold_cap_for(burden.level)
        return ShellExtensionState(
            startup_ready=self.services.context_engine.ready,
            shutdown_ready=shutdown_ready,
            accepting_actions=self.action_gate_open,
            degraded_mode=self.repair_state.degraded_mode,
            governance=GovernancePanelState(
                pending_holds=self.services.governance_hooks.pending_holds,
                approvals_required=self.services.governance_hooks.approvals_required,
            ),
            audit=AuditPanelState(
                receipt_count=receipt_count,
                continuity_links=continuity_count,
            ),
            memory=MemoryPanelState(
                durable_records=len(memory_snapshot.records),
                dirty=memory_snapshot.dirty,
            ),
            trust=TrustPanelState(
                blocked_sources=self.services.trust_hooks.blocked_sources,
                ambiguous_sources=self.services.trust_hooks.ambiguous_sources,
                active_conflicts=self.services.conflict_store.count(),
            ),
            burden=burden,
            stability=stability,
            overload=OverloadPanelState(
                triggered=overload_signal.triggered,
                level=overload_signal.level,
                reasons=overload_signal.reasons,
                concurrent_holds=self.concurrent_holds,
                concurrent_hold_cap=cap,
            ),
        )

    def canon_summaries(self, query: CanonHistoryQuery) -> tuple[CanonTransitionSummary, ...]:
        return self.services.canon_explanations.query_transition_summaries(query)

    def canon_summary_page(self, query: CanonHistoryQuery) -> CanonSummaryPage:
        return self.services.canon_explanations.page_transition_summaries(query)

    def canon_linked_context(self, transition_id: str) -> CanonLinkedContext:
        return self.services.canon_explanations.linked_context(transition_id)

    def canon_bounded_preset_page(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
        ) -> CanonBoundedLinkedViewPage:
        return self.services.canon_explanations.preset_bounded_views(
            preset=preset,
            topic=topic,
            lineage_id=lineage_id,
            cursor=cursor,
            limit=limit,
        )

    def canon_attention_preset_page(
        self,
        *,
        preset: CanonAttentionPreset,
        limit_per_group: int = 3,
    ) -> CanonAttentionPage:
        return self.services.canon_explanations.attention_preset_page(
            preset=preset,
            limit_per_group=limit_per_group,
        )

    def canon_attention_group_page(
        self,
        *,
        preset: CanonAttentionPreset,
        pressure_type: CanonPressureType,
        cursor: str | None = None,
        limit: int = 5,
    ) -> CanonAttentionGroup:
        return self.services.canon_explanations.attention_group_page(
            preset=preset,
            pressure_type=pressure_type,
            cursor=cursor,
            limit=limit,
        )

    def canon_follow_up_preset_page(
        self,
        *,
        preset: CanonFollowUpPreset,
        limit_per_group: int = 3,
    ) -> CanonFollowUpPage:
        return self.services.canon_explanations.follow_up_preset_page(
            preset=preset,
            limit_per_group=limit_per_group,
        )

    def canon_follow_up_group_page(
        self,
        *,
        preset: CanonFollowUpPreset,
        follow_up_type: CanonFollowUpType,
        cursor: str | None = None,
        limit: int = 5,
    ) -> CanonFollowUpGroup:
        return self.services.canon_explanations.follow_up_group_page(
            preset=preset,
            follow_up_type=follow_up_type,
            cursor=cursor,
            limit=limit,
        )

    def canon_resolution_preset_page(
        self,
        *,
        preset: CanonResolutionPreset,
        limit_per_group: int = 3,
    ) -> CanonResolutionPage:
        return self.services.canon_explanations.resolution_preset_page(
            preset=preset,
            limit_per_group=limit_per_group,
        )

    def canon_resolution_group_page(
        self,
        *,
        preset: CanonResolutionPreset,
        resolution_type: CanonResolutionType,
        cursor: str | None = None,
        limit: int = 5,
    ) -> CanonResolutionGroup:
        return self.services.canon_explanations.resolution_group_page(
            preset=preset,
            resolution_type=resolution_type,
            cursor=cursor,
            limit=limit,
        )

    def canon_preset_page(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
    ) -> CanonSummaryPage:
        return self.services.canon_explanations.preset_transition_summaries(
            preset=preset,
            topic=topic,
            lineage_id=lineage_id,
            cursor=cursor,
            limit=limit,
        )


def build_lifecycle(root: Path) -> OdinClawLifecycle:
    receipt_chain = ReceiptChain(root / "receipts.jsonl")
    continuity_store = ContinuityEvidenceStore(root / "continuity.jsonl")
    memory_authority = DurableMemoryAuthority(root / "memory.json", receipt_chain=receipt_chain)
    conflict_store = ConflictMemoryStore(memory_authority)
    approvals = ApprovalStore()
    canon_history = CanonHistoryStore(root / "canon_history.jsonl")
    governed_memory = GovernedMemoryMutations(
        authority=memory_authority,
        approvals=approvals,
        receipt_chain=receipt_chain,
        continuity_store=continuity_store,
        history_store=canon_history,
    )
    canon_explanations = CanonExplanationService(
        authority=memory_authority,
        history_store=canon_history,
        continuity_store=continuity_store,
        approvals=approvals,
        conflict_store=conflict_store,
        receipt_chain=receipt_chain,
    )
    context_engine = OdinContextEngine(
        continuity_store=continuity_store,
        receipt_chain=receipt_chain,
        memory_authority=memory_authority,
        conflict_store=conflict_store,
    )
    services = LifecycleServices(
        receipt_chain=receipt_chain,
        continuity_store=continuity_store,
        memory_authority=memory_authority,
        conflict_store=conflict_store,
        approvals=approvals,
        canon_history=canon_history,
        canon_explanations=canon_explanations,
        governed_memory=governed_memory,
        governance_hooks=GovernanceHookSet(),
        trust_hooks=TrustHookSet(),
        context_engine=context_engine,
    )
    return OdinClawLifecycle(services=services)
