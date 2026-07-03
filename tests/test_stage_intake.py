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
