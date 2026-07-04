# engine/confine.py
"""Assert a path stays inside a root (symlinks resolved, case-insensitive-FS safe), so plaintext
client artifacts cannot be written/read outside the boundary. A point-in-time CHECK, not a sandbox:
a symlink planted between the check and a later write can still escape — callers should re-check
before sensitive writes. Stdlib-only."""
import os

# Detect a case-INSENSITIVE filesystem once (macOS/APFS, Windows): does this module resolve under a
# case-swapped name? `os.path.normcase` does NOT detect this on POSIX — it only lowercases on Windows
# (re-audit R1). Fall back to case-sensitive (safer: over-blocks rather than over-permits).
_here = os.path.realpath(__file__)
try:
    _CASE_INSENSITIVE = os.path.exists(os.path.join(os.path.dirname(_here),
                                                    os.path.basename(_here).swapcase()))
except OSError:
    _CASE_INSENSITIVE = False


def _key(p: str) -> str:
    return p.casefold() if _CASE_INSENSITIVE else p


def assert_within(root: str, path: str) -> str:
    if not os.path.isabs(root) or not os.path.isabs(path):
        raise ValueError("assert_within requires absolute paths (root=%r, path=%r)" % (root, path))
    real = os.path.realpath(path)
    rk, pk = _key(os.path.realpath(root)), _key(real)
    if rk != pk and os.path.commonpath([rk, pk]) != rk:
        raise ValueError("path %r escapes the sovereign root %r" % (path, root))
    return real
