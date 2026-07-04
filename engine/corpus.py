"""The single grounding corpus every stage grounds and audits against, so a fact added for one
consumer resolves for the other. Intake lines + brand facts + an optional generic
`corpus-intelligence.json`. The bundle grows across stages (brand.json arrives after research), so
the guarantee is monotone growth, not one fixed set. Deterministic; absent/malformed inputs
contribute nothing. Stdlib-only."""
import json
import sys
from typing import Dict

from engine.bundle import Bundle


def build_corpus(bundle: Bundle) -> Dict[str, str]:
    facts: Dict[str, str] = {}
    doc = bundle.read("0_CUSTOMER_INTAKE.md") or ""
    n = 0
    for line in doc.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            n += 1
            facts["intake:%d" % n] = line
    raw = bundle.read("brand.json")
    if raw:
        try:
            for i, c in enumerate(json.loads(raw).get("colors", []) or []):
                facts["brand:%d" % i] = "brand %s %s" % (c.get("role", ""), c.get("hex", ""))
        except (ValueError, AttributeError, TypeError):
            pass
    raw = bundle.read("corpus-intelligence.json")
    if raw:
        try:
            for item in json.loads(raw).get("items", []) or []:
                cid, stmt = item.get("id"), item.get("statement")
                key = "corpus:%s" % cid
                if cid and stmt and key not in facts:      # F5: first-wins, no silent shadow
                    facts[key] = stmt
        except (ValueError, AttributeError, TypeError) as e:
            print("WARN: corpus-intelligence.json ignored (%s)" % type(e).__name__, file=sys.stderr)
    return facts
