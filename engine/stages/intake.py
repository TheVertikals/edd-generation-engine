import json
from typing import Optional

from engine.adapter import pack_to_bundle
from engine.bundle import Bundle
from engine.inputpack import InputPack
from engine.stage import GateSpec, Stage


class IntakeStage(Stage):
    """Stage 1 — deterministic. Adapts the input pack into the bundle: a customer intake doc
    plus the persisted beacon id for downstream provenance. No generation, no egress.
    Pack sources[] are read structured and persisted as a list; empty beacon_id fails loudly."""
    name = "intake"

    def __init__(self, pack: InputPack):
        self.pack = pack

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        manifest = pack_to_bundle(self.pack, bundle)  # writes intake/source.txt
        beacon = str(manifest.get("beacon_id", "") or "").strip()
        if not beacon:
            raise ValueError("input pack manifest is missing a non-empty beacon_id "
                             "(the dossier join key)")
        sources = manifest.get("sources", [])
        if not isinstance(sources, list):
            sources = [sources] if sources else []
        transcript = bundle.read("intake/source.txt") or ""
        bundle.write("0_CUSTOMER_INTAKE.md", "# Customer Intake\n\n" + transcript + "\n")
        bundle.write("intake/manifest.json", json.dumps(
            {"beacon_id": beacon, "sources": sources}, indent=2))

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="captured right?", preview="0_CUSTOMER_INTAKE.md")
