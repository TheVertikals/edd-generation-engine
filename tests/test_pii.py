# tests/test_pii.py
from engine.pii import residual_pii

def test_masks_email_phone_card_ssn():
    t = residual_pii("reach jane@realco.com or +1 (415) 555-2671; ssn 123-45-6789; card 4111 1111 1111 1111")
    assert "jane@realco.com" not in t and "<email>" in t
    assert "555-2671" not in t and "<phone>" in t
    assert "123-45-6789" not in t and "<ssn>" in t
    assert "4111 1111 1111 1111" not in t and "<card>" in t

def test_leaves_ordinary_text_and_short_numbers():
    assert residual_pii("we shipped 6 weeks late in Q3") == "we shipped 6 weeks late in Q3"

def test_is_honest_about_names():
    # a name is NOT pattern-shaped -> the sweep cannot mask it (documents the residual)
    assert "Acme Robotics" in residual_pii("the buyer is Acme Robotics")
