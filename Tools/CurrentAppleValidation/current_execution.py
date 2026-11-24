"""Finite orchestration for new current-App builds; original-only routes remain unchanged."""
from __future__ import annotations
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import signal
import stat
import subprocess
import sys
import tarfile
import time
import uuid
import contracts as c

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "source-inputs.json"
INVENTORY_POLICY = "owned-inventory-timeout-v1"
INVENTORY_SOURCE = "8dc5ee02db71517a5eb08535a6b266da62adfe30"
_FINALIZING = False
_CANCELLED = False

def cancel(signum, frame):
    global _CANCELLED
    _CANCELLED = True
    if not _FINALIZING:
        raise KeyboardInterrupt("Current Apple owned execution cancelled")

def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024**2), b""):
            h.update(chunk)
    return h.hexdigest()

def read(path, maximum=32 * 1024**2):
    return c.strict_json(c.read(path, maximum))

def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)

def error(value):
    result = {"type": type(value).__name__, "message": str(value)}
    for key in ("timeout_observations", "quiescence_observation"):
        if hasattr(value, key):
            result[key] = getattr(value, key)
    return result

def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], check=True, capture_output=True,
                          timeout=30, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"}).stdout

def metadata(path):
    st = path.lstat()
    if stat.S_ISREG(st.st_mode):
        return {"kind": "file", "bytes": st.st_size, "mode": stat.S_IMODE(st.st_mode), "sha256": digest(path)}
    if stat.S_ISLNK(st.st_mode):
        return {"kind": "symlink", "mode": stat.S_IMODE(st.st_mode), "target": os.readlink(path)}
    raise ValueError("unsupported_source_type")

def admit(profile, expected, inventory_policy=None):
    c.require(platform.system() == "Darwin" and platform.machine() == "arm64"
              and os.environ.get("GITHUB_ACTIONS") == "true"
              and os.environ.get("GITHUB_REPOSITORY") == c.REPOSITORY, "owned_apple_ci_required")
    c.require(re.fullmatch("[0-9a-f]{40}", expected) and expected == os.environ.get("GITHUB_SHA")
              and git("rev-parse", "HEAD").decode().strip() == expected, "source_identity_mismatch")
    c.require(not git("status", "--porcelain", "--untracked-files=no").strip(), "tracked_source_dirty")
    git("merge-base", "--is-ancestor", c.BASE, expected)
    for key in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        c.require(re.fullmatch("[1-9][0-9]*", os.environ.get(key, "")), "run_identity_required")
    fixed = read(MANIFEST)
    c.require(fixed["base"] == c.BASE and fixed["native"] == {"heart": c.HEART, "any": c.ANY}, "profile_changed")
    c.require(len(fixed["retainedMethods"]) == 22
              and not set(c.methods(profile)).intersection(fixed["retainedMethods"])
              and c.SOURCE_DRAG not in c.methods(profile), "historical_pass_selected")
    recovery = inventory_spec(fixed, inventory_policy)
    origin = recovery["sourceCommit"] if recovery is not None else c.BASE
    if recovery is not None:
        git("merge-base", "--is-ancestor", origin, expected)
    trees = (recovery["productTrees"] if recovery is not None else fixed["productTrees"])[profile]
    all_trees = {**trees, **fixed["helperTrees"]}
    for name, oid in all_trees.items():
        c.require(git("rev-parse", "HEAD:" + name).decode().strip() == oid, "compiled_source_tree_changed:" + name)
    paths = [*all_trees, *fixed["helperInputs"], "Tools/CurrentAppleValidation",
             ".github/workflows/pinkha-current-release-return-rtl.yml",
             ".github/workflows/pinkha-current-native-ui-failed.yml"]
    files, origins = {}, {}
    for row in git("ls-tree", "-r", "-z", "HEAD", "--", *paths).split(b"\0"):
        if not row:
            continue
        info, raw_name = row.split(b"\t", 1)
        mode, kind, oid = info.decode().split()
        name = raw_name.decode()
        c.require(kind == "blob" and mode in ("100644", "100755", "120000"), "unsupported_git_input")
        path = ROOT / name
        c.require(path.parent.resolve() == path.parent, "source_parent_link")
        value = metadata(path)
        raw = c.read(path, 128 * 1024**2) if value["kind"] == "file" else value["target"].encode()
        c.require(hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == oid,
                  "physical_source_differs_from_git:" + name)
        c.require((mode == "120000") == (value["kind"] == "symlink"), "source_type_differs")
        if mode == "120000":
            c.require(path.resolve().is_relative_to(ROOT), "external_source_link")
        else:
            c.require(bool(value["mode"] & 0o111) == (mode == "100755"), "source_mode_differs")
        if name in fixed["helperInputs"]:
            spec = fixed["helperInputs"][name]
            c.require(spec == {"gitMode": mode, "gitBlob": oid, "sha256": c.sha(raw)}, "helper_changed:" + name)
        files[name], origins[name] = value, {"gitMode": mode, "gitBlob": oid}
    c.require(set(fixed["helperInputs"]).issubset(files), "missing_helper_input")
    context = {"profile": profile, "sourceCommit": expected, "runID": os.environ["GITHUB_RUN_ID"],
               "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"], "repository": c.REPOSITORY}
    source = {"manifestSHA256": digest(MANIFEST), "files": files, "gitInputs": origins,
              "compiledTrees": trees, "compiledOrigin": origin}
    if recovery is not None:
        source["inventoryRecoveryPolicy"] = inventory_policy
    return context, source

def recheck(source):
    c.require(digest(MANIFEST) == source["manifestSHA256"]
              and {name: metadata(ROOT / name) for name in source["files"]} == source["files"],
              "admitted_source_changed")
    observed = {}
    fixed = read(MANIFEST)
    for name, path in module_origins(fixed, source).items():
        if name in sys.modules:
            c.require(Path(sys.modules[name].__file__).resolve() == ROOT / path, "foreign_module_origin:" + name)
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).absolute()
        resolved = path.resolve()
        if resolved.is_relative_to(ROOT):
            relative = resolved.relative_to(ROOT).as_posix()
            c.require(path == resolved and relative in source["files"]
                      and digest(path) == source["files"][relative]["sha256"], "unadmitted_loaded_module:" + relative)
            observed[relative] = digest(path)
    return observed

