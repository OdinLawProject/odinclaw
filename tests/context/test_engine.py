from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.contracts.events import utc_now
from odinclaw.contracts.action_ids import new_trace_ids
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore, ContinuityLink
from odinclaw.odin.context.engine import OdinContextEngine
from odinclaw.odin.memory.conflict_store import ConflictMemoryStore
from odinclaw.odin.memory.authority import DurableMemoryAuthority


def test_context_engine_composes_continuity_memory_doctrine_and_receipts(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    memory = DurableMemoryAuthority(tmp_path / "memory.json", receipt_chain=receipts)
    conflicts = ConflictMemoryStore(memory)
    memory.load()
    provenance = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    doctrine = ProvenanceRecord(
        source_type="doctrine",
        source_label="odin-base",
        trust_class=TrustClass.TRUSTED_INTERNAL_KNOWLEDGE,
    )
    memory.remember(
        topic="governance",
        content="Governance before capability release.",
        provenance=doctrine,
        kind=__import__("odinclaw.contracts.memory", fromlist=["MemoryKind"]).MemoryKind.DOCTRINE,
    )
    memory.remember(
        topic="receipts",
        content="Receipts must be visible in context assembly.",
        provenance=provenance,
        kind=__import__("odinclaw.contracts.memory", fromlist=["MemoryKind"]).MemoryKind.OBSERVATION,
    )
    trace_ids = new_trace_ids()
    receipts.append(
        ReceiptRecord(
            receipt_id=trace_ids.action_id,
            receipt_type="action",
            trace_ids=trace_ids,
            action_name="open_url",
            created_at=utc_now(),
            provenance=provenance,
            data={"action_class": ActionClass.NAVIGATION_ONLY.value},
        )
    )
    continuity.append(
        ContinuityLink(
            session_id=trace_ids.session_id,
            run_id=trace_ids.run_id,
            parent_session_id="session-parent",
            parent_run_id="run-parent",
            reason="session_started",
            recorded_at=utc_now(),
        )
    )
    conflicts.record(
        topic="receipts",
        claim="page claims no audit trail",
        conflicting_claim="receipt chain exists",
        severity="medium",
        provenance=provenance,
    )

    engine = OdinContextEngine(
        continuity_store=continuity,
        receipt_chain=receipts,
        memory_authority=memory,
        conflict_store=conflicts,
    )
    engine.mark_ready()
    assembly = engine.assemble_context(
        session_id=trace_ids.session_id,
        run_id=trace_ids.run_id,
        topic="receipts",
        trust_state=TrustClass.AMBIGUOUS_EXTERNAL,
        session_memory=("recent shell note",),
    )
    kinds = {item.kind for item in assembly.items}
    assert "doctrine" in kinds
    assert "memory" in kinds
    assert "continuity" in kinds
    assert "receipt" in kinds
    assert "conflict" in kinds
    assert "session" in kinds
    assert assembly.receipts[0].provenance.source_label == "cli"
    assert "ambiguous external source" in assembly.warnings
    assert assembly.memory_recall is not None
    assert len(assembly.memory_recall.canon) == 0 or all(record.tier.value == "canon" for record in assembly.memory_recall.canon)
