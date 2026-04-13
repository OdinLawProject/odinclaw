from pathlib import Path

from odinclaw.contracts.governance import ActionRequest, GovernanceDecision, GovernanceOutcome
from odinclaw.contracts.memory import MemoryKind, MemoryTier
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.memory.authority import DurableMemoryAuthority


def test_memory_authority_enforces_canon_and_provisional_rules(tmp_path: Path) -> None:
    authority = DurableMemoryAuthority(tmp_path / "memory.json")
    snapshot = authority.load()
    assert snapshot.records == ()

    canon = authority.remember(
        topic="navigation",
        content="Prefer receipts before broader autonomy.",
        provenance=ProvenanceRecord(
            source_type="doctrine",
            source_label="odin-base",
            trust_class=TrustClass.TRUSTED_INTERNAL_KNOWLEDGE,
        ),
        kind=MemoryKind.DOCTRINE,
    )
    provisional = authority.remember(
        topic="navigation",
        content="Operator suggested a tentative shortcut.",
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        kind=MemoryKind.OBSERVATION,
    )
    assert canon.tier == MemoryTier.CANON
    assert provisional.tier == MemoryTier.PROVISIONAL
    demoted = authority.demote_to_provisional(canon.memory_id, reason="new contradiction")
    assert demoted.tier == MemoryTier.PROVISIONAL
    dirty = authority.snapshot()
    assert dirty.dirty is True
    flushed = authority.flush()
    assert flushed.dirty is False
    assert len(flushed.records) == 2


def test_memory_authority_persists_governance_and_trust_significance(tmp_path: Path) -> None:
    authority = DurableMemoryAuthority(tmp_path / "memory.json")
    authority.load()
    provenance = ProvenanceRecord(
        source_type="external",
        source_label="https://example.com",
        trust_class=TrustClass.AMBIGUOUS_EXTERNAL,
    )
    authority.record_governance_decision(
        request=ActionRequest(action_name="submit_form", action_class=__import__("odinclaw.contracts.action_classes", fromlist=["ActionClass"]).ActionClass.EXTERNAL_STATE_MUTATION, provenance=provenance),
        decision=GovernanceDecision(outcome=GovernanceOutcome.ESCALATE, reason="needs escalation"),
    )
    authority.record_trust_state_change(
        source_label="https://example.com",
        previous=None,
        current=TrustClass.AMBIGUOUS_EXTERNAL,
        provenance=provenance,
    )
    records = authority.snapshot().records
    assert any(record.kind == MemoryKind.GOVERNANCE for record in records)
    assert any(record.kind == MemoryKind.TRUST for record in records)
