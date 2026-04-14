from __future__ import annotations

import hmac as _hmac
import os
import secrets
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
    """Raised when a receipt HMAC fails verification."""


def _load_or_create_key(key_path: Path) -> bytes:
    """
    Load the HMAC key from *key_path*, or generate and persist a new one.
    The key file is created with mode 0o600 (owner-read/write only).
    """
    if key_path.exists():
        raw = key_path.read_bytes()
        if len(raw) == 32:
            return raw
        # File exists but is wrong length — regenerate
    key = secrets.token_bytes(32)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    key_path.write_bytes(key)
    try:
        os.chmod(key_path, 0o600)
    except Exception:
        pass  # Windows doesn't support Unix permissions; best-effort
    return key


def _compute_hmac(key: bytes, payload: str) -> str:
    """Compute HMAC-SHA256 over an arbitrary payload string."""
    return _hmac.new(key, payload.encode("utf-8"), "sha256").hexdigest()


def _canonical_payload(record_dict: dict) -> str:
    """Return the canonical JSON of a record for HMAC computation.

    Strips the ``hmac`` field (which holds the signature itself) before
    serialising so that the HMAC covers every other field, including
    ``receipt_hash``, ``data``, ``provenance``, etc.  Any field-level
    tampering therefore invalidates the signature.
    """
    payload = {k: v for k, v in record_dict.items() if k != "hmac"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


class ReceiptChain:
    """
    Append-only JSONL receipt chain with SHA-256 content chaining and
    HMAC-SHA256 per-record authentication.

    Each record stores:
      parent_receipt_hash  — SHA-256 of the previous record (chaining)
      receipt_hash         — SHA-256 of this record's canonical JSON
      hmac                 — HMAC-SHA256(key, receipt_hash) authenticating
                             the record against the key in .receipt_key

    On ``iter_receipts()``, any record whose HMAC does not verify raises
    ``TamperedReceiptError``.  Records written before HMAC was introduced
    (no "hmac" field) are accepted with a warning — set
    ``strict_hmac=True`` on the constructor to reject them instead.
    """

    KEY_FILENAME = ".receipt_key"

    def __init__(self, path: Path, *, strict_hmac: bool = False) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._flush_count = 0
        self._strict_hmac = strict_hmac
        self._key = _load_or_create_key(path.parent / self.KEY_FILENAME)

    # ── write ────────────────────────────────────────────────────────────────

    def append(self, record: ReceiptRecord) -> ReceiptRecord:
        parent_hash = self.latest_receipt_hash()
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
        with self.path.open("a", encoding="utf-8") as handle:
            serialised = asdict(stored)
            serialised["created_at"] = stored.created_at.isoformat()
            # HMAC covers the full record (every field except "hmac" itself)
            # so that field-level tampering is detected even if receipt_hash
            # is left intact.
            serialised["hmac"] = ""  # placeholder so the key is present
            record_hmac = _compute_hmac(self._key, _canonical_payload(serialised))
            serialised["hmac"] = record_hmac
            handle.write(json.dumps(serialised, sort_keys=True) + "\n")
        return stored

    # ── read ─────────────────────────────────────────────────────────────────

    def iter_receipts(self) -> Iterable[ReceiptRecord]:
        if not self.path.exists():
            return ()

        def _iter() -> Iterable[ReceiptRecord]:
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

                    # ── HMAC verification ────────────────────────────────────
                    stored_hmac = raw.get("hmac")
                    receipt_hash = raw.get("receipt_hash", "")
                    if stored_hmac:
                        # Re-derive the canonical payload (hmac="" placeholder)
                        # so that any field change — not just receipt_hash —
                        # invalidates the signature.
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

        return _iter()

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
        latest: ReceiptRecord | None = None
        for latest in self.iter_receipts():
            pass
        return None if latest is None else latest.receipt_hash

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
