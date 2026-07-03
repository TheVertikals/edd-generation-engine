from engine.adapter import pack_to_bundle
from engine.bundle import Bundle
from engine.gate import AutoApproveGate
from engine.inputpack import InputPack
from engine.runner import Runner
from engine.stages.demo import SeedStage, TransformStage


def test_stub_pack_walks_to_output(tmp_path):
    # a stub InputPack (no real intake source) — proves the skeleton end to end
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (pack_dir / "inputpack.yaml").write_text(
        "beacon_id: 01SKEL\npack_version: 1\n", encoding="utf-8"
    )
    (pack_dir / "transcript.txt").write_text("a discovery call", encoding="utf-8")
    pack = InputPack(str(pack_dir))

    bundle = Bundle(str(tmp_path / "bundle"))
    manifest = pack_to_bundle(pack, bundle)  # intake seam, through engine code

    out = Runner(bundle, AutoApproveGate()).run([SeedStage(), TransformStage()])
    assert out["status"] == "complete"
    assert out["completed"] == ["seed", "transform"]
    assert "A DISCOVERY CALL" in bundle.read("result.md")
    assert manifest["beacon_id"] == "01SKEL"
