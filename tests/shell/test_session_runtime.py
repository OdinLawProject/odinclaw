from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.shell.session_runtime import start_session


def test_start_session_writes_initial_continuity_link(tmp_path: Path) -> None:
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    runtime = start_session(
        "demo",
        continuity_store=continuity,
        parent_session_id="session-parent",
        parent_run_id="run-parent",
    )
    links = continuity.list_for_session(runtime.session_id)
    assert len(links) == 1
    assert links[0].parent_session_id == "session-parent"
    assert links[0].parent_run_id == "run-parent"


def test_record_action_writes_receipt_for_meaningful_actions(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    runtime = start_session("demo", receipt_chain=receipts)
    event = runtime.record_action(
        action_name="open_url",
        action_class=ActionClass.NAVIGATION_ONLY,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        payload={"url": "https://example.com"},
    )
    stored = receipts.query(ReceiptQuery(action_id=event.trace_ids.action_id))
    assert len(stored) == 1
    assert stored[0].action_name == "open_url"


def test_record_action_skips_receipt_for_non_meaningful_actions(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    runtime = start_session("demo", receipt_chain=receipts)
    runtime.record_action(
        action_name="heartbeat",
        action_class=ActionClass.READ_ONLY_LOCAL,
        provenance=ProvenanceRecord(
            source_type="system",
            source_label="runtime",
            trust_class=TrustClass.TRUSTED_SELF,
        ),
        meaningful=False,
    )
    assert receipts.query(ReceiptQuery()) == []
