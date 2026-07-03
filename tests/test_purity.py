from engine.generator import FakeGenerator, GenResult
from engine.purity import PurityError, check_purity
from engine.stage import StageBlocked


def test_all_cited_sources_resolve_passes():
    html = '<h2 data-source="s1">x</h2><p data-source="s2">y</p>'
    assert check_purity(html, {"s1", "s2"}).ok


def test_orphan_citation_fails():
    r = check_purity('<h2 data-source="GHOST">x</h2>', {"s1"})
    assert not r.ok and any("GHOST" in f.problem for f in r.findings)


def test_reconciliation_mismatch_fails():
    r = check_purity('<div data-total="100" data-parts="34,41,12">x</div>', {"s1"})
    assert not r.ok and any("reconcile" in f.problem.lower() for f in r.findings)


def test_all_sample_content_is_allowed():
    assert check_purity('<p>Projection <span class="tag">SAMPLE</span></p>', set()).ok


def test_uncited_untagged_prose_fails():
    r = check_purity('<p>40% faster</p>', {"s1"})
    assert not r.ok


def test_adversarial_sweep_flags_uncited():
    g = FakeGenerator(lambda r: GenResult(ok=True, data={"uncited": ["40% faster"]}))
    r = check_purity('<p data-source="s1">grounded</p>', {"s1"}, generator=g)
    assert not r.ok and any("uncited" in f.problem for f in r.findings)


def test_purity_error_is_a_block():
    assert issubclass(PurityError, StageBlocked)
