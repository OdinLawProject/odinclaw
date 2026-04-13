from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from datetime import datetime

from odinclaw.contracts.provenance import ProvenanceRecord


class MemoryTier(StrEnum):
    CANON = "canon"
    PROVISIONAL = "provisional"
    CONFLICT = "conflict"


class MemoryKind(StrEnum):
    DOCTRINE = "doctrine"
    LESSON = "lesson"
    OBSERVATION = "observation"
    GOVERNANCE = "governance"
    TRUST = "trust"
    CONFLICT = "conflict"


class DurableMutationClass(StrEnum):
    LOW_SIGNIFICANCE_PROVISIONAL_WRITE = "low_significance_provisional_write"
    PROMOTION_CANDIDATE = "promotion_candidate"
    CANON_MUTATION = "canon_mutation"
    TRUST_GOVERNANCE_SIGNIFICANT_UPDATE = "trust_governance_significant_update"


@dataclass(frozen=True)
class DurableMemoryRecord:
    memory_id: str
    topic: str
    content: str
    tier: MemoryTier
    kind: MemoryKind
    provenance: ProvenanceRecord | None = None
    metadata: dict[str, str] = field(default_factory=dict)
    linked_receipt_id: str | None = None
    linked_run_id: str | None = None


@dataclass(frozen=True)
class MemorySnapshot:
    records: tuple[DurableMemoryRecord, ...]
    dirty: bool = False


@dataclass(frozen=True)
class MemoryRecall:
    canon: tuple[DurableMemoryRecord, ...]
    provisional: tuple[DurableMemoryRecord, ...]
    conflicts: tuple[DurableMemoryRecord, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonTransitionRecord:
    transition_id: str
    memory_id: str
    transition_type: str
    status: str
    reason: str
    requested_at: datetime
    requested_by: ProvenanceRecord
    approval_id: str | None = None
    approved_by: str | None = None
    prior_state_id: str | None = None
    prior_content: str | None = None
    resulting_state_id: str | None = None
    resulting_content: str | None = None
    receipt_id: str | None = None
    lineage_id: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)
