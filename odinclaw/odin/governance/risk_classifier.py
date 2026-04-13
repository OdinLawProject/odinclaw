from __future__ import annotations

from odinclaw.contracts.action_classes import ActionClass
from odinclaw.contracts.governance import ActionRequest


def classify_action_request(request: ActionRequest) -> ActionClass:
    payload_text = " ".join(str(value).lower() for value in request.payload.values())
    action_name = request.action_name.lower()

    if request.action_class != ActionClass.READ_ONLY_LOCAL:
        return request.action_class
    if any(token in action_name or token in payload_text for token in ("delete", "destroy", "wipe", "remove")):
        return ActionClass.DESTRUCTIVE_ACTION
    if any(token in action_name or token in payload_text for token in ("password", "token", "credential", "secret")):
        return ActionClass.CREDENTIALED_ACTION
    if any(token in action_name or token in payload_text for token in ("write_memory", "remember", "durable")):
        return ActionClass.DURABLE_INTERNAL_STATE_MUTATION
    if any(token in action_name or token in payload_text for token in ("submit", "post", "upload", "mutate")):
        return ActionClass.EXTERNAL_STATE_MUTATION
    if "http" in payload_text or "open_url" in action_name or "navigate" in action_name:
        return ActionClass.NAVIGATION_ONLY
    if "tool" in action_name:
        return ActionClass.NON_DESTRUCTIVE_TOOL_USE
    return request.action_class
