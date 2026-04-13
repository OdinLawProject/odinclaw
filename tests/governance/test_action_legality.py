from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest, GovernanceOutcome
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.governance.action_legality import evaluate_action, preflight_action


def test_destructive_actions_hold_for_approval() -> None:
    decision = evaluate_action(ActionClass.DESTRUCTIVE_ACTION, TrustClass.TRUSTED_OPERATOR)
    assert decision.outcome == GovernanceOutcome.HOLD


def test_blocked_sources_are_denied() -> None:
    decision = evaluate_action(ActionClass.READ_ONLY_EXTERNAL, TrustClass.KNOWN_BAD_OR_BLOCKED)
    assert decision.outcome == GovernanceOutcome.DENY


def test_low_trust_mutation_escalates() -> None:
    decision = preflight_action(
        ActionRequest(
            action_name="submit_form",
            action_class=ActionClass.EXTERNAL_STATE_MUTATION,
            provenance=ProvenanceRecord(
                source_type="external",
                source_label="https://example.com",
                trust_class=TrustClass.UNTRUSTED_EXTERNAL,
            ),
        )
    )
    assert decision.outcome == GovernanceOutcome.ESCALATE


def test_durable_internal_mutation_is_held() -> None:
    decision = preflight_action(
        ActionRequest(
            action_name="write_memory",
            action_class=ActionClass.DURABLE_INTERNAL_STATE_MUTATION,
            provenance=ProvenanceRecord(
                source_type="operator",
                source_label="cli",
                trust_class=TrustClass.TRUSTED_OPERATOR,
            ),
        )
    )
    assert decision.outcome == GovernanceOutcome.HOLD
