from __future__ import annotations

from dataclasses import dataclass, field

from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass


@dataclass(frozen=True)
class ReaderRequest:
    uri: str
    content: str
    source_hint: str = "external"
    allow_execution: bool = False
    allow_mutation: bool = False
    allow_credentials: bool = False


@dataclass(frozen=True)
class ReaderResult:
    uri: str
    sanitized_text: str
    trust_class: TrustClass
    provenance: ProvenanceRecord
    restricted: bool = True
    metadata: dict[str, str] = field(default_factory=dict)
