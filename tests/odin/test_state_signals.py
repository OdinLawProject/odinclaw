from odinclaw.odin.state.signals import BurdenInputs, StabilityInputs, evaluate_burden, evaluate_stability


def test_burden_signal_uses_bounded_real_metrics() -> None:
    burden = evaluate_burden(
        BurdenInputs(
            pending_holds=2,
            approvals_required=1,
            escalations_required=1,
            blocked_sources=1,
            ambiguous_sources=2,
            active_conflicts=2,
            memory_dirty=True,
            receipt_count=150,
            continuity_links=120,
        )
    )
    assert burden.level == "CRITICAL"
    assert 0 <= burden.score <= 100
    assert "pending_holds=2" in burden.reasons
    assert "memory_dirty=true" in burden.reasons


def test_stability_signal_reports_runtime_condition_deterministically() -> None:
    stable = evaluate_stability(
        StabilityInputs(
            startup_ready=True,
            shutdown_ready=False,
            accepting_actions=True,
            degraded_mode=False,
            memory_dirty=False,
            active_conflicts=0,
        )
    )
    degraded = evaluate_stability(
        StabilityInputs(
            startup_ready=True,
            shutdown_ready=False,
            accepting_actions=False,
            degraded_mode=True,
            memory_dirty=True,
            active_conflicts=2,
        )
    )
    halted = evaluate_stability(
        StabilityInputs(
            startup_ready=True,
            shutdown_ready=True,
            accepting_actions=False,
            degraded_mode=False,
            memory_dirty=False,
            active_conflicts=0,
        )
    )
    assert stable.status == "STABLE"
    assert degraded.status == "DEGRADED"
    assert "degraded_mode=true" in degraded.signals
    assert "active_conflicts=2" in degraded.signals
    assert halted.status == "HALTED"
    assert "shutdown_ready=true" in halted.signals
