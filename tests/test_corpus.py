import json
from engine.bundle import Bundle
from engine.corpus import build_corpus

def _bundle(tmp_path, **files):
    b = Bundle(str(tmp_path / "b"))
    for rel, txt in files.items():
        b.write(rel, txt)
    return b

def test_intake_and_brand(tmp_path):
    b = _bundle(tmp_path, **{"0_CUSTOMER_INTAKE.md": "# h\nonboarding is slow\nchurn is rising\n",
                             "brand.json": json.dumps({"colors": [{"role": "primary", "hex": "#0073cf"}]})})
    c = build_corpus(b)
    assert c["intake:1"] == "onboarding is slow" and c["intake:2"] == "churn is rising"
    assert c["brand:0"] == "brand primary #0073cf"
    assert not any(k.startswith("corpus:") for k in c)

def test_corpus_intelligence_folded_in(tmp_path):
    b = _bundle(tmp_path, **{"0_CUSTOMER_INTAKE.md": "x\n",
        "corpus-intelligence.json": json.dumps({"items": [
            {"id": "mkt-1", "statement": "week-2 activation is the churn driver", "sources": ["ext-1"]}]})})
    assert build_corpus(b)["corpus:mkt-1"] == "week-2 activation is the churn driver"

def test_malformed_corpus_file_is_tolerated(tmp_path):   # F1
    b = _bundle(tmp_path, **{"0_CUSTOMER_INTAKE.md": "x\n", "corpus-intelligence.json": "{not json"})
    c = build_corpus(b)                                   # no crash
    assert c == {"intake:1": "x"} and not any(k.startswith("corpus:") for k in c)

def test_duplicate_corpus_id_first_wins(tmp_path):       # F5
    b = _bundle(tmp_path, **{"corpus-intelligence.json": json.dumps({"items": [
        {"id": "d", "statement": "first"}, {"id": "d", "statement": "second"}]})})
    assert build_corpus(b)["corpus:d"] == "first"

def test_absent_inputs_empty(tmp_path):
    assert build_corpus(Bundle(str(tmp_path / "empty"))) == {}
