from __future__ import annotations

from dataclasses import dataclass


PACING_NONE = "NONE"
PACING_ACTIVE = "PACING"
PACING_HOLD_NEW = "HOLD_NEW_ACTIONS"

CONCURRENT_HOLD_CAP: dict[str, int] = {
    "LOW": 999,
    "MEDIUM": 20,
    "HIGH": 10,
    "CRITICAL": 5,
}


@dataclass(frozen=True)
class OverloadSignal:
    triggered: bool
    level: str
    burden_level: str
    stability_status: str
    reasons: tuple[str, ...]


def evaluate_overload(
    burden_level: str,
    stability_status: str,
    burden_reasons: tuple[str, ...],
) -> OverloadSignal:
    if stability_status in {"DEGRADED", "HALTED"}:
        return OverloadSignal(
            triggered=True,
            level=PACING_HOLD_NEW,
            burden_level=burden_level,
            stability_status=stability_status,
            reasons=(f"stability_{stability_status.lower()}",) + burden_reasons,
        )
    if burden_level == "CRITICAL":
        return OverloadSignal(
            triggered=True,
            level=PACING_HOLD_NEW,
            burden_level=burden_level,
            stability_status=stability_status,
            reasons=("burden_critical",) + burden_reasons,
        )
    if burden_level == "HIGH":
        return OverloadSignal(
            triggered=True,
            level=PACING_ACTIVE,
            burden_level=burden_level,
            stability_status=stability_status,
            reasons=("burden_high",) + burden_reasons,
        )
    return OverloadSignal(
        triggered=False,
        level=PACING_NONE,
        burden_level=burden_level,
        stability_status=stability_status,
        reasons=(),
    )


def concurrent_hold_cap_for(burden_level: str) -> int:
    return CONCURRENT_HOLD_CAP.get(burden_level, 999)
