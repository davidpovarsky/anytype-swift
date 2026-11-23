"""Exact loaded-source verification for the explicit original-Products controller."""
import hashlib
from pathlib import Path
import re
import subprocess
import sys

MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_BATCH_BYTES = 64 * 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def decode_batch(raw, names):
    """Read the fixed cat-file protocol without trusting missing or oversized rows."""
    require(isinstance(raw, bytes) and len(raw) <= MAX_BATCH_BYTES,
            "Bounded original controller Git response required")
    cursor = 0
    result = {}
    for name in names:
        end = raw.find(b"\n", cursor)
        require(end >= cursor and end - cursor < 128, "Missing bounded Git object header")
        fields = raw[cursor:end].split(b" ")
        require(len(fields) == 3 and re.fullmatch(b"[0-9a-f]{40}", fields[0])
                and fields[1] == b"blob" and fields[2].isdigit(), "Exact Git blob response required")
        size = int(fields[2])
        require(size <= MAX_SOURCE_BYTES, "Loaded controller source exceeds its bound")
        cursor = end + 1
        require(cursor + size < len(raw) and raw[cursor + size:cursor + size + 1] == b"\n",
                "Truncated Git blob response")
        value = raw[cursor:cursor + size]
        identity = hashlib.sha1(b"blob " + str(size).encode() + b"\0" + value).hexdigest().encode()
        require(identity == fields[0], "Git object header differs from original source bytes")
        require(name not in result, "Duplicate loaded controller source")
        result[name] = value
        cursor += size + 1
    require(cursor == len(raw), "Unexpected extra Git object response")
    return result


def control_sources(control, head):
    """Use one bounded Git process for the same exact loaded module closure."""
    control = Path(control).resolve()
    require(re.fullmatch(r"[0-9a-f]{40}", head), "Exact immutable controller commit required")
    require(not subprocess.check_output(["git", "-C", str(control), "status", "--porcelain",
                                         "--untracked-files=no"], text=True, timeout=30).strip(),
            "Tracked controller source is dirty")
    paths = {}
    for module in tuple(sys.modules.values()):
        name = getattr(module, "__file__", None)
        if not name:
            continue
        path = Path(name).resolve()
        if path.suffix != ".py" or not path.is_relative_to(control):
            continue
        relative = path.relative_to(control).as_posix()
        require("\n" not in relative and "\r" not in relative and "\0" not in relative
                and ":" not in relative, "Unambiguous controller object path required")
        require(path.is_file() and path.stat().st_size <= MAX_SOURCE_BYTES,
                "Bounded physical controller source required")
        paths[relative] = path
    require("Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py" in paths
            and "Tools/PinkhaSimulatorGate/coherent_controller_sources.py" in paths
            and 5 <= len(paths) <= 256, "Controller and imported source closure missing")
    require(sum(path.stat().st_size for path in paths.values()) <= MAX_BATCH_BYTES,
            "Loaded source closure exceeds its total bound")
    names = sorted(paths)
    request = b"".join((head + ":" + name + "\n").encode("utf-8") for name in names)
    raw = subprocess.check_output(["git", "-C", str(control), "cat-file", "--batch"],
                                  input=request, timeout=30)
    original = decode_batch(raw, names)
    hashes = {}
    for name in names:
        observed = paths[name].read_bytes()
        require(observed == original[name], "Loaded controller source differs from exact checkout")
        hashes[name] = hashlib.sha256(observed).hexdigest()
    return hashes
