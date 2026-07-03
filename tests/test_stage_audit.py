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
