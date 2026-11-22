#!/usr/bin/env python3
"""Compile the frozen original importer target; never execute its test binary.

No original importer, native schema, or portable observation tests are replayed.
The owned command lifecycle and declared-input readers retain the proven native
schema lane implementation. Only the selected package/compile-only main differ.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time

PIN = "d98420b1113536afd08cde6de9a5816f6d27ffff"
ORIGIN = "20cb8998211eaefa5ddb00ef60ff2462dd3271e9"
ORIGIN_TREE = "be05778c6a9e6412d181ced642694daee3baf30b"
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
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


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
    def __init__(self, evidence, env, deadline):
        self.evidence, self.env, self.deadline = evidence, env, deadline
        self.monotonic_deadline = time.monotonic() + max(0.0, deadline - time.time())
        self.items = []
        self.owned_groups_drained = True

    def persist(self):
        write_json(self.evidence / "COMMANDS.json", self.items)

    def cleanup_event(self, item, event, **values):
        item.setdefault("cleanup", []).append({"event": event, "unix": time.time(), **values})
        # Cleanup must still happen if receipt storage itself fails.
        try:
            self.persist()
        except Exception as error:
            item["receipt_error_type"] = type(error).__name__

    @staticmethod
    def group_exists(pgid):
        try:
            os.killpg(pgid, 0)
            return True
        except ProcessLookupError:
            return False

    def signal_group(self, item, sig):
        self.cleanup_event(item, "SIGNAL_REQUESTED", signal=int(sig))
        try:
            os.killpg(item["process_group_id"], sig)
            self.cleanup_event(item, "SIGNAL_SENT", signal=int(sig))
        except ProcessLookupError:
            self.cleanup_event(item, "GROUP_ALREADY_ABSENT", signal=int(sig))

    def drain(self, item, process, terminate):
        pgid = item["process_group_id"]
        if terminate:
            self.signal_group(item, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                pass
        # A parent that exits after TERM may leave an ignoring descendant.
        # Check the originally owned group even when that parent has exited.
        if self.group_exists(pgid):
            self.signal_group(item, signal.SIGKILL)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.cleanup_event(item, "PARENT_REAP_TIMEOUT")
        deadline = time.monotonic() + 5
        while self.group_exists(pgid) and time.monotonic() < deadline:
            time.sleep(0.1)
        drained = not self.group_exists(pgid)
        self.cleanup_event(item, "OWNED_GROUP_DRAIN_RESULT", drained=drained)
        if not drained:
            self.owned_groups_drained = False
        return drained

    def run(self, label, argv, cwd, seconds):
        index = len(self.items) + 1
        stdout = self.evidence / f"{index:02d}-{label}.stdout"
        stderr = self.evidence / f"{index:02d}-{label}.stderr"
        started = time.time()
        effective_seconds = min(float(seconds), max(0.0, self.monotonic_deadline - time.monotonic()))
        item = {
            "label": label, "argv": [str(x) for x in argv], "cwd": str(cwd),
            "status": "STARTING", "started_unix": started, "pid": None,
            "process_group_id": None, "start_new_session": True,
            "requested_timeout_seconds": seconds, "effective_timeout_seconds": effective_seconds,
            "absolute_command_deadline_unix": self.deadline,
            "returncode": None, "effective_returncode": None, "timed_out": False,
            "stdout": stdout.name, "stderr": stderr.name, "cleanup": [],
        }
        self.items.append(item)
        self.persist()  # Actionable start intent exists before Popen.
        process = None
        try:
            with stdout.open("wb") as out, stderr.open("wb") as err:
                if effective_seconds <= 0:
                    item.update({"status": "REFUSED_GLOBAL_DEADLINE", "effective_returncode": 124, "budget_exhausted": True})
                else:
                    process = subprocess.Popen(argv, cwd=cwd, env=self.env, stdout=out, stderr=err, start_new_session=True)
                    # POSIX start_new_session creates this owned process group.
                    item.update({"status": "RUNNING", "pid": process.pid, "process_group_id": process.pid,
                                 "child_started_unix": time.time()})
                    self.persist()  # Persist ownership BEFORE awaiting the child.
                    try:
                        remaining = min(effective_seconds, max(0.0, self.monotonic_deadline - time.monotonic()))
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(argv, remaining)
                        code = process.wait(timeout=remaining)
                    except subprocess.TimeoutExpired:
                        item.update({"status": "TIMED_OUT", "timed_out": True})
                        self.persist()
                        self.drain(item, process, terminate=True)
                        code = process.returncode
                    else:
                        if self.group_exists(process.pid):
                            item["unexpected_owned_descendants"] = True
                            self.drain(item, process, terminate=False)
                        else:
                            self.cleanup_event(item, "OWNED_GROUP_ABSENT_AFTER_WAIT", drained=True)
                    effective_code = 124 if item["timed_out"] else (code if code is not None else 125)
                    if item.get("unexpected_owned_descendants") or not self.owned_groups_drained:
                        effective_code = effective_code or 125
                    item.update({"status": "TERMINAL", "returncode": code, "effective_returncode": effective_code})
        except BaseException as error:
            item.update({"status": "INTERRUPTED_OR_FAILED", "error_type": type(error).__name__,
                         "effective_returncode": 125})
            if process is not None:
                try:
                    self.drain(item, process, terminate=True)
                except Exception as cleanup_error:
                    self.owned_groups_drained = False
                    self.cleanup_event(item, "DRAIN_ERROR", error_type=type(cleanup_error).__name__)
                item["returncode"] = process.returncode
            raise
        finally:
            item["duration_seconds"] = round(time.time() - started, 3)
            for name, path in (("stdout", stdout), ("stderr", stderr)):
                if path.exists():
                    item[name + "_sha256"] = digest(path)
            self.persist()
        print(json.dumps({"stage": label, "returncode": item["returncode"],
                          "effective_returncode": item["effective_returncode"], "timed_out": item["timed_out"]}), flush=True)
        return item["effective_returncode"], stdout, stderr

    def require(self, label, argv, cwd, seconds):
        code, stdout, stderr = self.run(label, argv, cwd, seconds)
        if code or self.items[-1]["timed_out"]:
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


def dependency_inputs(listing, heart, expected_inputs):
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
    selected = {"github.com/anyproto/anytype-heart/core/block/import"}
    present = {entry["import_path"] for entry in packages}
    if not files or not packages or not selected.issubset(present):
        raise RuntimeError("empty/incomplete original selected-package dependency closure")
    coverage = []
    for entry in expected_inputs:
        path = str((heart / entry["path"]).resolve())
        actual = files.get(path)
        if actual is None or actual["sha256"] != entry["sha256"]:
            raise RuntimeError("declared closure omits/differs from reviewed product/test input: " + entry["path"])
        coverage.append({"path": entry["path"], "sha256": actual["sha256"]})
    return {
        "selected_original_packages": sorted(selected), "required_product_test_coverage": coverage,
        "scope": "Actual original Go-declared package/test/embed/native source inputs; generated cgo outputs and complete Apple SDK headers are not claimed.",
        "packages": packages, "files": sorted(files.values(), key=lambda x: x["path"]),
    }


def native_library_inputs(heart):
    directory = heart / "deps/libs/darwin-arm64"
    archive = heart / "deps/libs/darwin-arm64.tar.gz"
    if not directory.is_dir() or not archive.is_file():
        raise RuntimeError("actual original Tantivy archive/library directory is absent")
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise RuntimeError("unexpected native library symlink")
        if path.is_file():
            files.append({"path": path.relative_to(directory).as_posix(), "bytes": path.stat().st_size, "sha256": digest(path)})
    if not files:
        raise RuntimeError("actual extracted native dependency set is empty")
    return {"architecture": "darwin-arm64", "archive_sha256": digest(archive), "files": files}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--execution-manifest-sha256", required=True)
    parser.add_argument("--heart", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control, packet, heart, work, evidence = (p.resolve() for p in (
        args.control_root, args.packet, args.heart, args.work, args.evidence))
    if work.exists() or evidence.exists():
        raise RuntimeError("fresh owned work/evidence paths are required")
    if not all(p.is_relative_to(control) and p != control for p in (packet, heart, work, evidence)):
        raise RuntimeError("all execution paths must remain in the owned control checkout")
    if any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
           for i, a in enumerate((packet, heart, work, evidence))
           for b in (packet, heart, work, evidence)[i + 1:]):
        raise RuntimeError("packet, Heart, work, and evidence roots must be disjoint")
    evidence.mkdir(parents=True)
    work.mkdir(parents=True)
    owned_temp = work / "compiler-temp"
    owned_temp.mkdir()
    allowed_env = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT", "GOCACHE", "GOMODCACHE")
    env = {key: os.environ[key] for key in allowed_env if key in os.environ}
    env.update({"TMPDIR": str(owned_temp), "CGO_ENABLED": "1", "GOMAXPROCS": "2",
                "GOTOOLCHAIN": "local", "GOWORK": "off", "GOENV": "off", "GOFLAGS": "-mod=readonly"})
    commands = Commands(evidence, env, args.job_deadline_unix - 180)
    result = {
        "status": "STARTED_NOT_ACCEPTED", "control_head": args.control_head,
        "heart_base": PIN, "origin_commit": ORIGIN, "origin_packet_tree": ORIGIN_TREE,
        "job_deadline_unix": args.job_deadline_unix, "command_deadline_unix": commands.deadline,
        "tests_executed": 0, "native_imports_executed": 0, "test_binary_executed": False,
        "prior_unit_cases_not_replayed": 50,
        "prior_unit_result_sha256": "cdd51f4581c2d78bacc072cf81956b51f94a8370c3e1d57f22e95ee2fd8d1cfb",
        "scope": "Original-module source/link compatibility only; no import execution, lifetime proof, mapping authority, semantic native readback, or ACK.",
    }
    write_json(evidence / "RESULT.json", result)
    success = False
    try:
        if args.job_deadline_unix > time.time() + 7000 or commands.deadline <= time.time():
            raise RuntimeError("invalid/exhausted absolute workflow budget")
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("actual Darwin arm64 original native toolchain is required")
        if git(control, "rev-parse", "HEAD") != args.control_head:
            raise RuntimeError("control checkout does not match the actual workflow head")
        if git(heart, "rev-parse", "HEAD") != PIN or git(heart, "status", "--porcelain", "--untracked-files=all"):
            raise RuntimeError("fresh immutable original Heart checkout required")
        manifest_path = packet / "EXECUTION_INPUTS.json"
        if digest(manifest_path) != args.execution_manifest_sha256:
            raise RuntimeError("execution manifest differs from the reviewed workflow binding")
        manifest = json.loads(manifest_path.read_bytes())
        if manifest["heart_base"] != PIN or manifest["origin_commit"] != ORIGIN or manifest["origin_packet_tree"] != ORIGIN_TREE:
            raise RuntimeError("unexpected native/origin source binding")
        for entry in manifest["gate_inputs"]:
            check_file(packet, entry)
        origin_path = manifest["origin_packet_path"]
        origin = safe_path(control, origin_path)
        if git(control, "rev-parse", "HEAD:" + origin_path) != ORIGIN_TREE:
            raise RuntimeError("the frozen 94-file origin packet changed")
        # The tree binds the entire retained origin packet; individual checks also
        # bind the exact bytes read and installed by this process.
        for entry in manifest["origin_inputs"]:
            check_file(origin, entry)
        bindings = json.loads((origin / "composition/r14/SOURCE_BINDINGS.json").read_bytes())
        if len(bindings) != 6 or {e["path"]: e["sha256"] for e in bindings} != manifest["six_product_hashes"]:
            raise RuntimeError("unexpected six-file r14 composition")
        original_module_hashes = {p: digest(heart / p) for p in manifest["original_module_hashes"]}
        if original_module_hashes != manifest["original_module_hashes"]:
            raise RuntimeError("original module/native checksum inputs differ")
        result["execution_manifest_sha256"] = digest(manifest_path)
        result["original_module_hashes"] = original_module_hashes
        result["gate_input_readback"] = manifest["gate_inputs"]
        result["origin_input_readback"] = manifest["origin_inputs"]
        write_json(evidence / "RESULT.json", result)

        go_binary = shutil.which("go")
        if not go_binary:
            raise RuntimeError("the original Go toolchain is absent")
        go_binary = str(Path(go_binary).resolve())
        version = commands.require("go-version", [go_binary, "version"], heart, 30).read_text().strip()
        if version != "go version go1.26.5 darwin/arm64":
            raise RuntimeError("the actual Go version/architecture differs")
        result["go"] = {"version": version, "path": go_binary, "sha256": digest(go_binary)}
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], heart, 30).read_text().splitlines()
        if not xcode or not xcode[0].startswith("Xcode 27"):
            raise RuntimeError("the reviewed native compiler route requires Xcode 27")
        commands.require("macos-sdk-version", ["xcrun", "--sdk", "macosx", "--show-sdk-version"], heart, 30)
        commands.require("clang-version", ["xcrun", "--sdk", "macosx", "clang", "--version"], heart, 30)

        patch = check_file(control, manifest["r14_patch"])
        inventory_path = check_file(control, manifest["r14_inventory"])
        inventory = json.loads(inventory_path.read_bytes())
        if inventory["heart_sha"] != PIN or inventory["patch_sha256"] != digest(patch):
            raise RuntimeError("original r14 inventory differs")
        commands.require("r14-apply-check", ["git", "apply", "--check", str(patch)], heart, 30)
        commands.require("r14-apply", ["git", "apply", str(patch)], heart, 30)
        for entry in inventory["files"]:
            if digest(safe_path(heart, entry["path"])) != entry["after_sha256"]:
                raise RuntimeError("exact original r14 afterimage differs: " + entry["path"])
        commands.require("install-frozen-origin-overlay", [
            sys.executable, "-I", str(origin / "install_native_sources.py"),
            "--source-root", str(heart), "--receipt", str(evidence / "SOURCE_OVERLAY.json"),
        ], heart, 30)
        for entry in bindings:
            if digest(heart / entry["path"]) != entry["sha256"]:
                raise RuntimeError("installed r14 composition differs: " + entry["path"])
        # The original 35-file r14 projection is retained byte-exact except for
        # the reviewed composed processor. No observer/schema overlay is applied.
        composed_hashes = {e["path"]: e["after_sha256"] for e in inventory["files"]}
        composed_hashes.update(manifest["six_product_hashes"])
        changed = git(heart, "status", "--porcelain", "--untracked-files=all").splitlines()
        if any(line[:2] not in (" M", "??") or line[3:] not in composed_hashes for line in changed):
            raise RuntimeError("unexpected native source change after composition")
        for path, sha in composed_hashes.items():
            if digest(heart / path) != sha:
                raise RuntimeError("unreviewed r14/source composition at " + path)
        gofmt = Path(go_binary).with_name("gofmt")
        formatting = commands.require("source-format-equality", [str(gofmt), "-l", *[str(heart / e["path"]) for e in bindings]], heart, 30)
        if formatting.read_text().strip():
            raise RuntimeError("frozen six-file source differs from pinned gofmt; no automatic rewrite")
        result["gofmt"] = {"sha256": digest(gofmt), "six_source_files_unchanged": True}
        result["composed_source_hashes"] = composed_hashes
        write_json(evidence / "RESULT.json", result)

        helper = check_file(packet, manifest["original_setup_helper"])
        child = check_file(packet, manifest["original_setup_child"])
        commands.require("original-tantivy-setup", [
            sys.executable, "-I", str(child), "--heart", str(heart), "--helper", str(helper),
            "--helper-sha256", manifest["original_setup_helper"]["sha256"],
            "--receipt", str(evidence / "TANTIVY_SETUP.json"),
        ], heart, 600)
        setup = json.loads((evidence / "TANTIVY_SETUP.json").read_bytes())
        native_before = native_library_inputs(heart)
        if native_before["archive_sha256"] != setup["archive_sha256"] or native_before != manifest["expected_tantivy_inputs"]:
            raise RuntimeError("actual original Tantivy archive/library bindings differ")
        write_json(evidence / "TANTIVY_INPUTS_BEFORE.json", native_before)
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/darwin-arm64")
        result["compiler_environment"] = {k: env[k] for k in (
            "CGO_ENABLED", "GOMAXPROCS", "GOTOOLCHAIN", "GOWORK", "GOENV", "GOFLAGS", "CGO_LDFLAGS")}
        listing = commands.require("declared-dependency-inputs", [go_binary, "list", "-deps", "-test", "-json", "./core/block/import"], heart, 1200)
        closure = dependency_inputs(listing, heart, bindings)
        if len(closure["required_product_test_coverage"]) != 6:
            raise RuntimeError("the original dependency closure does not include all six changed source files")
        write_json(evidence / "DECLARED_NATIVE_INPUTS.json", closure)
        result["declared_native_inputs_sha256"] = digest(evidence / "DECLARED_NATIVE_INPUTS.json")
        result["declared_native_input_count"] = len(closure["files"])
        result["iosrepacks_scope"] = "No iosrepacks bootstrap is added; only actual original Go-declared inputs and original Tantivy linkage are qualified."
        binary = work / "original-importer.test"
        result["compile_command"] = [go_binary, "test", "-c", "-p", "2", "-o", str(binary), "./core/block/import"]
        write_json(evidence / "RESULT.json", result)
        commands.require("compile-original-importer", result["compile_command"], heart, 3600)
        if not binary.is_file() or binary.stat().st_size == 0:
            raise RuntimeError("the original importer compiler produced no binary")
        result["compiled_binary"] = {
            "path": str(binary), "bytes": binary.stat().st_size, "sha256": digest(binary),
            "executed": False,
            "evidence_scope": "Runner-observed output hash; executable bytes remain in the owned work directory, outside the uploaded evidence.",
        }
        commands.require("compiled-binary-buildinfo", [go_binary, "version", "-m", str(binary)], heart, 30)
        # No code path executes the binary, selects a test, or initializes a Heart
        # application. go version -m reads its build metadata without running it.
        for entry in closure["files"]:
            if digest(entry["path"]) != entry["sha256"]:
                raise RuntimeError("declared original compilation input changed: " + entry["path"])
        for path, sha in composed_hashes.items():
            if digest(heart / path) != sha:
                raise RuntimeError("composed product input changed during compilation")
        if {p: digest(heart / p) for p in original_module_hashes} != original_module_hashes:
            raise RuntimeError("original module/native checksum inputs changed")
        native_after = native_library_inputs(heart)
        write_json(evidence / "TANTIVY_INPUTS_AFTER.json", native_after)
        if native_after != native_before or digest(binary) != result["compiled_binary"]["sha256"]:
            raise RuntimeError("native dependency or compiled binary changed after linking")
        for entry in manifest["gate_inputs"]:
            check_file(packet, entry)
        for entry in manifest["origin_inputs"]:
            check_file(origin, entry)
        result["post_compile_input_recheck"] = True
        result["status"], success = "PASS_COMPILE_ONLY", True
    except BaseException as error:
        result["status"], success = "FAIL", False
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
    finally:
        # Only compiler temporary files under the new owned work root are removed.
        # Preserve every file if an owned subprocess group has not drained.
        try:
            if not commands.owned_groups_drained:
                raise RuntimeError("owned compiler group did not drain; preserve temporary state")
            shutil.rmtree(owned_temp)
            result["owned_compiler_temp_removed"] = True
        except Exception as error:
            result["owned_compiler_temp_removed"] = False
            result["cleanup_error_type"] = type(error).__name__
            result["status"], success = "FAIL", False
        result["commands"] = len(commands.items)
        result["finished_unix"] = time.time()
        write_json(evidence / "RESULT.json", result)
        write_json(evidence / "EVIDENCE_INDEX.json", {
            "scope": "Source/dependency/toolchain bindings and actual compiler streams; no binary execution or native account state.",
            "files": [{"path": p.name, "bytes": p.stat().st_size, "sha256": digest(p)}
                      for p in sorted(evidence.iterdir()) if p.is_file() and p.name != "EVIDENCE_INDEX.json"],
        })
    return 0 if success else 1


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("workflow interruption signal " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
