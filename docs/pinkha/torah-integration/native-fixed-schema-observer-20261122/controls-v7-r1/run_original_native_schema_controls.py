#!/usr/bin/env python3
"""Run only the newly reviewed original Heart observer controls on macOS ARM64.

Requires a fresh original Heart checkout and unchanged reviewed V5 plus V6 product.
Only the TWO unresolved genuine counter cases execute. Strict12, original13,
and V6 eighteen passing cases are retained without replay.
This does not build an iOS framework, invoke old regression packages, provision
production schema, or use an existing wallet/account. Native fixture setup owns
a disposable LocalOnly original application and removes it through AccountStop.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time

PIN = "d98420b1113536afd08cde6de9a5816f6d27ffff"
GO_VERSION = "go1.26.5"
PACKAGES = {
    "native": ("./core/block/object/objectcreator", "TestOtzariaFixedSchemaNativeObserverV5"),
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
    selected = {"github.com/anyproto/anytype-heart/" + package[2:] for package, _ in PACKAGES.values()}
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


def validate_counter_observations(evidence, expected):
    """Verify retained actual row bytes/attempt selection; no alternate native decoder."""
    paths = sorted(evidence.glob("counter-*.json"))
    reports = {case: [] for case in expected}
    if not 2 <= len(paths) <= 6:
        raise RuntimeError("exact two counter cases require one to three observations each")
    for path in paths:
        record = json.loads(path.read_text(encoding="utf-8"))
        case = record.get("Case")
        attempt = record.get("Attempt")
        if (case not in reports or type(attempt) is not int or not 1 <= attempt <= 3 or
                path.name != f"counter-{case}-attempt-{attempt}.json" or
                record.get("Schema") != "otzaria.native-counter-observation/1" or
                record.get("MaximumAttempts") != 3 or type(record.get("ProcessID")) is not int or
                record["ProcessID"] <= 0):
            raise RuntimeError("unexpected counter observation identity/selection")
        reports[case].append((attempt, path, record))
    result = {}
    process_ids = set()
    for case, entries in reports.items():
        entries.sort(key=lambda entry: entry[0])
        if not entries or [entry[0] for entry in entries] != list(range(1, len(entries) + 1)):
            raise RuntimeError("missing/duplicated bounded counter observation")
        first = entries[0][2]
        reference = base64.b64decode(first["CounterBefore"], validate=True)
        if not reference:
            raise RuntimeError("empty genuine counter row")
        for position, (_, path, record) in enumerate(entries):
            process_ids.add(record["ProcessID"])
            if (record.get("Failure") or record.get("ScopeUnchanged") is not True or
                    record.get("CounterUnchanged") is not True or
                    record["Scope"] != first["Scope"] or record["ObjectID"] != first["ObjectID"] or
                    record["ChangeID"] != first["ChangeID"] or record["ExpectedCounter"] != first["ExpectedCounter"] or
                    not record["ObjectID"] or not record["ChangeID"] or
                    base64.b64decode(record["CounterBefore"], validate=True) != reference or
                    base64.b64decode(record["CounterAfter"], validate=True) != reference):
                raise RuntimeError("counter/scope guard did not remain exact")
            if type(record["ExpectedCounter"]) is not int or (
                    case == "ActualLocalZeroCounterAccepted" and record["ExpectedCounter"] != 0) or (
                    case == "NativeComputedRemoteCounterAccepted" and record["ExpectedCounter"] <= 0):
                raise RuntimeError("wrong genuine native counter value")
            snapshots = record["Snapshots"]
            if len(snapshots) != 2:
                raise RuntimeError("two complete original snapshots required")
            decoded = []
            for number, snapshot in enumerate(snapshots, 1):
                if (snapshot["Index"] != number or snapshot["Committed"] is not True or
                        snapshot["Done"] is not True or snapshot["CommitError"] or
                        snapshot["ReadErrors"] or snapshot["TraceErrors"] or not snapshot["Rows"]):
                    raise RuntimeError("native snapshot/read/commit/trace failure")
                rows = {}
                for key, row in snapshot["Rows"].items():
                    raw = base64.b64decode(row["Encoded"], validate=True)
                    if (not raw or key != row["Collection"] + "\0" + row["ID"] or
                            hashlib.sha256(raw).hexdigest() != row["SHA256"]):
                        raise RuntimeError("retained original row identity/hash mismatch")
                    rows[key] = raw
                counter_key = "changes\0" + record["ChangeID"]
                if rows.get(counter_key) != reference:
                    raise RuntimeError("snapshot did not retain exact genuine counter row")
                decoded.append(rows)
            changed = sorted(key for key in set(decoded[0]) | set(decoded[1])
                             if decoded[0].get(key) != decoded[1].get(key))
            differences = record["Differences"] or []
            diff_keys = []
            for difference in differences:
                key = difference["Collection"] + "\0" + difference["ID"]
                diff_keys.append(key)
                left, right = snapshots[0]["Rows"].get(key), snapshots[1]["Rows"].get(key)
                if (difference["FirstPresent"] != (left is not None) or
                        difference["SecondPresent"] != (right is not None) or
                        difference["FirstSHA256"] != (left["SHA256"] if left else "") or
                        difference["SecondSHA256"] != (right["SHA256"] if right else "")):
                    raise RuntimeError("reported snapshot difference does not match retained rows")
                a, b = left["Fields"] if left else {}, right["Fields"] if right else {}
                fields = sorted(field for field in set(a) | set(b) if a.get(field) != b.get(field))
                if (difference["ChangedFields"] or []) != fields:
                    raise RuntimeError("reported field difference does not match original projections")
            if sorted(diff_keys) != changed:
                raise RuntimeError("recorded snapshot delta is incomplete")
            terminal = position == len(entries) - 1
            if terminal:
                if (record["CompleteStableMatch"] is not True or record["RetryAdmitted"] is not False or
                        record["Error"] or record["ExactChangedError"] is not False or
                        record["Disposition"] != 1 or changed):
                    raise RuntimeError("no final complete stable native PersistedMatch")
            elif (record["CompleteStableMatch"] is not False or record["RetryAdmitted"] is not True or
                    record["ExactChangedError"] is not True or record["Disposition"] != 5 or not changed or
                    record["Error"] != "fixed schema context or persisted input changed while reading"):
                raise RuntimeError("retry lacks exact error/disposition/actual native delta")
        result[case] = {
            "attempts": len(entries), "stable_final_match": True,
            "counter_sha256": hashlib.sha256(reference).hexdigest(),
            "files": [{"path": path.name, "bytes": path.stat().st_size, "sha256": digest(path)} for _, path, _ in entries],
        }
    if len(process_ids) != 1:
        raise RuntimeError("counter observations did not come from one native test process")
    return {"cases": result, "reported_native_process_id": next(iter(process_ids)),
            "scope": "Original encoded rows are independently rehashed; field projection semantics remain the original anyenc fixture's observation. No replacement native decoder or direct child-PID observation is claimed."}


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
    parser.add_argument("--job-deadline-unix", required=True, type=int)
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
    selected_cases = manifest["expected_cases"]
    if selected_cases != {"native": ["ActualLocalZeroCounterAccepted", "NativeComputedRemoteCounterAccepted"]}:
        raise RuntimeError("exact reviewed TWO-counter-case native-only selection required")
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
    owned_temp = work / "native-temp"
    owned_temp.mkdir()
    # Preserve the real system HOME/PATH. Do not forward CI credentials or arbitrary
    # API keys to the disposable native runtime; no environment values are logged.
    allowed_env = ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT", "GOCACHE", "GOMODCACHE")
    env = {key: os.environ[key] for key in allowed_env if key in os.environ}
    env["TMPDIR"] = str(owned_temp)
    env["OTZARIA_SCHEMA_COUNTER_EVIDENCE"] = str(evidence)
    env.update({"CGO_ENABLED": "1", "GOMAXPROCS": "2", "GOTOOLCHAIN": "local", "GOWORK": "off", "GOFLAGS": "-mod=readonly"})
    # The first workflow step fixes the absolute job deadline. Reserve three
    # minutes inside it for owned cleanup/evidence, plus five more before the
    # outer 120-minute job timeout for artifact upload.
    commands = Commands(evidence, env, args.job_deadline_unix - 180)
    result = {
        "status": "STARTED_NOT_ACCEPTED", "heart_base": PIN, "control_head": args.control_head,
        "source_index_sha256": manifest["source_index_sha256"],
        "execution_manifest_sha256": digest(manifest_path), "tests": {},
        "baseline_run_id": 45012913358,
        "observer_delta_sha256": manifest["observer_delta_patch"]["sha256"],
        "unchanged_prior_cases_not_replayed": {"strict": 12, "native_early_rejection": 13, "native_v6_passed": 18},
        "job_deadline_unix": args.job_deadline_unix,
        "command_deadline_unix": commands.deadline,
        "cleanup_reserve_seconds": 180,
        "observer_write_scope": "Reviewed observer adds no mutation API; no whole-database no-write runtime measurement is claimed.",
        "ios_build": False,
        "scope": "Disposable genuine original LocalOnly Heart runtime; no production registration/repair, annotation authority/receipt or ACK.",
    }
    write_json(evidence / "RESULT.json", result)
    success = False
    try:
        if args.job_deadline_unix > time.time() + 7000 or commands.deadline <= time.time():
            raise RuntimeError("invalid/exhausted absolute workflow budget")
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
        # Preserve frozen V5, then apply the separately reviewed one-file native
        # key-derivation correction. Both before and after bytes are sealed.
        product_by_path = {entry["path"]: entry for entry in source_manifest["candidate"]}
        delta = manifest["observer_product_delta"]
        if len(delta) != 1 or delta[0]["path"] != "core/block/object/objectcreator/fixed_schema_replay.go":
            raise RuntimeError("only the reviewed original replay key delta is admitted")
        for entry in delta:
            original = product_by_path.get(entry["path"])
            if original is None or original["sha256"] != entry["before_sha256"] or digest(heart / entry["path"]) != entry["before_sha256"]:
                raise RuntimeError("wrong product preimage before V6 correction")
            check_file(controls, entry)
            product_by_path[entry["path"]] = entry
        correction_patch = check_file(controls, manifest["observer_delta_patch"])
        commands.require("observer-v6-apply-check", ["git", "apply", "--check", str(correction_patch)], heart, 30)
        commands.require("observer-v6-apply", ["git", "apply", str(correction_patch)], heart, 30)
        compiled_product_inputs = []
        for entry in product_by_path.values():
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
        setup_child = check_file(controls, manifest["original_setup_child"])
        setup_receipt = evidence / "TANTIVY_SETUP.json"
        commands.require("original-tantivy-setup", [
            sys.executable, str(setup_child), "--heart", str(heart), "--helper", str(helper),
            "--helper-sha256", manifest["original_setup_helper"]["sha256"],
            "--receipt", str(setup_receipt),
        ], heart, 600)
        result["tantivy"] = json.loads(setup_receipt.read_text())
        native_before = native_library_inputs(heart)
        if native_before["archive_sha256"] != result["tantivy"]["archive_sha256"]:
            raise RuntimeError("native archive changed after original setup")
        write_json(evidence / "TANTIVY_INPUTS_BEFORE.json", native_before)
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/darwin-arm64")
        listing = commands.require("declared-dependency-inputs", [args.go, "list", "-deps", "-test", "-json", *[v[0] for v in PACKAGES.values()]], heart, 1200)
        closure = dependency_inputs(listing, heart, compiled_product_inputs)
        if len(closure["required_product_test_coverage"]) != 9:
            raise RuntimeError("exact five product plus four native test input coverage required")
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
            binary_before = digest(binary)
            actual = {"compiled": True, "pass": False, "binary_sha256_before": binary_before,
                      "binary_bytes": binary.stat().st_size, "execution_started": False,
                      "binary_evidence_scope": "Runner-observed hashes; executable bytes are excluded from uploaded evidence and not independently rehashed by root."}
            result["tests"][name] = actual
            write_json(evidence / "RESULT.json", result)
            buildinfo = commands.require("buildinfo-" + name, [args.go, "version", "-m", str(binary)], heart, 30)
            actual.update({"buildinfo_sha256": digest(buildinfo), "execution_started": True})
            write_json(evidence / "RESULT.json", result)
            selection = "^" + re.escape(parent) + "$/^(" + "|".join(re.escape(case) for case in selected_cases[name]) + ")$"
            actual["selection"] = selection
            write_json(evidence / "RESULT.json", result)
            code, output, _ = commands.run("run-" + name, [
                args.go, "tool", "test2json", "-t", "-p", package, str(binary),
                "-test.v=test2json", "-test.count=1", "-test.run=" + selection, "-test.timeout=12m",
            ], heart, 780)
            binary_after = digest(binary)
            actual.update(validate_cases(output, parent, manifest["expected_cases"][name]))
            actual.update({"binary_sha256_after": binary_after, "binary_unchanged": binary_before == binary_after,
                           "process_returncode": commands.items[-1]["returncode"], "effective_returncode": code,
                           "timed_out": commands.items[-1]["timed_out"]})
            actual["pass"] = actual["pass"] and code == 0 and not actual["timed_out"] and actual["binary_unchanged"]
            result["tests"][name] = actual
            write_json(evidence / "RESULT.json", result)
            observations = validate_counter_observations(evidence, selected_cases[name])
            result["counter_observations"] = observations
            write_json(evidence / "RESULT.json", result)

        for entry in compiled_product_inputs:
            if digest(heart / entry["path"]) != entry["sha256"]:
                raise RuntimeError("native product/test source changed during execution")
        if {p: digest(heart / p) for p in original_module_hashes} != original_module_hashes:
            raise RuntimeError("original module/native checksum input changed")
        for entry in closure["files"]:
            if digest(entry["path"]) != entry["sha256"]:
                raise RuntimeError("declared native source input changed during execution")
        native_after = native_library_inputs(heart)
        write_json(evidence / "TANTIVY_INPUTS_AFTER.json", native_after)
        if native_before != native_after:
            raise RuntimeError("extracted native library file set/bytes changed during linking/execution")
        result["native_library_inputs_unchanged"] = True
        result["post_execution_source_recheck"] = True
        success = set(result["tests"]) == set(PACKAGES) and all(v["pass"] for v in result["tests"].values())
        result["status"] = "PASS" if success else "FAIL"
    except Exception as error:
        result["status"] = "FAIL"
        result["error_type"] = type(error).__name__
        result["error"] = str(error)
    finally:
        # This exact directory was created by this run under a previously absent
        # owned work root. No original account path is ever removed.
        try:
            if not commands.owned_groups_drained:
                raise RuntimeError("owned native process group did not drain; preserve its temporary files for explicit cleanup")
            shutil.rmtree(owned_temp)
            result["owned_disposable_temp_removed"] = True
        except Exception as error:
            result["owned_disposable_temp_removed"] = False
            result["cleanup_error_type"] = type(error).__name__
            result["status"], success = "FAIL", False
        result["commands"] = len(commands.items)
        result["finished_unix"] = time.time()
        write_json(evidence / "RESULT.json", result)
        payloads = [
            {"path": p.name, "bytes": p.stat().st_size, "sha256": digest(p)}
            for p in sorted(evidence.iterdir()) if p.is_file() and p.name != "EVIDENCE_INDEX.json"
        ]
        write_json(evidence / "EVIDENCE_INDEX.json", {
            "scope": "Result/commands/source closure, original streams, and exact disposable counter snapshot rows; no wallet or native account directory is included.",
            "files": payloads,
        })
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
