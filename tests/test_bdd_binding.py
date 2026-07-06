import re
import subprocess
import sys
from pathlib import Path

_BDD = Path(__file__).resolve().parent / "bdd"
_FEATURES = _BDD / "features"
_STEP_DEFS = _BDD / "step_defs"
_REPO = Path(__file__).resolve().parents[1]
# A collected Feature-08 scenario node id: tests/bdd/step_defs/test_08x_*.py::test_...
_NODE = re.compile(r"^tests/bdd/step_defs/test_08[a-e]_[^:]*::test_")


def _declared_08_scenarios() -> int:
    n = 0
    for feature in sorted(_FEATURES.glob("08*.feature")):
        for line in feature.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("Scenario:"):
                n += 1
    return n


def test_every_08_feature_scenario_is_bound_and_collected():
    """Bound-ness guard. The name-level drift gate only checks that Scenario NAMES exist; an
    08*.feature that no step module binds via scenarios() would satisfy that gate yet never
    execute (silently green). Assert the number of Scenario: lines across 08*.feature equals the
    number of Feature-08 scenario items pytest-bdd actually COLLECTS."""
    declared = _declared_08_scenarios()
    assert declared == 20, "expected 20 Feature-08 scenarios in 08*.feature, found %d" % declared

    # --collect-only never runs the scenarios (so the xfail smoke's deliberate failure is inert);
    # -p no:warnings keeps the output to bare node ids so the count is exact.
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:warnings",
         str(_STEP_DEFS)],
        cwd=str(_REPO), capture_output=True, text=True)
    assert proc.returncode == 0, "collect failed:\n%s\n%s" % (proc.stdout, proc.stderr)

    collected = [ln for ln in proc.stdout.splitlines() if _NODE.match(ln)]
    assert len(collected) == declared, (
        "bound-ness drift: %d Feature-08 scenarios declared in 08*.feature but %d collected by "
        "pytest-bdd — an unbound (or misbound) feature?\n%s"
        % (declared, len(collected), proc.stdout))
