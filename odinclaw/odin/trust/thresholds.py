from __future__ import annotations

from dataclasses import dataclass

from odinclaw.contracts.context import ContextItem
from odinclaw.contracts.reader import ReaderResult
from odinclaw.contracts.trust import TrustClass


@dataclass(frozen=True)
class TrustThresholdDecision:
    include_in_context: bool
    allow_action: bool
    reader_restricted: bool
    caution: str | None = None


def evaluate_threshold(trust_class: TrustClass) -> TrustThresholdDecision:
    if trust_class == TrustClass.KNOWN_BAD_OR_BLOCKED:
        return TrustThresholdDecision(False, False, True, "blocked source")
    if trust_class == TrustClass.UNTRUSTED_EXTERNAL:
        return TrustThresholdDecision(False, False, True, "untrusted external source")
    if trust_class == TrustClass.AMBIGUOUS_EXTERNAL:
        return TrustThresholdDecision(True, False, True, "ambiguous external source")
    return TrustThresholdDecision(True, True, False, None)


def context_item_allowed(item: ContextItem) -> bool:
    trust_name = item.metadata.get("trust_class")
    if trust_name is None:
        return True
    return evaluate_threshold(TrustClass(trust_name)).include_in_context


def reader_result_allowed(result: ReaderResult) -> bool:
    return evaluate_threshold(result.trust_class).include_in_context
