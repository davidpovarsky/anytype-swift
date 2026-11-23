"""Read only the SDK declaration-projection source repair; never import its code."""
from __future__ import annotations
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

BASE = "b15cd58e376461b066df7fd1639946bb8dca5848"
APP = "75bd6d7af18dfd511e85582ce7f994d2801b7703"
ROOT = Path("/run/anytapy-wave15-source-overlay-20261123/sdk")
DOC = "docs/validation/20261123-sdk06-projection-mock-closure"
GENERATOR = "Tools/PinkhaSimulatorGate/sdk06_component_projection.py"
CONTRACT = "Tools/PinkhaSimulatorGate/sdk06-component-projection-source.json"
CONTROLLER = "Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
MOCK = "AnytypeTests/Markdown/Mocks/BlockMarkupChangerMock.swift"
MOCK_SHA = "3648c5cda4541c0b5297cce33835132a0ebea72f521a66917360cc0bf9dc48cc"
os.environ["GIT_OPTIONAL_LOCKS"] = "0"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True

def require(value, message):
    if not value:
        raise ValueError(message)

def digest(value):
    return hashlib.sha256(value).hexdigest()

def git(*args):
    result = subprocess.run(["git", "-C", str(ROOT), *args], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, timeout=30)
    require(result.returncode == 0, "Git source read failed: " + repr(args) + " " +
            result.stderr.decode(errors="replace"))
    require(len(result.stdout) <= 4 * 1024**2, "Git source output exceeded its bound")
    return result.stdout

def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()

def blob(ref, path):
    return git("show", ref + ":" + path)

def mode(ref, path):
    row = git("ls-tree", ref, "--", path).decode().strip().split("\t")
    require(len(row) == 2 and row[1] == path, "Expected one exact Git source path")
    return row[0].split()[0]

def resource():
    available = int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:"))) * 1024
    require(available >= 2 * 1024**3, "RAM source admission requires 2 GiB MemAvailable")
    mount_rows = [line.split() for line in Path("/proc/self/mountinfo").read_text().splitlines()]
    selected = [row for row in mount_rows
                if row[4] == "/run/anytapy-wave15-source-overlay-20261123"]
    require(len(selected) == 1 and selected[0][selected[0].index("-") + 1] == "tmpfs",
            "The dedicated source tmpfs is required")
    total = os.statvfs(ROOT).f_blocks * os.statvfs(ROOT).f_frsize
    require(total <= 64 * 1024**2, "The source tmpfs size changed")
    logical = allocated = 0
    for item in [ROOT, *ROOT.rglob("*")]:
        observed = item.lstat()
        require(stat.S_ISDIR(observed.st_mode) or stat.S_ISREG(observed.st_mode),
                "Special files are not allowed in this private source writer")
        logical += observed.st_size
        allocated += observed.st_blocks * 512
    require(logical <= 8 * 1024**2 and allocated <= 8 * 1024**2,
            "The private SDK writer exceeded its 8 MiB source budget")
    return {"mem_available_bytes": available, "logical_bytes": logical,
            "allocated_bytes": allocated, "tmpfs_bytes": total}

