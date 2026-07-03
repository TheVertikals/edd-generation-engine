from typing import List, Tuple

CONFIDENCE_TIERS = ("verified", "corroborated", "inferred", "speculative")
FACT_TIERS = ("verified", "corroborated")
OPINION_TIERS = ("inferred",)

PAINSET_SCHEMA = {
    "type": "object",
    "required": ["pains"],
    "properties": {
        "pains": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "statement", "kind", "confidence", "sources", "basis"],
                "properties": {
                    "id": {"type": "string"},
                    "statement": {"type": "string"},
                    "kind": {"enum": ["stated", "latent"]},
                    "confidence": {"enum": list(CONFIDENCE_TIERS)},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "basis": {"type": "array", "items": {"type": "string"}},
                },
            },
        }
    },
}


def validate_claims(claims: List[dict]) -> List[Tuple[str, str]]:
    """Structural check only, returned as (claim_id, message) pairs. Facts need non-empty
    sources; opinions need non-empty basis. Source/basis *resolution* is the audit's job."""
    issues: List[Tuple[str, str]] = []
    for i, c in enumerate(claims):
        cid = c.get("id") or "#%d" % i
        conf = c.get("confidence")
        if not c.get("id") or not c.get("statement"):
            issues.append((cid, "missing id or statement"))
        if conf not in CONFIDENCE_TIERS:
            issues.append((cid, "unknown confidence %r" % conf))
            continue
        if conf in FACT_TIERS and not c.get("sources"):
            issues.append((cid, "fact (%s) has no source" % conf))
        if conf in OPINION_TIERS and not c.get("basis"):
            issues.append((cid, "opinion (%s) has no basis" % conf))
    return issues


SOLUTIONSET_SCHEMA = {
    "type": "object", "required": ["solutions"],
    "properties": {"solutions": {"type": "array", "items": {"type": "object",
        "required": ["id", "pain_id", "approach", "confidence", "sources", "basis"],
        "properties": {"id": {"type": "string"}, "pain_id": {"type": "string"},
            "approach": {"type": "string"}, "confidence": {"enum": list(CONFIDENCE_TIERS)},
            "sources": {"type": "array", "items": {"type": "string"}},
            "basis": {"type": "array", "items": {"type": "string"}}}}}},
}
CREATIVE_DIRECTION_SCHEMA = {
    "type": "object", "required": ["claims"],
    "properties": {"claims": {"type": "array", "items": {"type": "object",
        "required": ["id", "statement", "confidence", "sources", "basis"],
        "properties": {"id": {"type": "string"}, "statement": {"type": "string"},
            "confidence": {"enum": list(CONFIDENCE_TIERS)},
            "sources": {"type": "array", "items": {"type": "string"}},
            "basis": {"type": "array", "items": {"type": "string"}}}}}},
}
