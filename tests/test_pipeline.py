import pytest

from engine.bundle import Bundle
from engine.egress import EgressError, EgressGuard, EgressPolicy
from engine.gate import AutoApproveGate
from engine.generator import FakeGenerator, GenResult, Generator
from engine.inputpack import InputPack
from engine.pipeline import STAGE_ORDER, build_pipeline
from engine.runner import Runner


def _pack(tmp_path, transcript="hello"):
    (tmp_path / "inputpack.yaml").write_text('beacon_id: 01P\n', encoding="utf-8")
    (tmp_path / "transcript.txt").write_text(transcript, encoding="utf-8")
    return InputPack(str(tmp_path))


def _cleartext():
    return EgressPolicy(alias="acme", terms=[], allow_cleartext=True)


class _Capture(Generator):
    def __init__(self):
        self.seen = []

    def generate(self, req):
        self.seen.append(self.compose_prompt(req))
        return GenResult(ok=True, data={"pains": []})


def test_build_pipeline_returns_the_canonical_ordered_stages(tmp_path):
    g = FakeGenerator(lambda req: GenResult(ok=True, data={}))
    stages = build_pipeline(_pack(tmp_path), g, _cleartext())
    assert [s.name for s in stages] == list(STAGE_ORDER)
    assert STAGE_ORDER == ("intake", "research", "solution", "audit", "mockup", "synthesize")


def test_build_pipeline_wires_generator_and_pack_into_the_right_stages(tmp_path):
    g = FakeGenerator(lambda req: GenResult(ok=True, data={}))
    intake, research, solution, audit, mockup, synth = build_pipeline(
        _pack(tmp_path), g, _cleartext())
    assert isinstance(research.gen, EgressGuard) and research.gen.inner is g
    assert solution.gen is research.gen and audit.gen is research.gen
    assert mockup.gen is research.gen and synth.gen is research.gen
    assert solution.pack is not None


def test_generating_stages_share_one_egress_guard_intake_is_unwrapped(tmp_path):
    pol = _cleartext()
    intake, research, solution, audit, mockup, synth = build_pipeline(
        _pack(tmp_path), _Capture(), pol)
    # one throat: every generating stage holds the SAME guard sharing the one policy
    guard = research.gen
    assert isinstance(guard, EgressGuard) and guard.policy is pol
    assert solution.gen is guard and audit.gen is guard
    assert mockup.gen is guard and mockup.verifier is guard and synth.gen is guard
    # intake does no egress -> it is not a generating stage and holds no guard
    assert not hasattr(intake, "gen")


def test_a_rejecting_egress_policy_blocks_the_run_at_the_first_generating_stage(tmp_path):
    # Cap B scenario 4, bound to the SHIPPED pipeline + Runner (not a test-local EgressStage).
    pol = EgressPolicy(alias="acme", terms=["X"], preview=lambda prompt: False)
    stages = build_pipeline(_pack(tmp_path, transcript="X slow onboarding"), _Capture(), pol)
    out = Runner(Bundle(str(tmp_path / "b")), AutoApproveGate()).run(stages)
    assert out["status"] == "blocked" and out["blocked_at"] == "research"


def test_egress_is_required_and_a_bad_policy_cannot_be_built(tmp_path):
    g = FakeGenerator(lambda req: GenResult(ok=True, data={}))
    with pytest.raises(TypeError):          # egress is a REQUIRED positional -> omitting it raises
        build_pipeline(_pack(tmp_path), g)
    with pytest.raises(EgressError):        # empty terms + no cleartext -> fail closed at construction
        EgressPolicy(alias="acme", terms=[])
