import os
from pathlib import Path
from typing import Optional


class Bundle:
    """A file-backed working directory. Stages read/write artifacts here; this is the
    ONLY channel between stages. Writes are atomic (temp + os.replace). Paths are
    confined to the bundle root — absolute paths and '..' escapes are rejected, so a
    stage cannot write outside the boundary."""

    def __init__(self, root: str):
        self.root = root
        Path(root).mkdir(parents=True, exist_ok=True)

    def _abs(self, rel: str) -> Path:
        if os.path.isabs(rel) or ".." in Path(rel).parts:
            raise ValueError("unsafe bundle path: {}".format(rel))
        return Path(self.root) / rel

    def write(self, rel: str, text: str) -> None:
        p = self._abs(rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.parent / (p.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, p)

    def read(self, rel: str) -> Optional[str]:
        p = self._abs(rel)
        try:
            return p.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            return None

    def exists(self, rel: str) -> bool:
        return self._abs(rel).exists()
