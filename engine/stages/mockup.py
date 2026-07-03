import json
from typing import Optional

from engine.bundle import Bundle
from engine.fonts import font_faces
from engine.generator import GenRequest, Generator
from engine.prompts import DESIGN_BRIEF
from engine.purity import PurityError, PurityFinding, check_purity
from engine.stage import GateSpec, Stage


class MockupStage(Stage):
    """Stage 3b — model-authored hi-fi HTML. Runs AFTER the grounding audit, so the claim ids
    are all grounded. Deterministically injects the face kit + brand tokens, purity-checks the
    citations, verifies the model actually used the brand, and runs one adversarial sweep."""
    name = "mockup"

    def __init__(self, generator: Generator, verifier: Optional[Generator] = None, max_regen: int = 2):
        self.gen, self.verifier, self.max_regen = generator, verifier, max_regen

    def _grounded_ids(self, bundle):
        ids = set()
        for rel, key in (("solutions.json", "solutions"), ("pains.json", "pains"),
                         ("creative-direction.json", "claims")):
            raw = bundle.read(rel)
            if raw:
                ids |= {c["id"] for c in json.loads(raw).get(key, []) if c.get("id")}
        return ids

    def _brand(self, bundle):
        raw = bundle.read("brand.json")
        cols = json.loads(raw).get("colors", []) if raw else []
        return (cols[0]["hex"].lower() if cols else None), cols

    def _inject(self, html, cols):  # doctype-safe: never before <!doctype>
        toks = "".join("--brand-%d:%s;" % (i, c["hex"]) for i, c in enumerate(cols))
        if cols:
            toks = "--brand-primary:%s;%s" % (cols[0]["hex"], toks)
        style = "<style>%s\n:root{%s}</style>" % (font_faces(), toks)
        if "</head>" in html:
            return html.replace("</head>", style + "</head>", 1)
        if "<body>" in html:
            return html.replace("<body>", "<body>" + style, 1)
        return html + style

    def _context(self, bundle):
        g = {}
        for rel in ("solutions.json", "creative-direction.json", "brand.json"):
            raw = bundle.read(rel)
            if raw:
                g[rel] = raw
        return g

    def run(self, bundle: Bundle, note: Optional[str] = None) -> None:
        ids, (primary, cols) = self._grounded_ids(bundle), self._brand(bundle)
        current, html = note, ""
        for _ in range(self.max_regen + 1):
            res = self.gen.generate(GenRequest(task="mockup", instructions=DESIGN_BRIEF,
                                               grounding=self._context(bundle), note=current))
            if not res.ok:
                raise RuntimeError(res.error or "mockup generation failed")
            raw = res.text or ""
            html = self._inject(raw, cols)                 # provide the tokens
            report = check_purity(html, ids)               # deterministic each iteration
            # brand FIDELITY: inspect the MODEL's own output, not our injected definition
            brand_used = primary is None or "var(--brand-primary)" in raw or primary in raw.lower()
            extra = [] if brand_used else [PurityFinding("brand primary not used (var(--brand-primary))")]
            if report.ok and not extra:
                break
            current = ("Fix: " + "; ".join(f.problem for f in report.findings + extra)
                       + ". Cite every claim with a resolving data-source; use var(--brand-primary).")
        else:
            bundle.write("surfaces/prototype.html", html)
            raise PurityError("mockup failed purity/brand after regeneration")
        if self.verifier is not None:  # ONE adversarial semantic sweep on the accepted candidate
            sweep = check_purity(html, ids, generator=self.verifier)
            if not sweep.ok:
                bundle.write("surfaces/prototype.html", html)
                raise PurityError("mockup failed adversarial sweep: %d finding(s)" % len(sweep.findings))
        bundle.write("surfaces/prototype.html", html)

    def gate(self, bundle: Bundle) -> Optional[GateSpec]:
        return GateSpec(question="approve the prototype?", preview="surfaces/prototype.html")
