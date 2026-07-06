from pytest_bdd import given, scenarios

scenarios("../features/_xfail_smoke.feature")


@given("a step that always fails")
def _always_fails():
    # The @xfail tag (wired by tests/bdd/conftest.py -> pytest.mark.xfail(strict=True)) turns this
    # deliberate failure into an EXPECTED failure. If the hook were not wired the scenario would be
    # a hard failure and the suite would go red, so a green suite proves the tag reached pytest.
    assert False, "deliberate: proves @xfail is wired to a strict xfail mark"
