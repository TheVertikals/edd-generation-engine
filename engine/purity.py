import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

from engine.generator import GenRequest, Generator
from engine.prompts import PURITY_SWEEP_INSTR
from engine.stage import StageBlocked

_SRC = re.compile(r'data-source="([^"]+)"')
_TOTAL = re.compile(r'data-total="(\d+)"')
_TAGS = ("sample", "preview")


class PurityError(StageBlocked):
    """Raised to block a mockup that carries content not traceable to grounded claims."""


@dataclass
class PurityFinding:
    problem: str


@dataclass
class PurityReport:
    ok: bool
    findings: List[PurityFinding] = field(default_factory=list)


def _parts_for(html: str, total: str) -> Optional[str]:
    m = (re.search(r'data-total="%s"[^>]*data-parts="([0-9,\s]+)"' % total, html)
         or re.search(r'data-parts="([0-9,\s]+)"[^>]*data-total="%s"' % total, html))
    return m.group(1) if m else None


def check_purity(html: str, grounded_ids: Iterable[str], generator: Optional[Generator] = None) -> PurityReport:
    ids = set(grounded_ids)
    lower = html.lower()
    findings: List[PurityFinding] = []

    cited = set(_SRC.findall(html))
    for c in sorted(cited):
        if c not in ids:
            findings.append(PurityFinding("citation %r does not resolve to a grounded claim" % c))
    # visible content with no citations at all — unless it is explicitly all-SAMPLE
    if html.strip() and not cited and not any(t in lower for t in _TAGS):
        findings.append(PurityFinding("mockup carries no data-source citations at all"))

    for total in _TOTAL.findall(html):
        parts = _parts_for(html, total)
        if parts is not None:
            s = sum(int(p) for p in parts.split(",") if p.strip())
            if s != int(total):
                findings.append(PurityFinding("total %s does not reconcile with parts (sum %d)" % (total, s)))

    if generator is not None:
        res = generator.generate(GenRequest(task="purity-sweep", instructions=PURITY_SWEEP_INSTR,
                                            grounding={"html": html}))
        if res.ok and isinstance(res.data, dict):
            for q in res.data.get("uncited", []):
                findings.append(PurityFinding("uncited claim: %s" % q))

    return PurityReport(ok=(len(findings) == 0), findings=findings)