def helpers(source):
    for path in reversed(("Tools/PinkhaSimulatorGate", "Tools/AnyEnginePort", "Tools/Hanlin",
                          "Tools/PinkhaNativeDerived")):
        sys.path.insert(0, str(ROOT / path))
    for name, relative in module_origins(read(MANIFEST), source).items():
        specification = importlib.util.find_spec(name)
        c.require(specification is not None and specification.origin is not None
                  and Path(specification.origin).resolve() == ROOT / relative,
                  "foreign_or_missing_declared_module:" + name)
    result = {}
    names = {"wave15_batch": "Tools/PinkhaSimulatorGate", "run_owned_single_lane": "Tools/PinkhaSimulatorGate",
             "simulator_selection": "Tools/PinkhaSimulatorGate", "native_ui_transition_contract": "Tools/AnyEnginePort",
             "verify_native_test_execution": "Tools/AnyEnginePort", "verify_archive_roundtrip": "Tools/AnyEnginePort",
             "continue_native_acceptance": "Tools/AnyEnginePort", "verify_custom_type": "Tools/AnyEnginePort"}
    for name, directory in names.items():
        result[name] = importlib.import_module(name)
        c.require(Path(result[name].__file__).resolve() == ROOT / directory / (name + ".py"),
                  "foreign_required_helper:" + name)
    recheck(source)
    return result

def inventory_spec(fixed, policy):
    if policy is None:
        return None
    c.require(policy == INVENTORY_POLICY, "unreviewed_inventory_policy")
    spec = fixed["inventoryRecovery"]
    c.require(spec["policy"] == INVENTORY_POLICY and spec["sourceCommit"] == INVENTORY_SOURCE
              and spec["budgets"] == {"postboot": 120, "pre-cleanup": 90}
              and set(spec["productTrees"]) == set(c.PROFILES), "inventory_policy_profile_changed")
    return spec

def module_origins(fixed, source):
    origins = dict(fixed["moduleOrigins"])
    if inventory_spec(fixed, source.get("inventoryRecoveryPolicy")) is not None:
        c.require("owned_inventory_recovery" not in origins, "inventory_module_origin_collision")
        origins["owned_inventory_recovery"] = "Tools/CurrentAppleValidation/owned_inventory_recovery.py"
    return origins

def configure_inventory_recovery(commands, source):
    if source.get("inventoryRecoveryPolicy") is not None:
        inventory_spec(read(MANIFEST), source["inventoryRecoveryPolicy"])
        module = importlib.import_module("owned_inventory_recovery")
        recheck(source)
        c.require(module.POLICY == INVENTORY_POLICY and module.BUDGETS == {"postboot": 120, "pre-cleanup": 90},
                  "inventory_policy_implementation_changed")
        commands.inventory_recovery = module.Policy(commands, cwd=str(ROOT),
            recheck_source=lambda: recheck(source), write_json=write)

def verify_owned_inventory(commands, item, name, states=None, *, phase):
    policy = getattr(commands, "inventory_recovery", None)
    if policy is None:
        return verify_device(commands, item, name, states)
    return policy.verify(verify_device, item, name, states, phase)

def inventory_recovery_result(commands):
    policy = getattr(commands, "inventory_recovery", None)
    return None if policy is None else policy.summary()

