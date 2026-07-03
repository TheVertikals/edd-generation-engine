from engine.bundle import Bundle
from engine.inputpack import InputPack


def pack_to_bundle(pack: InputPack, bundle: Bundle) -> dict:
    """Minimal intake adapter (the InputPack seam): materialize the pack's normalized
    input into the bundle under intake/, and return the manifest so callers can join on
    beacon_id. A real intake source implements this same contract behind the same shape,
    so the runner never sees where the input came from."""
    manifest = pack.manifest()
    bundle.write("intake/source.txt", pack.read("transcript.txt") or "")
    return manifest
