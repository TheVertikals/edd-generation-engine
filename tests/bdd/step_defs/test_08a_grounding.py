import json

import pytest
from pytest_bdd import given, scenarios, then, when

from engine.bundle import Bundle
from engine.corpus import build_corpus
from engine.egress import EgressPolicy
from engine.gate import AutoApproveGate
from engine.generator import FakeGenerator, GenResult
from engine.grounding import GroundingError, audit
from engine.inputpack import InputPack
from engine.pipeline import build_pipeline
from engine.runner import Runner
from engine.stages.audit import GroundingAuditStage
from engine.stages.research import ResearchStage

scenarios("../features/08a-grounding.feature")


@pytest.fixture
def ctx():
    return {}


def _cleartext():
    return EgressPolicy(alias="acme", terms=[], allow_cleartext=True)


# ----- Scenario 1: a stated pain cites a resolving fact -----
@given("a customer intake adapted into the shared corpus as intake facts")
def _intake_corpus(ctx, tmp_path):
    b = Bundle(str(tmp_path / "b"))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding takes 6 weeks\n")
    ctx["bundle"] = b
    ctx["corpus"] = build_corpus(b)  # {"intake:1": "onboarding takes 6 weeks"}


@when("research proposes a stated pain that cites a corpus id")
def _stated_pain(ctx):
    ctx["good"] = [{"id": "p1", "statement": "slow onboarding", "confidence": "verified",
                    "sources": ["intake:1"], "basis": []}]
    ctx["bad"] = [{"id": "p1", "statement": "slow onboarding", "confidence": "verified",
                   "sources": ["intake:9"], "basis": []}]


@then("the pain is a fact tier and its cited id resolves to the corpus")
def _pain_resolves(ctx):
    assert audit(ctx["good"], corpus_ids=ctx["corpus"].keys()).ok


@then("a pain that cites an id not in the corpus is regenerated and then blocked by the audit")
def _regen_then_block(ctx):
    calls = {"n": 0}

    def responder(req):
        calls["n"] += 1
        return GenResult(ok=True, data={"pains": ctx["bad"]})  # always ungrounded

    ResearchStage(FakeGenerator(responder), max_regen=2).run(ctx["bundle"])
    assert calls["n"] == 3  # 1 + max_regen regenerations, all ungrounded
    with pytest.raises(GroundingError):  # the blocking audit still refuses to finalize
        GroundingAuditStage().run(ctx["bundle"])


# ----- Scenario 2: latent opinion traces transitively, no cycles -----
@given("a latent pain marked confidence inferred")
def _latent(ctx, tmp_path):
    b = Bundle(str(tmp_path / "b"))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding is slow\n")
    b.write("pains.json", json.dumps({"pains": [
        {"id": "p1", "statement": "onboarding is slow", "kind": "stated",
         "confidence": "verified", "sources": ["intake:1"], "basis": []},
        {"id": "p2", "statement": "latent churn", "kind": "latent",
         "confidence": "inferred", "sources": [], "basis": ["p1"]}]}))
    ctx["bundle"] = b


@when("the grounding audit evaluates it")
def _eval(ctx):
    GroundingAuditStage().run(ctx["bundle"])  # p2 grounds transitively via p1 -> no raise
    ctx["report"] = json.loads(ctx["bundle"].read("audit-report.json"))


@then("an opinion whose basis resolves transitively to a grounded fact passes")
def _transitive_ok(ctx):
    assert ctx["report"]["ok"] is True


@then("an opinion whose basis is missing, cyclic, or itself ungrounded fails the audit")
def _bad_basis_fails(ctx):
    corpus = {"intake:1"}
    # MISSING: the basis names an id that exists nowhere (not a claim, not the corpus).
    missing = [{"id": "m", "statement": "s", "confidence": "inferred", "sources": [], "basis": ["nope"]}]
    assert not audit(missing, corpus_ids=corpus).ok
    # CYCLIC: two opinions whose bases point only at each other — no fact floor.
    cyc = [{"id": "a", "statement": "s", "confidence": "inferred", "sources": [], "basis": ["b"]},
           {"id": "b", "statement": "s", "confidence": "inferred", "sources": [], "basis": ["a"]}]
    assert not audit(cyc, corpus_ids=corpus).ok
    # ITSELF UNGROUNDED: o resolves to a present opinion u, but u is itself ungrounded (its own
    # basis dangles), so the transitive walk never reaches a grounded fact.
    chain = [{"id": "u", "statement": "s", "confidence": "inferred", "sources": [], "basis": ["ghost"]},
             {"id": "o", "statement": "s", "confidence": "inferred", "sources": [], "basis": ["u"]}]
    assert not audit(chain, corpus_ids=corpus).ok


