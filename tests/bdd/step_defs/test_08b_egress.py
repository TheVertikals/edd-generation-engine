import pytest
from pytest_bdd import given, scenarios, then, when

from engine.bundle import Bundle
from engine.egress import EgressError, EgressGuard, EgressPolicy
from engine.gate import AutoApproveGate
from engine.generator import GenRequest, GenResult, Generator
from engine.inputpack import InputPack
from engine.pipeline import build_pipeline
from engine.runner import Runner

scenarios("../features/08b-egress.feature")


class _Capture(Generator):
    def __init__(self):
        self.seen = []

    def generate(self, req):
        self.seen.append(self.compose_prompt(req))
        return GenResult(ok=True, data={"pains": []})


@pytest.fixture
def ctx():
    return {}


def _pack(tmp_path, transcript="x"):
    d = tmp_path / "pack"
    d.mkdir(exist_ok=True)
    (d / "inputpack.yaml").write_text('beacon_id: 01B\nbrand_colors: "#0A2540"\n', encoding="utf-8")
    (d / "transcript.txt").write_text(transcript, encoding="utf-8")
    return InputPack(str(d))


# ----- Scenario 1 -----
@given("a pipeline built with a redacting egress policy and a capturing generator")
def _redacting(ctx, tmp_path):
    cap = _Capture()
    pol = EgressPolicy(alias="acme", terms=["RealCo Inc", "Jane Realname"],
                       preview=lambda prompt: True)
    stages = build_pipeline(_pack(tmp_path), cap, pol)
    # the wiring under test is production: the guard came from build_pipeline, shared across stages
    assert isinstance(stages[1].gen, EgressGuard) and stages[1].gen.policy is pol
    assert stages[2].gen is stages[1].gen
    ctx["capture"], ctx["guard"] = cap, stages[1].gen


@when("a request that names the client and contains an email passes the shared guard")
def _pass(ctx):
    # the email + a client term appear in EVERY field so we can assert masking across all of them (F8)
    ctx["guard"].generate(GenRequest(
        task="research", instructions="handle RealCo Inc, reply to jane@realco.com",
        grounding={"corpus:mkt-1": "RealCo Inc slow; jane@realco.com"},
        note="Jane Realname (jane@realco.com) called"))


@then("the client terms are replaced by the alias and the email is masked across all fields")
def _scrubbed(ctx):
    sent = ctx["capture"].seen[0]
    # client terms redacted in instructions + grounding + note, AND the email masked in every field (F8)
    assert "RealCo Inc" not in sent and "Jane Realname" not in sent
    assert "jane@realco.com" not in sent and "<email>" in sent


@then("the grounding ids are left intact so they still resolve at the audit")
def _ids(ctx):
    assert "corpus:mkt-1" in ctx["capture"].seen[0]


# ----- Scenario 2 -----
@given("an egress policy with an empty redact-term list and no cleartext allowance")
def _noop2(ctx):
    pass


@when("the policy is constructed")
def _construct(ctx):
    try:
        EgressPolicy(alias="acme", terms=[])
        ctx["raised"] = False
    except EgressError:
        ctx["raised"] = True


@then("it raises and blocks before any pipeline can be built")
def _raised(ctx):
    assert ctx["raised"] is True


# ----- Scenario 3 -----
@given("a pipeline built with an operator-preview egress policy")
def _preview(ctx, tmp_path):
    ctx["shown"] = []
    pol = EgressPolicy(alias="a", terms=["X"],
                       preview=lambda prompt: (ctx["shown"].append(prompt) or True))
    ctx["guard"] = build_pipeline(_pack(tmp_path), _Capture(), pol)[1].gen
    ctx["reject_guard"] = build_pipeline(
        _pack(tmp_path), _Capture(),
        EgressPolicy(alias="a", terms=["X"], preview=lambda prompt: False))[1].gen


@when("the same client content is sent twice with different instructions then new content is sent")
def _three(ctx):
    g = ctx["guard"]
    g.generate(GenRequest(task="research", instructions="find pains", grounding={"intake:1": "X slow"}))
    g.generate(GenRequest(task="solution", instructions="DIFFERENT", grounding={"intake:1": "X slow"}))
    g.generate(GenRequest(task="research", instructions="i", grounding={"note:1": "X new content"}))


@then("the operator is asked once for the repeat and again for the new content")
def _deduped(ctx):
    assert len(ctx["shown"]) == 2


@then("a rejected preview raises an egress block")
def _reject_raises(ctx):
    with pytest.raises(EgressError):
        ctx["reject_guard"].generate(GenRequest(task="research", instructions="i",
                                                 grounding={"intake:1": "X slow"}))


@then("a missing preview also blocks the egress")
def _missing_preview_blocks(ctx, tmp_path):
    # no preview callback + no cleartext -> a distinct payload can't be operator-approved -> blocks
    # (doc Cap B sc3; production already covers this in test_egress.py's missing-preview unit tests, F8)
    with pytest.raises(EgressError):
        guard = build_pipeline(_pack(tmp_path), _Capture(),
                               EgressPolicy(alias="a", terms=["X"]))[1].gen
        guard.generate(GenRequest(task="research", instructions="i",
                                  grounding={"intake:1": "X slow"}))


# ----- Scenario 4 -----
@given("a pipeline built with an egress policy whose operator rejects the preview")
def _reject_pipeline(ctx, tmp_path):
    pol = EgressPolicy(alias="a", terms=["X"], preview=lambda prompt: False)
    ctx["stages"] = build_pipeline(_pack(tmp_path, transcript="X slow onboarding"), _Capture(), pol)
    ctx["bundle"] = Bundle(str(tmp_path / "b"))


@when("the runner walks the pipeline and the first generating stage hits the guard")
def _walk(ctx):
    ctx["out"] = Runner(ctx["bundle"], AutoApproveGate()).run(ctx["stages"])


@then("the run status is blocked and nothing is sent to the model")
def _blocked(ctx):
    assert ctx["out"]["status"] == "blocked" and ctx["out"]["blocked_at"] == "research"
