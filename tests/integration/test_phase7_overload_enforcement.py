"""Integration tests for Phase 7 — overload enforcement through the full lifecycle."""
from pathlib import Path

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest, GovernanceOutcome
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.orchestration.lifecycle import build_lifecycle


def _operator_request(action_class: ActionClass = ActionClass.NAVIGATION_ONLY) -> ActionRequest:
    return ActionRequest(
        action_name="test_action",
        action_class=action_class,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="test",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
    )


class TestStabilityRegulation:
    def test_degraded_mode_holds_all_new_preflights(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.enter_degraded_mode(reason="test_degraded")

        decision = lifecycle.preflight(_operator_request())
        assert decision.outcome == GovernanceOutcome.HOLD
        assert "overload_gate" in decision.reason

    def test_exit_degraded_mode_restores_normal_preflight(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.enter_degraded_mode(reason="test")
        lifecycle.exit_degraded_mode(reason="recovered")

        decision = lifecycle.preflight(_operator_request(ActionClass.NAVIGATION_ONLY))
        # Navigation-only from trusted operator should be allowed after recovery.
        assert decision.outcome == GovernanceOutcome.ALLOW


class TestOverloadPanelInShellState:
    def test_shell_state_exposes_overload_panel(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        state = lifecycle.shell_state()
        assert hasattr(state, "overload")
        assert state.overload.level in {"NONE", "PACING", "HOLD_NEW_ACTIONS"}

    def test_clean_startup_state_has_no_overload(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        state = lifecycle.startup()
        assert state.overload.triggered is False
        assert state.overload.level == "NONE"

    def test_degraded_mode_overload_panel_reflects_hold(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.enter_degraded_mode(reason="simulate overload")
        state = lifecycle.shell_state()
        assert state.overload.triggered is True
        assert state.overload.level == "HOLD_NEW_ACTIONS"

    def test_overload_panel_includes_concurrent_holds_and_cap(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        state = lifecycle.shell_state()
        assert state.overload.concurrent_holds == 0
        assert state.overload.concurrent_hold_cap >= 1


class TestConcurrentHoldPacing:
    def test_hold_decisions_increment_concurrent_holds(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        assert lifecycle.concurrent_holds == 0

        # Destructive action → HOLD
        decision = lifecycle.preflight(_operator_request(ActionClass.DESTRUCTIVE_ACTION))
        assert decision.outcome == GovernanceOutcome.HOLD
        assert lifecycle.concurrent_holds == 1

    def test_release_hold_decrements_counter(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.preflight(_operator_request(ActionClass.DESTRUCTIVE_ACTION))
        assert lifecycle.concurrent_holds == 1

        lifecycle.release_hold()
        assert lifecycle.concurrent_holds == 0

    def test_release_hold_does_not_go_negative(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.release_hold()
        assert lifecycle.concurrent_holds == 0
