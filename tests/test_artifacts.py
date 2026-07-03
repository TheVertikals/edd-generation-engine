from engine.artifacts import PAINSET_SCHEMA, validate_claims


def _fact(**kw):
    base = {"id": "p1", "statement": "s", "confidence": "verified", "sources": ["s1"], "basis": []}
    base.update(kw)
    return base


def test_valid_fact_and_opinion_pass():
    claims = [_fact(), _fact(id="p2", confidence="inferred", sources=[], basis=["p1"])]
    assert validate_claims(claims) == []


def test_fact_without_source_fails():
    issues = validate_claims([_fact(sources=[])])
    assert issues and issues[0][0] == "p1" and "source" in issues[0][1]


def test_opinion_without_basis_fails():
    issues = validate_claims([_fact(id="p2", confidence="inferred", sources=[], basis=[])])
    assert any(cid == "p2" and "basis" in msg for cid, msg in issues)


def test_unknown_confidence_fails():
    issues = validate_claims([_fact(confidence="totally-sure")])
    assert any("confidence" in msg for _, msg in issues)


def test_speculative_with_no_sources_or_basis_is_structurally_valid():
    assert validate_claims([_fact(id="p3", confidence="speculative", sources=[], basis=[])]) == []


def test_schema_shape_is_declared():
    assert PAINSET_SCHEMA["type"] == "object" and "pains" in PAINSET_SCHEMA["properties"]
