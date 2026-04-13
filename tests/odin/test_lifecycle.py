from pathlib import Path

from odinclaw.odin.orchestration.lifecycle import build_lifecycle


def test_startup_sequence_is_ordered(tmp_path: Path) -> None:
    lifecycle = build_lifecycle(tmp_path)
    state = lifecycle.startup()
    assert lifecycle.startup_steps == [
        "trace_receipt_services",
        "continuity_services",
        "durable_memory_authority",
        "governance_trust_hooks",
        "context_engine_readiness",
    ]
    assert state.startup_ready is True
    assert state.accepting_actions is True


def test_shutdown_flushes_and_persists(tmp_path: Path) -> None:
    lifecycle = build_lifecycle(tmp_path)
    lifecycle.startup()
    state = lifecycle.shutdown()
    assert lifecycle.shutdown_steps == [
        "stop_new_actions",
        "flush_receipts",
        "persist_continuity",
        "persist_durable_memory",
        "persist_repair_state",
    ]
    assert lifecycle.services.receipt_chain.flush_count == 1
    assert lifecycle.services.continuity_store.flush_count == 1
    assert lifecycle.repair_state.persisted is True
    assert state.shutdown_ready is True
