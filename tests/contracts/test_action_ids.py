from odinclaw.contracts.action_ids import new_trace_ids


def test_new_trace_ids_are_populated() -> None:
    ids = new_trace_ids()
    assert ids.session_id
    assert ids.run_id
    assert ids.action_id
