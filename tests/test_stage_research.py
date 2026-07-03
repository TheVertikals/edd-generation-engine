import json

import pytest

from engine.bundle import Bundle
from engine.generator import FakeGenerator, GenResult
from engine.stages.research import GenerationError, ResearchStage


def _bundle(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding takes 6 weeks\nno self-serve docs\n")
    return b


def test_research_writes_grounded_painset(tmp_path):
    grounded = {"pains": [{"id": "p1", "statement": "slow onboarding", "kind": "stated",
                           "confidence": "verified", "sources": ["intake:1"], "basis": []}]}
    b = _bundle(tmp_path)
    ResearchStage(FakeGenerator({"research": grounded})).run(b)
    assert json.loads(b.read("pains.json"))["pains"][0]["id"] == "p1"


def test_research_self_corrects_then_succeeds(tmp_path):
    calls = {"n": 0}

    def responder(req):
        calls["n"] += 1
        src = "GHOST" if calls["n"] == 1 else "intake:1"
        return GenResult(ok=True, data={"pains": [
            {"id": "p1", "statement": "x", "kind": "stated",
             "confidence": "verified", "sources": [src], "basis": []}]})

    b = _bundle(tmp_path)
    ResearchStage(FakeGenerator(responder), max_regen=2).run(b)
    assert calls["n"] == 2
    assert json.loads(b.read("pains.json"))["pains"][0]["sources"] == ["intake:1"]


def test_research_raises_on_unusable_output(tmp_path):
    b = _bundle(tmp_path)
    with pytest.raises(GenerationError):
        ResearchStage(FakeGenerator(lambda req: GenResult(ok=True, data=None))).run(b)
