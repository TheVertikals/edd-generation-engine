from engine.bundle import Bundle

_SECTIONS = {
    "2_ENDSTATE_SPEC.md": "# 2 · Endstate Spec\n",
    "6_SEED_DATA.md": "# 6 · Seed Data\n",
    "8_SCOPED_PROPOSAL.md": "# 8 · Scoped Proposal\n",
    "9_CONTINUITY_TRACKER.md": "# 9 · Continuity Tracker\n",
}


class Scaffolder:
    def scaffold(self, bundle: Bundle, ctx: dict) -> None:
        raise NotImplementedError


class InternalScaffolder(Scaffolder):
    """Writes the four bundle-doc stubs only when absent — never clobbers existing content."""
    def scaffold(self, bundle: Bundle, ctx: dict) -> None:
        for name, stub in _SECTIONS.items():
            if not bundle.exists(name):
                bundle.write(name, stub)


class EddInitScaffolder(Scaffolder):
    """The true-reuse path (edd-init subprocess) — deferred; use InternalScaffolder for now."""
    def __init__(self, run=None):
        self._run = run

    def scaffold(self, bundle: Bundle, ctx: dict) -> None:
        raise NotImplementedError("edd-init reuse deferred (Plan 3+); use InternalScaffolder")
