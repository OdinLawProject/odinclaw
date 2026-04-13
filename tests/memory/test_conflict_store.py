from pathlib import Path

from odinclaw.contracts.memory import MemoryKind, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.memory.authority import DurableMemoryAuthority
from odinclaw.odin.memory.conflict_store import ConflictMemoryStore


def test_conflict_records_are_stored_through_durable_authority_and_resurfaced(tmp_path: Path) -> None:
    authority = DurableMemoryAuthority(tmp_path / "memory.json")
    authority.load()
    store = ConflictMemoryStore(authority)
    provenance = ProvenanceRecord(
        source_type="external",
        source_label="reader",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    store.record(
        topic="identity",
        claim="site says trusted",
        conflicting_claim="receipt says untrusted",
        severity="high",
        provenance=provenance,
    )
    records = store.relevant(topic="identity")
    assert len(records) == 1
    assert records[0].severity == "high"
    durable = authority.snapshot().records[0]
    assert durable.kind == MemoryKind.CONFLICT
    assert durable.tier == MemoryTier.CONFLICT
