from engine.generator import FakeGenerator, GenResult
from engine.grounding import GroundingError, audit


def _c(cid, conf, sources, basis=None):
    return {"id": cid, "statement": "s", "confidence": conf, "sources": sources, "basis": basis or []}


def test_grounded_set_passes():
    claims = [_c("p1", "verified", ["s1"]), _c("p2", "inferred", [], basis=["p1"])]
    assert audit(claims, corpus_ids={"s1", "s2"}).ok


def test_fact_with_unresolvable_source_is_hard():
    r = audit([_c("p1", "verified", ["GHOST"])], corpus_ids={"s1"})
    assert not r.ok and any(f.claim_id == "p1" and "source" in f.problem for f in r.findings)


def test_opinion_basis_must_resolve_to_a_fact():
    claims = [_c("p1", "inferred", [], basis=["p2"]), _c("p2", "inferred", [], basis=["p1"])]
    r = audit(claims, corpus_ids={"s1"})
    assert not r.ok and any("basis" in f.problem for f in r.findings)


def test_speculative_soft_by_default_hard_when_blocked():
    claims = [_c("p1", "speculative", [])]
    assert audit(claims, corpus_ids={"s1"}).ok
    assert not audit(claims, corpus_ids={"s1"}, block_speculative=True).ok


def test_require_nonempty_blocks_empty():
    assert audit([], corpus_ids={"s1"}).ok
    assert not audit([], corpus_ids={"s1"}, require_nonempty=True).ok


def test_adversarial_verifier_flags_claim():
    gen = FakeGenerator(lambda req: GenResult(ok=True, data={"unsupported": ["p1"]}))
    r = audit([_c("p1", "verified", ["s1"])], corpus_ids={"s1"}, generator=gen, grounding={"s1": "x"})
    assert not r.ok and any("adversarial" in f.problem for f in r.findings)


def test_grounding_error_is_a_block():
    from engine.stage import StageBlocked
    assert issubclass(GroundingError, StageBlocked)
