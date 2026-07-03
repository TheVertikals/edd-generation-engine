import json
from typing import Dict, Optional

from engine.artifacts import PAINSET_SCHEMA
from engine.bundle import Bundle
from engine.generator import GenRequest, Generator
from engine.grounding import audit
from engine.stage import GateSpec, Stage

_INSTRUCTIONS = (
    "From the GROUNDING FACTS (the customer intake), identify the customer's pain points — "
    "both stated and latent. Return a JSON object matching the schema: a `pains` array where "
    "each pain has id, statement, kind (stated|latent), confidence, sources, basis. Cite intake "
    "source ids in `sources` for stated pains; latent pains are `inferred` and must list their "
    "`basis` (the stated-pain ids they reason from)."
)


class GenerationError(Exception):
    """The generator failed or returned unusable output — a crash, not a grounding block."""


class ResearchStage(Stage):
    name = "research"

    def __init__(self, generator: Generator, max_regen: int = 2):
        self.gen = generator
        self.max_regen = max_regen

    def _grounding(self, bundle: Bundle) -> Dict[str, str]:
        doc = bundle.read("0_CUSTOMER_INTAKE.md") or ""
        facts, n = {}, 0
        for line in doc.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                n += 1
                facts["intake:%d" % n] = line
        return facts

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        grounding = self._grounding(bundle)
        current_note = note
        data = None
        for _ in range(self.max_regen + 1):
            res = self.gen.generate(GenRequest(task="research", instructions=_INSTRUCTIONS,
                                               grounding=grounding, schema=PAINSET_SCHEMA,
                                               note=current_note))
            if not res.ok or not isinstance(res.data, dict) or "pains" not in res.data:
                raise GenerationError(res.error or "research returned unusable output")
            data = res.data
            report = audit(data.get("pains", []), corpus_ids=grounding.keys())
            if report.ok:
                break
            current_note = ("Previous output failed grounding: "
                            + "; ".join("%s: %s" % (f.claim_id, f.problem) for f in report.findings)
                            + ". Regenerate so every claim is grounded in the facts.")
        bundle.write("pains.json", json.dumps(data, indent=2))

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="right pains?", preview="pains.json")
