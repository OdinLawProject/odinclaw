from __future__ import annotations

from dataclasses import asdict, replace
from pathlib import Path
import json
from uuid import uuid4

from odinclaw.contracts.governance import ActionRequest, GovernanceDecision, GovernanceOutcome
from odinclaw.contracts.memory import DurableMemoryRecord, MemoryKind, MemoryRecall, MemorySnapshot, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain


class DurableMemoryAuthority:
    def __init__(self, path: Path, *, receipt_chain: ReceiptChain | None = None) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.receipt_chain = receipt_chain
        self._records: list[DurableMemoryRecord] = []
        self._dirty = False
        self._loaded = False

    def load(self) -> MemorySnapshot:
        if self.path.exists():
            with self.path.open(encoding="utf-8") as handle:
                raw_records = json.load(handle)
            self._records = [
                DurableMemoryRecord(
                    memory_id=item["memory_id"],
                    topic=item["topic"],
                    content=item["content"],
                    tier=MemoryTier(item["tier"]),
                    kind=MemoryKind(item["kind"]),
                    provenance=(
                        None
                        if item.get("provenance") is None
                        else ProvenanceRecord(
                            source_type=item["provenance"]["source_type"],
                            source_label=item["provenance"]["source_label"],
                            trust_class=TrustClass(item["provenance"]["trust_class"]),
                            via=item["provenance"].get("via", "direct"),
                            metadata=item["provenance"].get("metadata", {}),
                        )
                    ),
                    metadata=item.get("metadata", {}),
                    linked_receipt_id=item.get("linked_receipt_id"),
                    linked_run_id=item.get("linked_run_id"),
                )
                for item in raw_records
            ]
        self._loaded = True
        self._dirty = False
        return self.snapshot()

    def snapshot(self) -> MemorySnapshot:
        return MemorySnapshot(records=tuple(self._records), dirty=self._dirty)

    def doctrine_records(self) -> tuple[DurableMemoryRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.kind == MemoryKind.DOCTRINE and record.tier == MemoryTier.CANON
        )

    def relevant_records(self, topic: str | None = None) -> tuple[DurableMemoryRecord, ...]:
        recall = self.recall(topic=topic)
        return recall.canon + recall.provisional

    def recall(
        self,
        *,
        topic: str | None = None,
        trust_state: TrustClass | None = None,
        limit: int = 6,
    ) -> MemoryRecall:
        matched = self._match(topic)
        canon = tuple(record for record in matched if record.tier == MemoryTier.CANON and record.kind != MemoryKind.CONFLICT)
        provisional = tuple(record for record in matched if record.tier == MemoryTier.PROVISIONAL)
        conflicts = tuple(record for record in matched if record.tier == MemoryTier.CONFLICT or record.kind == MemoryKind.CONFLICT)
        warnings: list[str] = []
        if conflicts:
            warnings.append("conflict memory present for recalled topic")
        if trust_state in {TrustClass.UNTRUSTED_EXTERNAL, TrustClass.KNOWN_BAD_OR_BLOCKED}:
            provisional = ()
            warnings.append("provisional memory suppressed by trust threshold")
        elif trust_state == TrustClass.AMBIGUOUS_EXTERNAL and provisional:
            provisional = provisional[:1]
            warnings.append("provisional memory narrowed by trust threshold")
        return MemoryRecall(
            canon=canon[:limit],
            provisional=provisional[: max(0, limit - len(canon[:limit]))],
            conflicts=conflicts[:3],
            warnings=tuple(warnings),
        )

    def _match(self, topic: str | None) -> tuple[DurableMemoryRecord, ...]:
        if topic is None:
            return tuple(self._records)
        lowered = topic.lower()
        return tuple(
            record
            for record in self._records
            if lowered in record.topic.lower() or lowered in record.content.lower()
        )

    def remember(
        self,
        *,
        topic: str,
        content: str,
        provenance: ProvenanceRecord,
        kind: MemoryKind = MemoryKind.OBSERVATION,
        tier: MemoryTier | None = None,
        metadata: dict[str, str] | None = None,
        receipt: ReceiptRecord | None = None,
        linked_run_id: str | None = None,
    ) -> DurableMemoryRecord:
        effective_tier = tier or self._default_tier(kind=kind, provenance=provenance)
        record = DurableMemoryRecord(
            memory_id=f"memory-{uuid4().hex}",
            topic=topic,
            content=content,
            tier=effective_tier,
            kind=kind,
            provenance=provenance,
            metadata=dict(metadata or {}),
            linked_receipt_id=None if receipt is None else receipt.receipt_id,
            linked_run_id=linked_run_id if linked_run_id is not None else (None if receipt is None else receipt.trace_ids.run_id),
        )
        self._records.append(record)
        self._dirty = True
        if receipt is not None and self.receipt_chain is not None:
            self.receipt_chain.append(
                ReceiptRecord(
                    receipt_id=receipt.receipt_id,
                    receipt_type="memory_write",
                    trace_ids=receipt.trace_ids,
                    action_name=f"memory:{topic}",
                    created_at=receipt.created_at,
                    provenance=provenance,
                    data={
                        "memory_id": record.memory_id,
                        "tier": record.tier.value,
                        "kind": record.kind.value,
                    },
                )
            )
        return record

    def record_governance_decision(
        self,
        *,
        request: ActionRequest,
        decision: GovernanceDecision,
        receipt: ReceiptRecord | None = None,
    ) -> DurableMemoryRecord | None:
        if decision.outcome == GovernanceOutcome.ALLOW:
            return None
        return self.remember(
            topic=f"governance:{request.action_name}",
            content=f"{decision.outcome.value}: {decision.reason}",
            provenance=request.provenance,
            kind=MemoryKind.GOVERNANCE,
            tier=MemoryTier.PROVISIONAL,
            metadata={"action_class": request.action_class.value, "outcome": decision.outcome.value},
            receipt=receipt,
        )

    def record_trust_state_change(
        self,
        *,
        source_label: str,
        previous: TrustClass | None,
        current: TrustClass,
        provenance: ProvenanceRecord,
        receipt: ReceiptRecord | None = None,
    ) -> DurableMemoryRecord | None:
        if previous == current:
            return None
        return self.remember(
            topic=f"trust:{source_label}",
            content=f"{previous.value if previous is not None else 'none'} -> {current.value}",
            provenance=provenance,
            kind=MemoryKind.TRUST,
            tier=MemoryTier.PROVISIONAL,
            metadata={"source_label": source_label, "current": current.value},
            receipt=receipt,
        )

    def remember_conflict(
        self,
        *,
        topic: str,
        claim: str,
        conflicting_claim: str,
        severity: str,
        provenance: ProvenanceRecord,
        receipt: ReceiptRecord | None = None,
    ) -> DurableMemoryRecord:
        return self.remember(
            topic=topic,
            content=f"{claim} <> {conflicting_claim}",
            provenance=provenance,
            kind=MemoryKind.CONFLICT,
            tier=MemoryTier.CONFLICT,
            metadata={"severity": severity, "claim": claim, "conflicting_claim": conflicting_claim},
            receipt=receipt,
        )

    def promote_to_canon(self, memory_id: str, *, approved: bool, active_conflicts: int = 0) -> DurableMemoryRecord:
        raise RuntimeError("use GovernedMemoryMutations for canon promotion")

    def demote_to_provisional(self, memory_id: str, *, reason: str) -> DurableMemoryRecord:
        record = self._find(memory_id)
        demoted = replace(record, tier=MemoryTier.PROVISIONAL, metadata={**record.metadata, "demotion_reason": reason})
        self._replace(demoted)
        return demoted

    def _promote_to_canon(self, memory_id: str, *, metadata: dict[str, str]) -> DurableMemoryRecord:
        record = self._find(memory_id)
        if record.tier == MemoryTier.CANON:
            return record
        promoted = replace(record, tier=MemoryTier.CANON, metadata={**record.metadata, **metadata})
        self._replace(promoted)
        return promoted

    def _mutate_canon(self, memory_id: str, *, new_content: str, metadata: dict[str, str]) -> DurableMemoryRecord:
        record = self._find(memory_id)
        if record.tier != MemoryTier.CANON:
            raise ValueError("only canon records can be canon-mutated")
        updated = replace(record, content=new_content, metadata={**record.metadata, **metadata})
        self._replace(updated)
        return updated

    def _default_tier(self, *, kind: MemoryKind, provenance: ProvenanceRecord) -> MemoryTier:
        if kind == MemoryKind.DOCTRINE:
            return MemoryTier.CANON
        if provenance.trust_class in {
            TrustClass.TRUSTED_SELF,
            TrustClass.TRUSTED_OPERATOR,
            TrustClass.TRUSTED_INTERNAL_KNOWLEDGE,
        } and kind == MemoryKind.LESSON:
            return MemoryTier.CANON
        return MemoryTier.PROVISIONAL

    def _find(self, memory_id: str) -> DurableMemoryRecord:
        for record in self._records:
            if record.memory_id == memory_id:
                return record
        raise KeyError(memory_id)

    def get(self, memory_id: str) -> DurableMemoryRecord:
        return self._find(memory_id)

    def has_blocking_conflicts(self, topic: str) -> bool:
        return any(
            record.kind == MemoryKind.CONFLICT
            and record.topic == topic
            and record.metadata.get("severity", "").lower() in {"high", "critical", "blocking"}
            for record in self._records
        )

    def attach_receipt(self, memory_id: str, receipt_id: str, run_id: str | None) -> None:
        record = self._find(memory_id)
        updated = replace(record, linked_receipt_id=receipt_id, linked_run_id=run_id or record.linked_run_id)
        self._replace(updated)

    def _replace(self, updated: DurableMemoryRecord) -> None:
        self._records = [updated if record.memory_id == updated.memory_id else record for record in self._records]
        self._dirty = True

    def flush(self) -> MemorySnapshot:
        serialised = [asdict(record) for record in self._records]
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(serialised, handle, indent=2, sort_keys=True)
        self._dirty = False
        return self.snapshot()

    @property
    def loaded(self) -> bool:
        return self._loaded
