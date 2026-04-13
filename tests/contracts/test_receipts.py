from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.action_ids import new_trace_ids
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery, ReceiptRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.contracts.events import utc_now


def test_receipt_query_defaults_are_optional() -> None:
    query = ReceiptQuery()
    assert query.run_id is None
    assert query.action_id is None
    assert query.receipt_type is None


def test_receipt_record_carries_trace_and_provenance() -> None:
    trace_ids = new_trace_ids()
    provenance = ProvenanceRecord(
        source_type="operator",
        source_label="cli",
        trust_class=TrustClass.TRUSTED_OPERATOR,
    )
    receipt = ReceiptRecord(
        receipt_id=trace_ids.action_id,
        receipt_type="action",
        trace_ids=trace_ids,
        action_name="open_url",
        created_at=utc_now(),
        provenance=provenance,
        data={"action_class": ActionClass.NAVIGATION_ONLY.value},
    )
    assert receipt.trace_ids == trace_ids
    assert receipt.provenance.source_label == "cli"
    assert receipt.data["action_class"] == ActionClass.NAVIGATION_ONLY.value
