from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from engine.artifacts import FACT_TIERS, OPINION_TIERS, validate_claims
from engine.generator import GenRequest, Generator
from engine.stage import StageBlocked


class GroundingError(StageBlocked):
    """Raised to BLOCK the pipeline when generated content fails the grounding audit."""


@dataclass
class AuditFinding:
    claim_id: str
    problem: str
    severity: str = "hard"


@dataclass
class AuditReport:
    ok: bool
    findings: List[AuditFinding] = field(default_factory=list)


def _grounded(cid, by_id, corpus, memo, stack):
    """A claim is grounded if it is a fact with resolvable sources, or an inferred claim whose
    basis all resolve — transitively — to grounded claims. Cycles (no fact floor) are not grounded."""
    if cid in memo:
        return memo[cid]
    if cid in stack:  # cycle
        return False
    c = by_id.get(cid)
    if c is None:
        return False
    conf = c.get("confidence")
    if conf in FACT_TIERS:
        ok = bool(c.get("sources")) and all(s in corpus for s in c["sources"])
    elif conf in OPINION_TIERS:
        basis = c.get("basis") or []
        stack.add(cid)
        ok = bool(basis) and all(_grounded(b, by_id, corpus, memo, stack) for b in basis)
        stack.discard(cid)
    else:  # speculative etc. are never "grounded"
        ok = False
    memo[cid] = ok
    return ok


def audit(claims: List[dict], corpus_ids: Iterable[str], generator: Optional[Generator] = None,
          grounding: Optional[dict] = None, block_speculative: bool = False,
          require_nonempty: bool = False) -> AuditReport:
    corpus = set(corpus_ids)
    by_id = {c.get("id"): c for c in claims}
    findings: List[AuditFinding] = []

    if require_nonempty and not claims:
        findings.append(AuditFinding("*", "no claims to finalize — generation produced nothing"))

    # duplicate ids across the union would let by_id silently shadow one claim with another
    id_list = [c.get("id") for c in claims if c.get("id")]
    for dup in sorted({i for i in id_list if id_list.count(i) > 1}):
        findings.append(AuditFinding(dup, "duplicate claim id across the audited set"))

    for cid, msg in validate_claims(claims):
        findings.append(AuditFinding(cid, msg))

    for c in claims:
        cid = c.get("id", "?")
        conf = c.get("confidence")
        if conf in FACT_TIERS:
            for s in c.get("sources", []):
                if s not in corpus:
                    findings.append(AuditFinding(cid, "source %r does not resolve to the corpus" % s))
        elif conf in OPINION_TIERS:
            # an opinion is grounded if its basis resolves — transitively — to a fact (no cycles)
            if not _grounded(cid, by_id, corpus, {}, set()):
                findings.append(AuditFinding(
                    cid, "opinion basis does not trace to a grounded fact (missing/cyclic/ungrounded)"))
        elif conf == "speculative":
            findings.append(AuditFinding(cid, "speculative claim present",
                                         severity="hard" if block_speculative else "soft"))

    if generator is not None:
        ids = sorted(str(i) for i in by_id if i)
        res = generator.generate(GenRequest(
            task="grounding-audit",
            instructions=('Given the GROUNDING FACTS and claim ids %s, return JSON '
                          '{"unsupported": [ids...]} listing every claim whose statement is not '
                          "supported by the facts or appears manufactured. Be strict." % ids),
            grounding=grounding or {}))
        if res.ok and isinstance(res.data, dict):
            for cid in res.data.get("unsupported", []):
                findings.append(AuditFinding(str(cid), "flagged by adversarial verifier as unsupported"))

    hard = [f for f in findings if f.severity == "hard"]
    return AuditReport(ok=(len(hard) == 0), findings=findings)
