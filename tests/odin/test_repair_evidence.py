from pathlib import Path

from odinclaw.odin.orchestration.lifecycle import build_lifecycle
from odinclaw.odin.repair.evidence import RepairReceiptRecord, RollbackEvidence


class TestRepairReceiptTypes:
    def test_repair_receipt_record_is_immutable(self) -> None:
        from odinclaw.contracts.action_ids import TraceIds, new_action_id, new_run_id, new_session_id
        trace_ids = TraceIds(
            session_id=new_session_id(),
            run_id=new_run_id(),
            action_id=new_action_id(),
        )
        receipt = RepairReceiptRecord(
            trace_ids=trace_ids,
            repair_type="enter_degraded_mode",
            reason="test reason",
        )
        assert receipt.repair_type == "enter_degraded_mode"
        assert receipt.rollback_evidence is None

    def test_rollback_evidence_carries_action_info(self) -> None:
        from odinclaw.contracts.action_ids import TraceIds, new_action_id, new_run_id, new_session_id
        trace_ids = TraceIds(
            session_id=new_session_id(),
            run_id=new_run_id(),
            action_id=new_action_id(),
        )
        evidence = RollbackEvidence(
            trace_ids=trace_ids,
            reason="action produced corrupt state",
            rolled_back_action_id="abc123",
            rolled_back_action_name="write_config",
            restored_to_checkpoint="checkpoint_v1",
        )
        assert evidence.rolled_back_action_id == "abc123"
        assert evidence.restored_to_checkpoint == "checkpoint_v1"


class TestDegradedModeTransitions:
    def test_enter_degraded_mode_sets_flag_and_emits_receipt(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        assert lifecycle.repair_state.degraded_mode is False

        receipt = lifecycle.enter_degraded_mode(reason="test_enter")
        assert lifecycle.repair_state.degraded_mode is True
        assert receipt.repair_type == "enter_degraded_mode"
        assert receipt.reason == "test_enter"
        assert receipt in lifecycle.repair_state.repair_receipts

    def test_exit_degraded_mode_clears_flag_and_emits_receipt(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.enter_degraded_mode(reason="entering")

        receipt = lifecycle.exit_degraded_mode(reason="test_exit")
        assert lifecycle.repair_state.degraded_mode is False
        assert receipt.repair_type == "exit_degraded_mode"
        assert len(lifecycle.repair_state.repair_receipts) == 2

    def test_record_rollback_stores_evidence_in_receipt(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()

        receipt = lifecycle.record_rollback(
            reason="state corruption detected",
            rolled_back_action_id="evt-999",
            rolled_back_action_name="mutate_memory",
            restored_to_checkpoint="pre_mutation",
        )
        assert receipt.repair_type == "rollback"
        assert receipt.rollback_evidence is not None
        assert receipt.rollback_evidence.rolled_back_action_name == "mutate_memory"
        assert receipt in lifecycle.repair_state.repair_receipts

    def test_shutdown_persists_repair_state_including_receipts(self, tmp_path: Path) -> None:
        lifecycle = build_lifecycle(tmp_path)
        lifecycle.startup()
        lifecycle.enter_degraded_mode(reason="pre-shutdown test")
        lifecycle.shutdown()

        assert lifecycle.repair_state.persisted is True
        assert len(lifecycle.repair_state.repair_receipts) == 1
