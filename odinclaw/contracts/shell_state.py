from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GovernancePanelState:
    pending_holds: int = 0
    approvals_required: int = 0


@dataclass(frozen=True)
class AuditPanelState:
    receipt_count: int = 0
    continuity_links: int = 0


@dataclass(frozen=True)
class MemoryPanelState:
    durable_records: int = 0
    dirty: bool = False


@dataclass(frozen=True)
class TrustPanelState:
    blocked_sources: int = 0
    ambiguous_sources: int = 0
    active_conflicts: int = 0


@dataclass(frozen=True)
class BurdenPanelState:
    level: str = "LOW"
    score: int = 0
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class StabilityPanelState:
    status: str = "STABLE"
    signals: tuple[str, ...] = ()


@dataclass(frozen=True)
class OverloadPanelState:
    triggered: bool = False
    level: str = "NONE"  # "NONE" | "PACING" | "HOLD_NEW_ACTIONS"
    reasons: tuple[str, ...] = ()
    concurrent_holds: int = 0
    concurrent_hold_cap: int = 999


@dataclass(frozen=True)
class ShellExtensionState:
    startup_ready: bool = False
    shutdown_ready: bool = False
    accepting_actions: bool = False
    degraded_mode: bool = False
    governance: GovernancePanelState = field(default_factory=GovernancePanelState)
    audit: AuditPanelState = field(default_factory=AuditPanelState)
    memory: MemoryPanelState = field(default_factory=MemoryPanelState)
    trust: TrustPanelState = field(default_factory=TrustPanelState)
    burden: BurdenPanelState = field(default_factory=BurdenPanelState)
    stability: StabilityPanelState = field(default_factory=StabilityPanelState)
    overload: OverloadPanelState = field(default_factory=OverloadPanelState)
