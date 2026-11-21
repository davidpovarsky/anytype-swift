"""Compose the separate Space.Close test without replacing product/module files.

The original account-RPC overlay remains intact. Seven exact native files gain
test observations, and three separately inventoried Go files join this binary.
The two AnySync replacements address its actual selected immutable module cache;
the cache and original Heart files are never written.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import shutil

HERE = Path(__file__).resolve().parent
PRODUCT = "16b7493fa05bdc3abbae190c6e6c364c81874eea"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
ANY_SYNC = "github.com/anyproto/any-sync"
VERSION = "v0.13.8"
COMMIT = "5d71ccad5db77997df2d2426011ebae4e7600d98"
INSTRUMENTED = {
    ("heart", "core/block/editor/torahops/native_host.go"),
    ("heart", "core/block/editor/torahops/native_commit_guard.go"),
    ("heart", "core/block/editor/torahopsobject/target_lease.go"),
    ("heart", "space/clientspace/space.go"),
    ("heart", "space/spacecore/storage/anystorage/clientstorage.go"),
    ("any-sync", "app/ocache/ocache.go"),
    ("any-sync", "commonspace/settings/settingsobject.go"),
}
ADDED = {
    "clientlibrary/service/pinkha_t2_native_rpc_space_close_test.go": "native_rpc_space_close_test.go",
    "space/pinkha_t2_owned_space_close.go": "owned_controller.go",
    "util/pinkhat2spaceclosetest/observer.go": "space_close_observer.go",
}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Regular source file required")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(value):
    require(isinstance(value, str), "Source path must be a string")
    path = PurePosixPath(value)
    require(bool(path.parts) and not path.is_absolute() and ".." not in path.parts
            and "\\" not in value and ":" not in value, "Unsafe source path")
    return Path(*path.parts)


def module_identity(heart, selected):
    """Bind the selected module to the unchanged pinned Heart go.mod/go.sum."""
    require(isinstance(selected, dict) and "Replace" not in selected
            and selected.get("Path") == ANY_SYNC and selected.get("Version") == VERSION,
            "Only the original selected AnySync module is supported")
    module_lines = (heart / "go.mod").read_text().splitlines()
    require(sum(bool(re.fullmatch(r"\s*" + re.escape(ANY_SYNC) + r"\s+" + re.escape(VERSION)
                                 + r"\s*(?://.*)?", line)) for line in module_lines) == 1,
            "Pinned Heart no longer selects the reviewed AnySync version")
    sums = {}
    for version, key in [(VERSION, "Sum"), (VERSION + "/go.mod", "GoModSum")]:
        matches = [line.split()[2] for line in (heart / "go.sum").read_text().splitlines()
                   if len(line.split()) == 3 and line.split()[:2] == [ANY_SYNC, version]]
        require(len(matches) == 1 and re.fullmatch(r"h1:[A-Za-z0-9+/]{43}=", matches[0])
                and selected.get(key) == matches[0], "AnySync checksum differs from immutable Heart input")
        sums[key] = matches[0]
    require(isinstance(selected.get("Dir"), str) and isinstance(selected.get("GoMod"), str),
            "Selected AnySync files were not resolved")
    root, go_mod = Path(selected["Dir"]), Path(selected["GoMod"])
    require(root.is_absolute() and root.is_dir() and not root.is_symlink()
            and root.resolve(strict=True) == root and not root.is_relative_to(heart)
            and go_mod.is_absolute() and go_mod.resolve(strict=True) == go_mod,
            "Canonical separate AnySync module files required")
    require((root / "go.mod").read_bytes() == go_mod.read_bytes(),
            "Selected module and checksum carrier have different go.mod bytes")
    require(re.search(r"(?m)^module\s+" + re.escape(ANY_SYNC) + r"\s*$", go_mod.read_text()),
            "Selected module declares a foreign path")
    origin = selected.get("Origin")
    if origin is not None:
        require(isinstance(origin, dict) and origin.get("Hash") == COMMIT,
                "Reported AnySync origin differs from the reviewed commit")
    return {"path": ANY_SYNC, "version": VERSION, "reviewed_commit": COMMIT,
            "selected_dir": str(root), "go_mod_path": str(go_mod),
            "go_mod_sha256": digest(go_mod), "module_go_mod_sha256": digest(root / "go.mod"),
            "sum": sums["Sum"], "go_mod_sum": sums["GoModSum"],
            "origin": origin, "commit_evidence": "REVIEWED_TAG_SOURCE_BINDINGS_AND_PINNED_MODULE_CHECKSUMS"}


def module_tree(root):
    """Inventory regular source bytes, rejecting links before any copy follows them."""
    require(root.is_dir() and not root.is_symlink() and root.resolve(strict=True) == root,
            "Canonical module source directory required")
    files = {}
    for path in sorted(root.rglob("*")):
        require(not path.is_symlink(), "Module source must not contain symlinks")
        if path.is_file():
            files[path.relative_to(root).as_posix()] = digest(path)
        else:
            require(path.is_dir(), "Module source contains a special file")
    require("go.mod" in files, "Module source has no go.mod")
    return files


def tree_digest(files):
    return hashlib.sha256(json.dumps(files, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def copy_module_for_overlay(module, destination):
    """Make one byte-exact, nonsymlink source copy outside the immutable cache."""
    root = Path(module["selected_dir"])
    require(destination.is_absolute() and destination.parent.resolve(strict=True) == destination.parent
            and not destination.exists() and not destination.is_symlink()
            and not destination.is_relative_to(root), "Fresh separate module copy required")
    before = module_tree(root)
    destination.mkdir(mode=0o700)
    for name in before:
        source, target = root / relative(name), destination / relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)  # New writable bytes; never chmod a cached source.
    require(module_tree(root) == before and module_tree(destination) == before,
            "Selected module changed while copying")
    return {"source_dir": str(root), "copy_dir": str(destination),
            "tree_sha256": tree_digest(before), "file_count": len(before),
            "scope": "BYTE_EXACT_TEST_WORKSPACE_COPY_NOT_SHIPPED_PRODUCT"}


def verify_module_copy(module, copy):
    require(copy.get("source_dir") == module["selected_dir"]
            and copy.get("scope") == "BYTE_EXACT_TEST_WORKSPACE_COPY_NOT_SHIPPED_PRODUCT",
            "Foreign module copy binding")
    original = module_tree(Path(module["selected_dir"]))
    copied = module_tree(Path(copy["copy_dir"]))
    require(original == copied and len(original) == copy["file_count"]
            and tree_digest(original) == copy["tree_sha256"], "Module source/copy changed")
    return True


def prepare(heart, selected, existing, output):
    heart, existing = heart.resolve(strict=True), existing.resolve(strict=True)
    output = output.absolute()
    require(output.parent.resolve(strict=True) == output.parent
            and not output.exists() and not output.is_symlink(), "Fresh canonical overlay destination required")
    module = module_identity(heart, selected)
    manifest_path = HERE / "candidate.json"
    manifest = json.loads(manifest_path.read_text())
    require(manifest.get("schema") == "pinkha-t2-space-close-composition-v1"
            and manifest.get("scope") == "TEST_COMPILE_OVERLAYS_ONLY_NOT_SHIPPED_PRODUCT"
            and manifest.get("product_base_sha") == PRODUCT and manifest.get("heart_sha") == HEART
            and manifest.get("app_capability") == "OFF"
            and manifest.get("original_cache_close_timeout_seconds") == 10
            and manifest.get("any_sync") == {"module": ANY_SYNC, "version": VERSION, "commit": COMMIT},
            "Wrong reviewed Space.Close composition")
    require(digest(HERE / "test-composition.patch") == manifest.get("patch_sha256"),
            "Composition patch changed")
    entries = manifest.get("instrumented")
    require(isinstance(entries, list) and len(entries) == 7
            and {(entry.get("module"), entry.get("path")) for entry in entries} == INSTRUMENTED,
            "Exactly seven reviewed native observation paths required")
    require(isinstance(manifest.get("added"), dict) and set(manifest["added"]) == set(ADDED),
            "Exactly three reviewed test-only Go files required")
    module_copy = copy_module_for_overlay(module, output.parent / "any-sync-source")
    roots = {"heart": heart, "any-sync": Path(module_copy["copy_dir"])}
    original = json.loads(existing.read_text())
    require(set(original) == {"Replace"} and isinstance(original["Replace"], dict)
            and original["Replace"], "Original account-RPC overlay required")
    replacements, hashes = {}, {}
    for target, source in original["Replace"].items():
        a, b = Path(target), Path(source)
        require(a.is_absolute() and b.is_absolute() and a.resolve() == a
                and b.resolve(strict=True) == b and a.is_relative_to(heart),
                "Original overlay must keep canonical native target/source bindings")
        hashes[source] = digest(b)
        replacements[target] = source
    added, source_before, replacement_after = {}, {}, {}
    for entry in entries:
        root = roots[entry["module"]]
        rel = relative(entry["path"])
        target, source = root / rel, HERE / "overlay" / entry["module"] / rel
        require(target.resolve(strict=True).is_relative_to(root)
                and source.resolve(strict=True).is_relative_to(HERE)
                and digest(target) == entry["before_sha256"]
                and digest(source) == entry["after_sha256"], "Exact native observation source differs")
        require(str(target) not in replacements and str(target) not in added,
                "Observation cannot hide an existing compile overlay")
        added[str(target)] = str(source)
        source_before[str(target)] = entry["before_sha256"]
        if entry["module"] == "any-sync":
            source_before[str(Path(module["selected_dir"]) / rel)] = entry["before_sha256"]
        replacement_after[str(source)] = entry["after_sha256"]
    for name, fixture in ADDED.items():
        entry = manifest["added"][name]
        require(entry.get("fixture") == fixture, "Foreign added fixture")
        target, source = heart / relative(name), HERE / fixture
        require(not target.exists() and not target.is_symlink()
                and source.resolve(strict=True).is_relative_to(HERE)
                and digest(source) == entry["sha256"] and str(target) not in replacements,
                "New test fixture would replace an existing source")
        added[str(target)] = str(source)
        replacement_after[str(source)] = entry["sha256"]
    helper = heart / "util/pinkhat2spaceclosetest"
    require(not helper.exists() and not helper.is_symlink(), "Fresh test-only package directory required")
    require(len(added) == 10, "Wrong overlay entry count")
    # Go discovers the package using this empty directory; every source byte is
    # still read through the overlay. No file is written into either module.
    helper.mkdir()
    replacements.update(added)
    output.write_text(json.dumps({"Replace": replacements}, indent=2, sort_keys=True) + "\n")
    return {"scope": manifest["scope"], "candidate_sha256": digest(manifest_path),
            "original_overlay_sha256": digest(existing), "composed_overlay_sha256": digest(output),
            "added_overlay_entries": len(added), "product_source_mutations": 0, "module_cache_mutations": 0,
            "empty_package_directory": str(helper), "any_sync": module, "any_sync_copy": module_copy,
            "source_before_sha256": source_before, "replacement_after_sha256": replacement_after,
            "original_fixture_sha256": hashes, "native_execution": "NOT_RUN"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--heart", type=Path, required=True)
    parser.add_argument("--selected-module", type=Path, required=True)
    parser.add_argument("--existing-overlay", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.heart, json.loads(args.selected_module.read_text()),
                             args.existing_overlay, args.output)))
