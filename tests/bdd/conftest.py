import pytest


def pytest_bdd_apply_tag(tag, function):
    """Wire the `@xfail` Gherkin tag to a real strict xfail mark.

    pytest-bdd does not turn an `@xfail` feature/scenario tag into `pytest.mark.xfail` on its own,
    so the cross-repo drift gate's xfail-parity guarantee (a fail-by-design scenario is never
    silently green) would be cosmetic on the runnable side without this hook. `strict=True` so an
    xpass — a scenario that was meant to fail but passed — fails the suite instead of quietly
    turning green. Future-proofs the 09/10 features that carry @xfail-flagged scenarios.

    Returning True consumes the tag; any other tag is deferred (None) to pytest-bdd's default.
    """
    if tag == "xfail":
        pytest.mark.xfail(strict=True, reason="scenario tagged @xfail in its .feature")(function)
        return True
    return None
