import json

import pytest

from engine.bundle import Bundle
from engine.grounding import GroundingError
from engine.stages.audit import GroundingAuditStage


def _bundle(tmp_path, pains):
    b = Bundle(str(tmp_path))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding takes 6 weeks\n")
    b.write("pains.json", json.dumps({"pains": pains}))
    return b


def test_audit_passes_grounded_claims(tmp_path):
    b = _bundle(tmp_path, [{"id": "p1", "statement": "x", "kind": "stated",
                            "confidence": "verified", "sources": ["intake:1"], "basis": []}])
    GroundingAuditStage().run(b)
    assert json.loads(b.read("audit-report.json"))["ok"] is True


def test_audit_blocks_ungrounded_claims(tmp_path):
    b = _bundle(tmp_path, [{"id": "p1", "statement": "x", "kind": "stated",
                            "confidence": "verified", "sources": ["GHOST"], "basis": []}])
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(b)
    assert json.loads(b.read("audit-report.json"))["ok"] is False


def test_audit_blocks_empty_painset(tmp_path):
    b = _bundle(tmp_path, [])
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(b)


def _intake_and_pains(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding is slow\n")
    b.write("pains.json", json.dumps({"pains": [
        {"id": "p1", "statement": "onboarding is slow", "kind": "stated",
         "confidence": "verified", "sources": ["intake:1"], "basis": []},
        {"id": "p2", "statement": "latent churn risk", "kind": "latent",
         "confidence": "inferred", "sources": [], "basis": ["p1"]}]}))
    return b


def test_audit_passes_solution_grounded_off_a_latent_pain(tmp_path):
    b = _intake_and_pains(tmp_path)
    b.write("solutions.json", json.dumps({"solutions": [
        {"id": "sol1", "pain_id": "p2", "approach": "x", "statement": "x",
         "confidence": "inferred", "sources": [], "basis": ["p2"]}]}))
    GroundingAuditStage().run(b)
    assert json.loads(b.read("audit-report.json"))["ok"] is True


def test_audit_blocks_an_ungrounded_solution_from_the_solutions_file(tmp_path):
    b = _intake_and_pains(tmp_path)
    b.write("solutions.json", json.dumps({"solutions": [
        {"id": "sol1", "pain_id": "p1", "approach": "x", "statement": "x",
         "confidence": "inferred", "sources": [], "basis": ["GHOST"]}]}))
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(b)


def _spec_bundle(tmp_path):
    b = Bundle(str(tmp_path))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nonboarding is slow\n")
    b.write("pains.json", json.dumps({"pains": [
        {"id": "p1", "statement": "maybe churn", "kind": "latent",
         "confidence": "speculative", "sources": [], "basis": []}]}))
    return b


def test_speculative_blocks_without_a_waiver(tmp_path):
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(_spec_bundle(tmp_path))


def test_speculative_passes_with_a_content_bound_waiver(tmp_path):
    b = _spec_bundle(tmp_path)
    b.write("waivers.json", json.dumps({"approved_speculative": [{"id": "p1", "statement": "maybe churn"}],
                                        "approved_by": "human:operator"}))
    GroundingAuditStage().run(b)
    rep = json.loads(b.read("audit-report.json"))
    assert rep["ok"] is True and rep["waived"] == ["p1"]


def test_waiver_without_approver_is_ignored(tmp_path):
    b = _spec_bundle(tmp_path)
    b.write("waivers.json", json.dumps({"approved_speculative": [{"id": "p1", "statement": "maybe churn"}]}))
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(b)


def test_content_mismatch_waiver_is_rejected(tmp_path):
    b = _spec_bundle(tmp_path)   # claim p1 says "maybe churn"
    b.write("waivers.json", json.dumps({"approved_speculative": [{"id": "p1", "statement": "definitely churn"}],
                                        "approved_by": "human:operator"}))
    with pytest.raises(GroundingError):   # statement swapped -> waiver does NOT inherit approval
        GroundingAuditStage().run(b)
    rep = json.loads(b.read("audit-report.json"))
    assert rep["waived"] == [] and rep["rejected_waivers"]


def test_malformed_waiver_file_fails_closed_with_report(tmp_path):
    b = _spec_bundle(tmp_path)
    b.write("waivers.json", "not json at all")
    with pytest.raises(GroundingError):
        GroundingAuditStage().run(b)
    assert json.loads(b.read("audit-report.json"))["ok"] is False   # report still written
