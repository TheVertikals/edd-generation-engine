import json

from engine.bundle import Bundle
from engine.gate import AutoApproveGate
from engine.generator import FakeGenerator, GenResult
from engine.inputpack import InputPack
from engine.runner import Runner
from engine.stages.audit import GroundingAuditStage
from engine.stages.intake import IntakeStage
from engine.stages.research import ResearchStage


def _pack(tmp_path):
    d = tmp_path / "pack"
    d.mkdir()
    (d / "inputpack.yaml").write_text("beacon_id: 01E2E\npack_version: 1\n", encoding="utf-8")
    (d / "transcript.txt").write_text("VP: onboarding takes 6 weeks\nno self-serve docs", encoding="utf-8")
    return InputPack(str(d))


def _verifier_ok():
    return FakeGenerator(lambda req: GenResult(ok=True, data={"unsupported": []}))


def test_grounded_run_completes_through_audit(tmp_path):
    grounded = {"pains": [{"id": "p1", "statement": "slow onboarding", "kind": "stated",
                           "confidence": "verified", "sources": ["intake:1"], "basis": []}]}
    b = Bundle(str(tmp_path / "b"))
    stages = [IntakeStage(_pack(tmp_path)), ResearchStage(FakeGenerator({"research": grounded})),
              GroundingAuditStage(generator=_verifier_ok())]
    out = Runner(b, AutoApproveGate()).run(stages)
    assert out["status"] == "complete"
    assert out["completed"] == ["intake", "research", "audit"]
    assert json.loads(b.read("audit-report.json"))["ok"] is True


def test_ungrounded_run_is_blocked_at_audit(tmp_path):
    bad = {"pains": [{"id": "p1", "statement": "made up", "kind": "stated",
                      "confidence": "verified", "sources": ["GHOST"], "basis": []}]}
    b = Bundle(str(tmp_path / "b"))
    stages = [IntakeStage(_pack(tmp_path)), ResearchStage(FakeGenerator({"research": bad}), max_regen=1),
              GroundingAuditStage()]
    out = Runner(b, AutoApproveGate()).run(stages)
    assert out["status"] == "blocked" and out["blocked_at"] == "audit"
    assert json.loads(b.read("audit-report.json"))["ok"] is False


def test_garbled_generation_errors_not_silently_finalized(tmp_path):
    b = Bundle(str(tmp_path / "b"))
    stages = [IntakeStage(_pack(tmp_path)),
              ResearchStage(FakeGenerator(lambda req: GenResult(ok=True, data=None))),
              GroundingAuditStage()]
    out = Runner(b, AutoApproveGate()).run(stages)
    assert out["status"] == "error" and out["failed_at"] == "research"
