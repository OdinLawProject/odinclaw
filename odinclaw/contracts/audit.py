from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


@dataclass(frozen=True)
class CanonStateSummary:
    memory_id: str
    topic: str
    tier: str
    kind: str
    content: str
    receipt_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True)
class CanonSemanticDiff:
    added_fields: dict[str, str] = field(default_factory=dict)
    removed_fields: dict[str, str] = field(default_factory=dict)
    changed_fields: dict[str, tuple[str, str]] = field(default_factory=dict)
    transition_reason: str = ""
    transition_type: str = ""
    annotations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonTransitionExplanation:
    transition_id: str
    transition_summary: str
    approval_reference: str | None
    prior_state: CanonStateSummary | None
    resulting_state: CanonStateSummary | None
    semantic_delta: CanonSemanticDiff
    continuity_summary: tuple[str, ...] = ()
    lineage: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonHistoryQuery:
    topic: str | None = None
    mutation_class: str | None = None
    transition_types: tuple[str, ...] = ()
    approval_id: str | None = None
    lineage_id: str | None = None
    outcome_type: str | None = None
    require_linked_approval: bool = False
    require_linked_trust: bool = False
    require_linked_conflict: bool = False
    limit: int = 10
    cursor: str | None = None


class CanonAuditPreset(StrEnum):
    RECENT_CHANGES = "recent_changes"
    TOPIC_CHANGES = "topic_changes"
    RECENT_APPROVED = "recent_approved"
    REJECTED_CANCELLED = "rejected_cancelled"
    LINEAGE_FOCUS = "lineage_focus"
    HIGH_SIGNIFICANCE = "high_significance"
    WITH_APPROVAL_CONTEXT = "with_approval_context"
    WITH_TRUST_CONTEXT = "with_trust_context"
    WITH_CONFLICT_CONTEXT = "with_conflict_context"
    HIGH_SIGNIFICANCE_GOVERNED = "high_significance_governed"
    RELEVANCE_NOW_APPROVAL = "relevance_now_approval"
    RELEVANCE_NOW_TRUST = "relevance_now_trust"
    RELEVANCE_NOW_CONFLICT = "relevance_now_conflict"
    RELEVANCE_NOW_GOVERNED = "relevance_now_governed"


class CanonPressureType(StrEnum):
    APPROVAL_PRESSURE = "approval_pressure"
    CONFLICT_PRESSURE = "conflict_pressure"
    TRUST_PRESSURE = "trust_pressure"
    GOVERNED_MUTATION_PRESSURE = "governed_mutation_pressure"
    REVIEW_ONLY = "review_only"


class CanonAttentionPreset(StrEnum):
    NEEDS_APPROVAL = "needs_approval"
    CONFLICT_BLOCKED = "conflict_blocked"
    TRUST_DOWNGRADED = "trust_downgraded"
    RECENT_HIGH_SIGNIFICANCE = "recent_high_significance"
    UNRESOLVED_GOVERNED_MUTATIONS = "unresolved_governed_mutations"
    REVIEW_NOW = "review_now"


class CanonResolutionType(StrEnum):
    APPROVAL_RESOLVED = "approval_resolved"
    CONFLICT_RESOLVED = "conflict_resolved"
    TRUST_RECOVERED = "trust_recovered"
    GOVERNED_MUTATION_COMPLETED = "governed_mutation_completed"
    REVIEW_CLOSED = "review_closed"


class CanonResolutionPreset(StrEnum):
    RECENTLY_APPROVED = "recently_approved"
    RECENTLY_REJECTED = "recently_rejected"
    RECENTLY_CANCELLED = "recently_cancelled"
    CONFLICT_CLEARED = "conflict_cleared"
    TRUST_RESTORED = "trust_restored"
    RECENTLY_COMPLETED_GOVERNED_MUTATIONS = "recently_completed_governed_mutations"


class CanonFollowUpType(StrEnum):
    CANON_SIGNIFICANCE_FOLLOW_UP = "canon_significance_follow_up"
    TRUST_POSTURE_FOLLOW_UP = "trust_posture_follow_up"
    CONTINUITY_LINEAGE_FOLLOW_UP = "continuity_lineage_follow_up"
    GOVERNANCE_AFTERCARE = "governance_aftercare"
    REVIEW_FOLLOW_UP = "review_follow_up"


