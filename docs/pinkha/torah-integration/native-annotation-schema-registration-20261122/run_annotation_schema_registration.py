#!/usr/bin/env python3
"""Run only thirteen new original Heart annotation schema registration controls.

Requires a fresh original Heart checkout, retained V5/V6 observer, and the
proven copyout/readback package, and four additive registration product files.
All previously passed strict/native controls are retained without replay.
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
    "native": ("./core/block/object/objectcreator", "TestOtzariaAnnotationSchemaRegistration"),
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


def validate_schema_readback(evidence):
    """Validate report framing; original Go controls own protobuf assertions."""
    path = evidence / "annotation-schema-readback.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != "otzaria-native-schema-readback/1" or record.get("protocol") != "pinkha.torah.annotation/1":
        raise RuntimeError("wrong original schema readback report")
    if record.get("disposition") != "MATCHING_SCHEMA_OBSERVED" or type(record.get("process_id")) is not int or record["process_id"] <= 0:
        raise RuntimeError("missing actual matching native process report")
    entries = record.get("definitions", [])
    if len(entries) != 18 or len({e.get("object_id") for e in entries}) != 18 or len({e.get("native_key") for e in entries}) != 18:
        raise RuntimeError("actual schema report does not contain exact distinct eighteen native objects")
    for entry in entries:
        if not entry.get("object_id") or not entry.get("native_key") or not entry.get("persisted_heads"):
            raise RuntimeError("actual native identity or heads missing")
        if entry.get("account_identity") != record.get("account_identity") or entry.get("space_id") != record.get("space_id"):
            raise RuntimeError("native schema report crossed account/Space scope")
        if not entry.get("acl_id") or not entry.get("acl_head") or not entry.get("archive_id") or not entry.get("archive_heads"):
            raise RuntimeError("actual native read scope is incomplete")
        if entry.get("index") != "ONE_MATCHING_LOCAL_INDEX_ROW" or not base64.b64decode(entry.get("details_protobuf", ""), validate=True):
            raise RuntimeError("actual native persisted/index readback is missing")
        for block in entry.get("blocks_protobuf", []):
            if not base64.b64decode(block, validate=True):
                raise RuntimeError("empty original block protobuf")
    layout = record.get("type_layout", {})
    if layout.get("Disposition") != "MATCHING_SCHEMA_OBSERVED" or layout.get("Hidden") is not True or layout.get("DiscoveryHidden") is not True or not layout.get("ViewIDs") or layout.get("MissingRelationKeys"):
        raise RuntimeError("original native type layout was not fully observed")
    return {"path": path.name, "sha256": digest(path), "definition_count": len(entries),
            "reported_native_process_id": record["process_id"],
            "scope": "Historical actual native schema report; protobuf semantics are asserted by the exact executed Go controls, not a replacement Python model."}


def validate_registration_phases(evidence, readback):
    """Check original emitted call identities; Go owns native mutation assertions."""
    path = evidence / "annotation-schema-registration-phases.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("schema") != "otzaria-native-schema-registration-phases/1" or record.get("process_id") != readback["reported_native_process_id"]:
        raise RuntimeError("registration phases were not emitted by the observed native process")
    calls = record.get("calls", [])
    if not 1 <= len(calls) <= 21 or any(call.get("app_admitted") is not True for call in calls):
        raise RuntimeError("missing/beyond-bound admitted native registration phases")
    created = []
    applies = 0
    for call in calls:
        if call.get("type_apply_invoked"):
            applies += 1
            if call.get("type_apply_returned") is not True:
                raise RuntimeError("positive registration lost an uncertain native Apply")
        elif call.get("type_apply_returned"):
            raise RuntimeError("native Apply returned without actual invocation")
        for creation in call.get("creations") or []:
            if creation.get("invoked") is not True:
                continue
            native_id = creation.get("fixed_id")
            if not native_id or creation.get("returned_id") != native_id or native_id in created:
                raise RuntimeError("missing/uncertain/repeated native fixed-root creation")
            created.append(native_id)
    schema_record = json.loads((evidence / "annotation-schema-readback.json").read_text(encoding="utf-8"))
    if len(created) != 18 or set(created) != {entry["object_id"] for entry in schema_record["definitions"]} or applies != 1:
        raise RuntimeError("positive native registration lacks exact eighteen unique creates plus one type Apply")
    if calls[-1].get("disposition") != "MATCHING_SCHEMA_OBSERVED":
        raise RuntimeError("final positive phase lacks strict native matching readback")
    return {"path": path.name, "sha256": digest(path), "phase_count": len(calls), "native_create_count": len(created),
            "type_apply_count": applies, "reported_native_process_id": record["process_id"],
            "scope": "Actual positive fixture call phases; error strings and all negative/lifecycle controls remain in the unmodified native test event stream."}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", required=True, type=Path)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--controls", required=True, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--execution-manifest-sha256", required=True)
    parser.add_argument("--heart", required=True, type=Path)
    parser.add_argument("--work", required=True, type=Path)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--go", default="go")
    parser.add_argument("--job-deadline-unix", required=True, type=int)
    args = parser.parse_args()
    control, source, controls, heart = (p.resolve() for p in (args.control_root, args.source, args.controls, args.heart))
    evidence, work = args.evidence.resolve(), args.work.resolve()
    schema = args.schema.resolve()
    registration = args.registration.resolve()
    if evidence.exists() or work.exists():
        raise RuntimeError("fresh owned evidence/work paths are required")
    if any(not packet.is_relative_to(control) for packet in (source, controls, schema, registration)):
        raise RuntimeError("all sealed packets must belong to the exact control checkout")
    if git(control, "rev-parse", "HEAD") != args.control_head:
        raise RuntimeError("wrong control commit")
    if git(heart, "rev-parse", "HEAD") != PIN or git(heart, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("fresh exact original Heart checkout required")
    manifest_path = registration / "EXECUTION_INPUTS.json"
    if digest(manifest_path) != args.execution_manifest_sha256:
        raise RuntimeError("unreviewed execution manifest")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_cases = manifest["expected_cases"]
    if selected_cases != {"native": ['ActualRegistrationAndStrictReadback', 'RepeatedRegistrationDoesNotMutate', 'MissingAttachmentUsesOneNativeApply', 'VisibleColumnRemainsConflict', 'RootOnlyStopsAllCreation', 'DifferentActiveAccountIsRefused', 'CancelledBeforeAdmissionWritesNothing', 'NativeRootCollisionDoesNotInitialize', 'NativePopulatedCollisionDoesNotOverwrite', 'NativeReaderRoleCannotRegister', 'QueuedAccountStopDrainsWithCancellation', 'QueuedAccountSelectDrainsNativeApply', 'StopCancelsQueuedSelectWithoutDraining']}:
        raise RuntimeError("exact reviewed THIRTEEN-new-case native-only selection required")
    for entry in manifest["control_inputs"]:
        check_file(registration, entry)
    schema_manifest_path = schema / "EXECUTION_INPUTS.json"
    if digest(schema_manifest_path) != manifest["readback_execution_manifest_sha256"]:
        raise RuntimeError("wrong proven nine-case readback source manifest")
    schema_manifest = json.loads(schema_manifest_path.read_text(encoding="utf-8"))
    for entry in schema_manifest["control_inputs"]:
        check_file(schema, entry)
    prior_manifest_path = controls / "EXECUTION_INPUTS.json"
    if digest(prior_manifest_path) != manifest["prior_execution_manifest_sha256"]:
        raise RuntimeError("wrong retained V7R1 input manifest")
    prior_manifest = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    for entry in prior_manifest["control_inputs"]:
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
    env["OTZARIA_ANNOTATION_SCHEMA_EVIDENCE"] = str(evidence)
    env.update({"CGO_ENABLED": "1", "GOMAXPROCS": "2", "GOTOOLCHAIN": "local", "GOWORK": "off", "GOFLAGS": "-mod=readonly"})
    # The first workflow step fixes the absolute job deadline. Reserve three
    # minutes inside it for owned cleanup/evidence, plus five more before the
    # outer 120-minute job timeout for artifact upload.
    commands = Commands(evidence, env, args.job_deadline_unix - 180)
    result = {
        "status": "STARTED_NOT_ACCEPTED", "heart_base": PIN, "control_head": args.control_head,
        "source_index_sha256": manifest["source_index_sha256"],
        "execution_manifest_sha256": digest(manifest_path), "tests": {},
        "baseline_run_id": 45032882624,
        "retained_v7r1_run_id": 45027606300,
        "observer_delta_sha256": prior_manifest["observer_delta_patch"]["sha256"],
        "schema_copyout_patch_sha256": schema_manifest["copyout_patch"]["sha256"],
        "registration_product_files": [e["path"] for e in manifest["new_product_sources"]],
        "unchanged_prior_cases_not_replayed": {"strict": 12, "native_early_rejection": 13, "native_v6_passed": 18, "native_v7_passed": 2, "native_readback_passed": 9},
        "job_deadline_unix": args.job_deadline_unix,
        "command_deadline_unix": commands.deadline,
        "cleanup_reserve_seconds": 180,
        "observer_write_scope": "Proven observer files are unchanged; separate new methods perform bounded original native registration in disposable fixtures.",
        "ios_build": False,
        "scope": "Disposable genuine original LocalOnly Heart registration/admission and missing hidden-attachment controls; no Swift/RPC integration, ordinary annotation create, mapping, body authority or ACK.",
    }
    write_json(evidence / "RESULT.json", result)
    success = False
    try:
        if args.job_deadline_unix > time.time() + 7000 or commands.deadline <= time.time():
            raise RuntimeError("invalid/exhausted absolute workflow budget")
        original_module_hashes = {p: digest(heart / p) for p in ("go.mod", "go.sum", "tantivity_sha256.txt")}
        if original_module_hashes != prior_manifest["original_module_hashes"]:
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

        patch = check_file(controls, prior_manifest["r14_patch"])
        inventory_path = check_file(controls, prior_manifest["r14_inventory"])
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
        delta = prior_manifest["observer_product_delta"]
        if len(delta) != 1 or delta[0]["path"] != "core/block/object/objectcreator/fixed_schema_replay.go":
            raise RuntimeError("only the reviewed original replay key delta is admitted")
        for entry in delta:
            original = product_by_path.get(entry["path"])
            if original is None or original["sha256"] != entry["before_sha256"] or digest(heart / entry["path"]) != entry["before_sha256"]:
                raise RuntimeError("wrong product preimage before V6 correction")
            check_file(controls, entry)
            product_by_path[entry["path"]] = entry
        correction_patch = check_file(controls, prior_manifest["observer_delta_patch"])
        commands.require("observer-v6-apply-check", ["git", "apply", "--check", str(correction_patch)], heart, 30)
        commands.require("observer-v6-apply", ["git", "apply", str(correction_patch)], heart, 30)
        copyout_patch = check_file(schema, schema_manifest["copyout_patch"])
        for entry in schema_manifest["copyout_afterimages"]:
            if digest(heart / entry["path"]) != entry["before_sha256"]:
                raise RuntimeError("native copyout preimage differs: " + entry["path"])
            check_file(schema, entry)
        commands.require("schema-copyout-apply-check", ["git", "apply", "--check", str(copyout_patch)], heart, 30)
        commands.require("schema-copyout-apply", ["git", "apply", str(copyout_patch)], heart, 30)
        for entry in schema_manifest["copyout_afterimages"]:
            product_by_path[entry["path"]] = entry
        for packet, entries in ((schema, schema_manifest["new_product_sources"]), (registration, manifest["new_product_sources"])):
            for entry in entries:
                destination = safe_path(heart, entry["path"])
                if destination.exists():
                    raise RuntimeError("new schema product path already exists")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(check_file(packet, entry), destination)
                product_by_path[entry["path"]] = entry
        compiled_product_inputs = []
        for entry in product_by_path.values():
            path = heart / entry["path"]
            if digest(path) != entry["sha256"]:
                raise RuntimeError("composed product source differs")
            compiled_product_inputs.append({"path": entry["path"], "sha256": digest(path), "bytes": path.stat().st_size})
        for root, entries in ((controls, prior_manifest["test_sources"]), (schema, schema_manifest["new_test_sources"]), (registration, manifest["new_test_sources"])):
            for entry in entries:
                destination = safe_path(heart, entry["path"])
                if destination.exists():
                    raise RuntimeError("new native test source already exists")
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(check_file(root, entry), destination)
                compiled_product_inputs.append({"path": entry["path"], "sha256": digest(destination), "bytes": destination.stat().st_size})
        baseline = manifest["unchanged_composed_baseline_inputs"]
        if len(baseline) != 13 or len({e["path"] for e in baseline}) != 13:
            raise RuntimeError("exact thirteen proven composed baseline inputs required")
        for entry in baseline:
            check_file(heart, entry)
        result["baseline_inputs_unchanged"] = baseline
        gofmt = Path(go_binary).resolve().with_name("gofmt")
        if not gofmt.is_file():
            raise RuntimeError("pinned Go formatter is absent")
        format_paths = schema_manifest["copyout_afterimages"] + schema_manifest["new_product_sources"] + schema_manifest["new_test_sources"] + manifest["new_product_sources"] + manifest["new_test_sources"]
        formatting = commands.require("source-format-equality", [str(gofmt), "-l", *[str(heart / e["path"]) for e in format_paths]], heart, 30)
        if formatting.read_text().strip():
            raise RuntimeError("frozen source differs from pinned gofmt; no source is rewritten")
        result["gofmt"] = {"path": str(gofmt), "sha256": digest(gofmt), "source_equality": True}
        allowed_paths = {e["path"] for e in inventory["files"]} | {e["path"] for e in compiled_product_inputs}
        changed = git(heart, "status", "--porcelain", "--untracked-files=all").splitlines()
        if any(line[:2] not in (" M", "??") or line[3:] not in allowed_paths for line in changed):
            raise RuntimeError("unexpected composed Heart working change")
        result["composed_product_and_test_inputs"] = compiled_product_inputs
        result["r14_patch_sha256"] = digest(patch)
        write_json(evidence / "RESULT.json", result)

        helper = check_file(controls, prior_manifest["original_setup_helper"])
        setup_child = check_file(controls, prior_manifest["original_setup_child"])
        setup_receipt = evidence / "TANTIVY_SETUP.json"
        commands.require("original-tantivy-setup", [
            sys.executable, str(setup_child), "--heart", str(heart), "--helper", str(helper),
            "--helper-sha256", prior_manifest["original_setup_helper"]["sha256"],
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
        if len(closure["required_product_test_coverage"]) != 19:
            raise RuntimeError("exact twelve product plus seven native test input coverage required")
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
            observations = validate_schema_readback(evidence)
            result["schema_readback"] = observations
            result["registration_phases"] = validate_registration_phases(evidence, observations)
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
            "scope": "Result/commands/source closure, original streams, actual disposable schema details/block protobufs and registration call phases; no wallet or native account directory is included.",
            "files": payloads,
        })
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

