# tests/test_egress.py
import pytest
from engine.generator import GenRequest, GenResult, Generator
from engine.egress import EgressGuard, EgressPolicy, EgressError

class _Capture(Generator):
    def __init__(self): self.seen = []
    def generate(self, req):
        self.seen.append(self.compose_prompt(req)); return GenResult(ok=True, data={})

def _req(text, key="intake:1", note=None):
    return GenRequest(task="t", instructions="do it", grounding={key: text}, note=note)

def test_fail_closed_terms():
    with pytest.raises(EgressError): EgressPolicy(alias="x", terms=[])
    with pytest.raises(EgressError): EgressPolicy(alias="x", terms="RealCo Inc")
    EgressPolicy(alias="x", terms=[], allow_cleartext=True)

def test_scrubs_values_and_note_keeps_clean_keys():
    cap = _Capture()
    g = EgressGuard(cap, EgressPolicy(alias="ns", terms=["RealCo Inc", "Jane Realname"], preview=lambda p: True))
    g.generate(_req("RealCo Inc slow; jane@realco.com", key="corpus:mkt-1", note="Jane Realname called"))
    sent = cap.seen[0]
    assert "RealCo Inc" not in sent and "Jane Realname" not in sent    # value + note scrubbed
    assert "<email>" in sent and "corpus:mkt-1" in sent                # clean id preserved (resolves at audit)

def test_whitespace_key_blocks():                                      # N1: a client-content id fails closed
    g = EgressGuard(_Capture(), EgressPolicy(alias="ns", terms=["X"], preview=lambda p: True))
    with pytest.raises(EgressError):
        g.generate(_req("x", key="note-RealCo Inc-7"))

def test_preview_every_distinct_payload_and_dedupes():
    shown = []
    pol = EgressPolicy(alias="a", terms=["X"], preview=lambda p: (shown.append(p) or True))
    g = EgressGuard(_Capture(), pol)
    g.generate(_req("X one")); g.generate(_req("X one")); g.generate(_req("X two"))
    assert len(shown) == 2         # two DISTINCT payloads previewed; the repeat deduped (F4)

def test_missing_or_rejected_preview_blocks():
    with pytest.raises(EgressError):    # F2: no silent skip when a preview is required
        EgressGuard(_Capture(), EgressPolicy(alias="a", terms=["X"], preview=None)).generate(_req("X"))
    with pytest.raises(EgressError):
        EgressGuard(_Capture(), EgressPolicy(alias="a", terms=["X"], preview=lambda p: False)).generate(_req("X"))

def test_two_throats_share_dedup_state():
    shown = []
    pol = EgressPolicy(alias="a", terms=["X"], preview=lambda p: (shown.append(p) or True))
    EgressGuard(_Capture(), pol).generate(_req("X same"))
    EgressGuard(_Capture(), pol).generate(_req("X same"))
    assert len(shown) == 1         # identical payload across throats previewed once


def test_preview_dedups_on_client_content_not_instructions():
    shown = []
    pol = EgressPolicy(alias="a", terms=["X"], preview=lambda p: (shown.append(p) or True))
    g = EgressGuard(_Capture(), pol)
    g.generate(GenRequest(task="research", instructions="find pains", grounding={"intake:1": "X slow"}))
    g.generate(GenRequest(task="solution", instructions="DIFFERENT instructions", grounding={"intake:1": "X slow"}))
    assert len(shown) == 1        # same client content -> one approval, despite different instructions
    g.generate(GenRequest(task="stakeholder", instructions="i", grounding={"note:1": "X new content"}))
    assert len(shown) == 2        # genuinely new client content -> re-preview


def test_empty_grounding_is_not_covered_by_a_prior_approval():
    # B① skeleton-key: a prior approval of real client content must NOT cover an
    # empty-grounding payload (None key -> gate hashes the PROMPT, a distinct decision).
    shown = []
    pol = EgressPolicy(alias="a", terms=["X"], preview=lambda p: (shown.append(p) or True))
    g = EgressGuard(_Capture(), pol)
    g.generate(GenRequest(task="research", instructions="find pains", grounding={"intake:1": "X slow"}))
    assert len(shown) == 1
    g.generate(GenRequest(task="empty", instructions="no grounding here", grounding={}))
    assert len(shown) == 2        # empty grounding is a NEW decision, not auto-approved


def test_empty_grounding_still_fails_closed():
    # Empty grounding must still block on reject / missing preview (no skeleton-key bypass).
    with pytest.raises(EgressError):
        EgressGuard(_Capture(), EgressPolicy(alias="a", terms=["X"], preview=lambda p: False)).generate(
            GenRequest(task="t", instructions="i", grounding={}))
    with pytest.raises(EgressError):
        EgressGuard(_Capture(), EgressPolicy(alias="a", terms=["X"], preview=None)).generate(
            GenRequest(task="t", instructions="i", grounding={}))


def test_egress_reject_is_a_blocked_run_not_error(tmp_path):
    # F-6: an operator egress-reject is a first-class human block, not a crash.
    from engine.stage import Stage, StageBlocked
    from engine.bundle import Bundle
    from engine.gate import AutoApproveGate
    from engine.runner import Runner

    assert issubclass(EgressError, StageBlocked)

    class EgressStage(Stage):
        name = "egress"

        def run(self, bundle, note=None):
            EgressGuard(_Capture(), EgressPolicy(alias="a", terms=["X"], preview=lambda p: False)).generate(_req("X"))

    out = Runner(Bundle(str(tmp_path)), AutoApproveGate()).run([EgressStage()])
    assert out["status"] == "blocked"
    assert out["blocked_at"] == "egress"
