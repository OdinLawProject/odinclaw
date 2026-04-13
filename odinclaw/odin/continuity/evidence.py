from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import json

from odinclaw.contracts.continuity import ContinuityLink


class ContinuityEvidenceStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._flush_count = 0

    def append(self, link: ContinuityLink) -> None:
        serialised = asdict(link)
        serialised["recorded_at"] = link.recorded_at.isoformat()
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(serialised, sort_keys=True) + "\n")

    def list_for_session(self, session_id: str) -> list[ContinuityLink]:
        return [link for link in self.iter_links() if link.session_id == session_id]

    def iter_links(self) -> list[ContinuityLink]:
        if not self.path.exists():
            return []
        links: list[ContinuityLink] = []
        with self.path.open(encoding="utf-8") as handle:
            for line in handle:
                raw = json.loads(line)
                links.append(
                    ContinuityLink(
                        session_id=raw["session_id"],
                        run_id=raw["run_id"],
                        parent_session_id=raw.get("parent_session_id"),
                        parent_run_id=raw.get("parent_run_id"),
                        reason=raw["reason"],
                        recorded_at=datetime.fromisoformat(raw["recorded_at"]),
                        prior_state_id=raw.get("prior_state_id"),
                        resulting_state_id=raw.get("resulting_state_id"),
                        approval_id=raw.get("approval_id"),
                    )
                )
        return links

    def count(self) -> int:
        return len(self.iter_links())

    def flush(self) -> None:
        self._flush_count += 1

    @property
    def flush_count(self) -> int:
        return self._flush_count
