from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from odinclaw.contracts.provenance import ProvenanceRecord


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class ApprovalRequest:
    approval_id: str
    subject_type: str
    subject_id: str
    requested_action: str
    requested_by: ProvenanceRecord
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    metadata: dict[str, str] = field(default_factory=dict)