class Commands:
    def __init__(self, evidence, context, modules):
        self.root = evidence / "commands"
        self.root.mkdir(parents=True, exist_ok=True)
        self.context, self.helpers = context, modules
        # Two new single-method stages add their unchanged 360/1800s budgets plus
        # the existing 300s per-stage command overhead; other profiles stay exact.
        self.deadline = time.monotonic() + (9960 if context["profile"] == "native-ui-failed" else 7200)
        self.cleanup_mode = False

    def run(self, argv, name, timeout, observe=None):
        c.require(re.fullmatch("[a-z0-9][a-z0-9-]*", name) and 0 < timeout <= 3900, "bounded_command_required")
        c.require(self.cleanup_mode or time.monotonic() + timeout + 30 <= self.deadline, "execution_budget_exhausted")
        c.require(not self.cleanup_mode or timeout <= 90, "cleanup_command_budget_exceeded")
        log, start, final = (self.root / (name + suffix) for suffix in (".log", ".started.json", ".command.json"))
        c.require(not any(p.exists() for p in (log, start, final)), "command_replay_forbidden")
        record = {"context": self.context, "argv": argv, "cwd": str(ROOT), "timeoutSeconds": timeout,
                  "status": "FAIL", "started": time.time(), "environmentValuesRecorded": False}
        process, primary = None, None
        stream = log.open("xb")
        try:
            try:
                process = subprocess.Popen(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                c.require(process.pid > 1 and process.pid != os.getpgrp(), "invalid_owned_group")
                record.update(pid=process.pid, pgid=process.pid)
                write(start, record)
                try:
                    record["returnCode"] = process.wait(timeout=timeout)
                    if process.returncode:
                        primary = subprocess.CalledProcessError(process.returncode, argv)
                except BaseException as failure:
                    primary = failure
                stream.flush()
                os.fsync(stream.fileno())
                if observe:
                    try:
                        observe(log, record)
                    except BaseException as failure:
                        record["observationFailure"] = error(failure)
                        primary = primary or failure
            except BaseException as failure:
                if primary is not None and failure is not primary:
                    record.setdefault("secondaryFailures", []).append(
                        {"stage": "command_body", **error(failure)})
                primary = primary or failure
            finally:
                if process:
                    try:
                        self.helpers["wave15_batch"].terminate_owned(process)
                        record["ownedGroupCleanup"] = "TERM_THEN_KILL"
                        record["kernelObservation"] = self.helpers["run_owned_single_lane"]._sdk06_kernel_group_observation(
                            process.pid, time.monotonic() + 10)
                        c.require(record["kernelObservation"]["outcome"] == "ABSENT_ESRCH", "owned_group_not_absent")
                    except BaseException as failure:
                        record["cleanupFailure"] = error(failure)
                        primary = primary or failure
                    record["returnCode"] = process.returncode
                try:
                    stream.flush()
                    os.fsync(stream.fileno())
                except BaseException as failure:
                    record.setdefault("preservationFailures", []).append(
                        {"stage": "final_log_flush", **error(failure)})
                    primary = primary or failure
        finally:
            try:
                stream.close()
            except BaseException as failure:
                record.setdefault("preservationFailures", []).append(
                    {"stage": "log_close", **error(failure)})
                primary = primary or failure
        record.update(finished=time.time(), logSHA256=None, logBytes=None, logMetadataStatus="UNAVAILABLE")
        try:
            record.update(logSHA256=digest(log), logBytes=log.stat().st_size, logMetadataStatus="AVAILABLE")
        except BaseException as failure:
            record.setdefault("preservationFailures", []).append(
                {"stage": "final_log_metadata", **error(failure)})
            primary = primary or failure
        if primary:
            record["firstFailure"] = error(primary)
        else:
            record["status"] = "PASS"
        try:
            write(final, record)
        except BaseException as preservation:
            if primary:
                raise primary from preservation
            raise
        if primary:
            raise primary
        return log

    def json(self, argv, name, timeout=60):
        return read(self.run(argv, name, timeout), 8 * 1024**2)


def device_map(value):
    c.require(isinstance(value, dict) and isinstance(value.get("devices"), dict), "device_inventory_shape")
    result = {}
    for runtime, rows in value["devices"].items():
        c.require(isinstance(runtime, str) and isinstance(rows, list), "runtime_inventory_shape")
        for row in rows:
            identity = row.get("udid")
            c.require(isinstance(identity, str) and identity not in result, "duplicate_device_uuid")
            result[identity] = (runtime, row)
    return result

def fixed_pair(commands, profile):
    spec = c.PROFILES[profile]
    selector = commands.helpers["simulator_selection"]
    runtimes = selector._unique(commands.json(["xcrun", "simctl", "list", "runtimes", "--json"],
                                              "runtimes").get("runtimes"), "runtimes")
    types = selector._unique(commands.json(["xcrun", "simctl", "list", "devicetypes", "--json"],
                                           "device-types").get("devicetypes"), "device types")
    c.require(spec["runtime"] in runtimes and spec["device"] in types, "fixed_pair_unavailable")
    runtime, device = runtimes[spec["runtime"]], types[spec["device"]]
    c.require(runtime.get("version") == spec["version"] and runtime.get("buildversion") == spec["build"],
              "fixed_runtime_changed")
    return selector.choose_pair({"runtimes": [runtime]}, {"devicetypes": [device]},
                                product_family="iPad", major=27, architecture="arm64")

def verify_device(commands, item, name, states=None):
    found = device_map(commands.json(["xcrun", "simctl", "list", "devices", item["udid"], "--json"], name, 30))
    c.require(set(found) == {item["udid"]}, "owned_uuid_query_not_exact")
    runtime, row = found[item["udid"]]
    c.require(runtime == item["runtime"]["identifier"] and row.get("name") == item["name"]
              and row.get("deviceTypeIdentifier") == item["device"]["identifier"]
              and row.get("isAvailable") is True, "owned_device_identity_changed")
    if states is not None:
        c.require(row.get("state") in states, "owned_device_state_changed")

def create_device(commands, pair, name, evidence, owned):
    index = len(owned)
    baseline = device_map(commands.json(["xcrun", "simctl", "list", "devices", "--json"], "before-create-" + str(index)))
    c.require(not any(row.get("name") == name for _, row in baseline.values()), "planned_name_already_exists")
    directory = evidence / ("device-" + str(index))
    directory.mkdir(mode=0o700)
    argv = ["xcrun", "simctl", "create", name, pair["device"]["identifier"], pair["runtime"]["identifier"]]
    write(directory / "intent.json", {"context": commands.context, "argv": argv, "name": name,
          "baseline": sorted(baseline), "runtime": pair["runtime"], "device": pair["device"]})
    def capture(log, record):
        raw = c.read(log, 128).decode().strip()
        try:
            identity = str(uuid.UUID(raw)).upper()
        except ValueError:
            return
        c.require(identity == raw.upper() and identity not in baseline and len(owned) == index, "create_not_fresh")
        item = {"udid": identity, "name": name, "directory": str(directory), "runtime": pair["runtime"],
                "device": pair["device"], "context": commands.context, "createArgv": argv,
                "createLogSHA256": digest(log), "createReturnCode": record.get("returnCode")}
        write(directory / "created.json", item)
        owned.append(item)
    commands.run(argv, "create-device-" + str(index), 60, observe=capture)
    c.require(len(owned) == index + 1, "create_uuid_missing")
    item = owned[-1]
    verify_device(commands, item, "created-" + str(index), {"Shutdown"})
    commands.run(["xcrun", "simctl", "boot", item["udid"]], "boot-" + str(index), 120)
    commands.run(["xcrun", "simctl", "bootstatus", item["udid"], "-b"], "bootstatus-" + str(index), 180)
    verify_owned_inventory(commands, item, "booted-" + str(index), {"Booted"}, phase="postboot")
    return item

def inventory(root):
    root = Path(root)
    c.require(root.is_absolute() and root.resolve() == root and root.is_dir(), "inventory_root_missing_or_linked")
    result, total, deadline = {}, 0, time.monotonic() + 180
    for parent, directories, files in os.walk(root, followlinks=False):
        for name in sorted(directories + files):
            p = Path(parent) / name
            st = p.lstat()
            c.require(time.monotonic() < deadline and len(result) < 100000, "inventory_bound_exceeded")
            if stat.S_ISDIR(st.st_mode):
                value = {"kind": "directory", "mode": stat.S_IMODE(st.st_mode)}
            elif stat.S_ISLNK(st.st_mode):
                c.require(not Path(os.readlink(p)).is_absolute() and p.resolve().is_relative_to(root),
                          "external_product_link")
                value = metadata(p)
            elif stat.S_ISREG(st.st_mode):
                total += st.st_size
                c.require(total <= 16 * 1024**3, "inventory_bytes_exceeded")
                value = metadata(p)
            else:
                raise ValueError("special_product_entry")
            result[p.relative_to(root).as_posix()] = value
    c.require(time.monotonic() < deadline, "inventory_returned_after_deadline")
    return result

def check_products(products, original, copies):
    expected = {**original["files"], **copies}
    c.require(not set(copies).intersection(original["files"]) and inventory(products) == expected,
              "original_products_or_registered_descriptors_changed")
    return {"complete": True, "originalEntries": len(original["files"]), "newDescriptors": copies}

def dependencies(derived):
    marker = ROOT / "Dependencies/Hanlin/.pinkha-source.json"
    hanlin = read(marker)
    c.require(hanlin["revision"] == c.HANLIN, "canonical_hanlin_changed")
    for name, expected in hanlin["files"].items():
        path = ROOT / "Dependencies/Hanlin" / name
        c.require(path.resolve() == path and digest(path) == expected, "canonical_hanlin_file_changed")
    checkouts = derived / "SourcePackages/checkouts"
    c.require(checkouts.is_dir(), "actual_checkouts_missing")
    heads = {}
    for path in sorted(checkouts.iterdir()):
        c.require(path.resolve() == path and path.is_dir(), "invalid_checkout")
        head = subprocess.run(["git", "-C", str(path), "rev-parse", "HEAD"], check=True,
                              capture_output=True, timeout=20).stdout.decode().strip()
        status = subprocess.run(["git", "-C", str(path), "status", "--porcelain", "--untracked-files=no"],
                                check=True, capture_output=True, timeout=20).stdout
        c.require(re.fullmatch("[0-9a-f]{40}", head) and not status.strip(), "unbound_or_dirty_dependency")
        heads[path.name] = head
    c.require("e7bf34111e603ca977becd007dd4e5bb109af857" in heads.values(), "swift_ai_sdk_pin_missing")
    return {"hanlin": hanlin, "markerSHA256": digest(marker), "actualPackageCommits": heads,
            "workspaceStateSHA256": digest(derived / "SourcePackages/workspace-state.json")}

def code_carriers(app):
    values = {}
    magic = (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xfe\xed\xfa\xcf", b"\xca\xfe\xba\xbe", b"\xca\xfe\xba\xbf")
    for path in sorted(app.rglob("*")):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                if stream.read(4) in magic:
                    values[path.relative_to(app).as_posix()] = digest(path)
    c.require(values, "application_has_no_macho")
    return values

def build(commands, profile, device, work, evidence, source):
    spec = c.PROFILES[profile]
    derived = work / "derived"
    c.require(not derived.exists(), "fresh_derived_root_required")
    argv = ["xcodebuild", "build-for-testing", "-project", spec["project"], "-scheme", spec["scheme"],
            "-configuration", spec["configuration"], "-destination", "platform=iOS Simulator,id=" + device["udid"],
            "-derivedDataPath", str(derived), "-parallel-testing-enabled", "NO",
            "-resultBundlePath", str(evidence / "build.xcresult"),
            *c.selectors(profile), *spec["flags"], *c.COMMON_FLAGS]
    write(evidence / "build-intent.json", {"context": commands.context, "argv": argv,
          "applicationBuildInvocations": 1, "uiRunnerBuildInvocations": spec["uiRunnerBuilds"],
          "nativeLibraryBuildInvocations": 0})
    try:
        commands.run(argv, "build-for-testing", 3900)
    except BaseException as original_failure:
        # Keep actual partial output independently; never relabel it a completed build.
        partial = derived / "Build/Products"
        if partial.is_dir():
            try:
                entries = inventory(partial)
                archive = evidence / "failed-build-partial-products.tar.gz"
                with tarfile.open(archive, "x:gz", dereference=False) as output:
                    output.add(partial, arcname="Build/Products")
                c.require(inventory(partial) == entries, "partial_products_changed")
                write(evidence / "failed-build-partial-products.json",
                      {"context": commands.context, "files": entries, "archiveSHA256": digest(archive),
                       "buildStatus": "FAIL", "reusable": False})
            except BaseException as preservation:
                write(evidence / "partial-build-preservation-failure.json", error(preservation))
        raise original_failure
    products = derived / "Build/Products"
    before = inventory(products)
    write(derived / "Build/PinkhaSourceInputs.json", {"context": commands.context, "sources": source, "argv": argv})
    archive = evidence / "original-build-products.tar.gz"
    with tarfile.open(archive, "x:gz", dereference=False) as output:
        output.add(products, arcname="Build/Products")
        output.add(derived / "Build/PinkhaSourceInputs.json", arcname="Build/PinkhaSourceInputs.json")
    c.require(inventory(products) == before, "products_changed_during_archive")
    original = {"context": commands.context, "files": before, "archive": archive.name,
                "archiveSHA256": digest(archive), "archiveBytes": archive.stat().st_size,
                "phase": "AFTER_BUILD_BEFORE_ADMISSION"}
    write(evidence / "original-products.json", original)
    candidates = []
    for p in products.glob("*.xctestrun"):
        value = plistlib.loads(c.read(p))
        targets = [x for cfg in value.get("TestConfigurations", []) for x in cfg.get("TestTargets", [])]
        if spec["target"] in value or any(x.get("BlueprintName") == spec["target"] for x in targets):
            candidates.append(p)
    c.require(len(candidates) == 1, "one_original_descriptor_required")
    descriptor = candidates[0]
    with (evidence / "original.xctestrun").open("xb") as f:
        f.write(c.read(descriptor))
    app = products / (spec["configuration"] + "-iphonesimulator") / spec["app"]
    c.require(plistlib.loads(c.read(app / "Info.plist")).get("CFBundleIdentifier") == spec["bundle"],
              "actual_app_bundle_changed")
    commands.run(["codesign", "--verify", "--deep", "--strict", str(app)], "verify-current-signature", 60)
    if profile == "release-return-rtl":
        verification = ("import sys;from pathlib import Path;sys.path.insert(0," +
                        repr(str(ROOT / "Tools/PinkhaNativeDerived")) +
                        ");from validate_wave1 import verify_runtime_copies;import json;" +
                        "r=json.loads(Path(" + repr(str(evidence / "heart/heart-installation.json")) + ").read_bytes());" +
                        "verify_runtime_copies(Path(" + repr(str(app)) + "),r['expected_app_get_version'].encode()," +
                        "Path(" + repr(str(evidence)) + "))")
        commands.run([sys.executable, "-B", "-c", verification], "verify-current-heart-copies", 120)
    dependency = dependencies(derived)
    write(evidence / "actual-dependencies.json", dependency)
    record = {"context": commands.context, "descriptor": str(descriptor), "descriptorSHA256": digest(descriptor),
              "app": str(app), "codeCarriers": code_carriers(app), "nativeBuilds": 0,
              "applicationBuilds": 1, "uiRunnerBuilds": spec["uiRunnerBuilds"],
              "productsReceiptSHA256": digest(evidence / "original-products.json")}
    write(evidence / "build.json", record)
    return derived, original, descriptor, app, dependency

def installed_app(commands, device, app, bundle, stage):
    log = commands.run(["xcrun", "simctl", "get_app_container", device["udid"], bundle, "app"],
                       stage + "-installed-app", 30)
    path = Path(c.read(log, 4096).decode().strip())
    root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device["udid"]
    c.require(path.is_absolute() and path.resolve() == path and path.is_relative_to(root)
              and path.name == app.name and code_carriers(path) == code_carriers(app),
              "installed_application_not_current_owned_build")
    return {"path": str(path), "codeCarriers": code_carriers(app), "originalLogSHA256": digest(log)}


TITLES = {
    c.RETURN[0]: "An already rendered split row keeps the request published by the real service",
    c.RETURN[1]: "The actual general event can render and consume the same pending split request",
    c.RETURN[2]: "A genuinely later editor request still cancels the split row's deferred request",
    c.PREPARATION[0]: "Creates disposable Pinkha, ordinary Note and ordinary Page documents",
}

def raw_terminal(raw, profile, stage, cases, modules):
    if profile == "native-ui-failed":
        normalized = {name.removeprefix(c.PROFILES[profile]["target"] + "/"): value
                      for name, value in cases.items()}
        modules["continue_native_acceptance"].verify_log(raw, normalized)
        return {"parser": "unchanged_original_xctest_log", "cases": normalized}
    text = raw.decode("utf-8")
    titles = {TITLES[name] for name in c.PROFILES[profile]["stages"][stage][0]}
    found = re.findall(r'[\u25c7\u2714\u2718]\s+Test "([^"]+)" (started|passed|failed)', text)
    starts = [title for title, status in found if status == "started"]
    terminals = [(title, status) for title, status in found if status != "started"]
    c.require(len(starts) == len(titles) and set(starts) == titles and len(terminals) == len(titles)
              and set(terminals) == {(title, "passed") for title in titles},
              "original_swift_testing_named_log_not_exact")
    return {"parser": "explicit_new_swift_testing_titles", "titles": sorted(titles)}

def owned_container(commands, device, bundle, phase):
    log = commands.run(["xcrun", "simctl", "get_app_container", device["udid"], bundle, "data"], phase, 30)
    path = Path(c.read(log, 4096).decode().strip())
    root = Path.home() / "Library/Developer/CoreSimulator/Devices" / device["udid"] / "data/Containers/Data/Application"
    c.require(path.is_absolute() and path.resolve() == path and path.parent == root and path.is_dir(),
              "owned_application_data_container_required")
    c.require(str(uuid.UUID(path.name)).upper() == path.name.upper(), "data_container_uuid_required")
    return path, {"argv": read(commands.root / (phase + ".command.json"))["argv"], "logSHA256": digest(log)}

def archive_semantics(commands, device, directory):
    validator = commands.helpers["verify_archive_roundtrip"]
    receipt, raw = validator.ui_receipt(directory / "private-attachments")
    scope = receipt.get("scopeUUID")
    c.require(isinstance(scope, str) and str(uuid.UUID(scope)).upper() == scope, "actual_ui_export_uuid_required")
    container, observation = owned_container(commands, device, c.PROFILES["native-ui-failed"]["bundle"],
                                              "archive-owned-container")
    exports = container / "Documents/Exports"
    c.require(exports.is_dir() and not exports.is_symlink() and exports.resolve() == exports,
              "actual_owned_exports_directory_required")
    names = ("canonical-source-" + scope + ".json", "canonical-destination-" + scope + ".json",
             "canonical-source-cold-" + scope + ".json")
    values = [validator.regular_bytes(exports / name, exports, validator.MAXIMUM_BYTES) for name in names]
    proof = validator.validate_roundtrip(values[0], values[1], receipt, source_cold_bytes=values[2])
    private = directory / "private-export-originals"
    private.mkdir(mode=0o700)
    for name, value in [*zip(names, values), ("ui-receipt.json", raw)]:
        with (private / name).open("xb") as stream:
            stream.write(value)
        (private / name).chmod(0o400)
    return {"semanticProof": proof, "readOnlyPostflight": True, "ownedContainerCommand": observation,
            "uiReceiptSHA256": c.sha(raw), "originalFiles": {n: c.sha(v) for n, v in zip(names, values)},
            "validatorSHA256": digest(Path(validator.__file__)), "bodyProof": "Original UI and native cold assertions"}

def execute_stage(commands, profile, stage, device, built, source, evidence, copies):
    derived, original, original_descriptor, app, dependency = built
    products = derived / "Build/Products"
    directory = evidence / stage
    directory.mkdir(mode=0o700)
    outcome = {"status": "FAIL", "context": commands.context, "stage": stage, "testCommandInvoked": False,
               "partialNamed": None, "completeStageAcceptance": False, "errors": []}
    first = None
    try:
        write(directory / "source-before.json", source)
        write(directory / "loaded-before.json", recheck(source))
        check_products(products, original, copies)
        raw, binding = c.scope_descriptor(c.read(original_descriptor), profile, stage, products)
        descriptor = products / ("Current-" + stage + ".xctestrun")
        c.require(not descriptor.exists() and descriptor.name not in copies, "descriptor_replay_forbidden")
        with descriptor.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        descriptor.chmod(0o600)
        copies[descriptor.name] = metadata(descriptor)
        binding.update(copiedPath=str(descriptor), copiedSHA256=c.sha(raw), context=commands.context)
        write(directory / "descriptor-binding.json", binding)
        plan = c.test_command(profile, stage, descriptor, device["udid"], directory / "original.xcresult")
        enum = c.enumeration_command(plan, directory / "enumeration.json")
        write(directory / "plan.json", {"context": commands.context, "command": plan, "enumerationCommand": enum,
                                        "sourceDragSelected": False, "retainedTestsSelected": 0})
        commands.run(enum, stage + "-enumeration", 120)
        outcome["enumeration"] = c.validate_enumeration(read(directory / "enumeration.json"), profile, stage,
            commands.helpers["native_ui_transition_contract"].enumerated_identifiers)
        c.require(metadata(descriptor) == copies[descriptor.name], "enumerated_descriptor_changed")
        check_products(products, original, copies)
        recheck(source)
        outcome["testCommandInvoked"] = True
        write(directory / "test-invocation.json", {"context": commands.context, "argv": plan,
              "descriptorSHA256": digest(descriptor), "enumerationSHA256": digest(directory / "enumeration.json")})
        names, allowance = c.PROFILES[profile]["stages"][stage]
        commands.run(plan, stage + "-test", len(names) * allowance + 300)
    except BaseException as failure:
        first = failure
        outcome["firstFailure"] = error(failure)
    result = directory / "original.xcresult"
    if result.is_dir():
        for kind in ("summary", "tests"):
            try:
                log = commands.run(["xcrun", "xcresulttool", "get", "test-results", kind,
                                    "--path", str(result), "--format", "json"], stage + "-xcresult-" + kind, 120)
                raw = c.read(log, 32 * 1024**2)
                c.strict_json(raw)
                with (directory / (kind + ".json")).open("xb") as stream:
                    stream.write(raw)
            except BaseException as failure:
                outcome["errors"].append({"phase": kind, **error(failure)})
        try:
            attachments = directory / "private-attachments"
            commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result),
                          "--output-path", str(attachments)], stage + "-attachments", 120)
            attachments.chmod(0o700)
        except BaseException as failure:
            outcome["errors"].append({"phase": "attachments", **error(failure)})
    elif outcome["testCommandInvoked"]:
        outcome["errors"].append({"phase": "original-xcresult", "type": "MissingOriginalResult"})
    if (directory / "tests.json").is_file():
        try:
            outcome["partialNamed"] = commands.helpers["verify_native_test_execution"].test_cases(
                read(directory / "tests.json"))
        except BaseException as failure:
            outcome["errors"].append({"phase": "partial-named", **error(failure)})
    try:
        write(directory / "loaded-after.json", recheck(source))
        write(directory / "source-after.json", source)
        outcome["integrity"] = check_products(products, original, copies)
        c.require(dependencies(derived) == dependency, "actual_dependency_changed")
        if first is None and not outcome["errors"]:
            c.require(outcome["testCommandInvoked"], "actual_test_command_required")
            outcome["actual"] = c.validate_results(read(directory / "summary.json"), read(directory / "tests.json"),
                profile, stage, device["udid"], commands.helpers["verify_native_test_execution"].test_cases)
            raw = c.read(commands.root / (stage + "-test.log"), 32 * 1024**2)
            outcome["rawNamed"] = raw_terminal(raw, profile, stage, outcome["actual"]["actualCases"], commands.helpers)
            outcome["installedCurrentApplication"] = installed_app(commands, device, app,
                c.PROFILES[profile]["bundle"], stage)
            if stage == "archive-roundtrip":
                outcome["archive"] = archive_semantics(commands, device, directory)
            elif stage == "custom-type":
                validator = commands.helpers["verify_custom_type"]
                receipt, receipt_raw = validator.original_receipt(directory / "private-attachments")
                outcome["customType"] = {"proof": validator.validate_receipt(receipt),
                    "originalReceiptSHA256": c.sha(receipt_raw),
                    "validatorSHA256": digest(Path(validator.__file__)),
                    "sameCurrentProducts": True, "newApplicationBuilds": 0}
            outcome.update(status="PASS", completeStageAcceptance=True)
    except BaseException as failure:
        outcome["errors"].append({"phase": "qualification", **error(failure)})
        first = first or failure
    if outcome["errors"] and first is None:
        first = RuntimeError("original_result_or_postflight_incomplete")
    if first is not None:
        outcome["firstFailure"] = error(first)
    write(directory / "result.json", outcome)
    return outcome

