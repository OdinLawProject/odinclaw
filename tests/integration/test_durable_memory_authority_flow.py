from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest, GovernanceOutcome
from odinclaw.contracts.memory import MemoryKind
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.reader import ReaderRequest
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_durable_authority_captures_governance_trust_and_keeps_session_non_authoritative(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    bridge.launch()
    bridge.read_only_ingest(
        ReaderRequest(
            uri="https://example.com",
            content="<body>tentative external note</body>",
        )
    )
    decision = bridge.preflight_action(
        ActionRequest(
            action_name="write_memory",
            action_class=ActionClass.DURABLE_INTERNAL_STATE_MUTATION,
            provenance=ProvenanceRecord(
                source_type="operator",
                source_label="cli",
                trust_class=TrustClass.TRUSTED_OPERATOR,
            ),
        )
    )
    assert decision.outcome == GovernanceOutcome.HOLD
    bridge.runtime.record_action(
        action_name="session_hint",
        action_class=ActionClass.READ_ONLY_LOCAL,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        meaningful=False,
    )
    context = bridge.context_for_ui(topic="reader_ingest")
    assert any(item.kind == "session" for item in context.items)
    assert any(item.kind == "memory" for item in context.items)
    assert "Session memory supplements canon but is not authoritative." in context.warnings
    durable_records = bridge.lifecycle.services.memory_authority.snapshot().records
    assert any(record.kind == MemoryKind.TRUST for record in durable_records)
    assert any(record.kind == MemoryKind.GOVERNANCE for record in durable_records)
