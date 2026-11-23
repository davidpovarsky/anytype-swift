"""Fixed source-derived Clang support for the isolated SDK06 test bundle.

This packet supplies declarations, never App/native implementation binaries.
Five maps are preserved source bytes; thirteen maps are newly derived.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat

MANIFEST = "Tools/PinkhaSimulatorGate/sdk06-compile-support.json"
MANIFEST_SHA = "a41132dc149e39580f4eda4386d8175fcb4f2105ff94b0921167dca3ea7b19a4"
PACKET = "Tools/PinkhaSimulatorGate/sdk06-compile-support-source.json.gz"
SOURCE = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
_SEAL = object()


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate compile-support JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique)


def _relative(name):
    require(type(name) is str and name and "\\" not in name and ":" not in name
            and "\0" not in name and not name.startswith("/")
            and all(part not in ("", ".", "..") for part in name.split("/"))
            and PurePosixPath(name).as_posix() == name,
            "Unsafe compile-support relative member")
    return name


def _ancestors(path):
    require(path.is_absolute(), "An absolute compile-support path is required")
    for current in reversed((path, *path.parents)):
        if current.exists() or current.is_symlink():
            require(not current.is_symlink(), "Compile support traverses a symbolic link")
            if current != path:
                require(current.is_dir(), "Compile-support ancestor is not a directory")


def _regular(path, maximum):
    _ancestors(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and 0 <= before.st_size <= maximum,
            "Compile-support input is not a bounded single regular file")
    with path.open("rb") as stream:
        raw = stream.read(maximum + 1)
    after = path.lstat()
    fields = ("st_dev", "st_ino", "st_size", "st_mode", "st_mtime_ns", "st_ctime_ns")
    require(len(raw) == before.st_size
            and all(getattr(before, field) == getattr(after, field) for field in fields),
            "Compile-support input changed during its read")
    return raw


def fixed_inputs(control):
    control = Path(control)
    manifest_raw = _regular(control / MANIFEST, 256 * 1024)
    require(digest(manifest_raw) == MANIFEST_SHA, "The fixed compile-support manifest changed")
    fixed = _json(manifest_raw)
    require(fixed["protocol"] == "sdk06-fixed-compile-support-v1"
            and fixed["original_app_source"] == SOURCE
            and len(fixed["packages"]) == 7 and len(fixed["files"]) == 105
            and len(fixed["blobs"]) == 109 and len(fixed["source_maps"]) == 5
            and len(fixed["derived_maps"]) == 13 and len(fixed["link_proofs"]) == 4
            and len(fixed["map_order"]) == len(set(fixed["map_order"])) == 18
            and len(fixed["include_order"]) == len(set(fixed["include_order"])) == 18,
            "The finite compile-support scope changed")
    compressed = _regular(control / PACKET, 256 * 1024)
    require(len(compressed) == fixed["packet"]["bytes"]
            and digest(compressed) == fixed["packet"]["sha256"],
            "The fixed compile-support source packet changed")
    with gzip.GzipFile(fileobj=io.BytesIO(compressed), mode="rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    require(len(raw) == fixed["packet"]["decoded_bytes"] <= 1024 * 1024
            and digest(raw) == fixed["packet"]["decoded_sha256"],
            "The decoded compile-support source packet changed")
    packet = _json(raw)
    require(packet["protocol"] == "sdk06-git-header-blobs-v1"
            and set(packet) == {"protocol", "objects"}
            and set(packet["objects"]) == set(fixed["blobs"]),
            "The exact Git header-object set is required")
    objects = {}
    for oid, row in fixed["blobs"].items():
        require(re.fullmatch(r"[0-9a-f]{40}", oid) is not None,
                "Invalid Git header-object identity")
        value = base64.b64decode(packet["objects"][oid], validate=True)
        require(len(value) == row["bytes"] <= 128 * 1024
                and digest(value) == row["sha256"]
                and hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest() == oid,
                "A pinned package header object changed")
        objects[oid] = value
    require(sum(len(raw) for raw in objects.values()) == 319378,
            "The fixed package-object byte count changed")
    return fixed, objects


def _file_plan(fixed, objects, root):
    files = {}
    used = set()
    packages = {row["identity"]: row["revision"] for row in fixed["packages"]}
    for row in fixed["files"]:
        name = _relative(row["path"])
        require(name not in files and row["identity"] in packages
                and row["revision"] == packages[row["identity"]]
                and name == "SourcePackages/" + row["identity"] + "/" + _relative(row["source_path"])
                and row["runtime_mode"] in (0o644, 0o755),
                "A fixed package file has an invalid origin")
        if row["original_mode"] == "120000":
            matches = [item for item in fixed["link_proofs"]
                       if item["identity"] == row["identity"]
                       and item["link_path"] == row["source_path"]]
            require(len(matches) == 1, "A package link lacks its exact target proof")
            proof = matches[0]
            link = objects[proof["link_blob"]]
            require(link.decode("utf-8") == proof["link_text"]
                    and row["original_blob"] == proof["link_blob"]
                    and not proof["link_text"].startswith("/")
                    and posixpath.normpath(posixpath.join(posixpath.dirname(proof["link_path"]),
                                                         proof["link_text"])) == proof["target_path"]
                    and row["content_blob"] == proof["target_blob"]
                    and row["runtime_mode"] == 0o644,
                    "A package link-to-target proof changed")
            used.add(proof["link_blob"])
        else:
            require(row["original_mode"] in ("100644", "100755")
                    and row["content_blob"] == row["original_blob"]
                    and row["runtime_mode"] == int(row["original_mode"][-3:], 8),
                    "A preserved regular header has changed provenance")
        content = objects[row["content_blob"]]
        require(len(content) == row["bytes"] and digest(content) == row["sha256"],
                "A materialized header differs from its pinned source")
        used.add(row["content_blob"])
        files[name] = (row["runtime_mode"], content)
    require(len(files) == 105 and sum(len(value[1]) for value in files.values()) == 319317
            and used == set(objects), "The complete fixed header-object closure is required")
    for row in fixed["source_maps"]:
        require(row["path"] in files and digest(files[row["path"]][1]) == row["sha256"]
                and row["provenance"] == "PRESERVED_PINNED_PACKAGE_SOURCE",
                "A preserved source module map changed")
    derived = []
    for row in fixed["derived_maps"]:
        name, umbrella = _relative(row["path"]), _relative(row["umbrella"])
        require(name not in files and row["provenance"] == "NEW_DERIVED"
                and row["original_generated_bytes_preserved"] is False
                and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", row["module"]) is not None
                and any(path.startswith(umbrella + "/") for path in files),
                "A newly derived map has an invalid fixed umbrella")
        raw = ("module " + row["module"] + " {\n    umbrella "
               + json.dumps(str(root / umbrella), ensure_ascii=True)
               + "\n    export *\n}\n").encode()
        files[name] = (0o644, raw)
        derived.append(name)
    require(len(files) == 118 and len(derived) == 13
            and set(fixed["map_order"]) == set(derived) | {row["path"] for row in fixed["source_maps"]},
            "Only the fixed eighteen maps may be passed to the compiler")
    for relative in fixed["include_order"]:
        _relative(relative)
        require(any(name.startswith(relative + "/") for name in files),
                "An include root lacks its fixed public source")
    return files


def _inventory(root):
    _ancestors(root)
    require(root.is_dir(), "The materialized compile-support root is absent")
    found = {}
    def failed(error):
        raise error
    for current, dirs, names in os.walk(root, followlinks=False, onerror=failed):
        for path in [Path(current)] + [Path(current) / name for name in sorted(names + dirs)]:
            key = "." if path == root else path.relative_to(root).as_posix()
            if key in found:
                continue
            record = path.lstat()
            require(not stat.S_ISLNK(record.st_mode), "Compile support contains a symbolic link")
            if stat.S_ISDIR(record.st_mode):
                found[key] = ("directory", stat.S_IMODE(record.st_mode), 0, "")
            else:
                require(stat.S_ISREG(record.st_mode) and record.st_nlink == 1,
                        "Compile support contains a non-regular or shared file")
                raw = _regular(path, 128 * 1024)
                found[key] = ("file", stat.S_IMODE(record.st_mode), len(raw), digest(raw))
    return found


@dataclass(frozen=True)
class FixedCompileSupport:
    root: Path
    _entries: tuple
    _maps: tuple
    _includes: tuple
    _manifest: bytes
    _seal: object

    def verify(self):
        require(self._seal is _SEAL and type(self) is FixedCompileSupport,
                "A concrete fixed compile-support instance is required")
        expected = dict(self._entries)
        require(_inventory(self.root) == expected,
                "The exact compile-support path, kind, mode or bytes changed")
        return expected

    def settings(self):
        self.verify()
        return {"HEADER_SEARCH_PATHS": [str(self.root / name) for name in self._includes],
                "OTHER_SWIFT_FLAGS": ["$(inherited)"] + [
                    part for name in self._maps
                    for part in ("-Xcc", "-fmodule-map-file=" + str(self.root / name))]}

    def receipt(self):
        actual = self.verify()
        fixed = _json(self._manifest)
        return {"protocol": "sdk06-materialized-compile-support-v1",
                "original_app_source": SOURCE, "manifest_sha256": MANIFEST_SHA,
                "packet": fixed["packet"], "root": str(self.root),
                "packages": fixed["packages"], "link_proofs": fixed["link_proofs"],
                "preserved_source_maps": fixed["source_maps"],
                "new_derived_maps": fixed["derived_maps"],
                "original_generated_maps_preserved": False,
                "input_regular_files": 105, "new_derived_maps_count": 13,
                "inventory": {name: {"kind": row[0], "mode": row[1],
                                      "bytes": row[2], "sha256": row[3]}
                              for name, row in sorted(actual.items())},
                "app_or_native_builds": 0, "compile_or_product_acceptance": False}


def materialize(control, project_root):
    """Create only fixed regular source support under one fresh generated project."""
    project_root = Path(project_root)
    require(project_root.is_absolute() and project_root == project_root.absolute()
            and re.fullmatch(r"/[A-Za-z0-9_./+\-]+", str(project_root)) is not None
            and ".." not in project_root.parts and "." not in project_root.parts,
            "The fixed build path must be absolute and shell-independent")
    _ancestors(project_root)
    require(not project_root.exists() and not project_root.is_symlink()
            and project_root.parent.is_dir(),
            "The support project destination must be a fresh direct child")
    fixed, objects = fixed_inputs(control)
    root = project_root / "CompileSupport"
    files = _file_plan(fixed, objects, root)
    directories = {"."}
    for name in files:
        directories.update(parent.as_posix() for parent in PurePosixPath(name).parents)
    require(len(directories) <= 80, "Unexpected compile-support directory growth")
    expected = {name: ("directory", 0o755, 0, "") for name in directories}
    expected.update({name: ("file", mode, len(raw), digest(raw))
                     for name, (mode, raw) in files.items()})
    # No filesystem mutation precedes complete source/shape admission.
    project_root.mkdir(mode=0o755)
    project_root.chmod(0o755)
    for name in sorted(directories, key=lambda item: (len(PurePosixPath(item).parts), item)):
        path = root if name == "." else root / name
        path.mkdir(mode=0o755)
        path.chmod(0o755)
    for name, (mode, raw) in sorted(files.items()):
        path = root / name
        with path.open("xb") as stream:
            stream.write(raw)
        path.chmod(mode)
    result = FixedCompileSupport(root, tuple(sorted(expected.items())),
                                 tuple(fixed["map_order"]), tuple(fixed["include_order"]),
                                 json.dumps(fixed, sort_keys=True, separators=(",", ":")).encode(), _SEAL)
    result.verify()
    return result