def cleanup_devices(commands, evidence, owned):
    import cleanup_policy
    results = []
    commands.cleanup_mode = True
    for index, item in enumerate(owned):
        directory = Path(item["directory"])
        path = directory / "cleanup.json"
        if path.exists():
            prior = read(path)
            c.require(prior["context"] == commands.context and prior["owned_simulator"]["udid"] == item["udid"],
                      "foreign_prior_cleanup")
            results.append(prior)
            continue
        receipt = {"context": commands.context, "owned_simulator": {"udid": item["udid"]},
                   "createReceiptSHA256": digest(directory / "created.json")}
        try:
            verify_owned_inventory(commands, item, "pre-cleanup-" + str(index), phase="pre-cleanup")
            def run(argv, name, timeout):
                return commands.run(argv, "device-" + str(index) + "-" + name, timeout)
            cleanup_policy.cleanup_owned_simulator(run, receipt, item["udid"])
        except BaseException as failure:
            receipt["firstFailure"] = error(failure)
            receipt["owned_simulator_cleanup_status"] = "INCOMPLETE"
        recovery = inventory_recovery_result(commands)
        if recovery is not None:
            receipt["inventoryRecovery"] = recovery
        write(path, receipt)
        results.append(receipt)
    return results


def evidence_root(profile):
    run, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    c.require(profile in c.PROFILES and re.fullmatch("[1-9][0-9]*", run)
              and re.fullmatch("[1-9][0-9]*", attempt), "fixed_run_identity_required")
    return ROOT / "build" / ("current-apple-" + profile + "-" + run + "-" + attempt)

