from engine.bundle import Bundle
from engine.stage import GateSpec
from engine.stages.demo import SeedStage, TransformStage


def test_seed_stage_reads_source_writes_seed(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw input")
    SeedStage().run(b)
    assert "raw input" in b.read("seed.md")
    assert SeedStage().gate(b) is None


def test_transform_stage_reads_seed_writes_result_with_gate(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("seed.md", "seeded")
    t = TransformStage()
    t.run(b)
    assert b.read("result.md") is not None
    spec = t.gate(b)
    assert isinstance(spec, GateSpec) and spec.question
