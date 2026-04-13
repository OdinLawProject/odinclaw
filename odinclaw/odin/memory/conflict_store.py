from __future__ import annotations

from odinclaw.contracts.conflict import ConflictRecord
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.odin.memory.authority import DurableMemoryAuthority


class ConflictMemoryStore:
    def __init__(self, authority: DurableMemoryAuthority) -> None:
        self.authority = authority

    def record(
        self,
        *,
        topic: str,
        claim: str,
        conflicting_claim: str,
        severity: str,
        provenance: ProvenanceRecord,
        metadata: dict[str, str] | None = None,
    ) -> ConflictRecord:
        durable = self.authority.remember_conflict(
            topic=topic,
            claim=claim,
            conflicting_claim=conflicting_claim,
            severity=severity,
            provenance=provenance,
        )
        return ConflictRecord(
            conflict_id=durable.memory_id,
            topic=topic,
            claim=claim,
            conflicting_claim=conflicting_claim,
            severity=severity,
            provenance=provenance,
            metadata=dict(metadata or {}),
        )

    def all(self) -> tuple[ConflictRecord, ...]:
        records: list[ConflictRecord] = []
        for record in self.authority.snapshot().records:
            if record.kind != MemoryKind.CONFLICT:
                continue
            records.append(
                ConflictRecord(
                    conflict_id=record.memory_id,
                    topic=record.topic,
                    claim=record.metadata.get("claim", ""),
                    conflicting_claim=record.metadata.get("conflicting_claim", ""),
                    severity=record.metadata.get("severity", "unknown"),
                    provenance=record.provenance if record.provenance is not None else ProvenanceRecord(
                        source_type="unknown",
                        source_label="unknown",
                        trust_class=__import__("odinclaw.contracts.trust", fromlist=["TrustClass"]).TrustClass.AMBIGUOUS_EXTERNAL,
                    ),
                    metadata=record.metadata,
                )
            )
        return tuple(records)

    def relevant(self, *, topic: str | None = None, limit: int = 5) -> tuple[ConflictRecord, ...]:
        records = self.all()
        if topic is not None:
            lowered = topic.lower()
            records = tuple(
                record
                for record in records
                if lowered in record.topic.lower()
                or lowered in record.claim.lower()
                or lowered in record.conflicting_claim.lower()
            )
        return records[-limit:]

    def count(self) -> int:
        return len(self.all())
