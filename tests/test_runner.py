from engine.bundle import Bundle
from engine.gate import AutoApproveGate, Gate, ScriptedGate, Verdict
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
        def run(self, bundle, note=None):
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

        def run(self, bundle, note=None):
            raise RuntimeError("kaboom")

    out = Runner(b, AutoApproveGate()).run([SeedStage(), Boom()])
    assert out["status"] == "error"
    assert out["failed_at"] == "boom"
    assert "kaboom" in out["error"]
    assert out["completed"] == ["seed"]  # seed finished before boom failed


def test_revise_passes_note_to_rerun(tmp_path):
    from engine.stage import GateSpec, Stage

    seen = []

    class NoteStage(Stage):
        name = "noteful"

        def run(self, bundle, note=None):
            seen.append(note)
            bundle.write("out.md", "x")

        def gate(self, bundle):
            return GateSpec("ok?")

    b = Bundle(str(tmp_path))
    Runner(b, ScriptedGate([Verdict("revise", note="tighten it"), Verdict("approve")])).run([NoteStage()])
    assert seen == [None, "tighten it"]


def test_unknown_verdict_fails_closed_rejected(tmp_path):
    # A2: a malformed/unknown verdict must NOT trigger revise/regenerate — fail closed.
    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    out = Runner(b, ScriptedGate([Verdict("garbage")])).run(_pipeline())
    assert out["status"] == "rejected"
    assert out["rejected_at"] == "transform"
    assert out["completed"] == ["seed"]


def test_runner_enriches_spec_with_stage_identity_and_preview_content(tmp_path):
    # A1: the Runner stamps spec.stage and resolves preview_content from the bundle.
    captured = []

    class CapturingGate(Gate):
        def request(self, spec):
            captured.append(spec)
            return Verdict("approve")

    b = Bundle(str(tmp_path))
    b.write("intake/source.txt", "raw")
    out = Runner(b, CapturingGate()).run(_pipeline())
    assert out["status"] == "complete"
    spec = captured[-1]
    assert spec.stage == "transform"
    assert spec.preview_content is not None
    assert spec.preview_content == b.read("result.md")


def test_blocked_distinct_from_error(tmp_path):
    from engine.stage import Stage, StageBlocked

    class Blocker(Stage):
        name = "blocker"

        def run(self, bundle, note=None):
            raise StageBlocked("policy")

    class Crasher(Stage):
        name = "crasher"

        def run(self, bundle, note=None):
            raise RuntimeError("bug")

    b1 = Bundle(str(tmp_path / "a"))
    out1 = Runner(b1, AutoApproveGate()).run([Blocker()])
    assert out1["status"] == "blocked" and out1["blocked_at"] == "blocker"

    b2 = Bundle(str(tmp_path / "b"))
    out2 = Runner(b2, AutoApproveGate()).run([Crasher()])
    assert out2["status"] == "error" and out2["failed_at"] == "crasher"
