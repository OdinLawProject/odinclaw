from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import json
from typing import Iterable

from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.receipts import ReceiptQuery, ReceiptRecord
from odinclaw.contracts.action_ids import TraceIds
from odinclaw.contracts.trust import TrustClass


class ReceiptChain:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._flush_count = 0

    def append(self, record: ReceiptRecord) -> ReceiptRecord:
        parent_hash = self.latest_receipt_hash()
        payload = asdict(record)
        payload["created_at"] = record.created_at.isoformat()
        payload["parent_receipt_hash"] = parent_hash
        payload["receipt_hash"] = ""
        receipt_hash = sha256(
            (
                (parent_hash or "")
                + json.dumps(payload, sort_keys=True, separators=(",", ":"))
            ).encode("utf-8")
        ).hexdigest()
        stored = ReceiptRecord(
            receipt_id=record.receipt_id,
            receipt_type=record.receipt_type,
            trace_ids=record.trace_ids,
            action_name=record.action_name,
            created_at=record.created_at,
            provenance=record.provenance,
            data=record.data,
            parent_receipt_hash=parent_hash,
            receipt_hash=receipt_hash,
        )
        with self.path.open("a", encoding="utf-8") as handle:
            serialised = asdict(stored)
            serialised["created_at"] = stored.created_at.isoformat()
            handle.write(json.dumps(serialised, sort_keys=True) + "\n")
        return stored

    def latest_receipt_hash(self) -> str | None:
        latest: ReceiptRecord | None = None
        for latest in self.iter_receipts():
            pass
        return None if latest is None else latest.receipt_hash

    def iter_receipts(self) -> Iterable[ReceiptRecord]:
        if not self.path.exists():
            return ()

        def _iter() -> Iterable[ReceiptRecord]:
            with self.path.open(encoding="utf-8") as handle:
                for line in handle:
                    raw = json.loads(line)
                    yield ReceiptRecord(
                        receipt_id=raw["receipt_id"],
                        receipt_type=raw["receipt_type"],
                        trace_ids=TraceIds(**raw["trace_ids"]),
                        action_name=raw["action_name"],
                        created_at=datetime.fromisoformat(raw["created_at"]),
                        provenance=ProvenanceRecord(
                            source_type=raw["provenance"]["source_type"],
                            source_label=raw["provenance"]["source_label"],
                            trust_class=TrustClass(raw["provenance"]["trust_class"]),
                            via=raw["provenance"].get("via", "direct"),
                            metadata=raw["provenance"].get("metadata", {}),
                        ),
                        data=raw["data"],
                        parent_receipt_hash=raw.get("parent_receipt_hash"),
                        receipt_hash=raw["receipt_hash"],
                    )

        return _iter()

    def query(self, query: ReceiptQuery) -> list[ReceiptRecord]:
        results: list[ReceiptRecord] = []
        for receipt in self.iter_receipts():
            if query.run_id is not None and receipt.trace_ids.run_id != query.run_id:
                continue
            if query.session_id is not None and receipt.trace_ids.session_id != query.session_id:
                continue
            if query.action_id is not None and receipt.trace_ids.action_id != query.action_id:
                continue
            if query.receipt_type is not None and receipt.receipt_type != query.receipt_type:
                continue
            results.append(receipt)
        return results

    def query_for_context(self, *, run_id: str, limit: int) -> list[ReceiptRecord]:
        receipts = self.query(ReceiptQuery(run_id=run_id))
        return receipts[-limit:]

    def count(self) -> int:
        return sum(1 for _ in self.iter_receipts())

    def flush(self) -> None:
        self._flush_count += 1

    @property
    def flush_count(self) -> int:
        return self._flush_count
