from engine.adapter import pack_to_bundle
from engine.bundle import Bundle
from engine.inputpack import InputPack


def test_pack_to_bundle_materializes_source_and_returns_manifest(tmp_path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "inputpack.yaml").write_text(
        "beacon_id: 01ADP\npack_version: 1\n", encoding="utf-8"
    )
    (pack_dir / "transcript.txt").write_text("call notes", encoding="utf-8")

    bundle = Bundle(str(tmp_path / "b"))
    manifest = pack_to_bundle(InputPack(str(pack_dir)), bundle)

    assert bundle.read("intake/source.txt") == "call notes"
    assert manifest["beacon_id"] == "01ADP"


import json
from engine.adapter import pack_to_bundle
from engine.bundle import Bundle
from engine.inputpack import InputPack

def test_pack_corpus_intelligence_materialized(tmp_path):
    p = tmp_path / "pack"; p.mkdir()
    (p / "inputpack.yaml").write_text("beacon_id: 01X\n", encoding="utf-8")
    (p / "transcript.txt").write_text("t", encoding="utf-8")
    (p / "corpus-intelligence.json").write_text(json.dumps({"items": [{"id": "c1", "statement": "s"}]}))
    b = Bundle(str(tmp_path / "b"))
    pack_to_bundle(InputPack(str(p)), b)
    assert json.loads(b.read("corpus-intelligence.json"))["items"][0]["id"] == "c1"

def test_pack_without_corpus_intelligence_ok(tmp_path):
    p = tmp_path / "pack"; p.mkdir()
    (p / "inputpack.yaml").write_text("beacon_id: 01X\n", encoding="utf-8")
    (p / "transcript.txt").write_text("t", encoding="utf-8")
    b = Bundle(str(tmp_path / "b"))
    pack_to_bundle(InputPack(str(p)), b)               # no crash
    assert b.read("corpus-intelligence.json") is None
