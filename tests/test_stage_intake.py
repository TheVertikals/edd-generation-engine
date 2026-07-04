import json

from engine.bundle import Bundle
from engine.inputpack import InputPack
from engine.stages.intake import IntakeStage


def test_intake_writes_customer_doc_and_persists_beacon(tmp_path):
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "inputpack.yaml").write_text("beacon_id: 01BEAC\npack_version: 1\n", encoding="utf-8")
    (pack_dir / "transcript.txt").write_text("VP of Eng: onboarding takes 6 weeks.", encoding="utf-8")

    bundle = Bundle(str(tmp_path / "b"))
    stage = IntakeStage(InputPack(str(pack_dir)))
    stage.run(bundle)

    assert "onboarding takes 6 weeks" in bundle.read("0_CUSTOMER_INTAKE.md")
    manifest = json.loads(bundle.read("intake/manifest.json"))
    assert manifest["beacon_id"] == "01BEAC" and manifest["sources"] == []
    assert stage.gate(bundle).question == "captured right?"


import json, pytest
from engine.bundle import Bundle
from engine.inputpack import InputPack
from engine.stages.intake import IntakeStage

def _pack(tmp_path, body):
    (tmp_path / "inputpack.yaml").write_text(body, encoding="utf-8")
    (tmp_path / "transcript.txt").write_text("hello", encoding="utf-8")
    return InputPack(str(tmp_path))

def test_intake_persists_real_sources_list(tmp_path):
    b = Bundle(str(tmp_path / "bundle"))
    IntakeStage(_pack(tmp_path, 'beacon_id: 01ABC\nsources:\n  - cap-1\n  - cap-2\n')).run(b)
    got = json.loads(b.read("intake/manifest.json"))
    assert got["sources"] == ["cap-1", "cap-2"] and got["beacon_id"] == "01ABC"

def test_intake_raises_on_empty_beacon(tmp_path):
    b = Bundle(str(tmp_path / "bundle"))
    with pytest.raises(ValueError):
        IntakeStage(_pack(tmp_path, 'beacon_id:\nsources: []\n')).run(b)
