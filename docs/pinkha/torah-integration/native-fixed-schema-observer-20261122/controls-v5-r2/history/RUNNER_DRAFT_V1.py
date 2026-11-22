#!/usr/bin/env python3
"""Run only the newly reviewed original Heart observer controls on macOS ARM64.

Requires a fresh original Heart checkout and the separately reviewed V5 packets.
This does not build an iOS framework, invoke old regression packages, provision
production schema, or use an existing wallet/account. Native fixture setup owns
a disposable LocalOnly original application and removes it through AccountStop.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time

PIN = "d98420b1113536afd08cde6de9a5816f6d27ffff"
GO_VERSION = "go1.26.5"
PACKAGES = {
    "native": ("./core/block/object/objectcreator", "TestOtzariaFixedSchemaNativeObserverV5"),
    "strict": ("./core/block/source/sourceimpl", "TestOtzariaFixedSchemaStrictReplayV5"),
}
INPUT_FIELDS = (
    "GoFiles", "CgoFiles", "CFiles", "CXXFiles", "MFiles", "HFiles", "FFiles",
    "SFiles", "SwigFiles", "SwigCXXFiles", "SysoFiles", "EmbedFiles",
    "TestGoFiles", "XTestGoFiles", "TestEmbedFiles", "XTestEmbedFiles",
)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def safe_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise RuntimeError("packet path escapes its owned root")
    return path


def check_file(root, entry):
    path = safe_path(root, entry.get("retained_path", entry["path"]))
    if not path.is_file() or digest(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
        raise RuntimeError("sealed input differs: " + entry["path"])
    return path


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True, timeout=30).rstrip("\r\n")


class Commands:
    def __init__(self, evidence, env):
        self.evidence, self.env, self.items = evidence, env, []

    def run(self, label, argv, cwd, seconds):
        index = len(self.items) + 1
        stdout = self.evidence / f"{index:02d}-{label}.stdout"
        stderr = self.evidence / f"{index:02d}-{label}.stderr"
        started = time.time()
        timed_out = False
        with stdout.open("wb") as out, stderr.open("wb") as err:
            process = subprocess.Popen(argv, cwd=cwd, env=self.env, stdout=out, stderr=err, start_new_session=True)
            try:
                code = process.wait(timeout=seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                # Only this freshly spawned owned process group is stopped.
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    code = process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    code = process.wait(timeout=10)
        item = {
            "label": label, "argv": [str(x) for x in argv], "cwd": str(cwd),
            "pid": process.pid, "returncode": code, "timed_out": timed_out,
            "duration_seconds": round(time.time() - started, 3),
            "stdout": stdout.name, "stdout_sha256": digest(stdout),
            "stderr": stderr.name, "stderr_sha256": digest(stderr),
        }
        self.items.append(item)
        write_json(self.evidence / "COMMANDS.json", self.items)
        print(json.dumps({"stage": label, "returncode": code, "timed_out": timed_out}), flush=True)
        return code, stdout, stderr

    def require(self, label, argv, cwd, seconds):
        code, stdout, stderr = self.run(label, argv, cwd, seconds)
        if code:
            raise RuntimeError("owned command failed: " + label)
        return stdout


def read_json_stream(path):
    text = path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    offset = 0
    values = []
    while offset < len(text):
        while offset < len(text) and text[offset].isspace():
            offset += 1
        if offset == len(text):
            break
        value, offset = decoder.raw_decode(text, offset)
        values.append(value)
    return values


def dependency_inputs(listing):
    packages, files = [], {}
    for package in read_json_stream(listing):
        if package.get("Error") or package.get("DepsErrors"):
            raise RuntimeError("original Go dependency resolution reported errors")
        directory = Path(package["Dir"]) if package.get("Dir") else None
        packages.append({
            "import_path": package.get("ImportPath"), "for_test": package.get("ForTest"),
            "directory": str(directory) if directory else None, "module": package.get("Module"),
        })
        if directory:
            for field in INPUT_FIELDS:
                for relative in package.get(field, []):
                    path = (directory / relative).resolve()
                    if not path.is_file():
                        raise RuntimeError("declared native compilation input is missing: " + str(path))
                    files[str(path)] = {"path": str(path), "bytes": path.stat().st_size, "sha256": digest(path)}
    return {
        "scope": "Actual original Go-declared package/test/embed/native source inputs; generated cgo outputs and complete Apple SDK headers are not claimed.",
        "packages": packages, "files": sorted(files.values(), key=lambda x: x["path"]),
    }


def validate_cases(path, parent, expected):
    terminal, started, packages, unexpected = {}, [], [], []
    for line in path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        name, action = event.get("Test"), event.get("Action")
        if not name:
            if action in ("pass", "fail", "skip"):
                packages.append(action)
            continue
        if name != parent and name not in {parent + "/" + item for item in expected}:
            unexpected.append(name)
        if action == "run":
            started.append(name)
        if action in ("pass", "fail", "skip"):
            if name in terminal:
                raise RuntimeError("duplicate terminal native test event")
            terminal[name] = action
    wanted = [parent] + [parent + "/" + item for item in expected]
    passed = not unexpected and sorted(started) == sorted(wanted) and terminal == {name: "pass" for name in wanted} and packages == ["pass"]
    return {"pass": passed, "expected": wanted, "started": started, "terminal": terminal, "package_terminal": packages, "unexpected": unexpected}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--controls", required=True, type=Path)
    parser.add_argument("--execution-manifest-sha256", required=True)
    parser.add_argument("--heart", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--go", default="go")
    args = parser.parse_args()
    control, source, controls, heart = (p.resolve() for p in (args.control_root, args.source, args.controls, args.heart))
    evidence, work = args.evidence.resolve(), args.work.resolve()
    if evidence.exists() or work.exists():
        raise RuntimeError("fresh owned evidence/work paths are required")
    if not source.is_relative_to(control) or not controls.is_relative_to(control):
        raise RuntimeError("both sealed packets must belong to the exact control checkout")
    if git(control, "rev-parse", "HEAD") != args.control_head:
        raise RuntimeError("wrong control commit")
    if git(heart, "rev-parse", "HEAD") != PIN or git(heart, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("fresh exact original Heart checkout required")
    manifest_path = controls / "EXECUTION_INPUTS.json"
    if digest(manifest_path) != args.execution_manifest_sha256:
        raise RuntimeError("unreviewed execution manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in manifest["control_inputs"]:
        check_file(controls, entry)
    if digest(source / "SOURCE_REVIEW_INDEX.json") != manifest["source_index_sha256"]:
        raise RuntimeError("wrong reviewed V5 source index")
    source_index = json.loads((source / "SOURCE_REVIEW_INDEX.json").read_text(encoding="utf-8"))
    for entry in source_index["files"]:
        check_file(source, entry)
    source_manifest = json.loads((source / "SOURCE_MANIFEST.json").read_text(encoding="utf-8"))
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("the reviewed real-runtime route requires actual macOS ARM64")
    evidence.mkdir(parents=True)
    work.mkdir(parents=True)
    # Preserve the real system HOME/PATH. Do not forward CI credentials or arbitrary
    # API keys to the disposable native runtime; no environment values are logged.
    allowed_env = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT", "GOCACHE", "GOMODCACHE")
    env = {key: os.environ[key] for key in allowed_env if key in os.environ}
    env.update({"CGO_ENABLED": "1", "GOMAXPROCS": "2", "GOTOOLCHAIN": "local", "GOWORK": "off", "GOFLAGS": "-mod=readonly"})
    commands = Commands(evidence, env)
    result = {
        "status": "STARTED_NOT_ACCEPTED", "heart_base": PIN, "control_head": args.control_head,
        "source_index_sha256": manifest["source_index_sha256"],
        "execution_manifest_sha256": digest(manifest_path), "tests": {},
        "native_schema_writes_by_observer": False, "ios_build": False,
        "scope": "Disposable genuine original LocalOnly Heart runtime; no production registration/repair, annotation authority/receipt or ACK.",
    }
    write_json(evidence / "RESULT.json", result)
    success = False
    try:
        original_module_hashes = {p: digest(heart / p) for p in ("go.mod", "go.sum", "tantivity_sha256.txt")}
        if original_module_hashes != manifest["original_module_hashes"]:
            raise RuntimeError("original module/native checksum inputs differ")
        go_binary = shutil.which(args.go)
        if not go_binary:
            raise RuntimeError("actual pinned Go binary unavailable")
        version = commands.require("go-version", [args.go, "version"], heart, 30).read_text().strip()
        if version != "go version " + GO_VERSION + " darwin/arm64":
            raise RuntimeError("wrong actual Go toolchain")
        result["go"] = {"version": version, "path": str(Path(go_binary).resolve()), "sha256": digest(Path(go_binary).resolve())}
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], heart, 30).read_text().splitlines()
        if not xcode or not xcode[0].startswith("Xcode 27"):
            raise RuntimeError("the reviewed native compiler route requires Xcode 27")
        commands.require("macos-sdk-version", ["xcrun", "--sdk", "macosx", "--show-sdk-version"], heart, 30)
        commands.require("clang-version", ["xcrun", "--sdk", "macosx", "clang", "--version"], heart, 30)

        patch = check_file(controls, manifest["r14_patch"])
        inventory_path = check_file(controls, manifest["r14_inventory"])
        inventory = json.loads(inventory_path.read_text())
        if inventory["heart_sha"] != PIN or inventory["patch_sha256"] != digest(patch):
            raise RuntimeError("original r14 inventory mismatch")
        commands.require("r14-apply-check", ["git", "apply", "--check", str(patch)], heart, 30)
        commands.require("r14-apply", ["git", "apply", str(patch)], heart, 30)
        for entry in inventory["files"]:
            if digest(heart / entry["path"]) != entry["after_sha256"]:
                raise RuntimeError("exact original r14 output differs: " + entry["path"])
        candidate_patch = source / "CANDIDATE.patch"
        commands.require("observer-apply-check", ["git", "apply", "--check", str(candidate_patch)], heart, 30)
        commands.require("observer-apply", ["git", "apply", str(candidate_patch)], heart, 30)
        compiled_product_inputs = []
        for entry in source_manifest["candidate"]:
            path = heart / entry["path"]
            if digest(path) != entry["sha256"]:
                raise RuntimeError("composed product source differs")
            compiled_product_inputs.append({"path": entry["path"], "sha256": digest(path), "bytes": path.stat().st_size})
        for entry in manifest["test_sources"]:
            destination = heart / entry["path"]
            if destination.exists():
                raise RuntimeError("new native test source already exists")
            shutil.copyfile(check_file(controls, entry), destination)
            compiled_product_inputs.append({"path": entry["path"], "sha256": digest(destination), "bytes": destination.stat().st_size})
        allowed_paths = {e["path"] for e in inventory["files"]} | {e["path"] for e in compiled_product_inputs}
        changed = git(heart, "status", "--porcelain", "--untracked-files=all").splitlines()
        if any(line[:2] not in (" M", "??") or line[3:] not in allowed_paths for line in changed):
            raise RuntimeError("unexpected composed Heart working change")
        result["composed_product_and_test_inputs"] = compiled_product_inputs
        result["r14_patch_sha256"] = digest(patch)
        write_json(evidence / "RESULT.json", result)

        helper = check_file(controls, manifest["original_setup_helper"])
        spec = importlib.util.spec_from_file_location("reviewed_original_heart_setup", helper)
        original_setup = importlib.util.module_from_spec(spec)
        sys.dont_write_bytecode = True
        spec.loader.exec_module(original_setup)
        # Only this pinned original download/checksum/extraction function is reused.
        # Its main(), old package list, gomobile and framework build are never called.
        prior_socket_timeout = socket.getdefaulttimeout()
        socket.setdefaulttimeout(60)
        try:
            result["tantivy"] = original_setup.fetch_tantivy(heart, "darwin-arm64")
        finally:
            socket.setdefaulttimeout(prior_socket_timeout)
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/darwin-arm64")
        listing = commands.require("declared-dependency-inputs", [args.go, "list", "-deps", "-test", "-json", *[v[0] for v in PACKAGES.values()]], heart, 1200)
        closure = dependency_inputs(listing)
        write_json(evidence / "DECLARED_NATIVE_INPUTS.json", closure)
        result["declared_native_inputs_sha256"] = digest(evidence / "DECLARED_NATIVE_INPUTS.json")
        result["declared_native_input_count"] = len(closure["files"])

        for name, (package, parent) in PACKAGES.items():
            binary = work / (name + ".test")
            code, _, _ = commands.run("compile-" + name, [args.go, "test", "-c", "-p", "2", "-o", str(binary), package], heart, 2400)
            if code:
                result["tests"][name] = {"compiled": False, "pass": False}
                write_json(evidence / "RESULT.json", result)
                continue
            buildinfo = commands.require("buildinfo-" + name, [args.go, "version", "-m", str(binary)], heart, 30)
            code, output, _ = commands.run("run-" + name, [
                args.go, "tool", "test2json", "-t", "-p", package, str(binary),
                "-test.v=test2json", "-test.count=1", "-test.run=^" + parent + "$", "-test.timeout=12m",
            ], heart, 780)
            actual = validate_cases(output, parent, manifest["expected_cases"][name])
            actual.update({"compiled": True, "binary_sha256": digest(binary), "binary_bytes": binary.stat().st_size,
                           "buildinfo_sha256": digest(buildinfo), "process_returncode": code})
            actual["pass"] = actual["pass"] and code == 0
            result["tests"][name] = actual
            write_json(evidence / "RESULT.json", result)

        for entry in compiled_product_inputs:
            if digest(heart / entry["path"]) != entry["sha256"]:
                raise RuntimeError("native product/test source changed during execution")
        if {p: digest(heart / p) for p in original_module_hashes} != original_module_hashes:
            raise RuntimeError("original module/native checksum input changed")
        for entry in closure["files"]:
            if digest(entry["path"]) != entry["sha256"]:
                raise RuntimeError("declared native source input changed during execution")
        result["post_execution_source_recheck"] = True
        success = set(result["tests"]) == set(PACKAGES) and all(v["pass"] for v in result["tests"].values())
        result["status"] = "PASS" if success else "FAIL"
    except Exception as error:
        result["status"] = "FAIL"
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
    finally:
        result["commands"] = len(commands.items)
        result["finished_unix"] = time.time()
        write_json(evidence / "RESULT.json", result)
        payloads = [
            {"path": p.name, "bytes": p.stat().st_size, "sha256": digest(p)}
            for p in sorted(evidence.iterdir()) if p.is_file() and p.name != "EVIDENCE_INDEX.json"
        ]
        write_json(evidence / "EVIDENCE_INDEX.json", {
            "scope": "Only result/commands/source closure and captured command streams; no native account directory or wallet is included.",
            "files": payloads,
        })
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
