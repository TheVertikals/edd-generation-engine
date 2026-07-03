import json
from typing import Dict, Optional

from engine.bundle import Bundle
from engine.generator import Generator
from engine.grounding import GroundingError, audit
from engine.stage import Stage


class GroundingAuditStage(Stage):
    """The blocking final audit gate. Audits the accumulated claim-set before any finalizing
    stage runs. Persists a report; raises GroundingError (a block, not a crash) on failure.
    Blocks empty, ungrounded, and (by default) speculative content from being finalized."""
    name = "audit"

    def __init__(self, generator: Optional[Generator] = None,
                 block_speculative: bool = True, require_nonempty: bool = True):
        self.gen = generator
        self.block_speculative = block_speculative
        self.require_nonempty = require_nonempty

    def _corpus(self, bundle: Bundle) -> Dict[str, str]:
        doc = bundle.read("0_CUSTOMER_INTAKE.md") or ""
        facts, n = {}, 0
        for line in doc.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                n += 1
                facts["intake:%d" % n] = line
        raw = bundle.read("brand.json")
        if raw:
            for i, c in enumerate(json.loads(raw).get("colors", [])):
                facts["brand:%d" % i] = "brand %s %s" % (c.get("role", ""), c.get("hex", ""))
        return facts

    def _claims(self, bundle: Bundle):
        out = []
        for rel, key in (("pains.json", "pains"), ("solutions.json", "solutions"),
                         ("creative-direction.json", "claims")):
            raw = bundle.read(rel)
            if raw:
                out.extend(json.loads(raw).get(key, []))
        return out

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        claims = self._claims(bundle)
        grounding = self._corpus(bundle)
        report = audit(claims, corpus_ids=grounding.keys(), generator=self.gen, grounding=grounding,
                       block_speculative=self.block_speculative, require_nonempty=self.require_nonempty)
        bundle.write("audit-report.json", json.dumps(
            {"ok": report.ok,
             "findings": [{"claim_id": f.claim_id, "problem": f.problem, "severity": f.severity}
                          for f in report.findings]}, indent=2))
        if not report.ok:
            raise GroundingError("grounding audit blocked the pipeline: %d finding(s)"
                                 % len([f for f in report.findings if f.severity == "hard"]))
