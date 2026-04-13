from odinclaw.contracts.trust import SourceDescriptor, TrustClass
from odinclaw.odin.trust.classification import classify_source


def test_trust_classification_covers_representative_sources() -> None:
    assert classify_source(SourceDescriptor(source_type="operator", source_label="cli")) == TrustClass.TRUSTED_OPERATOR
    assert classify_source(SourceDescriptor(source_type="tool", source_label="shell")) == TrustClass.APPROVED_TOOL
    assert classify_source(SourceDescriptor(source_type="external", source_label="page", uri="https://example.com")) == TrustClass.AMBIGUOUS_EXTERNAL
    assert classify_source(SourceDescriptor(source_type="external", source_label="blocked page", uri="https://bad.example", tags=("blocked",))) == TrustClass.KNOWN_BAD_OR_BLOCKED
