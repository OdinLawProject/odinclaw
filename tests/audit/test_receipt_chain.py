from pathlib import Path

from odinclaw.contracts.action_ids import new_trace_ids
from odinclaw.contracts.events import utc_now
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery, ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.audit.receipt_chain import ReceiptChain


def _record(action_name: str, *, action_id: str | None = None) -> ReceiptRecord:
    trace_ids = new_trace_ids(action_id=action_id)
    return ReceiptRecord(
        receipt_id=trace_ids.action_id,
        receipt_type="action",
        trace_ids=trace_ids,
        action_name=action_name,
        created_at=utc_now(),
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        data={"ok": True},
    )


def test_receipt_chain_links_hashes_and_queries_by_run(tmp_path: Path) -> None:
    chain = ReceiptChain(tmp_path / "receipts.jsonl")
    first = chain.append(_record("open_url"))
    second = chain.append(_record("capture_dom"))
    assert first.receipt_hash
    assert second.parent_receipt_hash == first.receipt_hash
    matches = chain.query(ReceiptQuery(run_id=second.trace_ids.run_id))
    assert [receipt.action_name for receipt in matches] == ["capture_dom"]


def test_receipt_chain_queries_by_action_id(tmp_path: Path) -> None:
    chain = ReceiptChain(tmp_path / "receipts.jsonl")
    first = chain.append(_record("open_url"))
    chain.append(_record("capture_dom"))
    matches = chain.query(ReceiptQuery(action_id=first.trace_ids.action_id))
    assert len(matches) == 1
    assert matches[0].action_name == "open_url"
