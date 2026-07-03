# EDD Generation Engine

The agnostic tier-2 **orchestration core** of the EDD autonomous pipeline: a resumable
`Runner` that walks an ordered list of `Stage`s over a file-backed `Bundle`, firing an
approve / revise / reject `Gate` between stages, driven by an `InputPack`.

**Agnostic by construction.** The engine imports nothing client-, product-, or
substrate-specific. Stages communicate *only* through files on the bundle — never by
calling each other. A CI test asserts zero references to any proprietary layer.

This repo is the **walking skeleton** (Plan 1 of the thin thread): the runner, the
seams (`Stage` / `Gate` / `InputPack`), checkpoint/resume, and the gate loop, exercised
by trivial demo stages on a stub input pack. Real generation stages, the proprietary
render layer, and the sovereign capture substrate arrive in later plans behind these
same contracts.

## Layout

- `engine/bundle.py` — file-backed working dir (atomic writes, path-confined, utf-8).
- `engine/checkpoint.py` — resumable state (`<root>/.engine/state.json`).
- `engine/stage.py` — `Stage` base + `GateSpec`.
- `engine/gate.py` — `Gate` + `Verdict` + `AutoApproveGate` / `ScriptedGate`.
- `engine/inputpack.py` — the generic input-pack reader (the intake boundary contract).
- `engine/adapter.py` — `pack_to_bundle` (minimal intake seam).
- `engine/runner.py` — the orchestration loop (approve/revise/reject, checkpoint, resume, fallible stages).
- `engine/stages/demo.py` — trivial stages for the skeleton e2e.

## Develop

```bash
make hooks   # enable the pre-push test gate (one time)
make test    # run the suite
```