def recover_owned(commands, evidence):
    owned = []
    directories = sorted(evidence.glob("device-*"))
    c.require(len(directories) <= 2, "unexpected_device_journal_count")
    for directory in directories:
        c.require(directory.name == "device-" + str(len(owned)) and directory.resolve() == directory,
                  "unexpected_device_journal")
        intent = read(directory / "intent.json")
        c.require(intent["context"] == commands.context and len(intent["argv"]) == 6
                  and intent["argv"][:3] == ["xcrun", "simctl", "create"]
                  and intent["argv"][3:] == [intent["name"], intent["device"]["identifier"],
                                             intent["runtime"]["identifier"]], "foreign_create_intent")
        path = directory / "created.json"
        if path.exists():
            item = read(path)
        else:
            index = len(owned)
            started = commands.root / ("create-device-" + str(index) + ".started.json")
            log = commands.root / ("create-device-" + str(index) + ".log")
            if not started.exists():
                c.require(not log.exists(), "create_output_without_original_start")
                # Intention alone grants no simulator ownership.
                break
            original = read(started)
            c.require(original["context"] == commands.context and original["argv"] == intent["argv"],
                      "create_start_not_bound")
            observation = commands.helpers["run_owned_single_lane"]._sdk06_kernel_group_observation(
                original["pgid"], time.monotonic() + 10)
            c.require(observation["outcome"] == "ABSENT_ESRCH", "create_group_still_active")
            raw = c.read(log, 128).decode().strip()
            identity = str(uuid.UUID(raw)).upper()
            c.require(raw.upper() == identity and identity not in intent["baseline"], "unproven_created_uuid")
            item = {"udid": identity, "name": intent["name"], "directory": str(directory),
                    "runtime": intent["runtime"], "device": intent["device"], "context": commands.context,
                    "createArgv": intent["argv"], "createLogSHA256": digest(log), "createReturnCode": None,
                    "recoveredFromOriginalCommand": True, "originalGroupObservation": observation}
            write(path, item)
        c.require(item["context"] == commands.context and item["udid"] not in intent["baseline"]
                  and str(uuid.UUID(item["udid"])).upper() == item["udid"]
                  and item["directory"] == str(directory) and item["createArgv"] == intent["argv"]
                  and item["runtime"] == intent["runtime"] and item["device"] == intent["device"]
                  and item["name"] == intent["name"], "created_device_receipt_changed")
        owned.append(item)
    return owned

