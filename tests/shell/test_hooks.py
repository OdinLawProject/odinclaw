from pathlib import Path

from odinclaw.shell.hooks import attach_odinclaw_shell


def test_shell_bridge_exposes_additive_state_for_ui(tmp_path: Path) -> None:
    bridge = attach_odinclaw_shell(tmp_path, "demo")
    bridge.launch()
    state = bridge.extension_state()
    assert state.startup_ready is True
    assert state.accepting_actions is True
    assert state.governance.pending_holds == 0
    assert state.audit.continuity_links == 1
    assert state.burden.level in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert isinstance(state.burden.score, int)
    assert state.stability.status == "STABLE"
