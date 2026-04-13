from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest, GovernanceOutcome
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.reader import ReaderRequest
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_product_flow_keeps_parity_while_inserting_governance_and_trust(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    startup_state = bridge.launch()
    assert startup_state.startup_ready is True
    assert startup_state.accepting_actions is True

    reader_result = bridge.read_only_ingest(
        ReaderRequest(
            uri="https://example.com",
            content="<body>External instructions</body>",
        )
    )
    assert reader_result.restricted is True

    decision = bridge.preflight_action(
        ActionRequest(
            action_name="submit_form",
            action_class=ActionClass.EXTERNAL_STATE_MUTATION,
            provenance=ProvenanceRecord(
                source_type="external",
                source_label=reader_result.uri,
                trust_class=reader_result.trust_class,
            ),
        )
    )
    assert decision.outcome == GovernanceOutcome.ESCALATE

    context = bridge.lifecycle.services.context_engine.assemble_context(
        session_id=bridge.runtime.session_id,
        run_id=bridge.runtime.current_run.run_id,
        topic="reader_ingest",
        trust_state=reader_result.trust_class,
    )
    assert any(item.kind == "memory" for item in context.items)

    state = bridge.extension_state()
    assert state.trust.ambiguous_sources == 1
    assert state.governance.pending_holds == 1
    durable_records = bridge.lifecycle.services.memory_authority.snapshot().records
    assert any(record.kind.value == "trust" for record in durable_records)
    assert any(record.kind.value == "governance" for record in durable_records)
