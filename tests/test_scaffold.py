from engine.bundle import Bundle
from engine.scaffold import InternalScaffolder


def test_scaffold_creates_absent_never_clobbers(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("2_ENDSTATE_SPEC.md", "KEEP")
    InternalScaffolder().scaffold(b, {})
    assert b.read("2_ENDSTATE_SPEC.md") == "KEEP"          # not clobbered
    assert b.exists("8_SCOPED_PROPOSAL.md")                # created
    assert b.exists("9_CONTINUITY_TRACKER.md")
