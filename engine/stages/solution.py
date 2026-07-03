import json
from typing import Optional

from engine.artifacts import CREATIVE_DIRECTION_SCHEMA, SOLUTIONSET_SCHEMA
from engine.brand import capture_brand
from engine.bundle import Bundle
from engine.generator import GenRequest, Generator
from engine.prompts import CREATIVE_DIRECTION_INSTR, SOLUTION_INSTR
from engine.stage import GateSpec, Stage


class SolutionStage(Stage):
    """Stage 3a — capture brand, then generate grounded creative direction + solutions. The ids
    handed to the model (pain ids, brand:i) ARE the ids the audit resolves. Grounding is enforced
    at the downstream audit gate (single honest call here)."""
    name = "solution"

    def __init__(self, generator: Generator, pack=None):
        self.gen, self.pack = generator, pack

    def _grounding(self, bundle: Bundle) -> dict:
        g = {}
        for p in json.loads(bundle.read("pains.json") or '{"pains":[]}').get("pains", []):
            g[p["id"]] = p.get("statement", "")               # raw pain id -> cited in basis
        raw = bundle.read("brand.json")
        if raw:
            for i, c in enumerate(json.loads(raw).get("colors", [])):
                g["brand:%d" % i] = "brand %s %s" % (c["role"], c["hex"])  # brand:i -> cited in sources
        return g

    def _gen(self, task, instr, schema, grounding, note):
        res = self.gen.generate(GenRequest(task=task, instructions=instr,
                                            grounding=grounding, schema=schema, note=note))
        if not res.ok or not isinstance(res.data, dict):
            raise RuntimeError(res.error or "%s returned unusable output" % task)
        return res.data

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        if self.pack is not None:
            bundle.write("brand.json", json.dumps(capture_brand(self.pack), indent=2))
        g = self._grounding(bundle)
        bundle.write("creative-direction.json",
                     json.dumps(self._gen("creative-direction", CREATIVE_DIRECTION_INSTR,
                                          CREATIVE_DIRECTION_SCHEMA, g, note), indent=2))
        sols = self._gen("solution", SOLUTION_INSTR, SOLUTIONSET_SCHEMA, g, note)
        for s in sols.get("solutions", []):
            s.setdefault("statement", s.get("approach", ""))   # solutions carry a statement to validate
        bundle.write("solutions.json", json.dumps(sols, indent=2))

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="right solutions?", preview="solutions.json")
