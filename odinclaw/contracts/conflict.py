from __future__ import annotations

from dataclasses import dataclass, field

from odinclaw.contracts.provenance import ProvenanceRecord


@dataclass(frozen=True)
class ConflictRecord:
    conflict_id: str
    topic: str
    claim: str
    conflicting_claim: str
    severity: str
    provenance: ProvenanceRecord
    metadata: dict[str, str] = field(default_factory=dict)
