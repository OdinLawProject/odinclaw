from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest
from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.governance.risk_classifier import classify_action_request


def _request(action_name: str, **payload: object) -> ActionRequest:
    return ActionRequest(
        action_name=action_name,
        action_class=ActionClass.READ_ONLY_LOCAL,
        provenance=ProvenanceRecord(
            source_type="operator",
            source_label="cli",
            trust_class=TrustClass.TRUSTED_OPERATOR,
        ),
        payload=payload,
    )


def test_action_class_mapping_is_explicit() -> None:
    assert classify_action_request(_request("open_url", url="https://example.com")) == ActionClass.NAVIGATION_ONLY
    assert classify_action_request(_request("tool_run", tool="ls")) == ActionClass.NON_DESTRUCTIVE_TOOL_USE
    assert classify_action_request(_request("use_secret", token="abc")) == ActionClass.CREDENTIALED_ACTION
    assert classify_action_request(_request("submit_form", body="mutate")) == ActionClass.EXTERNAL_STATE_MUTATION
    assert classify_action_request(_request("write_memory", target="durable")) == ActionClass.DURABLE_INTERNAL_STATE_MUTATION
    assert classify_action_request(_request("delete_file", target="tmp.txt")) == ActionClass.DESTRUCTIVE_ACTION
