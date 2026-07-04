import json
from typing import Dict, Optional

from engine.bundle import Bundle
from engine.corpus import build_corpus
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
        return build_corpus(bundle)

    def _claims(self, bundle: Bundle):
        out = []
        for rel, key in (("pains.json", "pains"), ("solutions.json", "solutions"),
                         ("creative-direction.json", "claims")):
            raw = bundle.read(rel)
            if raw:
                out.extend(json.loads(raw).get(key, []))
        return out

    def _waivers(self, bundle: Bundle, claims):
        """Resolve a fail-closed, CONTENT-BOUND waiver file. A waiver applies only when its {id,
        statement} matches a current claim exactly — so a relabel or a regenerated/swapped statement
        cannot inherit a prior approval. Any parse/shape error -> zero waivers (fail-closed)."""
        applied, rejected = set(), []
        raw = bundle.read("waivers.json")
        if not raw:
            return applied, rejected
        try:
            data = json.loads(raw)
            if not isinstance(data, dict):
                return applied, [{"why": "waivers.json is not an object"}]
            approver = data.get("approved_by")
            if not (isinstance(approver, str) and approver.strip()):
                return applied, [{"why": "waiver missing a non-empty approved_by"}]
            stmt_by_id = {c.get("id"): c.get("statement") for c in claims}
            for entry in data.get("approved_speculative", []) or []:
                if not isinstance(entry, dict):
                    rejected.append({"entry": entry, "why": "malformed entry"})
                    continue
                cid, stmt = entry.get("id"), entry.get("statement")
                if cid in stmt_by_id and stmt_by_id[cid] == stmt:
                    applied.add(cid)                              # content-bound match
                else:
                    rejected.append({"id": cid, "why": "unknown id or statement mismatch"})
        except (ValueError, TypeError, AttributeError):
            return set(), [{"why": "malformed waivers.json"}]
        return applied, rejected

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        claims = self._claims(bundle)
        grounding = self._corpus(bundle)
        waived, rejected = self._waivers(bundle, claims)
        report = audit(claims, corpus_ids=grounding.keys(), generator=self.gen, grounding=grounding,
                       block_speculative=self.block_speculative, require_nonempty=self.require_nonempty,
                       waivers=waived)
        bundle.write("audit-report.json", json.dumps(
            {"ok": report.ok,
             "waived": sorted(waived),                # ids ACTUALLY downgraded (content-matched)
             "rejected_waivers": rejected,            # audit trail for entries that did not apply
             "findings": [{"claim_id": f.claim_id, "problem": f.problem, "severity": f.severity}
                          for f in report.findings]}, indent=2))
        if not report.ok:
            raise GroundingError("grounding audit blocked the pipeline: %d finding(s)"
                                 % len([f for f in report.findings if f.severity == "hard"]))
