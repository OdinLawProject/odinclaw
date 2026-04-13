from pathlib import Path

from odinclaw.contracts.events import utc_now
from odinclaw.odin.continuity.evidence import ContinuityEvidenceStore, ContinuityLink


def test_continuity_store_persists_links(tmp_path: Path) -> None:
    store = ContinuityEvidenceStore(tmp_path / "continuity.jsonl")
    link = ContinuityLink(
        session_id="session-current",
        run_id="run-current",
        parent_session_id="session-parent",
        parent_run_id="run-parent",
        reason="session_started",
        recorded_at=utc_now(),
    )
    store.append(link)
    links = store.list_for_session("session-current")
    assert links == [link]
