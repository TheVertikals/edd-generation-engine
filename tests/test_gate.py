import pytest

from engine.gate import AutoApproveGate, ScriptedGate, Verdict
from engine.stage import GateSpec


def test_auto_approve_always_approves():
    assert AutoApproveGate().request(GateSpec("ok?")).decision == "approve"


def test_scripted_gate_pops_in_order():
    g = ScriptedGate([Verdict("revise"), Verdict("approve")])
    assert g.request(GateSpec("q")).decision == "revise"
    assert g.request(GateSpec("q")).decision == "approve"


def test_scripted_gate_exhausted_raises():
    g = ScriptedGate([])
    with pytest.raises(AssertionError):
        g.request(GateSpec("q"))
