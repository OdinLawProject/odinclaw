from __future__ import annotations

from dataclasses import dataclass

from odinclaw.contracts.shell_state import BurdenPanelState, StabilityPanelState


@dataclass(frozen=True)
class BurdenInputs:
    pending_holds: int
    approvals_required: int
    escalations_required: int
    blocked_sources: int
    ambiguous_sources: int
    active_conflicts: int
    memory_dirty: bool
    receipt_count: int
    continuity_links: int


@dataclass(frozen=True)
class StabilityInputs:
    startup_ready: bool
    shutdown_ready: bool
    accepting_actions: bool
    degraded_mode: bool
    memory_dirty: bool
    active_conflicts: int


def evaluate_burden(inputs: BurdenInputs) -> BurdenPanelState:
    score = 0
    reasons: list[str] = []

    if inputs.pending_holds > 0:
        score += min(inputs.pending_holds * 15, 30)
        reasons.append(f"pending_holds={inputs.pending_holds}")
    if inputs.approvals_required > 0:
        score += min(inputs.approvals_required * 10, 20)
        reasons.append(f"approvals_required={inputs.approvals_required}")
    if inputs.escalations_required > 0:
        score += min(inputs.escalations_required * 20, 20)
        reasons.append(f"escalations_required={inputs.escalations_required}")
    if inputs.blocked_sources > 0:
        score += min(inputs.blocked_sources * 10, 20)
        reasons.append(f"blocked_sources={inputs.blocked_sources}")
    if inputs.ambiguous_sources > 0:
        score += min(inputs.ambiguous_sources * 5, 10)
        reasons.append(f"ambiguous_sources={inputs.ambiguous_sources}")
    if inputs.active_conflicts > 0:
        score += min(inputs.active_conflicts * 10, 20)
        reasons.append(f"active_conflicts={inputs.active_conflicts}")
    if inputs.memory_dirty:
        score += 10
        reasons.append("memory_dirty=true")
    if inputs.receipt_count >= 100:
        score += 5
        reasons.append(f"receipt_volume={inputs.receipt_count}")
    if inputs.continuity_links >= 100:
        score += 5
        reasons.append(f"continuity_volume={inputs.continuity_links}")

    bounded = min(score, 100)
    if bounded >= 75:
        level = "CRITICAL"
    elif bounded >= 50:
        level = "HIGH"
    elif bounded >= 20:
        level = "MEDIUM"
    else:
        level = "LOW"

    return BurdenPanelState(level=level, score=bounded, reasons=tuple(reasons))


def evaluate_stability(inputs: StabilityInputs) -> StabilityPanelState:
    signals: list[str] = []

    if inputs.degraded_mode:
        signals.append("degraded_mode=true")
    if not inputs.startup_ready:
        signals.append("startup_ready=false")
    if not inputs.accepting_actions:
        signals.append("accepting_actions=false")
    if inputs.shutdown_ready:
        signals.append("shutdown_ready=true")
    if inputs.memory_dirty:
        signals.append("memory_dirty=true")
    if inputs.active_conflicts > 0:
        signals.append(f"active_conflicts={inputs.active_conflicts}")

    if inputs.degraded_mode or not inputs.startup_ready:
        status = "DEGRADED"
    elif inputs.shutdown_ready and not inputs.accepting_actions:
        status = "HALTED"
    elif not inputs.accepting_actions:
        status = "DEGRADED"
    else:
        status = "STABLE"

    return StabilityPanelState(status=status, signals=tuple(signals))
