import json

import pytest
from pytest_bdd import given, scenarios, then, when

from engine.bundle import Bundle
from engine.checkpoint import Checkpoint
from engine.egress import EgressPolicy
from engine.gate import AutoApproveGate, ScriptedGate, Verdict
from engine.generator import FakeGenerator, GenResult
from engine.inputpack import InputPack
from engine.pipeline import build_pipeline
from engine.runner import Runner
from engine.stages.intake import IntakeStage

scenarios("../features/08e-runner.feature")

_MOCKUP = ('<head></head><body><h2 data-source="sol1" '
           'style="color:var(--brand-primary)">W</h2></body>')


def _responder(req):
    t = req.task
    if t == "research":
        return GenResult(ok=True, data={"pains": [
            {"id": "p1", "statement": "slow", "kind": "stated", "confidence": "verified",
             "sources": ["intake:1"], "basis": []}]})
    if t == "creative-direction":
        return GenResult(ok=True, data={"claims": [
            {"id": "cd1", "statement": "primary", "confidence": "verified",
             "sources": ["brand:0"], "basis": []}]})
    if t == "solution":
        return GenResult(ok=True, data={"solutions": [
            {"id": "sol1", "pain_id": "p1", "approach": "wiz", "confidence": "inferred",
             "sources": [], "basis": ["p1"]}]})
    if t == "mockup":
        return GenResult(ok=True, text=_MOCKUP)
    if t == "grounding-audit":
        return GenResult(ok=True, data={"unsupported": []})
    if t == "purity-sweep":
        return GenResult(ok=True, data={"uncited": []})
    if t.startswith("synthesize:"):
        return GenResult(ok=True, text="## " + t + "\n")
    return GenResult(ok=False, error="unexpected %r" % t)


def _pack(tmp_path, beacon="01FULL", sub="pack"):
    d = tmp_path / sub
    d.mkdir(exist_ok=True)
    (d / "inputpack.yaml").write_text('beacon_id: %s\nbrand_colors: "#0073CF"\n' % beacon,
                                      encoding="utf-8")
    (d / "transcript.txt").write_text("onboarding takes 6 weeks", encoding="utf-8")
    return InputPack(str(d))


def _cleartext():
    return EgressPolicy(alias="acme", terms=[], allow_cleartext=True)


@pytest.fixture
def ctx():
    return {}


# ----- Scenario 1 -----
@given("an input pack whose manifest carries an engagement beacon id")
def _beacon_pack(ctx, tmp_path):
    ctx["tmp"] = tmp_path
    ctx["pack"] = _pack(tmp_path, beacon="01BEAC")


@when("intake adapts the pack into the bundle")
def _run_intake(ctx):
    ctx["bundle"] = Bundle(str(ctx["tmp"] / "b"))
    IntakeStage(ctx["pack"]).run(ctx["bundle"])


@then("the beacon id is persisted for downstream provenance")
def _persisted(ctx):
    assert json.loads(ctx["bundle"].read("intake/manifest.json"))["beacon_id"] == "01BEAC"


@then("an empty beacon id fails loudly")
def _empty(ctx):
    (ctx["tmp"] / "pack" / "inputpack.yaml").write_text("beacon_id:\n", encoding="utf-8")
    with pytest.raises(ValueError):
        IntakeStage(InputPack(str(ctx["tmp"] / "pack"))).run(Bundle(str(ctx["tmp"] / "b2")))


# ----- Scenario 2 -----
@given("a pipeline whose first stage fires the gate")
def _pipe(ctx, tmp_path):
    ctx["tmp"] = tmp_path
    ctx["pack"] = _pack(tmp_path)


@when("the operator returns a revise verdict then an approve")
def _revise(ctx):
    b = Bundle(str(ctx["tmp"] / "rev"))
    stages = build_pipeline(ctx["pack"], FakeGenerator(_responder), _cleartext())
    ctx["revise_out"] = Runner(b, ScriptedGate(
        [Verdict("revise", note="tighten"), Verdict("approve")] + [Verdict("approve")] * 6)).run(stages)


@then("the run completes after the revised stage re-runs")
def _rev_ok(ctx):
    assert ctx["revise_out"]["status"] == "complete"


@then("a reject or any unrecognized verdict stops the run as rejected")
def _reject(ctx):
    for bad in ("reject", "garbage"):
        b = Bundle(str(ctx["tmp"] / ("rej_" + bad)))
        stages = build_pipeline(ctx["pack"], FakeGenerator(_responder), _cleartext())
        out = Runner(b, ScriptedGate([Verdict(bad)])).run(stages)
        assert out["status"] == "rejected" and out["rejected_at"] == "intake"


# ----- Scenario 3 -----
@given("a run that completed intake and research then stopped")
def _partial(ctx, tmp_path):
    ctx["tmp"] = tmp_path
    ctx["pack"] = _pack(tmp_path)
    b = Bundle(str(tmp_path / "resume"))

    def fail_at_solution(req):
        if req.task in ("creative-direction", "solution"):
            return GenResult(ok=False, error="boom")
        return _responder(req)

    out = Runner(b, AutoApproveGate()).run(
        build_pipeline(ctx["pack"], FakeGenerator(fail_at_solution), _cleartext()))
    assert out["status"] == "error" and out["failed_at"] == "solution"
    assert Checkpoint(b.root).completed() == ["intake", "research"]
    ctx["bundle"] = b


@when("it is re-run")
def _rerun(ctx):
    ctx["out"] = Runner(ctx["bundle"], AutoApproveGate()).run(
        build_pipeline(ctx["pack"], FakeGenerator(_responder), _cleartext()))


@then("the checkpointed stages are skipped and it resumes at the next incomplete stage")
def _resumed(ctx):
    assert ctx["out"]["status"] == "complete"
    assert ctx["out"]["completed"] == [
        "intake", "research", "solution", "audit", "mockup", "synthesize"]


# ----- Scenario 4 -----
@given("a pipeline where a stage raises an unexpected error and another raises a policy block")
def _crash_and_block(ctx, tmp_path):
    ctx["tmp"] = tmp_path
    ctx["pack"] = _pack(tmp_path)


@when("the runner handles each")
def _handle(ctx):
    def ghost(req):  # policy block: an ungrounded solution -> GroundingAuditStage blocks at "audit"
        if req.task == "solution":
            return GenResult(ok=True, data={"solutions": [
                {"id": "sol1", "pain_id": "p1", "approach": "x", "confidence": "inferred",
                 "sources": [], "basis": ["GHOST"]}]})
        return _responder(req)

    b1 = Bundle(str(ctx["tmp"] / "block"))
    ctx["blocked"] = Runner(b1, AutoApproveGate()).run(
        build_pipeline(ctx["pack"], FakeGenerator(ghost), _cleartext()))
    ctx["block_bundle"] = b1

    def crash(req):  # unexpected error at research
        if req.task == "research":
            raise RuntimeError("kaboom")
        return _responder(req)

    b2 = Bundle(str(ctx["tmp"] / "crash"))
    ctx["errored"] = Runner(b2, AutoApproveGate()).run(
        build_pipeline(ctx["pack"], FakeGenerator(crash), _cleartext()))


@then("an unexpected error stops the run with status error and a policy block surfaces as blocked")
def _distinct(ctx):
    assert ctx["blocked"]["status"] == "blocked" and ctx["blocked"]["blocked_at"] == "audit"
    assert ctx["errored"]["status"] == "error" and ctx["errored"]["failed_at"] == "research"


@then("no later stage runs after the block")
def _no_later(ctx):
    assert not ctx["block_bundle"].exists("surfaces/prototype.html")
