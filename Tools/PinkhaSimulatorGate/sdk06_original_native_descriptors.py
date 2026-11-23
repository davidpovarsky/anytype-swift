"""Exact original Products plus five finite recorded SDK descriptor additions."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

PROTOCOL = "sdk06-original-native-descriptor-additions-v1"
PURPOSES = {
    "host-normalization": r"UI27-original-sdk06-host\.xctestrun",
    "discovery": r"UI27-original-sdk06-[0-9a-f]{32}-discovery\.xctestrun",
    "tagged-selection": r"UI27-original-sdk06-[0-9a-f]{32}-selected\.xctestrun",
    "text-native-ack": r"UI27-original-sdk06-selection-[0-9a-f]{32}\.xctestrun",
    "prepare": r"UI27-original-sdk06-selection-[0-9a-f]{32}\.xctestrun",
}
MAX_DESCRIPTOR_BYTES = 512 * 1024


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def member(name):
    require(isinstance(name, str) and name and "\\" not in name and "\x00" not in name,
            "Invalid original Products member")
    path = PurePosixPath(name)
    require(not path.is_absolute() and str(path) == name
            and all(part not in {"", ".", ".."} and ":" not in part for part in path.parts),
            "Products member must be an exact relative path")
    return path


def parent_members(entries):
    return {parent.as_posix() for name in entries for parent in member(name).parents
            if parent.as_posix() != "."} - set(entries)


def tree(derived):
    require(derived.is_dir() and not derived.is_symlink(), "Original Products root is not a real directory")
    observed = {}
    for current, directories, files in os.walk(derived, followlinks=False):
        for name in sorted(directories + files):
            path = Path(current) / name
            status = path.lstat()
            require(not stat.S_ISLNK(status.st_mode)
                    and (stat.S_ISDIR(status.st_mode) or stat.S_ISREG(status.st_mode)),
                    "Original Products tree contains a link or unsupported member")
            relative = path.relative_to(derived).as_posix()
            member(relative)
            observed[relative] = {
                "kind": "directory" if stat.S_ISDIR(status.st_mode) else "file",
                "mode": stat.S_IMODE(status.st_mode),
            }
            require(len(observed) <= 5020, "Original Products tree exceeds its fixed bounded closure")
    return observed


def original_tree(derived, entries):
    """Capture only implicit structural parents after exact archive restoration."""
    parents = parent_members(entries)
    observed = tree(derived)
    require(set(observed) == set(entries) | parents,
            "Restored original Products membership differs before descriptor additions")
    for name, expected in entries.items():
        require(observed[name] == {"kind": expected["kind"], "mode": expected["mode"]},
                "An original Products member type or mode differs")
    result = {name: observed[name] for name in sorted(parents)}
    require(all(row["kind"] == "directory" for row in result.values()),
            "An implicit original structural parent is not a directory")
    return result


def fingerprint(path):
    status = path.lstat()
    require(stat.S_ISREG(status.st_mode) and not path.is_symlink()
            and 0 < status.st_size <= MAX_DESCRIPTOR_BYTES
            and not stat.S_IMODE(status.st_mode) & ~0o666
            and status.st_mode & 0o600 == 0o600,
            "A generated descriptor must be a bounded regular nonexecutable file")
    raw = path.read_bytes()
    require(len(raw) == status.st_size, "Generated descriptor changed while reading")
    return {
        "bytes": len(raw), "mode": stat.S_IMODE(status.st_mode), "sha256": digest(raw),
        "inode": str(status.st_ino), "mtime_ns": str(status.st_mtime_ns),
        "descriptor_bytes_base64": base64.b64encode(raw).decode("ascii"),
    }


def records(derived, entries, evidence, binding):
    ledger = evidence / "generated-native-descriptors"
    require(evidence.is_dir() and not evidence.is_symlink(), "Exact descriptor evidence root is required")
    require(set(binding) == {"source_sha", "run_id", "run_attempt"},
            "Generated descriptors require exact current controller/run binding")
    if not ledger.exists():
        return {}
    require(ledger.is_dir() and not ledger.is_symlink(), "Descriptor addition ledger is not a real directory")
    paths = sorted(ledger.iterdir())
    require(len(paths) <= len(PURPOSES), "Unexpected generated descriptor ledger cardinality")
    result = {}
    keys = {"protocol", "purpose", "binding", "path", "original_descriptor_unchanged",
            "bytes", "mode", "sha256", "inode", "mtime_ns", "descriptor_bytes_base64"}
    for path in paths:
        require(path.name.endswith(".json") and path.stem in PURPOSES
                and path.is_file() and not path.is_symlink() and path.stat().st_size <= 1024 * 1024,
                "Unrecorded or unsupported descriptor-addition ledger member")
        value = json.loads(path.read_bytes())
        require(set(value) == keys and value["protocol"] == PROTOCOL
                and value["purpose"] == path.stem and value["binding"] == binding
                and value["original_descriptor_unchanged"] is True,
                "Generated descriptor ledger identity differs")
        relative = member(value["path"])
        require(relative.parent.as_posix() == "Build/Products"
                and re.fullmatch(PURPOSES[path.stem], relative.name)
                and value["path"] not in entries and value["path"] not in result,
                "Generated descriptor is not its finite fresh Products sibling")
        generated = derived / value["path"]
        actual = fingerprint(generated)
        require(actual == {key: value[key] for key in actual},
                "A recorded generated descriptor changed")
        result[value["path"]] = value
    return result


def verify(derived, entries, parents, evidence, binding, *, pending=None):
    require(set(parents) == parent_members(entries)
            and all(set(row) == {"kind", "mode"} and row["kind"] == "directory"
                    for row in parents.values()), "Original structural parent receipt differs")
    additions = records(derived, entries, evidence, binding)
    expected = {name: {"kind": row["kind"], "mode": row["mode"]} for name, row in entries.items()}
    expected.update(parents)
    expected.update({name: {"kind": "file", "mode": row["mode"]} for name, row in additions.items()})
    if pending is not None:
        path, purpose = pending
        require(purpose in PURPOSES and path.parent == derived / "Build/Products"
                and re.fullmatch(PURPOSES[purpose], path.name),
                "Pending descriptor is not an exact allowed direct Products sibling")
        name = path.relative_to(derived).as_posix()
        require(name not in expected and not (evidence / "generated-native-descriptors" / (purpose + ".json")).exists(),
                "Generated descriptor cannot replace an original or recorded member/purpose")
        expected[name] = {"kind": "file", "mode": fingerprint(path)["mode"]}
    require(tree(derived) == expected,
            "Original Products tree contains an unrecorded, missing or changed member")
    return additions


def register(derived, entries, parents, evidence, binding, path, purpose):
    require(path.is_absolute() and path.parent == derived / "Build/Products",
            "Generated descriptor must remain beside the original __TESTROOT__")
    verify(derived, entries, parents, evidence, binding, pending=(path, purpose))
    value = {
        "protocol": PROTOCOL, "purpose": purpose, "binding": binding,
        "path": path.relative_to(derived).as_posix(), "original_descriptor_unchanged": True,
        **fingerprint(path),
    }
    ledger = evidence / "generated-native-descriptors"
    ledger.mkdir(exist_ok=True)
    destination = ledger / (purpose + ".json")
    with destination.open("xb") as output:
        output.write((json.dumps(value, sort_keys=True, indent=2) + "\n").encode())
    verify(derived, entries, parents, evidence, binding)
    return value
