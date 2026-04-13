from __future__ import annotations

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest, GovernanceDecision, GovernanceOutcome
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.governance.risk_classifier import classify_action_request


def evaluate_action(action_class: ActionClass, trust_class: TrustClass) -> GovernanceDecision:
    request = ActionRequest(
        action_name=action_class.value.lower(),
        action_class=action_class,
        provenance=__import__("odinclaw.contracts.provenance", fromlist=["ProvenanceRecord"]).ProvenanceRecord(
            source_type="synthetic",
            source_label="compat",
            trust_class=trust_class,
        ),
    )
    return preflight_action(request)


def preflight_action(request: ActionRequest) -> GovernanceDecision:
    action_class = classify_action_request(request)
    trust_class = request.provenance.trust_class

    if trust_class == TrustClass.KNOWN_BAD_OR_BLOCKED:
        return GovernanceDecision(
            outcome=GovernanceOutcome.DENY,
            reason="source is blocked",
            risk_notes=("blocked_source",),
        )
    if action_class == ActionClass.DESTRUCTIVE_ACTION:
        return GovernanceDecision(
            outcome=GovernanceOutcome.HOLD,
            reason="destructive action requires approval",
            risk_notes=("destructive_action",),
        )
    if action_class in {ActionClass.CREDENTIALED_ACTION, ActionClass.EXTERNAL_STATE_MUTATION}:
        if trust_class in {TrustClass.AMBIGUOUS_EXTERNAL, TrustClass.UNTRUSTED_EXTERNAL}:
            return GovernanceDecision(
                outcome=GovernanceOutcome.ESCALATE,
                reason="external mutation or credentials on low-trust input",
                risk_notes=("credential_or_mutation", "low_trust"),
            )
        return GovernanceDecision(
            outcome=GovernanceOutcome.HOLD,
            reason="credentialed or mutating action requires approval",
            risk_notes=("credential_or_mutation",),
        )
    if action_class == ActionClass.DURABLE_INTERNAL_STATE_MUTATION:
        return GovernanceDecision(
            outcome=GovernanceOutcome.HOLD,
            reason="durable internal mutation requires governance approval",
            risk_notes=("durable_mutation",),
        )
    if trust_class == TrustClass.AMBIGUOUS_EXTERNAL:
        return GovernanceDecision(
            outcome=GovernanceOutcome.HOLD,
            reason="ambiguous external input must be held",
            risk_notes=("ambiguous_input",),
        )
    if trust_class == TrustClass.UNTRUSTED_EXTERNAL and action_class != ActionClass.READ_ONLY_EXTERNAL:
        return GovernanceDecision(
            outcome=GovernanceOutcome.ESCALATE,
            reason="untrusted external input cannot drive non-reader actions directly",
            risk_notes=("untrusted_input",),
        )
    return GovernanceDecision(
        outcome=GovernanceOutcome.ALLOW,
        reason="within current policy envelope",
    )
