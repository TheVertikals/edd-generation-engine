from engine.generator import FakeGenerator, GenResult
from engine.inputpack import InputPack
from engine.pipeline import STAGE_ORDER, build_pipeline


def _pack(tmp_path):
    (tmp_path / "inputpack.yaml").write_text('beacon_id: 01P\n', encoding="utf-8")
    return InputPack(str(tmp_path))


def test_build_pipeline_returns_the_canonical_ordered_stages(tmp_path):
    g = FakeGenerator(lambda req: GenResult(ok=True, data={}))
    stages = build_pipeline(_pack(tmp_path), g)
    assert [s.name for s in stages] == list(STAGE_ORDER)
    assert STAGE_ORDER == ("intake", "research", "solution", "audit", "mockup", "synthesize")


def test_build_pipeline_wires_generator_and_pack_into_the_right_stages(tmp_path):
    g = FakeGenerator(lambda req: GenResult(ok=True, data={}))
    intake, research, solution, audit, mockup, synth = build_pipeline(_pack(tmp_path), g)
    assert research.gen is g and solution.gen is g and audit.gen is g
    assert mockup.gen is g and mockup.verifier is g and synth.gen is g
    assert solution.pack is not None  # SolutionStage got the pack for brand capture
