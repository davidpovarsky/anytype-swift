"""Match retained companion source records across a case-insensitive volume.

This verifies an inventory only. It does not prepare, build, or qualify a
companion binary. Callers must retain the canonical and observed path names.
"""


def verify_tracked_inventory(tracked, inventory):
    observed = {}
    for path in inventory:
        key = path.casefold()
        if key in observed:
            raise ValueError(f"ambiguous case alias: {observed[key]!r}, {path!r}")
        observed[key] = path

    canonical = set()
    matches = {}
    for path, value in tracked.items():
        key = path.casefold()
        if key in canonical:
            raise ValueError(f"ambiguous canonical path: {path!r}")
        canonical.add(key)
        actual = observed.get(key)
        if actual is None:
            raise ValueError(f"missing tracked source: {path!r}")
        expected = value if isinstance(value, str) else value["sha256"]
        record = inventory[actual]
        if record.get("kind") != "file" or record.get("sha256") != expected:
            raise ValueError(f"tracked source differs: {path!r} at {actual!r}")
        matches[path] = actual
    return matches
