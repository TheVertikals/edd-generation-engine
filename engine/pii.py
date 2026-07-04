# engine/pii.py
"""A residual-PII sweep run on content BEFORE it leaves the boundary. Masks only PATTERN-SHAPED
PII — emails, phone numbers, card-like and SSN-like digit runs. It CANNOT catch names, company
names, or free-form addresses (not pattern-shaped); those are the operator preview's job. Order
matters: mask the most specific patterns first so a card run isn't partly eaten by the phone rule.
Stdlib-only, deterministic."""
import re

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_PHONE = re.compile(r"(?<![\w-])\+?\d(?:[\d\s().-]{7,})\d(?![\w-])")


def residual_pii(text: str) -> str:
    if not text:
        return text
    text = _EMAIL.sub("<email>", text)
    text = _SSN.sub("<ssn>", text)
    text = _CARD.sub("<card>", text)
    text = _PHONE.sub("<phone>", text)
    return text
