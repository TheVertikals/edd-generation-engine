from engine.redact import Redactor


def test_redacts_names_and_org_to_alias():
    r = Redactor("ACME-ALIAS", ["Northwind Logistics", "Northwind", "Jane Okafor"])
    out = r.redact("Jane Okafor at Northwind Logistics (part of Northwind) approved it.")
    assert "Northwind" not in out
    assert "Jane Okafor" not in out
    assert out.count("ACME-ALIAS") == 3


def test_case_insensitive_but_no_partial_word_clobber():
    r = Redactor("X", ["Ace"])
    out = r.redact("ACE and ace but not Peace or Aceton")
    assert out == "X and X but not Peace or Aceton"


def test_empty_terms_is_identity():
    assert Redactor("X", []).redact("nothing to do") == "nothing to do"
