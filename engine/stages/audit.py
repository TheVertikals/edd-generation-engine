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
        return facts

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        claims = json.loads(bundle.read("pains.json") or '{"pains": []}').get("pains", [])
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
