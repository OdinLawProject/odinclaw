from __future__ import annotations

import re

from odinclaw.contracts.provenance import ProvenanceRecord
from odinclaw.contracts.reader import ReaderRequest, ReaderResult
from odinclaw.contracts.trust import SourceDescriptor
from odinclaw.odin.trust.classification import classify_source


def read_external_content(request: ReaderRequest) -> ReaderResult:
    if request.allow_execution or request.allow_mutation or request.allow_credentials:
        raise ValueError("read-only reader forbids execution, mutation, and credentials")

    source = SourceDescriptor(
        source_type=request.source_hint,
        source_label=request.uri,
        uri=request.uri,
        tags=("external",),
    )
    trust_class = classify_source(source)
    sanitized = _sanitize(request.content)
    return ReaderResult(
        uri=request.uri,
        sanitized_text=sanitized,
        trust_class=trust_class,
        provenance=ProvenanceRecord(
            source_type=request.source_hint,
            source_label=request.uri,
            trust_class=trust_class,
            via="read_only_reader",
        ),
        metadata={"sanitized": "true", "source_type": request.source_hint},
    )


def _sanitize(content: str) -> str:
    without_scripts = re.sub(r"<script.*?>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)
    without_tags = re.sub(r"<[^>]+>", " ", without_scripts)
    squashed = re.sub(r"\s+", " ", without_tags).strip()
    return squashed[:500]
