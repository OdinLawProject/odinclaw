from __future__ import annotations

from dataclasses import dataclass, field

from odinclaw.contracts.conflict import ConflictRecord
from odinclaw.contracts.continuity import ContinuityLink
from odinclaw.contracts.memory import DurableMemoryRecord, MemoryRecall
from odinclaw.contracts.receipts import ReceiptRecord
from odinclaw.contracts.trust import TrustClass


@dataclass(frozen=True)
class ContextItem:
    kind: str
    value: str
    source: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextAssembly:
    run_id: str
    items: tuple[ContextItem, ...]
    doctrine: tuple[DurableMemoryRecord, ...]
    durable_memory: tuple[DurableMemoryRecord, ...]
    continuity: tuple[ContinuityLink, ...]
    receipts: tuple[ReceiptRecord, ...]
    memory_recall: MemoryRecall | None = None
    conflicts: tuple[ConflictRecord, ...] = ()
    trust_state: TrustClass | None = None
    warnings: tuple[str, ...] = ()
