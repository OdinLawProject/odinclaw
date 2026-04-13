import pytest

from odinclaw.contracts.reader import ReaderRequest
from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.trust.read_only_reader import read_external_content


def test_read_only_reader_sanitizes_and_emits_provenance() -> None:
    result = read_external_content(
        ReaderRequest(
            uri="https://example.com",
            content="<html><script>alert(1)</script><body>Hello <b>world</b></body></html>",
        )
    )
    assert "script" not in result.sanitized_text.lower()
    assert result.provenance.via == "read_only_reader"
    assert result.trust_class == TrustClass.AMBIGUOUS_EXTERNAL
    assert result.restricted is True


def test_read_only_reader_refuses_execution_or_mutation() -> None:
    with pytest.raises(ValueError):
        read_external_content(
            ReaderRequest(
                uri="https://example.com",
                content="unsafe",
                allow_execution=True,
            )
        )
