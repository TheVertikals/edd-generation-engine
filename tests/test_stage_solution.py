import json

from engine.bundle import Bundle
from engine.generator import FakeGenerator, GenResult
from engine.stages.solution import SolutionStage


def _b(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding takes 6 weeks\n")
    b.write("pains.json", json.dumps({"pains": [
        {"id": "p1", "statement": "slow onboarding", "kind": "stated",
         "confidence": "verified", "sources": ["intake:1"], "basis": []}]}))
    return b


def _responder(req):
    if req.task == "creative-direction":
        return GenResult(ok=True, data={"claims": [
            {"id": "cd1", "statement": "register: blueprint-navy", "confidence": "inferred",
             "sources": [], "basis": ["p1"]}]})
    return GenResult(ok=True, data={"solutions": [
        {"id": "sol1", "pain_id": "p1", "approach": "self-serve onboarding wizard",
         "confidence": "inferred", "sources": [], "basis": ["p1"]}]})


def test_solution_writes_grounded_solutions_and_direction(tmp_path):
    b = _b(tmp_path)
    stage = SolutionStage(FakeGenerator(_responder))
    stage.run(b)
    sol = json.loads(b.read("solutions.json"))["solutions"][0]
    assert sol["pain_id"] == "p1" and sol["basis"] == ["p1"] and sol["statement"] == sol["approach"]
    assert json.loads(b.read("creative-direction.json"))["claims"][0]["id"] == "cd1"
    assert stage.gate(b).question == "right solutions?"
