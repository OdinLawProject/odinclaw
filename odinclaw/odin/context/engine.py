from __future__ import annotations

from odinclaw.contracts.context import ContextAssembly, ContextItem
from odinclaw.contracts.memory import DurableMemoryRecord
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore, ContinuityLink
from odinclaw.odin.memory.conflict_store import ConflictMemoryStore
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.arbitration import arbitrate_memory, session_memory_from_events
from odinclaw.odin.trust.thresholds import context_item_allowed, evaluate_threshold


class OdinContextEngine:
    def __init__(
        self,
        *,
        continuity_store: ContinuityEvidenceStore,
        receipt_chain: ReceiptChain,
        memory_authority: DurableMemoryAuthority,
        conflict_store: ConflictMemoryStore | None = None,
    ) -> None:
        self.continuity_store = continuity_store
        self.receipt_chain = receipt_chain
        self.memory_authority = memory_authority
        self.conflict_store = conflict_store
        self._ready = False

    def mark_ready(self) -> None:
        self._ready = True

    @property
    def ready(self) -> bool:
        return self._ready

    def assemble_context(
        self,
        *,
        session_id: str,
        run_id: str,
        topic: str | None = None,
        limit: int = 8,
        trust_state: TrustClass | None = None,
        session_memory: tuple[str, ...] = (),
    ) -> ContextAssembly:
        continuity = tuple(self.continuity_store.list_for_session(session_id))
        receipts = tuple(self.receipt_chain.query_for_context(run_id=run_id, limit=limit))
        recall = self.memory_authority.recall(topic=topic, trust_state=trust_state, limit=limit)
        doctrine = self.memory_authority.doctrine_records()
        durable_memory = recall.canon + recall.provisional
        conflicts = () if self.conflict_store is None else self.conflict_store.relevant(topic=topic, limit=3)
        arbitration = arbitrate_memory(
            canon_reads=[record.content for record in recall.canon],
            provisional_reads=[record.content for record in recall.provisional],
            conflict_reads=[record.content for record in recall.conflicts],
            session_reads=list(session_memory_from_events(session_memory)),
            trust_state=trust_state,
        )
        items = self._items_from_sources(
            continuity=continuity,
            receipts=receipts,
            doctrine=tuple(record for record in doctrine if record.memory_id not in {r.memory_id for r in recall.canon}),
            durable_memory=recall.canon + recall.provisional,
            conflicts=conflicts,
            session_memory=tuple(arbitration.session_reads),
            limit=limit,
        )
        filtered_items = items
        warnings = list(arbitration.warnings)
        if trust_state is not None:
            threshold = evaluate_threshold(trust_state)
            filtered_items = tuple(item for item in items if context_item_allowed(item))
            if threshold.caution is not None:
                warnings.append(threshold.caution)
        return ContextAssembly(
            run_id=run_id,
            items=filtered_items,
            doctrine=doctrine,
            durable_memory=durable_memory,
            memory_recall=recall,
            continuity=continuity,
            receipts=receipts,
            conflicts=conflicts,
            trust_state=trust_state,
            warnings=tuple(warnings + list(recall.warnings)),
        )

    def _items_from_sources(
        self,
        *,
        continuity: tuple[ContinuityLink, ...],
        receipts: tuple[ReceiptRecord, ...],
        doctrine: tuple[DurableMemoryRecord, ...],
        durable_memory: tuple[DurableMemoryRecord, ...],
        conflicts: tuple,
        session_memory: tuple[str, ...],
        limit: int,
    ) -> tuple[ContextItem, ...]:
        items: list[ContextItem] = []
        for record in doctrine:
            items.append(
                ContextItem(
                    kind="doctrine",
                    value=record.content,
                    source=record.topic,
                    metadata={
                        "provenance": record.provenance.source_label if record.provenance else "unknown",
                        "trust_class": (
                            record.provenance.trust_class.value if record.provenance is not None else TrustClass.AMBIGUOUS_EXTERNAL.value
                        ),
                    },
                )
            )
        for record in durable_memory:
            items.append(
                ContextItem(
                    kind="memory",
                    value=record.content,
                    source=record.topic,
                    metadata={
                        "provenance": record.provenance.source_label if record.provenance else "unknown",
                        "trust_class": (
                            record.provenance.trust_class.value if record.provenance is not None else TrustClass.AMBIGUOUS_EXTERNAL.value
                        ),
                    },
                )
            )
        for link in continuity:
            items.append(
                ContextItem(
                    kind="continuity",
                    value=link.reason,
                    source=link.run_id,
                    metadata={"parent_run_id": link.parent_run_id or ""},
                )
            )
        for receipt in receipts:
            items.append(
                ContextItem(
                    kind="receipt",
                    value=receipt.action_name,
                    source=receipt.receipt_type,
                    metadata={
                        "provenance": receipt.provenance.source_label,
                        "trust_class": receipt.provenance.trust_class.value,
                    },
                )
            )
        for conflict in conflicts:
            items.append(
                ContextItem(
                    kind="conflict",
                    value=f"{conflict.claim} <> {conflict.conflicting_claim}",
                    source=conflict.topic,
                    metadata={
                        "severity": conflict.severity,
                        "trust_class": conflict.provenance.trust_class.value,
                    },
                )
            )
        for entry in session_memory:
            items.append(
                ContextItem(
                    kind="session",
                    value=entry,
                    source="shell-session",
                    metadata={"authority": "session-local"},
                )
            )
        return tuple(items[:limit])