# ----- Scenario 3: the audit blocks ungrounded content before the mockup (via build_pipeline) -----
@given("a solution whose basis cites a GHOST id that is not in the corpus")
def _ghost_pack(ctx, tmp_path):
    d = tmp_path / "pack"
    d.mkdir()
    (d / "inputpack.yaml").write_text('beacon_id: 01A\nbrand_colors: "#0073CF"\n', encoding="utf-8")
    (d / "transcript.txt").write_text("onboarding takes 6 weeks", encoding="utf-8")
    ctx["pack"] = InputPack(str(d))
    ctx["bundle"] = Bundle(str(tmp_path / "b"))

    _MOCKUP = ('<head></head><body><h2 data-source="sol1" '
               'style="color:var(--brand-primary)">W</h2></body>')

    def responder(req):
        t = req.task
        if t == "research":
            return GenResult(ok=True, data={"pains": [
                {"id": "p1", "statement": "slow", "kind": "stated", "confidence": "verified",
                 "sources": ["intake:1"], "basis": []}]})
        if t == "creative-direction":
            return GenResult(ok=True, data={"claims": [
                {"id": "cd1", "statement": "primary", "confidence": "verified",
                 "sources": ["brand:0"], "basis": []}]})
        if t == "solution":  # ungrounded: basis cites a GHOST id
            return GenResult(ok=True, data={"solutions": [
                {"id": "sol1", "pain_id": "p1", "approach": "x", "confidence": "inferred",
                 "sources": [], "basis": ["GHOST"]}]})
        if t == "mockup":
            return GenResult(ok=True, text=_MOCKUP)
        if t == "grounding-audit":
            return GenResult(ok=True, data={"unsupported": []})
        if t == "purity-sweep":
            return GenResult(ok=True, data={"uncited": []})
        if t.startswith("synthesize:"):
            return GenResult(ok=True, text="## " + t + "\n")
        return GenResult(ok=False, error="unexpected %r" % t)

    ctx["gen"] = FakeGenerator(responder)


@when("the pipeline runs the blocking audit between solution and mockup")
def _run_pipeline(ctx):
    stages = build_pipeline(ctx["pack"], ctx["gen"], _cleartext())
    ctx["out"] = Runner(ctx["bundle"], AutoApproveGate()).run(stages)


@then("the run status is blocked at the audit stage")
def _blocked_at_audit(ctx):
    assert ctx["out"]["status"] == "blocked" and ctx["out"]["blocked_at"] == "audit"


@then("no prototype mockup is ever written")
def _no_mockup(ctx):
    assert not ctx["bundle"].exists("surfaces/prototype.html")


# ----- Scenario 4: empty/speculative cannot finalize; content-bound waiver only -----
@given("an audited claim set that is empty or carries a speculative claim")
def _spec(ctx, tmp_path):
    b = Bundle(str(tmp_path / "b"))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nslow\n")
    b.write("pains.json", json.dumps({"pains": [
        {"id": "p1", "statement": "maybe churn", "kind": "latent",
         "confidence": "speculative", "sources": [], "basis": []}]}))
    ctx["bundle"] = b
    ctx["root"] = tmp_path


@when("the audit runs with require-nonempty and block-speculative on")
def _run_audit(ctx):
    ctx["blocked"] = False
    try:
        GroundingAuditStage(block_speculative=True, require_nonempty=True).run(ctx["bundle"])
    except GroundingError:
        ctx["blocked"] = True


@then("the empty set blocks and the speculative claim blocks by default")
def _blocks(ctx):
    assert ctx["blocked"] is True
    empty = Bundle(str(ctx["root"] / "empty"))
    empty.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nslow\n")
    empty.write("pains.json", json.dumps({"pains": []}))
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(empty)


@then("only a content-bound waiver with a named approver downgrades that one claim")
def _waiver(ctx):
    ctx["bundle"].write("waivers.json", json.dumps(
        {"approved_speculative": [{"id": "p1", "statement": "maybe churn"}],
         "approved_by": "human:operator"}))
    GroundingAuditStage(block_speculative=True, require_nonempty=True).run(ctx["bundle"])
    rep = json.loads(ctx["bundle"].read("audit-report.json"))
    assert rep["ok"] is True and rep["waived"] == ["p1"]


@then("any malformed or unbound waiver file applies zero waivers")
def _malformed(ctx):
    ctx["bundle"].write("waivers.json", "not json")
    with pytest.raises(GroundingError):
        GroundingAuditStage(block_speculative=True, require_nonempty=True).run(ctx["bundle"])
    assert json.loads(ctx["bundle"].read("audit-report.json"))["ok"] is False