def unfinished_groups(commands):
    observations = []
    for started in sorted(commands.root.glob("*.started.json")):
        original = read(started)
        c.require(original["context"] == commands.context, "foreign_owned_command")
        final = started.with_name(started.name.removesuffix(".started.json") + ".command.json")
        if final.exists():
            record = read(final)
            c.require(record["context"] == commands.context and record["pid"] == original["pid"]
                      and record["pgid"] == original["pgid"], "command_final_origin_changed")
            if record.get("kernelObservation", {}).get("outcome") == "ABSENT_ESRCH":
                continue
        # Read-only absence query; no cross-process PID signalling or PID-reuse assumption.
        observation = commands.helpers["run_owned_single_lane"]._sdk06_kernel_group_observation(
            original["pgid"], time.monotonic() + 10)
        c.require(observation["outcome"] == "ABSENT_ESRCH", "unfinished_owned_group_not_absent")
        observations.append({"original": started.name, "sha256": digest(started), "observation": observation})
    return observations

def final_integrity(evidence, source, built, copies, native):
    result = {"loadedAfter": recheck(source)}
    if native is not None:
        c.require(inventory(Path(native["path"])) == native["files"], "installed_native_library_changed")
        result["nativeLibraryUnchanged"] = True
    if built is not None:
        derived, original, _, _, dependency = built
        result["products"] = check_products(derived / "Build/Products", original, copies)
        c.require(dependencies(derived) == dependency, "built_dependency_changed")
        result["dependenciesUnchanged"] = True
    write(evidence / "source-after.json", source)
    write(evidence / "loaded-after.json", result["loadedAfter"])
    return result

