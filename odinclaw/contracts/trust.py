from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class TrustClass(StrEnum):
    TRUSTED_SELF = "TRUSTED_SELF"
    TRUSTED_OPERATOR = "TRUSTED_OPERATOR"
    APPROVED_TOOL = "APPROVED_TOOL"
    APPROVED_PROVIDER = "APPROVED_PROVIDER"
    TRUSTED_INTERNAL_KNOWLEDGE = "TRUSTED_INTERNAL_KNOWLEDGE"
    AMBIGUOUS_EXTERNAL = "AMBIGUOUS_EXTERNAL"
    UNTRUSTED_EXTERNAL = "UNTRUSTED_EXTERNAL"
    KNOWN_BAD_OR_BLOCKED = "KNOWN_BAD_OR_BLOCKED"


@dataclass(frozen=True)
class SourceDescriptor:
    source_type: str
    source_label: str
    uri: str | None = None
    tags: tuple[str, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)