class CanonFollowUpPreset(StrEnum):
    CANON_SIGNIFICANCE_CHANGED = "canon_significance_changed"
    TRUST_POSTURE_CHANGED_AFTER_RESOLUTION = "trust_posture_changed_after_resolution"
    CONTINUITY_LINEAGE_MATERIALLY_SHIFTED = "continuity_lineage_materially_shifted"
    RESOLVED_BUT_REVIEW_WORTHY = "resolved_but_review_worthy"
    POST_RESOLUTION_GOVERNANCE_RELEVANCE = "post_resolution_governance_relevance"
    AFTERCARE_NEEDED_NOW = "aftercare_needed_now"


@dataclass(frozen=True)
class CanonApprovalContext:
    approval_id: str
    status: str
    requested_action: str
    reason: str


@dataclass(frozen=True)
class CanonTrustContext:
    source_label: str
    trust_state: str
    summary: str


@dataclass(frozen=True)
class CanonConflictContext:
    topic: str
    severity: str
    summary: str


@dataclass(frozen=True)
class CanonLinkedContext:
    transition_id: str
    approval: CanonApprovalContext | None = None
    trust: CanonTrustContext | None = None
    conflict: CanonConflictContext | None = None
    continuity_summary: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonGovernanceReceiptContext:
    receipt_id: str
    receipt_type: str
    action_name: str
    ordering_marker: str
    summary: str


@dataclass(frozen=True)
class CanonTransitionSummary:
    transition_id: str
    topic: str
    mutation_class: str
    approval_reference: str | None
    approval_status: str | None
    lineage_cue: str
    semantic_delta_cue: str
    ordering_marker: str
    trust_cue: str | None = None
    conflict_cue: str | None = None
    continuity_cue: str | None = None


@dataclass(frozen=True)
class CanonSummaryPage:
    items: tuple[CanonTransitionSummary, ...]
    next_cursor: str | None = None
    preset: str | None = None


@dataclass(frozen=True)
class CanonBoundedLinkedView:
    summary: CanonTransitionSummary
    governance_receipt: CanonGovernanceReceiptContext | None = None
    linked_context: CanonLinkedContext | None = None
    why_this_matters_now: str = ""


@dataclass(frozen=True)
class CanonBoundedLinkedViewPage:
    items: tuple[CanonBoundedLinkedView, ...]
    next_cursor: str | None = None
    preset: str | None = None


@dataclass(frozen=True)
class CanonAttentionItem:
    summary: CanonTransitionSummary
    pressure_type: str
    why_this_matters_now: str
    linked_cue: str | None = None
    transition_id: str = ""


@dataclass(frozen=True)
class CanonAttentionGroup:
    pressure_type: str
    items: tuple[CanonAttentionItem, ...]
    next_cursor: str | None = None


@dataclass(frozen=True)
class CanonAttentionPage:
    groups: tuple[CanonAttentionGroup, ...]
    preset: str


@dataclass(frozen=True)
class CanonResolutionItem:
    summary: CanonTransitionSummary
    resolution_type: str
    why_resolved_now: str
    linked_cue: str | None = None
    transition_id: str = ""


@dataclass(frozen=True)
class CanonResolutionGroup:
    resolution_type: str
    items: tuple[CanonResolutionItem, ...]
    next_cursor: str | None = None


@dataclass(frozen=True)
class CanonResolutionPage:
    groups: tuple[CanonResolutionGroup, ...]
    preset: str


@dataclass(frozen=True)
class CanonFollowUpItem:
    summary: CanonTransitionSummary
    follow_up_type: str
    why_follow_up_now: str
    linked_cue: str | None = None
    transition_id: str = ""


@dataclass(frozen=True)
class CanonFollowUpGroup:
    follow_up_type: str
    items: tuple[CanonFollowUpItem, ...]
    next_cursor: str | None = None


@dataclass(frozen=True)
class CanonFollowUpPage:
    groups: tuple[CanonFollowUpGroup, ...]
    preset: str
