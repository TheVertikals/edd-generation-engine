"""The engine repo's one canonical production assembly of the agnostic six-stage generation pipeline.

The ordered stage list used to live only inside tests/test_e2e_pipeline.py; it lives here so the
engine's Runner and the engine BDD suite walk the SAME order from a single definition. This module
is authoritative for the ENGINE repo only: downstream composition roots in other repos (e.g. a
render tier) assemble their OWN pipelines that embed these six engine stages in this relative order
but may interleave tier-specific stages and wire egress differently; a separate alignment gate keeps
a downstream root's engine-stage order equal to STAGE_ORDER. Agnostic: no brand/client/proprietary
references (tests/test_agnosticism.py)."""
from typing import List, Optional, Tuple

from engine.egress import EgressGuard, EgressPolicy
from engine.generator import Generator
from engine.inputpack import InputPack
from engine.stage import Stage
from engine.stages.audit import GroundingAuditStage
from engine.stages.intake import IntakeStage
from engine.stages.mockup import MockupStage
from engine.stages.research import ResearchStage
from engine.stages.solution import SolutionStage
from engine.stages.synthesize import SynthesizeStage

STAGE_ORDER: Tuple[str, ...] = (
    "intake", "research", "solution", "audit", "mockup", "synthesize")


def build_pipeline(pack: InputPack, generator: Generator, egress: EgressPolicy,
                   *, verifier: Optional[Generator] = None) -> List[Stage]:
    """Return the ordered production stages the Runner walks, gating between each.

    Cap B — one guarded egress throat: every generating stage receives ONE shared EgressGuard
    wrapping `generator` under `egress`; dedup state lives on the policy, so approvals are shared
    across stages. Intake is deterministic (no egress) and is left unwrapped. `verifier` (default:
    the same guarded generator) runs the mockup's one adversarial sweep, also through the guard."""
    guard = EgressGuard(generator, egress)
    guarded_verifier = guard if verifier is None else EgressGuard(verifier, egress)
    return [
        IntakeStage(pack),
        ResearchStage(guard),
        SolutionStage(guard, pack),
        GroundingAuditStage(generator=guard),
        MockupStage(guard, verifier=guarded_verifier),
        SynthesizeStage(guard),
    ]
