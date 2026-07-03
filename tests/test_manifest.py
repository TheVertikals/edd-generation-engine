import json

from engine.bundle import Bundle
from engine.manifest import write_manifest


def test_manifest_records_presence(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("2_ENDSTATE_SPEC.md", "x")
    write_manifest(b, ["2_ENDSTATE_SPEC.md", "8_SCOPED_PROPOSAL.md"])
    m = json.loads(b.read(".edd-manifest.json"))
    assert m["schema"] == "edd-bundle-manifest/1"
    assert m["artifacts"]["2_ENDSTATE_SPEC.md"]["present"] is True
    assert m["artifacts"]["8_SCOPED_PROPOSAL.md"]["present"] is False
