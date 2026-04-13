from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from odinclaw.contracts.action_ids import TraceIds, new_action_id
from odinclaw.contracts.approval import ApprovalRequest
from odinclaw.contracts.audit import CanonAttentionPreset, CanonAuditPreset, CanonFollowUpPreset, CanonFollowUpType, CanonHistoryQuery, CanonPressureType, CanonResolutionPreset, CanonResolutionType
from odinclaw.contracts.governance import ActionRequest, GovernanceDecision
from odinclaw.contracts.context import ContextAssembly
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.reader import ReaderRequest, ReaderResult
from odinclaw.contracts.shell_state import ShellExtensionState
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.orchestration.lifecycle import OdinClawLifecycle, build_lifecycle
from odinclaw.shell.session_runtime import SessionRuntime, start_session


@dataclass
class ShellProductBridge:
    lifecycle: OdinClawLifecycle
    runtime: SessionRuntime

    def launch(self) -> ShellExtensionState:
        return self.lifecycle.startup()

    def shutdown(self) -> ShellExtensionState:
        self.runtime.close_to_new_actions()
        return self.lifecycle.shutdown()

    def extension_state(self) -> ShellExtensionState:
        return self.lifecycle.shell_state()

    def context_for_ui(self, *, topic: str | None = None) -> ContextAssembly:
        return self.lifecycle.services.context_engine.assemble_context(
            session_id=self.runtime.session_id,
            run_id=self.runtime.current_run.run_id,
            topic=topic,
            session_memory=tuple(action.action_name for action in self.runtime.actions),
        )

    def preflight_action(self, request: ActionRequest) -> GovernanceDecision:
        return self.lifecycle.preflight(request)

    def read_only_ingest(self, request: ReaderRequest) -> ReaderResult:
        return self.lifecycle.ingest_read_only(request)

    def request_canon_promotion(
        self,
        *,
        memory_id: str,
        requested_by: ProvenanceRecord,
        reason: str,
    ) -> ApprovalRequest:
        return self.lifecycle.services.governed_memory.request_canon_promotion(
            memory_id=memory_id,
            requested_by=requested_by,
            reason=reason,
        )

    def approve_canon_promotion(
        self,
        *,
        approval_id: str,
        approver: ProvenanceRecord,
    ):
        return self.lifecycle.services.governed_memory.approve_canon_promotion(
            approval_id=approval_id,
            approver=approver,
            trace_ids=TraceIds(
                session_id=self.runtime.session_id,
                run_id=self.runtime.current_run.run_id,
                action_id=new_action_id(),
            ),
        )

    def reject_canon_promotion(
        self,
        *,
        approval_id: str,
        rejected_by: ProvenanceRecord,
        reason: str,
    ):
        return self.lifecycle.services.governed_memory.reject_canon_promotion(
            approval_id=approval_id,
            rejected_by=rejected_by,
            reason=reason,
            trace_ids=TraceIds(
                session_id=self.runtime.session_id,
                run_id=self.runtime.current_run.run_id,
                action_id=new_action_id(),
            ),
        )

    def cancel_canon_promotion(
        self,
        *,
        approval_id: str,
        cancelled_by: ProvenanceRecord,
        reason: str,
    ):
        return self.lifecycle.services.governed_memory.cancel_canon_promotion(
            approval_id=approval_id,
            cancelled_by=cancelled_by,
            reason=reason,
            trace_ids=TraceIds(
                session_id=self.runtime.session_id,
                run_id=self.runtime.current_run.run_id,
                action_id=new_action_id(),
            ),
        )

    def explain_canon_transition(self, transition_id: str):
        return self.lifecycle.services.canon_explanations.explain_transition(transition_id)

    def canon_transition_summaries(self, query: CanonHistoryQuery):
        return self.lifecycle.canon_summaries(query)

    def canon_transition_page(self, query: CanonHistoryQuery):
        return self.lifecycle.canon_summary_page(query)

    def canon_linked_context(self, transition_id: str):
        return self.lifecycle.canon_linked_context(transition_id)

    def canon_preset_page(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
    ):
        return self.lifecycle.canon_preset_page(
            preset=preset,
            topic=topic,
            lineage_id=lineage_id,
            cursor=cursor,
            limit=limit,
        )

    def canon_linked_preset_page(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
    ):
        return self.canon_preset_page(
            preset=preset,
            topic=topic,
            lineage_id=lineage_id,
            cursor=cursor,
            limit=limit,
        )

    def canon_bounded_preset_page(
        self,
        *,
        preset: CanonAuditPreset,
        topic: str | None = None,
        lineage_id: str | None = None,
        cursor: str | None = None,
        limit: int = 10,
    ):
        return self.lifecycle.canon_bounded_preset_page(
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
    ):
        return self.lifecycle.canon_attention_preset_page(
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
    ):
        return self.lifecycle.canon_attention_group_page(
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
    ):
        return self.lifecycle.canon_follow_up_preset_page(
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
    ):
        return self.lifecycle.canon_follow_up_group_page(
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
    ):
        return self.lifecycle.canon_resolution_preset_page(
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
    ):
        return self.lifecycle.canon_resolution_group_page(
            preset=preset,
            resolution_type=resolution_type,
            cursor=cursor,
            limit=limit,
        )


def attach_odinclaw_shell(root: Path, session_name: str) -> ShellProductBridge:
    lifecycle = build_lifecycle(root)
    runtime = start_session(
        session_name,
        receipt_chain=lifecycle.services.receipt_chain,
        continuity_store=lifecycle.services.continuity_store,
    )
    return ShellProductBridge(lifecycle=lifecycle, runtime=runtime)
