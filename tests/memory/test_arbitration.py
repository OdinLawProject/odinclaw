from odinclaw.contracts.trust import TrustClass
from odinclaw.odin.memory.arbitration import arbitrate_memory


def test_arbitration_keeps_canon_authoritative_and_suppresses_low_trust_provisional() -> None:
    result = arbitrate_memory(
        canon_reads=["canon lesson"],
        provisional_reads=["tentative note"],
        conflict_reads=["claim <> conflict"],
        session_reads=["latest session note"],
        trust_state=TrustClass.UNTRUSTED_EXTERNAL,
    )
    assert result.canon_reads == ["canon lesson"]
    assert result.provisional_reads == []
    assert result.session_reads == ["latest session note"]
    assert "Conflict memory warns against naive recall." in result.warnings
