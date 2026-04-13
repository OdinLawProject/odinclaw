from __future__ import annotations

from dataclasses import dataclass, field

from odinclaw.contracts.memory import DurableMemoryRecord, MemoryTier
from odinclaw.contracts.trust import TrustClass


@dataclass
class MemoryArbitrationResult:
    canon_reads: list[str] = field(default_factory=list)
    provisional_reads: list[str] = field(default_factory=list)
    conflict_reads: list[str] = field(default_factory=list)
    session_reads: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def arbitrate_memory(
    *,
    canon_reads: list[str],
    provisional_reads: list[str],
    conflict_reads: list[str],
    session_reads: list[str],
    trust_state: TrustClass | None = None,
) -> MemoryArbitrationResult:
    warnings: list[str] = []
    if (canon_reads or provisional_reads) and session_reads:
        warnings.append("Session memory supplements canon but is not authoritative.")
    if conflict_reads:
        warnings.append("Conflict memory warns against naive recall.")
    if trust_state in {TrustClass.UNTRUSTED_EXTERNAL, TrustClass.KNOWN_BAD_OR_BLOCKED} and provisional_reads:
        provisional_reads = []
        warnings.append("Provisional memory removed under low trust.")
    return MemoryArbitrationResult(
        canon_reads=canon_reads,
        provisional_reads=provisional_reads,
        conflict_reads=conflict_reads,
        session_reads=session_reads,
        warnings=warnings,
    )


def select_memory_records(
    records: tuple[DurableMemoryRecord, ...],
    *,
    topic: str | None,
    limit: int,
) -> tuple[DurableMemoryRecord, ...]:
    if topic is None:
        return records[:limit]
    lowered = topic.lower()
    selected = tuple(
        record
        for record in records
        if lowered in record.topic.lower() or lowered in record.content.lower()
    )
    return selected[:limit]


def session_memory_from_events(session_entries: tuple[str, ...], *, limit: int = 3) -> tuple[str, ...]:
    return session_entries[-limit:]
