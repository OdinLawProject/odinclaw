from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.shell.hooks import attach_odinclaw_shell


def test_product_lifecycle_preserves_shell_shape_with_odin_hooks(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "desktop-app")
    startup_state = bridge.launch()
    assert startup_state.startup_ready is True
    assert startup_state.accepting_actions is True

    bridge.runtime.record_action(
        action_name="open_url",
        action_class=ActionClass.NAVIGATION_ONLY,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="launcher",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        payload={"url": "https://example.com"},
    )
    context = bridge.context_for_ui(topic="open_url")
    assert context.run_id == bridge.runtime.current_run.run_id
    shutdown_state = bridge.shutdown()
    assert shutdown_state.shutdown_ready is True
    assert shutdown_state.accepting_actions is False
