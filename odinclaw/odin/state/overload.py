from __future__ import annotations

from dataclasses import dataclass


# Pacing levels in ascending severity order.
# NONE         — no restriction; admit actions freely.
# PACING       — slow admission; warn shell; soft limit on concurrent holds.
# HOLD_NEW     — hold all new non-safe actions; do not deny, but gate until burden drops.
PACING_NONE = "NONE"
PACING_ACTIVE = "PACING"
PACING_HOLD_NEW = "HOLD_NEW_ACTIONS"

# Concurrent-hold limits per burden level.  At CRITICAL burden the substrate will
# refuse to admit new actions that would add to the hold queue beyond the cap.
CONCURRENT_HOLD_CAP: dict[str, int] = {
    "LOW": 999,
    "MEDIUM": 20,
    "HIGH": 10,
    "CRITICAL": 5,
}


@dataclass(frozen=True)
class OverloadSignal:
    """Evaluated overload state derived from burden and stability."""

    triggered: bool
    level: str  # PACING_NONE | PACING_ACTIVE | PACING_HOLD_NEW
    burden_level: str
    stability_status: str
    reasons: tuple[str, ...]


def evaluate_overload(
    burden_level: str,
    stability_status: str,
    burden_reasons: tuple[str, ...],
) -> OverloadSignal:
    """Derive a pacing / overload signal from current burden and stability.

    Stability takes priority: a DEGRADED or HALTED substrate holds new
    actions regardless of burden score.  CRITICAL burden also holds.
    HIGH burden triggers active pacing without a full hold.
    """
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
    """Return the maximum number of concurrent holds permitted at this burden level."""
    return CONCURRENT_HOLD_CAP.get(burden_level, 999)
