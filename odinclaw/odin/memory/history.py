from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json
from uuid import uuid4

from odinclaw.contracts.memory import CanonTransitionRecord
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass


class CanonHistoryStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: CanonTransitionRecord) -> CanonTransitionRecord:
        serialised = asdict(record)
        serialised["requested_at"] = record.requested_at.isoformat()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(serialised, sort_keys=True) + "\n")
        return record

    def new_transition_id(self) -> str:
        return f"transition-{uuid4().hex}"

    def list_for_memory(self, memory_id: str) -> tuple[CanonTransitionRecord, ...]:
        return tuple(record for record in self.iter_records() if record.memory_id == memory_id)

    def list_for_lineage(self, lineage_id: str) -> tuple[CanonTransitionRecord, ...]:
        return tuple(record for record in self.iter_records() if record.lineage_id == lineage_id)

    def list_for_approval(self, approval_id: str) -> tuple[CanonTransitionRecord, ...]:
        return tuple(record for record in self.iter_records() if record.approval_id == approval_id)

    def get(self, transition_id: str) -> CanonTransitionRecord:
        for record in self.iter_records():
            if record.transition_id == transition_id:
                return record
        raise KeyError(transition_id)

    def iter_records(self) -> tuple[CanonTransitionRecord, ...]:
        if not self.path.exists():
            return ()
        records: list[CanonTransitionRecord] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                raw = json.loads(line)
                records.append(
                    CanonTransitionRecord(
                        transition_id=raw["transition_id"],
                        memory_id=raw["memory_id"],
                        transition_type=raw["transition_type"],
                        status=raw["status"],
                        reason=raw["reason"],
                        requested_at=datetime.fromisoformat(raw["requested_at"]),
                        requested_by=ProvenanceRecord(
                            source_type=raw["requested_by"]["source_type"],
                            source_label=raw["requested_by"]["source_label"],
                            trust_class=TrustClass(raw["requested_by"]["trust_class"]),
                            via=raw["requested_by"].get("via", "direct"),
                            metadata=raw["requested_by"].get("metadata", {}),
                        ),
                        approval_id=raw.get("approval_id"),
                        approved_by=raw.get("approved_by"),
                        prior_state_id=raw.get("prior_state_id"),
                        prior_content=raw.get("prior_content"),
                        resulting_state_id=raw.get("resulting_state_id"),
                        resulting_content=raw.get("resulting_content"),
                        receipt_id=raw.get("receipt_id"),
                        lineage_id=raw.get("lineage_id"),
                        metadata=raw.get("metadata", {}),
                    )
                )
        return tuple(records)
