from __future__ import annotations

from odinclaw.contracts.trust import SourceDescriptor, TrustClass


def classify_source(source: SourceDescriptor) -> TrustClass:
    label = source.source_label.lower()
    source_type = source.source_type.lower()
    uri = (source.uri or "").lower()
    tags = {tag.lower() for tag in source.tags}

    if "blocked" in tags or "malware" in tags or "blocked" in label:
        return TrustClass.KNOWN_BAD_OR_BLOCKED
    if source_type == "self":
        return TrustClass.TRUSTED_SELF
    if source_type == "operator":
        return TrustClass.TRUSTED_OPERATOR
    if source_type == "tool":
        return TrustClass.APPROVED_TOOL
    if source_type == "provider":
        return TrustClass.APPROVED_PROVIDER
    if source_type in {"doctrine", "internal_knowledge"}:
        return TrustClass.TRUSTED_INTERNAL_KNOWLEDGE
    if uri.startswith("file://") or uri.startswith("app://"):
        return TrustClass.TRUSTED_SELF
    if "unknown" in tags or "ambiguous" in tags:
        return TrustClass.AMBIGUOUS_EXTERNAL
    if uri.startswith("http://") or uri.startswith("https://") or source_type == "external":
        if "untrusted" in tags:
            return TrustClass.UNTRUSTED_EXTERNAL
        if "approved" in tags:
            return TrustClass.APPROVED_PROVIDER
        return TrustClass.AMBIGUOUS_EXTERNAL
    return TrustClass.AMBIGUOUS_EXTERNAL
