import json
from typing import Optional

from engine.adapter import pack_to_bundle
from engine.bundle import Bundle
from engine.inputpack import InputPack
from engine.stage import GateSpec, Stage


class IntakeStage(Stage):
    """Stage 1 — deterministic. Adapts the input pack into the bundle: a customer intake doc
    plus the persisted beacon id for downstream provenance. No generation, no egress.
    (Pack capture sources[] are deferred to Plan 2b; persisted as [] here.)"""
    name = "intake"

    def __init__(self, pack: InputPack):
        self.pack = pack

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        manifest = pack_to_bundle(self.pack, bundle)  # writes intake/source.txt
        transcript = bundle.read("intake/source.txt") or ""
        bundle.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\n" + transcript + "\n")
        bundle.write("intake/manifest.json", json.dumps(
            {"beacon_id": manifest.get("beacon_id", ""), "sources": manifest.get("sources", [])},
            indent=2))

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="captured right?", preview="0_CUSTOMER_INTAKE.md")
