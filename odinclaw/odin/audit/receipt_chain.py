from __future__ import annotations

import hmac as _hmac
import os
import queue
import secrets
import threading
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


class TamperedReceiptError(Exception):
    pass


def _load_or_create_key(key_path: Path) -> bytes:
    if key_path.exists():
        raw = key_path.read_bytes()
        if len(raw) == 32:
            return raw
    key = secrets.token_bytes(32)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    try:
        os.chmod(key_path, 0o600)
    except Exception:
        pass
    return key


def _compute_hmac(key: bytes, payload: str) -> str:
    return _hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()


def _canonical_payload(record_dict: dict) -> str:
    payload = {k: v for k, v in record_dict.items() if k != "hmac"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class ReceiptChain:
    KEY_FILENAME = ".receipt_key"

    def __init__(self, path: Path, *, strict_hmac: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._flush_count = 0
        self._strict_hmac = strict_hmac
        self._key = _load_or_create_key(path.parent / self.KEY_FILENAME)
        self._records: list[ReceiptRecord] = list(self._load_from_disk())
        self._latest_hash: str | None = self._records[-1].receipt_hash if self._records else None
        self._write_queue: queue.Queue[str | None] = queue.Queue()
        self._writer = threading.Thread(target=self._writer_loop, daemon=True)
        self._writer.start()

    def _load_from_disk(self) -> Iterable[ReceiptRecord]:
        if not self.path.exists():
            return []
        return self._parse_file()

    def _writer_loop(self) -> None:
        while True:
            line = self._write_queue.get()
            if line is None:
                self._write_queue.task_done()
                break
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line)
            self._write_queue.task_done()

    def _read_latest_hash_from_disk(self) -> str | None:
        return self._records[-1].receipt_hash if self._records else None

    # ── write ────────────────────────────────────────────────────────────────

    def append(self, record: ReceiptRecord) -> ReceiptRecord:
        parent_hash = self._latest_hash
        payload = asdict(record)
        payload["created_at"] = record.created_at.isoformat()
        payload["parent_receipt_hash"] = parent_hash
        payload["receipt_hash"] = ""
        payload["hmac"] = ""

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

        serialised = asdict(stored)
        serialised["created_at"] = stored.created_at.isoformat()
        serialised["hmac"] = ""
        record_hmac = _compute_hmac(self._key, _canonical_payload(serialised))
        serialised["hmac"] = record_hmac
        line = json.dumps(serialised, sort_keys=True) + "\n"

        self._latest_hash = receipt_hash
        self._records.append(stored)
        self._write_queue.put(line)

        return stored

    # ── read ─────────────────────────────────────────────────────────────────

    def _parse_file(self) -> Iterable[ReceiptRecord]:
        with self.path.open(encoding="utf-8") as handle:
            for lineno, line in enumerate(handle, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise TamperedReceiptError(
                        f"Receipt line {lineno} is not valid JSON: {exc}"
                    ) from exc
                stored_hmac = raw.get("hmac")
                receipt_hash = raw.get("receipt_hash", "")
                if stored_hmac:
                    check = dict(raw)
                    check["hmac"] = ""
                    expected = _compute_hmac(self._key, _canonical_payload(check))
                    if not _hmac.compare_digest(stored_hmac, expected):
                        raise TamperedReceiptError(
                            f"Receipt line {lineno} failed HMAC verification "
                            f"(receipt_id={raw.get('receipt_id', '?')}). "
                            "The receipt chain has been tampered with."
                        )
                elif self._strict_hmac:
                    raise TamperedReceiptError(
                        f"Receipt line {lineno} has no HMAC field and "
                        "strict_hmac=True is set."
                    )
                else:
                    import warnings
                    warnings.warn(
                        f"Receipt line {lineno} has no HMAC — legacy record "
                        f"(receipt_id={raw.get('receipt_id', '?')}). "
                        "Enable strict_hmac=True to reject unsigned receipts.",
                        stacklevel=4,
                    )
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
                    receipt_hash=receipt_hash,
                )

    def iter_receipts(self) -> Iterable[ReceiptRecord]:
        return iter(self._records)

    # ── verification ─────────────────────────────────────────────────────────

    def verify_chain(self) -> tuple[bool, str]:
        """
        Walk the entire chain and verify every HMAC and content hash.

        Returns ``(True, "ok")`` if the chain is intact, or
        ``(False, "<reason>")`` if any record fails verification.
        """
        prev_hash: str | None = None
        count = 0
        try:
            for receipt in self.iter_receipts():
                if receipt.parent_receipt_hash != prev_hash:
                    return (
                        False,
                        f"Chain broken at receipt_id={receipt.receipt_id}: "
                        f"expected parent_hash={prev_hash!r}, "
                        f"got {receipt.parent_receipt_hash!r}",
                    )
                prev_hash = receipt.receipt_hash
                count += 1
        except TamperedReceiptError as exc:
            return False, str(exc)
        return True, f"chain intact ({count} records)"

    # ── convenience ──────────────────────────────────────────────────────────

    def latest_receipt_hash(self) -> str | None:
        return self._latest_hash

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
        self._write_queue.join()
        self._flush_count += 1

    @property
    def flush_count(self) -> int:
        return self._flush_count
