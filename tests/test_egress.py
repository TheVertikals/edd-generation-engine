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
