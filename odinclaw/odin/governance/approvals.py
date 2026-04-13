from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

from odinclaw.contracts.approval import ApprovalRequest, ApprovalStatus
from odinclaw.contracts.provenance import ProvenanceRecord


class ApprovalStore:
    def __init__(self) -> None:
        self._requests: dict[str, ApprovalRequest] = {}

    def create(
        self,
        *,
        subject_type: str,
        subject_id: str,
        requested_action: str,
        requested_by: ProvenanceRecord,
        reason: str,
        metadata: dict[str, str] | None = None,
    ) -> ApprovalRequest:
        request = ApprovalRequest(
            approval_id=f"approval-{uuid4().hex}",
            subject_type=subject_type,
            subject_id=subject_id,
            requested_action=requested_action,
            requested_by=requested_by,
            reason=reason,
            metadata=dict(metadata or {}),
        )
        self._requests[request.approval_id] = request
        return request

    def approve(self, approval_id: str) -> ApprovalRequest:
        request = self._requests[approval_id]
        approved = replace(request, status=ApprovalStatus.APPROVED)
        self._requests[approval_id] = approved
        return approved

    def reject(self, approval_id: str) -> ApprovalRequest:
        request = self._requests[approval_id]
        rejected = replace(request, status=ApprovalStatus.REJECTED)
        self._requests[approval_id] = rejected
        return rejected

    def cancel(self, approval_id: str) -> ApprovalRequest:
        request = self._requests[approval_id]
        cancelled = replace(request, status=ApprovalStatus.CANCELLED)
        self._requests[approval_id] = cancelled
        return cancelled

    def get(self, approval_id: str) -> ApprovalRequest:
        return self._requests[approval_id]
