import pathlib
import re


def test_engine_has_zero_proprietary_references():
    """The Engine tier must stay agnostic: no reference to any proprietary layer or
    sovereign substrate anywhere under engine/."""
    engine_dir = pathlib.Path(__file__).resolve().parent.parent / "engine"
    pat = re.compile(r"vantage|cortex", re.IGNORECASE)
    hits = []
    for p in sorted(engine_dir.rglob("*.py")):
        for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if pat.search(line):
                hits.append("{}:{}: {}".format(p.name, i, line.strip()))
    assert hits == [], "Engine must stay agnostic (no proprietary refs):\n" + "\n".join(hits)
