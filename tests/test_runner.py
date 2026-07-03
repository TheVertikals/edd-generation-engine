from engine.bundle import Bundle
from engine.gate import AutoApproveGate, ScriptedGate, Verdict
from engine.runner import Runner
from engine.stage import Stage
from engine.stages.demo import SeedStage, TransformStage


def _pipeline():
    return [SeedStage(), TransformStage()]


def test_runs_both_stages_to_complete(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    out = Runner(b, AutoApproveGate()).run(_pipeline())
    assert out["status"] == "complete"
    assert out["completed"] == ["seed", "transform"]
    assert b.read("result.md") is not None


def test_reject_stops_pipeline(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    out = Runner(b, ScriptedGate([Verdict("reject")])).run(_pipeline())
    assert out["status"] == "rejected"
    assert out["rejected_at"] == "transform"
    assert out["completed"] == ["seed"]


def test_revise_reruns_stage_then_approves(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    calls = {"n": 0}

    class Counting(TransformStage):
        def run(self, bundle):
            calls["n"] += 1
            super().run(bundle)

    out = Runner(b, ScriptedGate([Verdict("revise"), Verdict("approve")])).run(
        [SeedStage(), Counting()]
    )
    assert out["status"] == "complete"
    assert calls["n"] == 2  # ran once, revised (re-ran) once


def test_revision_limit_rejects(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    out = Runner(b, ScriptedGate([Verdict("revise")] * 10), max_revisions=2).run(
        _pipeline()
    )
    assert out["status"] == "rejected"
    assert out["rejected_at"] == "transform"


def test_stage_failure_returns_error_status(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")

    class Boom(Stage):
        name = "boom"

        def run(self, bundle):
            raise RuntimeError("kaboom")

    out = Runner(b, AutoApproveGate()).run([SeedStage(), Boom()])
    assert out["status"] == "error"
    assert out["failed_at"] == "boom"
    assert "kaboom" in out["error"]
    assert out["completed"] == ["seed"]  # seed finished before boom failed