def main():
    before = resource()
    require(ROOT.resolve() == ROOT and stat.S_IMODE(ROOT.stat().st_mode) == 0o700,
            "The private SDK source writer changed")
    head = git("rev-parse", "HEAD").decode().strip()
    require(not git("status", "--porcelain"), "The frozen source writer is not clean")
    manifest_name = DOC + "/source-inputs.json"
    manifest_raw = (ROOT / manifest_name).read_bytes()
    require(manifest_raw == blob(head, manifest_name), "The input manifest differs from Git")
    manifest = json.loads(manifest_raw)
    require(manifest["base"] == BASE and manifest["original_app_source"] == APP,
            "The source origins changed")
    checked = {}
    for name, expected in manifest["inputs"].items():
        path = ROOT / name
        observed = path.lstat()
        raw = path.read_bytes()
        require(stat.S_ISREG(observed.st_mode) and not path.is_symlink()
                and digest(raw) == expected["sha256"] and len(raw) == expected["bytes"]
                and stat.S_IMODE(observed.st_mode) == expected["physical_mode"]
                and mode(head, name) == expected["git_mode"]
                and raw == blob(head, name), "A fixed source input changed: " + name)
        checked[name] = expected
    old_fixed_raw, fixed_raw = blob(BASE, CONTRACT), (ROOT / CONTRACT).read_bytes()
    old_fixed, fixed = json.loads(old_fixed_raw), json.loads(fixed_raw)
    require(encoded(old_fixed) == old_fixed_raw and encoded(fixed) == fixed_raw,
            "Unexpected original/current JSON encoding")
    require(len(old_fixed["source_files"]) == 7 and len(fixed["source_files"]) == 8,
            "The exact seven-to-eight source correction changed")
    removed = json.loads(fixed_raw)
    extra = removed["source_files"].pop(MOCK)
    require(encoded(removed) == old_fixed_raw, "The fixed contract has an unrelated change")
    require(extra == {"basename": "BlockMarkupChangerMock.swift", "bytes": 1430,
                      "git_blob": "f57396ea7d25adb32eccbaa5baaa090a1ccfd193", "sha256": MOCK_SHA},
            "The real original mock identity changed")
    inverse = json.loads((ROOT / (DOC + "/exact-source-inverses.json")).read_bytes())
    for name, record in inverse["files"].items():
        current = (ROOT / name).read_bytes()
        require(digest(current) == record["after_sha256"], "Changed inverse input")
        recovered = current
        for replacement in reversed(record["replacements"]):
            old = replacement["before"].encode()
            new = replacement["after"].encode()
            require(recovered.count(new) == 1, "Inverse requires exactly one literal match")
            recovered = recovered.replace(new, old, 1)
        require(recovered == blob(BASE, name)
                and digest(recovered) == record["before_sha256"], "Whole-file inverse failed")
    old_controller = json.loads(blob(BASE, CONTROLLER))
    controller = json.loads((ROOT / CONTROLLER).read_bytes())
    expected_controller = json.loads(blob(BASE, CONTROLLER))
    for name in (GENERATOR, CONTRACT):
        expected_controller["inputs"][name]["sha256"] = digest((ROOT / name).read_bytes())
    require(controller == expected_controller and len(controller["inputs"]) == 85,
            "Only the two existing controller hash rows may change")
    require(controller["preload_modules"] == old_controller["preload_modules"]
            == sorted(controller["preload_modules"])
            and controller["modules"] == old_controller["modules"],
            "The qualified import closure must remain exact")
    current_git = {}
    for name, expected in controller["inputs"].items():
        raw = blob(head, name)
        require(digest(raw) == expected["sha256"]
                and mode(head, name) == expected["git_mode"],
                "A current controller Git input is stale: " + name)
        current_git[name] = expected
    originals, projected, original_rows = {}, {}, {}
    for name, row in fixed["source_files"].items():
        raw = blob(APP, name)
        require(raw == (ROOT / name).read_bytes()
                and len(raw) == row["bytes"] and digest(raw) == row["sha256"]
                and git("rev-parse", APP + ":" + name).decode().strip() == row["git_blob"],
                "An original App-source Swift declaration changed")
        originals[name] = raw
        changed = bytearray(raw)
        if name == "AnyTypeTests/Pinkha/TextBlockFocusLifecycleTests.swift":
            for patch in fixed["attribute_patches"]:
                start = patch["offset"]
                old, new = patch["before"].encode(), patch["after"].encode()
                require(raw[start:start + len(old)] == old and len(old) == len(new)
                        and new == bytes(10 if item == 10 else 32 for item in old),
                        "An existing registration-only patch changed")
                changed[start:start + len(old)] = new
            require(digest(changed) == fixed["projected_editor_sha256"],
                    "The unchanged projected editor bytes differ")
        projected[name] = bytes(changed)
        original_rows[name] = row
    token = rb"\b(?:[A-Z][A-Za-z0-9_]*Mock|Mock[A-Z][A-Za-z0-9_]*)\b"
    declaration = rb"\b(?:class|struct|enum|typealias)\s+([A-Za-z_][A-Za-z0-9_]*)"
    def missing(names):
        raw = b"\n".join(originals[name] for name in names)
        return set(re.findall(token, raw)) - set(re.findall(declaration, raw))
    old_missing = missing(old_fixed["source_files"])
    new_missing = missing(fixed["source_files"])
    require(old_missing == {b"BlockMarkupChangerMock"} and not new_missing,
            "The bounded mock-name declaration closure is not repaired")
    require(sum(raw.count(b"@Test(") for raw in originals.values()) == 30
            and sum(raw.count(b"@Test(") for raw in projected.values()) == 23
            and b"@Test" not in originals[MOCK]
            and fixed["selection"] == old_fixed["selection"]
            and len(fixed["selection"]["selected"]) == 23
            and len(fixed["selection"]["excluded"]) == 7
            and fixed["required_argument_cases"] == old_fixed["required_argument_cases"] == 32,
            "The original test registration/argument scope changed")
    old_tree, new_tree = ast.parse(blob(BASE, GENERATOR)), ast.parse((ROOT / GENERATOR).read_bytes())
    old_functions = {node.name: ast.dump(node, include_attributes=False)
                     for node in old_tree.body if isinstance(node, ast.FunctionDef)}
    new_functions = {node.name: ast.dump(node, include_attributes=False)
                     for node in new_tree.body if isinstance(node, ast.FunctionDef)}
    unchanged = sorted(name for name in old_functions if old_functions[name] == new_functions[name])
    require(set(old_functions) == set(new_functions)
            and set(old_functions) - set(unchanged) == {"contract", "projected_sources"},
            "An unrelated generator function changed")
    require({"project_value", "write_project", "descriptor_value",
             "require_pending_registration"}.issubset(unchanged),
            "Target membership, host/runtime or enumeration code changed")
    final_head = git("rev-parse", "HEAD").decode().strip()
    require(final_head == head and not git("status", "--porcelain"),
            "The source writer changed during its read-only check")
    after = resource()
    print(json.dumps({
        "protocol": "sdk06-projection-mock-source-check-v1", "status": "PASS_SOURCE_ONLY",
        "source": head, "base": BASE, "original_app_source": APP,
        "physical_git_inputs": checked, "current_controller_git_inputs": current_git,
        "current_controller_physical_closure_checked": False,
        "original_swift_sources": original_rows,
        "old_missing_mock_names": sorted(name.decode() for name in old_missing),
        "new_missing_mock_names": [], "mock_name_check_is_a_bounded_lexical_check": True,
        "unchanged_generator_functions": unchanged,
        "source_registrations_before": 30, "projected_source_registrations": 23,
        "excluded_registration_metadata": 7, "required_argument_cases": 32,
        "compiled_enumeration_proven": False, "swift_typecheck_proven": False,
        "repository_imports": 0, "test_methods_executed": 0, "builds": 0,
        "resource_before": before, "resource_after": after,
    }, sort_keys=True))

if __name__ == "__main__":
    main()
