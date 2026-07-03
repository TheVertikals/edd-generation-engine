from typing import Optional

from engine.bundle import Bundle
from engine.stage import GateSpec, Stage


class SeedStage(Stage):
    name = "seed"

    def run(self, bundle: Bundle) -> None:
        src = bundle.read("intake/source.txt") or ""
        bundle.write("seed.md", "# seed\n\n" + src)


class TransformStage(Stage):
    name = "transform"

    def run(self, bundle: Bundle) -> None:
        seed = bundle.read("seed.md") or ""
        bundle.write("result.md", "# result\n\n" + seed.upper())

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="result ok?", preview="result.md")
