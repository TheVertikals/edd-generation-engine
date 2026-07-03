import json

from engine.bundle import Bundle
from engine.manifest import write_manifest


def test_manifest_is_semantic_keyed_with_prototypes(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("2_ENDSTATE_SPEC.md", "x")
    b.write("surfaces/prototype.html", "<h1>x</h1>")
    write_manifest(b, {"spec": "2_ENDSTATE_SPEC.md", "scoped_proposal": "8_SCOPED_PROPOSAL.md"},
                   prototypes=["surfaces/prototype.html", "surfaces/missing.html"])
    m = json.loads(b.read(".edd-manifest.json"))
    assert m["schema"] == "edd-bundle-manifest/1"
    assert m["artifacts"]["spec"] == {"path": "2_ENDSTATE_SPEC.md", "present": True}
    assert m["artifacts"]["scoped_proposal"]["present"] is False   # semantic key, absent file
    assert m["prototypes"] == ["surfaces/prototype.html"]           # missing dropped
