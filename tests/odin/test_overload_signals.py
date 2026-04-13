"""Tests for Phase 7 — overload signal evaluation and pacing logic."""
from odinclaw.odin.state.overload import (
    PACING_NONE,
    PACING_ACTIVE,
    PACING_HOLD_NEW,
    evaluate_overload,
    concurrent_hold_cap_for,
)


class TestEvaluateOverload:
    def test_stable_low_burden_is_clear(self) -> None:
        signal = evaluate_overload("LOW", "STABLE", ())
        assert signal.triggered is False
        assert signal.level == PACING_NONE
        assert signal.reasons == ()

    def test_high_burden_triggers_pacing(self) -> None:
        signal = evaluate_overload("HIGH", "STABLE", ("burden_high_reason",))
        assert signal.triggered is True
        assert signal.level == PACING_ACTIVE
        assert "burden_high" in signal.reasons

    def test_critical_burden_triggers_hold(self) -> None:
        signal = evaluate_overload("CRITICAL", "STABLE", ("pending_holds=6",))
        assert signal.triggered is True
        assert signal.level == PACING_HOLD_NEW
        assert "burden_critical" in signal.reasons

    def test_degraded_stability_triggers_hold_regardless_of_burden(self) -> None:
        signal = evaluate_overload("LOW", "DEGRADED", ())
        assert signal.triggered is True
        assert signal.level == PACING_HOLD_NEW
        assert "stability_degraded" in signal.reasons

    def test_halted_stability_triggers_hold(self) -> None:
        signal = evaluate_overload("LOW", "HALTED", ())
        assert signal.triggered is True
        assert signal.level == PACING_HOLD_NEW
        assert "stability_halted" in signal.reasons

    def test_stability_takes_priority_over_medium_burden(self) -> None:
        signal = evaluate_overload("MEDIUM", "DEGRADED", ("memory_dirty=true",))
        assert signal.level == PACING_HOLD_NEW
        assert "stability_degraded" in signal.reasons

    def test_medium_burden_stable_is_clear(self) -> None:
        signal = evaluate_overload("MEDIUM", "STABLE", ())
        assert signal.triggered is False
        assert signal.level == PACING_NONE


class TestConcurrentHoldCap:
    def test_low_burden_cap_is_effectively_unlimited(self) -> None:
        assert concurrent_hold_cap_for("LOW") >= 100

    def test_high_burden_cap_is_lower_than_medium(self) -> None:
        assert concurrent_hold_cap_for("HIGH") < concurrent_hold_cap_for("MEDIUM")

    def test_critical_burden_cap_is_lowest(self) -> None:
        assert concurrent_hold_cap_for("CRITICAL") <= concurrent_hold_cap_for("HIGH")

    def test_unknown_level_returns_safe_default(self) -> None:
        assert concurrent_hold_cap_for("UNKNOWN") >= 1
