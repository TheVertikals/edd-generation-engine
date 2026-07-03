from engine.bundle import Bundle
from engine.checkpoint import Checkpoint
from engine.gate import AutoApproveGate
from engine.runner import Runner
from engine.stages.demo import SeedStage, TransformStage


def test_completed_stage_is_skipped_and_its_output_survives(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    # simulate a run interrupted after 'seed': seed already ran + was checkpointed
    b.write("seed.md", "# seed\n\nPRESERVED-UPSTREAM")
    Checkpoint(b.root).mark("seed")

    seed_calls = {"n": 0}

    class CountingSeed(SeedStage):
        def run(self, bundle):
            seed_calls["n"] += 1
            super().run(bundle)

    out = Runner(b, AutoApproveGate()).run([CountingSeed(), TransformStage()])
    assert out["status"] == "complete"
    assert seed_calls["n"] == 0                          # seed was complete -> skipped
    assert "PRESERVED-UPSTREAM" in b.read("seed.md")     # its output was not clobbered
    assert "PRESERVED-UPSTREAM" in b.read("result.md")   # and it flowed downstream
