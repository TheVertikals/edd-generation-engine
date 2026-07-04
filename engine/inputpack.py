from pathlib import Path
from typing import Optional

from engine.frontmatter import parse_yaml


class InputPack:
    """A per-engagement directory of generic, normalized input files plus a manifest.

    The pack is a boundary contract: its producer matures over phases (a stub fixture,
    then a minimal transcript/notes adapter, then a sovereign capture-and-memory
    substrate) but the Engine only ever sees plain files and cannot tell the producers
    apart. That is what keeps the Engine agnostic.
    """

    def __init__(self, root: str):
        self.root = root

    def manifest(self) -> dict:
        return parse_yaml(self.read("inputpack.yaml") or "")

    def read(self, rel: str) -> Optional[str]:
        try:
            return (Path(self.root) / rel).read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None
