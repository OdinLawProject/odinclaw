from __future__ import annotations

from dataclasses import dataclass, field

from odinclaw.contracts.trust import TrustClass


@dataclass(frozen=True)
class ProvenanceRecord:
    source_type: str
    source_label: str
    trust_class: TrustClass
    via: str = "direct"
    metadata: dict[str, str] = field(default_factory=dict)
