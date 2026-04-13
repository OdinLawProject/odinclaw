from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore
from odinclaw.shell.session_runtime import start_session


def test_runtime_wires_continuity_and_provenance_backed_receipts(tmp_path: Path) -> None:
    receipts = ReceiptChain(tmp_path / "receipts.jsonl")
    continuity = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    runtime = start_session(
        "demo",
        receipt_chain=receipts,
        continuity_store=continuity,
        parent_session_id="session-parent",
        parent_run_id="run-parent",
    )

    action = runtime.record_action(
        action_name="open_url",
        action_class=ActionClass.NAVIGATION_ONLY,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
            metadata={"intent": "inspect"},
        ),
        payload={"url": "https://example.com"},
    )

    stored_receipts = receipts.query(ReceiptQuery(action_id=action.trace_ids.action_id))
    stored_links = continuity.list_for_session(runtime.session_id)

    assert len(stored_receipts) == 1
    assert stored_receipts[0].provenance.metadata["intent"] == "inspect"
    assert len(stored_links) == 1
    assert stored_links[0].parent_run_id == "run-parent"