def execute(profile, expected, prepare_library, provider, inventory_policy=None):
    global _FINALIZING
    root = evidence_root(profile)
    c.require(not root.exists() and root.parent.resolve() == root.parent, "fresh_owned_execution_root_required")
    root.mkdir(mode=0o700, parents=True)
    evidence, work = root / "evidence", root / "work"
    evidence.mkdir(mode=0o700)
    work.mkdir(mode=0o700)
    outcome = {"status": "FAIL", "profile": profile, "stages": {}, "errors": [], "fullAcceptance": False,
               "historicalSourceDragExecutions": 0, "historical22Executions": 0, "nativeLibraryBuilds": 0,
               "applicationBuilds": 0, "uiRunnerBuilds": 0, "cSemanticAdmission": False}
    source = commands = context = built = native = None
    owned, copies = [], {}
    first = None
    try:
        context, source = admit(profile, expected, inventory_policy)
        outcome["context"] = context
        write(evidence / "source-before.json", source)
        write(evidence / "execution-intent.json", {"context": context, "selected": c.methods(profile),
              "sourceDragExcluded": c.SOURCE_DRAG, "sourceAdmissionSHA256": digest(evidence / "source-before.json"),
              **({"inventoryRecoveryPolicy": inventory_policy} if inventory_policy is not None else {})})
        modules = helpers(source)
        commands = Commands(evidence, context, modules)
        configure_inventory_recovery(commands, source)
        write(evidence / "loaded-before.json", recheck(source))
        version = commands.run(["xcodebuild", "-version"], "xcode-version", 30)
        c.require(c.read(version, 1024).decode().startswith("Xcode 27"), "xcode_27_required")
        commands.run([sys.executable, "-B", "Tools/Hanlin/prepare_sdk.py", "--source", ".ci/hanlin-source"],
                     "prepare-canonical-hanlin", 120)
        commands.run([sys.executable, "-B", "Tools/Hanlin/prepare_sdk.py", "--check"],
                     "verify-canonical-hanlin", 120)
        native = prepare_library(commands, work, evidence)
        write(evidence / "native-library.json", native)
        pair = fixed_pair(commands, profile)
        name = ("AnyNativePort-" + context["runID"] if profile == "native-ui-failed" else
                "CurrentReturn-" + context["runID"] + "-" + context["runAttempt"])
        device = create_device(commands, pair, name, evidence, owned)
        built = build(commands, profile, device, work, evidence, source)
        outcome["applicationBuilds"], outcome["uiRunnerBuilds"] = 1, c.PROFILES[profile]["uiRunnerBuilds"]
        if profile == "release-return-rtl":
            outcome["stages"]["return-controls"] = execute_stage(commands, profile, "return-controls", device,
                                                                  built, source, evidence, copies)
            recheck(source)
            check_products(built[0] / "Build/Products", built[1], copies)
            preparation = create_device(commands, pair,
                "CurrentRTL-" + context["runID"] + "-" + context["runAttempt"], evidence, owned)
            outcome["stages"]["preparation"] = execute_stage(commands, profile, "preparation", preparation,
                                                              built, source, evidence, copies)
        else:
            outcome["providerSetup"] = provider(commands, "prepare", device, evidence)
            outcome["stages"]["native-ui-three"] = execute_stage(commands, profile, "native-ui-three", device,
                                                                   built, source, evidence, copies)
            try:
                outcome["providerContract"] = provider(commands, "verify", device, evidence)
            except BaseException as failure:
                outcome["errors"].append({"phase": "provider-contract", **error(failure)})
                first = first or failure
            recheck(source)
            check_products(built[0] / "Build/Products", built[1], copies)
            outcome["stages"]["archive-roundtrip"] = execute_stage(commands, profile, "archive-roundtrip", device,
                                                                    built, source, evidence, copies)
            # The first four results keep their original stage receipts. The two
            # never-run journeys reuse this one build only after those and the
            # finite provider/archive postflight pass.
            initial = ("native-ui-three", "archive-roundtrip")
            outcome["initialFourPassed"] = first is None and all(
                outcome["stages"][name]["status"] == "PASS" for name in initial)
            if outcome["initialFourPassed"]:
                follow_on = create_device(commands, pair,
                    "CurrentNativeTypeHistory-" + context["runID"] + "-" + context["runAttempt"], evidence, owned)
                for stage in ("custom-type", "native-history"):
                    outcome["stages"][stage] = execute_stage(commands, profile, stage, follow_on,
                                                              built, source, evidence, copies)
            else:
                outcome["followOnAdmission"] = "NOT_RUN_INITIAL_FOUR_OR_PROVIDER_NOT_PASSED"
    except BaseException as failure:
        first = first or failure
        outcome["errors"].append({"phase": "execute", **error(failure)})
    finally:
        _FINALIZING = True
        outcome["cancellationObserved"] = _CANCELLED
        if commands is not None:
            commands.cleanup_mode = True
            try:
                outcome["providerCleanup"] = provider(commands, "cleanup", None, evidence)
            except BaseException as failure:
                outcome["errors"].append({"phase": "provider-cleanup", **error(failure)})
                first = first or failure
            try:
                outcome["simulatorCleanup"] = cleanup_devices(commands, evidence, owned)
                c.require(all(r["owned_simulator_cleanup_status"] == "COMPLETE"
                              for r in outcome["simulatorCleanup"]), "owned_simulator_cleanup_incomplete")
                outcome["groups"] = unfinished_groups(commands)
            except BaseException as failure:
                outcome["errors"].append({"phase": "owned-cleanup", **error(failure)})
                first = first or failure
        if source is not None:
            try:
                outcome["integrity"] = final_integrity(evidence, source, built, copies, native)
            except BaseException as failure:
                outcome["errors"].append({"phase": "final-integrity", **error(failure)})
                first = first or failure
        if (not _CANCELLED and not outcome["errors"] and first is None and set(outcome["stages"]) == set(c.PROFILES[profile]["stages"])
                and all(v["status"] == "PASS" for v in outcome["stages"].values())):
            outcome["status"] = "PASS"
        original_stage_failures = [v.get("firstFailure") for v in outcome["stages"].values()
                                   if v.get("firstFailure") is not None]
        if original_stage_failures:
            outcome["firstFailure"] = original_stage_failures[0]
            if first is not None:
                outcome["laterControllerFailure"] = error(first)
        elif first is not None:
            outcome["firstFailure"] = error(first)
        if commands is not None and (commands.root / "build-for-testing.started.json").exists():
            outcome["applicationBuilds"] = 1
            outcome["uiRunnerBuilds"] = c.PROFILES[profile]["uiRunnerBuilds"]
        recovery = inventory_recovery_result(commands)
        if recovery is not None:
            outcome["inventoryRecovery"] = recovery
        write(evidence / "execution.json", outcome)
    return outcome

