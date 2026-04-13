from __future__ import annotations

from dataclasses import dataclass, field

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.action_ids import TraceIds, new_action_id, new_run_id, new_session_id
from odinclaw.contracts.events import OdinClawEvent, RunPhase, RunTrace, utc_now
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore, ContinuityLink


@dataclass
class SessionRuntime:
    session_name: str
    session_id: str
    current_run: RunTrace
    receipt_chain: ReceiptChain | None = None
    continuity_store: ContinuityEvidenceStore | None = None
    actions: list[OdinClawEvent] = field(default_factory=list)
    accepting_actions: bool = True

    def begin_run(
        self,
        *,
        parent_session_id: str | None = None,
        parent_run_id: str | None = None,
        reason: str = "session_run_started",
    ) -> RunTrace:
        self.current_run = RunTrace(
            session_name=self.session_name,
            session_id=self.session_id,
            run_id=new_run_id(),
            parent_session_id=parent_session_id,
            parent_run_id=parent_run_id,
        )
        if self.continuity_store is not None:
            self.continuity_store.append(
                ContinuityLink(
                    session_id=self.session_id,
                    run_id=self.current_run.run_id,
                    parent_session_id=parent_session_id,
                    parent_run_id=parent_run_id,
                    reason=reason,
                    recorded_at=utc_now(),
                )
            )
        return self.current_run

    def close_to_new_actions(self) -> None:
        self.accepting_actions = False
        self.current_run = RunTrace(
            session_name=self.current_run.session_name,
            session_id=self.current_run.session_id,
            run_id=self.current_run.run_id,
            phase=RunPhase.SHUTTING_DOWN,
            started_at=self.current_run.started_at,
            parent_session_id=self.current_run.parent_session_id,
            parent_run_id=self.current_run.parent_run_id,
        )

    def record_action(
        self,
        *,
        action_name: str,
        action_class: ActionClass,
        provenance: ProvenanceRecord,
        payload: dict[str, object] | None = None,
        meaningful: bool = True,
        receipt_type: str = "action",
    ) -> OdinClawEvent:
        if not self.accepting_actions:
            raise RuntimeError("session runtime is not accepting new actions")
        event = OdinClawEvent(
            event_type=receipt_type,
            trace_ids=TraceIds(
                session_id=self.session_id,
                run_id=self.current_run.run_id,
                action_id=new_action_id(),
            ),
            action_name=action_name,
            action_class=action_class,
            meaningful=meaningful,
            payload=dict(payload or {}),
        )
        self.actions.append(event)
        if meaningful and self.receipt_chain is not None:
            self.receipt_chain.append(
                ReceiptRecord(
                    receipt_id=event.trace_ids.action_id,
                    receipt_type=receipt_type,
                    trace_ids=event.trace_ids,
                    action_name=action_name,
                    created_at=event.occurred_at,
                    provenance=provenance,
                    data={
                        "action_class": action_class.value,
                        "payload": event.payload,
                    },
                )
            )
        return event


def start_session(
    session_name: str,
    *,
    receipt_chain: ReceiptChain | None = None,
    continuity_store: ContinuityEvidenceStore | None = None,
    parent_session_id: str | None = None,
    parent_run_id: str | None = None,
) -> SessionRuntime:
    session_id = new_session_id()
    runtime = SessionRuntime(
        session_name=session_name,
        session_id=session_id,
        current_run=RunTrace(
            session_name=session_name,
            session_id=session_id,
            run_id=new_run_id(),
            parent_session_id=parent_session_id,
            parent_run_id=parent_run_id,
        ),
        receipt_chain=receipt_chain,
        continuity_store=continuity_store,
    )
    if continuity_store is not None:
        continuity_store.append(
            ContinuityLink(
                session_id=session_id,
                run_id=runtime.current_run.run_id,
                parent_session_id=parent_session_id,
                parent_run_id=parent_run_id,
                reason="session_started",
                recorded_at=utc_now(),
            )
        )
    return runtime
