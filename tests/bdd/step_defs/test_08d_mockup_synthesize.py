import json

import pytest
from pytest_bdd import given, scenarios, then, when

from engine.bundle import Bundle
from engine.generator import FakeGenerator, GenResult
from engine.purity import PurityError, check_purity
from engine.stage import StageBlocked
from engine.stages.mockup import MockupStage
from engine.stages.research import GenerationError
from engine.stages.synthesize import SynthesizeStage

scenarios("../features/08d-mockup-synthesize.feature")


@pytest.fixture
def ctx():
    return {}


def _brand_and_sol(bundle):
    bundle.write("brand.json", json.dumps(
        {"colors": [{"hex": "#0073cf", "role": "primary", "source": "pack"}]}))
    bundle.write("solutions.json", json.dumps({"solutions": [{"id": "sol1", "statement": "x"}]}))


# ----- Scenario 1 -----
@given("a set of grounded claim ids")
def _ids(ctx):
    ctx["ids"] = {"sol1", "p1"}


@when("the purity check runs against a model-authored prototype")
def _noopd(ctx):
    pass


@then("every cited id must resolve to a grounded claim")
def _resolves(ctx):
    assert check_purity('<h2 data-source="sol1">A</h2>', ctx["ids"]).ok
    assert not check_purity('<h2 data-source="GHOST">A</h2>', ctx["ids"]).ok


@then("visible content with no citations blocks unless tagged all-sample")
def _uncited(ctx):
    assert not check_purity("<h2>uncited</h2>", ctx["ids"]).ok
    assert check_purity("<h2>sample only</h2>", ctx["ids"]).ok


@then("a stated total must reconcile with the sum of its parts")
def _total(ctx):
    assert check_purity('<b data-source="sol1" data-total="3" data-parts="1,2">x</b>', ctx["ids"]).ok
    assert not check_purity('<b data-source="sol1" data-total="9" data-parts="1,2">x</b>', ctx["ids"]).ok


# ----- Scenario 2 -----
@given("a captured brand primary color and a generator that ignores the brand")
def _offbrand(ctx, tmp_path):
    b = Bundle(str(tmp_path))
    _brand_and_sol(b)
    ctx["bundle"] = b


@when("the mockup stage runs")
def _run_mockup(ctx):
    # Off-brand but PURE: the citation resolves (sol1 is grounded) so purity passes and ONLY
    # brand-fidelity fails — isolating the brand check (mirrors test_stage_mockup.py). Capture the
    # requests so we can prove the stage actually iterated rather than merely writing a file.
    reqs = []

    def responder(req):
        reqs.append(req)
        return GenResult(ok=True, text='<body><h2 data-source="sol1">x</h2></body>')

    ctx["reqs"] = reqs
    ctx["err"] = None
    try:
        MockupStage(FakeGenerator(responder), max_regen=1).run(ctx["bundle"])
    except PurityError as e:
        ctx["err"] = e


@then("a mockup that ignored the brand is regenerated")
def _regenerated(ctx):
    # Prove the iteration actually happened: max_regen(1) + 1 == 2 generate() calls, and the SECOND
    # request carried the regeneration feedback (mockup.py's var(--brand-primary) fix string).
    assert len(ctx["reqs"]) == 2
    assert "var(--brand-primary)" in (ctx["reqs"][1].note or "")
    assert ctx["bundle"].exists("surfaces/prototype.html")


@then("if it still fails purity or brand after the regeneration budget the stage raises a purity block")
def _raises(ctx):
    assert isinstance(ctx["err"], PurityError)


# ----- Scenario 3 -----
@given("a prototype that passed the deterministic purity checks")
def _clean(ctx, tmp_path):
    b = Bundle(str(tmp_path))
    _brand_and_sol(b)
    ctx["bundle"] = b


@when("a verifier runs one semantic sweep and flags an uncited claim")
def _sweep(ctx):
    good = FakeGenerator(lambda req: GenResult(
        ok=True, text='<body><h2 data-source="sol1" style="color:var(--brand-primary)">ok</h2></body>'))
    verifier = FakeGenerator(lambda req: GenResult(ok=True, data={"uncited": ["a hidden claim"]}))
    ctx["err"] = None
    try:
        MockupStage(good, verifier=verifier).run(ctx["bundle"])
    except PurityError as e:
        ctx["err"] = e


@then("the finding blocks the prototype as a policy block, not a crash")
def _policy_block(ctx):
    assert isinstance(ctx["err"], PurityError) and isinstance(ctx["err"], StageBlocked)


# ----- Scenario 4 -----
@given("a graded, audited bundle")
def _graded(ctx, tmp_path):
    b = Bundle(str(tmp_path / "b"))
    b.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\nslow\n")
    b.write("pains.json", json.dumps({"pains": [{"id": "p1", "statement": "slow"}]}))
    b.write("solutions.json", json.dumps({"solutions": [{"id": "sol1", "statement": "x"}]}))
    b.write("surfaces/prototype.html", "<body>ok</body>")
    ctx["bundle"] = b
    ctx["root"] = tmp_path


@when("synthesize runs")
def _run_synth(ctx):
    gen = FakeGenerator(lambda req: GenResult(ok=True, text="## " + req.task + "\ncopy\n"))
    SynthesizeStage(gen).run(ctx["bundle"])


@then("it fills the remaining docs with grounded copy and fails loudly if any is empty")
def _docs(ctx):
    for f in ("2_ENDSTATE_SPEC.md", "6_SEED_DATA.md", "8_SCOPED_PROPOSAL.md", "9_CONTINUITY_TRACKER.md"):
        assert (ctx["bundle"].read(f) or "").strip()
    empty_gen = FakeGenerator(lambda req: GenResult(ok=True, text="   "))
    with pytest.raises(GenerationError):  # an empty doc fails loudly
        SynthesizeStage(empty_gen).run(Bundle(str(ctx["root"] / "empty")))


@then("it writes a manifest listing only artifacts and prototype surfaces that exist on disk")
def _manifest(ctx):
    man = json.loads(ctx["bundle"].read(".edd-manifest.json"))
    assert man["schema"] == "edd-bundle-manifest/1"
    assert "surfaces/prototype.html" in man["prototypes"]
    assert man["artifacts"]["spec"]["present"] is True
