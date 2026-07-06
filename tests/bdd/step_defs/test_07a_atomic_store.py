"""Feature 07 Capability A — atomic-write, bound to the engine's production
checkpoint store (engine.checkpoint.Checkpoint).

ONLY the atomic-write scenario is authored engine-side. Checkpoint atomic-writes
(temp file + os.replace in _write) and TOLERATES a corrupt state.json by returning []
from completed() — but it does NOT sidecar-quarantine (no .corrupt directory). The
quarantine scenario ("A corrupt file is quarantined, not fatal") is therefore owned by
the loop's PendingStore and the Node notifier/store.js, NOT re-claimed here. Asserting a
quarantine engine-side would be a false claim; the ecosystem 07 drift-gate pins its absence.

Hermetic: tmp_path root, no network. The interruption is simulated deterministically by
monkeypatching os.replace to raise AFTER the .tmp is written but BEFORE the rename.
"""
import os

import pytest
from pytest_bdd import given, scenarios, then, when

from engine.checkpoint import Checkpoint

scenarios("../features/07a-atomic-store.feature")


@pytest.fixture
def ctx():
    return {}


@given("a resumable checkpoint store with committed state")
def _committed_state(ctx, tmp_path):
    cp = Checkpoint(str(tmp_path))
    cp.mark("intake")
    assert cp.completed() == ["intake"]
    ctx["cp"] = cp


@when("a checkpoint write is interrupted after the temp file exists but before the rename")
def _interrupt_write(ctx, monkeypatch):
    def _boom(src, dst):
        raise OSError("simulated crash after .tmp write, before rename")

    monkeypatch.setattr(os, "replace", _boom)
    with pytest.raises(OSError):
        ctx["cp"].mark("research")
    monkeypatch.undo()  # restore the real os.replace for the clean write in the Then


@then("the store still holds either the old state or none — never a partial")
def _no_partial_state(ctx):
    cp = ctx["cp"]
    # The interrupted write never corrupted state.json: it still holds only the OLD state.
    assert cp.completed() == ["intake"], "state.json must be intact after an interrupted write"
    # A subsequent CLEAN write commits atomically — the primitive still works.
    cp.mark("research")
    assert cp.completed() == ["intake", "research"]