def cleanup_only(profile, expected, provider, inventory_policy=None):
    global _FINALIZING
    _FINALIZING = True
    root = evidence_root(profile)
    if not root.exists():
        # No current intent, no simulator/global inventory, and no cleanup authority.
        return {"status": "NO_CURRENT_CREATION_INTENT", "profile": profile}
    evidence = root / "evidence"
    c.require(root.resolve() == root and evidence.resolve() == evidence, "owned_evidence_path_changed")
    path = evidence / "cleanup-final.json"
    c.require(not path.exists(), "cleanup_finalization_replay_forbidden")
    outcome = {"status": "FAIL", "profile": profile}
    try:
        c.require(platform.system() == "Darwin" and platform.machine() == "arm64"
              and os.environ.get("GITHUB_ACTIONS") == "true"
                  and os.environ.get("GITHUB_REPOSITORY") == c.REPOSITORY and expected == os.environ.get("GITHUB_SHA")
                  and git("rev-parse", "HEAD").decode().strip() == expected, "current_cleanup_identity_required")
        if not (evidence / "execution-intent.json").exists():
            c.require(not list(evidence.glob("device-*"))
                      and not list((evidence / "commands").glob("*.started.json")),
                      "resources_without_current_intent")
            outcome["status"] = "NO_CURRENT_CREATION_INTENT"
            write(path, outcome)
            return outcome
        intent = read(evidence / "execution-intent.json")
        context = {"profile": profile, "sourceCommit": expected, "runID": os.environ["GITHUB_RUN_ID"],
                   "runAttempt": os.environ["GITHUB_RUN_ATTEMPT"], "repository": c.REPOSITORY}
        c.require(intent["context"] == context and intent["sourceAdmissionSHA256"] ==
                  digest(evidence / "source-before.json"), "cleanup_source_admission_not_current")
        source = read(evidence / "source-before.json")
        c.require(intent.get("inventoryRecoveryPolicy") == inventory_policy
                  and source.get("inventoryRecoveryPolicy") == inventory_policy, "cleanup_inventory_policy_changed")
        recheck(source)
        commands = Commands(evidence, context, helpers(source))
        configure_inventory_recovery(commands, source)
        commands.cleanup_mode = True
        outcome["groups"] = unfinished_groups(commands)
        primary = None
        try:
            outcome["provider"] = provider(commands, "cleanup", None, evidence)
        except BaseException as failure:
            outcome["providerFailure"] = error(failure)
            primary = failure
        try:
            owned = recover_owned(commands, evidence)
            outcome["devices"] = cleanup_devices(commands, evidence, owned)
            c.require(all(r["owned_simulator_cleanup_status"] == "COMPLETE" for r in outcome["devices"]),
                      "prior_or_current_cleanup_incomplete")
        except BaseException as failure:
            outcome["deviceFailure"] = error(failure)
            primary = primary or failure
        try:
            outcome["loadedAfter"] = recheck(source)
        except BaseException as failure:
            outcome["loadedFailure"] = error(failure)
            primary = primary or failure
        recovery = inventory_recovery_result(commands)
        if recovery is not None:
            outcome["inventoryRecovery"] = recovery
        if primary:
            raise primary
        outcome["status"] = "PASS"
    except BaseException as failure:
        outcome["firstFailure"] = error(failure)
    write(path, outcome)
    return outcome

def main(profile, prepare_library, provider):
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("execute", "cleanup"))
    parser.add_argument("--expected-source", required=True)
    parser.add_argument("--inventory-recovery", dest="inventory_policy", choices=(INVENTORY_POLICY,))
    args = parser.parse_args()
    os.umask(0o077)
    previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    for number in previous:
        signal.signal(number, cancel)
    try:
        result = (execute(profile, args.expected_source, prepare_library, provider, args.inventory_policy)
                  if args.operation == "execute" else
                  cleanup_only(profile, args.expected_source, provider, args.inventory_policy))
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)
    print(json.dumps({"status": result["status"], "profile": profile, "fullAcceptance": False}))
    return 0 if result["status"] in ("PASS", "NO_CURRENT_CREATION_INTENT") else 1
