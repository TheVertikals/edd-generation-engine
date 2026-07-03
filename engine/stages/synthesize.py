from typing import Optional

from engine.bundle import Bundle
from engine.generator import GenRequest, Generator
from engine.manifest import write_manifest
from engine.scaffold import InternalScaffolder, Scaffolder
from engine.stage import GateSpec, Stage
from engine.stages.research import GenerationError

_DOCS = {
    "2_ENDSTATE_SPEC.md": "Draft the endstate spec: the target state per grounded pain + solution.",
    "6_SEED_DATA.md": "Draft realistic seed data notes grounded in the pains (label any sample data).",
    "8_SCOPED_PROPOSAL.md": "Draft the scoped proposal: the plays and path to proof, grounded.",
    "9_CONTINUITY_TRACKER.md": "Draft the continuity tracker seed (open questions grounded in pains).",
}


class SynthesizeStage(Stage):
    """Stage 5 — scaffold the bundle, fill the four docs with grounded copy, write the manifest."""
    name = "synthesize"

    def __init__(self, generator: Generator, scaffolder: Optional[Scaffolder] = None):
        self.gen = generator
        self.scaffolder = scaffolder or InternalScaffolder()

    def _grounding(self, bundle: Bundle) -> dict:
        g = {}
        for rel in ("pains.json", "solutions.json"):
            raw = bundle.read(rel)
            if raw:
                g[rel] = raw
        return g

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        self.scaffolder.scaffold(bundle, {})
        grounding = self._grounding(bundle)
        for name, instr in _DOCS.items():
            # markdown docs are prose: no schema, read res.text (NOT res.data)
            res = self.gen.generate(GenRequest(task="synthesize:%s" % name, instructions=instr,
                                               grounding=grounding, note=note))
            if not res.ok or not (res.text or "").strip():
                raise GenerationError(res.error or "synthesize produced no copy for %s" % name)
            bundle.write(name, res.text)
        write_manifest(bundle, {
            "intake": "0_CUSTOMER_INTAKE.md",
            "spec": "2_ENDSTATE_SPEC.md",
            "seed": "6_SEED_DATA.md",
            "scoped_proposal": "8_SCOPED_PROPOSAL.md",
            "tracker": "9_CONTINUITY_TRACKER.md",
        }, prototypes=["surfaces/prototype.html"])

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="bundle ready?", preview="8_SCOPED_PROPOSAL.md")
