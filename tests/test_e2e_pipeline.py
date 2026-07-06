import json

from engine.bundle import Bundle
from engine.egress import EgressPolicy
from engine.gate import AutoApproveGate
from engine.generator import FakeGenerator, GenResult
from engine.inputpack import InputPack
from engine.pipeline import build_pipeline
from engine.runner import Runner


def _pack(tmp_path):
    d = tmp_path / "pack"
    d.mkdir()
    (d / "inputpack.yaml").write_text(
        'beacon_id: 01FULL\nbrand_colors: "#0A2540,#0073CF"\n', encoding="utf-8")
    (d / "transcript.txt").write_text("VP: onboarding takes 6 weeks\nno self-serve docs", encoding="utf-8")
    return InputPack(str(d))


_PAINS = {"pains": [{"id": "p1", "statement": "slow onboarding", "kind": "stated",
                     "confidence": "verified", "sources": ["intake:1"], "basis": []}]}
_CD = {"claims": [{"id": "cd1", "statement": "primary #0073cf", "confidence": "verified",
                   "sources": ["brand:1"], "basis": []}]}
_SOLS = {"solutions": [{"id": "sol1", "pain_id": "p1", "approach": "self-serve wizard",
                        "confidence": "inferred", "sources": [], "basis": ["p1"]}]}
_MOCKUP = ('<head></head><body><h2 data-source="sol1" style="color:var(--brand-primary)">Wizard</h2>'
           '</body>')


def _responder(req):
    t = req.task
    if t == "research":
        return GenResult(ok=True, data=_PAINS)
    if t == "creative-direction":
        return GenResult(ok=True, data=_CD)
    if t == "solution":
        return GenResult(ok=True, data=_SOLS)
    if t == "mockup":
        return GenResult(ok=True, text=_MOCKUP)
    if t == "grounding-audit":
        return GenResult(ok=True, data={"unsupported": []})
    if t == "purity-sweep":
        return GenResult(ok=True, data={"uncited": []})
    if t.startswith("synthesize:"):
        return GenResult(ok=True, text="## " + t + "\n")
    return GenResult(ok=False, error="unexpected task %r" % t)


def test_full_pipeline_produces_a_grounded_bundle(tmp_path):
    g = FakeGenerator(_responder)
    pack = _pack(tmp_path)
    b = Bundle(str(tmp_path / "b"))
    stages = build_pipeline(pack, g, EgressPolicy(alias="acme", terms=[], allow_cleartext=True))
    out = Runner(b, AutoApproveGate()).run(stages)
    assert out["status"] == "complete"
    assert out["completed"] == ["intake", "research", "solution", "audit", "mockup", "synthesize"]
    for f in ("0_CUSTOMER_INTAKE.md", "pains.json", "solutions.json", "creative-direction.json",
              "brand.json", "surfaces/prototype.html", "2_ENDSTATE_SPEC.md", ".edd-manifest.json"):
        assert b.exists(f), f
    html = b.read("surfaces/prototype.html")
    assert 'data-source="sol1"' in html and "--brand-primary" in html
    assert json.loads(b.read("brand.json"))["colors"][0]["source"] == "pack"


def test_pipeline_blocks_ungrounded_solution_before_mockup(tmp_path):
    def bad(req):
        if req.task == "solution":
            return GenResult(ok=True, data={"solutions": [
                {"id": "sol1", "pain_id": "p1", "approach": "x", "confidence": "inferred",
                 "sources": [], "basis": ["GHOST"]}]})
        return _responder(req)

    g = FakeGenerator(bad)
    pack = _pack(tmp_path)
    b = Bundle(str(tmp_path / "b"))
    stages = build_pipeline(pack, g, EgressPolicy(alias="acme", terms=[], allow_cleartext=True))
    out = Runner(b, AutoApproveGate()).run(stages)
    assert out["status"] == "blocked" and out["blocked_at"] == "audit"
    assert not b.exists("surfaces/prototype.html")   # mockup never ran
