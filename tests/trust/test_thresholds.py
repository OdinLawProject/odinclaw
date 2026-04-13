from odinclaw.contracts.context import ContextItem
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.trust.thresholds import context_item_allowed, evaluate_threshold


def test_trust_thresholds_affect_context_and_actions() -> None:
    blocked = evaluate_threshold(TrustClass.KNOWN_BAD_OR_BLOCKED)
    assert blocked.include_in_context is False
    assert blocked.allow_action is False

    ambiguous = evaluate_threshold(TrustClass.AMBIGUOUS_EXTERNAL)
    assert ambiguous.include_in_context is True
    assert ambiguous.allow_action is False

    item = ContextItem(kind="receipt", value="x", source="action", metadata={"trust_class": TrustClass.UNTRUSTED_EXTERNAL.value})
    assert context_item_allowed(item) is False
