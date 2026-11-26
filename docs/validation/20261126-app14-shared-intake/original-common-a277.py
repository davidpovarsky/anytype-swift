#!/usr/bin/env python3
"""Execute the six exact Heart semantic journeys on qualified combined Products.

This is an owned Sentinel execution, never a fabricated GitHub Actions run.
It builds nothing, preserves original results, and uses a fresh simulator.
The immutable admission JSON is separately hashed on the command line after
the sole app/UI producer has finished. Every source and product is verified
against the actual producer before any XCTest invocation.
"""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import traceback
import uuid

sys.dont_write_bytecode = True
MANIFEST = "11619a9928d681ee4a0114bbba7b8c66d3b7383b6289e639e67d50e546b8ae8b"
OVERLAY = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
VERSION = "pinkha-dual-runtime-v1-" + MANIFEST
NATIVE_BINARY = "9f64b4469e221cd27b04c0f46b7479cf1fb079b36fce8a26c0fd8b0521ecaf5e"
LOCK = "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd"
SDK_RECEIPT = "b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150"
OBSERVATION_HELPER = "1943362eb5fb171252600134e4126a36160eb1e2adb233deb94df620c0b73262"
MENU_OVERRIDE_HELPER = "05c86ac0ce8871e353e4269f5c834fc6b2d4bacdcc8e93cdacad3440d24b57c7"
BUNDLE = "io.anytype.app"
RUNTIME = "com.apple.CoreSimulator.SimRuntime.iOS-27-0"
DEVICE = "com.apple.CoreSimulator.SimDeviceType.iPad-Pro-13-inch-M5-16GB"
OS_VERSION, OS_BUILD = "27.0", "24A434"
FLOOR = 2 * 1024**3
NATIVE_SUITE = "AnytypeTests/SemanticAnchorPage154MountedPreparationTests/"
UI_SUITE = "PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/"
STAGES = {
    "preparation": NATIVE_SUITE + "testPrepareOwnedPage154MountedFixture",
    "mounted": UI_SUITE + "testActualTextSelectionCancelThenCreateAndColdReopen",
    "linked-ui": UI_SUITE + "testExistingSemanticAnchorSourceLinkEditAndColdReopen",
    "linked-native": NATIVE_SUITE + "testReadBackExistingSemanticSourceAfterActualUIEditAndColdReopen",
    "unlinked-ui": UI_SUITE + "testExistingSemanticAnchorSourceUnlinkAndColdReopen",
    "unlinked-native": NATIVE_SUITE + "testReadBackSemanticSourceAbsenceAfterActualUIUnlinkAndColdReopen",
}
HELPERS = {
    "Tools/CurrentAppleValidation/contracts.py": "aa724f9236058081e92d1c6fedbc57f6d8864d8403ab522e2d9d4de917cd8316",
    "Tools/CurrentAppleValidation/page154_contract.py": "596a1761882c3efe2068b4af61b463eee0e063e7a2a43957e7c7f321c946dd00",
    "Tools/CurrentAppleValidation/page154_boundary.py": "76b40b54270610ede431b751432796e82e58e8a0c4ca8ef3df4e2e405f7b372c",
    "Tools/PinkhaSemanticAnchorWire/apple_consumer/consumer_contract.py": "235eae83ac85a8c280a10cf570e6675b87d11f6059c2ed46a2a12fda7c2df894",
    "Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_contract.py": "0fa1af7e7b3f45d0eec8f1aa4c2d4a4ef97d5ca1c4e94f8838ba69e3eeab28ff",
    "Tools/PinkhaSemanticAnchorWire/apple_mounted/warning_profile.py": "fa561fa2823047cd92177920779dbebc0ced35d3fce9869773b05a374932adbf",
}
FLAGS = ("PINKHA_DUAL_ENGINE_RUNTIME", "PINKHA_NATIVE_T2_AUTHORIZED_READ_V1",
         "PINKHA_NATIVE_SEMANTIC_ANCHOR_PAGE154_V1")
FIXTURE = "pinkha-semantic-page154-mounted-fixture.json"
CAPTURE = "pinkha-semantic-page154-mounted-capture.json"
REOPEN = "pinkha-semantic-page154-mounted-reopen.json"


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def raw(path, maximum=64 * 1024**2):
    path = Path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, "bounded regular file required: " + str(path))
    value = path.read_bytes()
    after = path.lstat()
    require((before.st_ino, before.st_dev, before.st_mtime_ns, before.st_size) ==
            (after.st_ino, after.st_dev, after.st_mtime_ns, after.st_size), "input changed while reading")
    return value


def decode(value):
    def unique(rows):
        result = {}
        for key, item in rows:
            require(key not in result, "duplicate JSON key")
            result[key] = item
        return result
    return json.loads(value, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))


def write(path, value):
    write_bytes(path, (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode())


def write_bytes(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    path.chmod(0o600)


def error(exc):
    return {"type": type(exc).__name__, "message": str(exc)}


def inventory(root):
    root = Path(root)
    require(root.resolve() == root and root.is_dir(), "unaliased product root required")
    result = {}
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        st = path.lstat()
        if stat.S_ISDIR(st.st_mode):
            result[name] = {"kind": "directory", "mode": stat.S_IMODE(st.st_mode)}
        elif stat.S_ISREG(st.st_mode):
            result[name] = {"kind": "file", "bytes": st.st_size, "mode": stat.S_IMODE(st.st_mode), "sha256": digest(path)}
        elif stat.S_ISLNK(st.st_mode):
            require(path.resolve().is_relative_to(root), "product symlink escaped owned root")
            result[name] = {"kind": "symlink", "mode": stat.S_IMODE(st.st_mode), "target": os.readlink(path)}
        else:
            raise ValueError("unsupported product file type")
    require(result and len(result) < 100_000, "bounded nonempty product inventory required")
    require(len({n.casefold() for n in result}) == len(result), "case-colliding products")
    return result


def pinned(row):
    require(set(row) == {"path", "sha256", "bytes"}, "pin schema changed")
    path = Path(row["path"])
    require(path.is_absolute() and path.resolve() == path, "unaliased original input required")
    value = raw(path)
    require(len(value) == row["bytes"] and sha(value) == row["sha256"], "original pinned bytes changed: " + str(path))
    return value


class Commands:
    def __init__(self, root, cwd):
        self.root, self.cwd = Path(root), Path(cwd)
        self.root.mkdir(mode=0o700)
        self.groups = []
        self.absent_groups = set()
        self.cancelled = False
        self.environment = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
        self.environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    def run(self, argv, label, timeout=120, *, checked=True, capacity=True):
        require(re.fullmatch(r"[a-z0-9-]+", label), "scoped command label required")
        require(not self.cancelled, "owned execution cancelled")
        directory = self.root / label
        directory.mkdir(mode=0o700)
        started, minimum = time.time(), shutil.disk_usage(self.root).free
        require(not capacity or minimum >= FLOOR, "free space below owned 2 GiB guard")
        log = directory / "original.log"
        outcome = {"argv": list(map(str, argv)), "cwd": str(self.cwd), "startedAt": started,
                   "timeoutSeconds": timeout, "freeBytesBefore": minimum, "status": "FAIL"}
        with log.open("xb") as stream:
            process = subprocess.Popen(argv, cwd=self.cwd, env=self.environment, stdout=stream,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            self.groups.append(process.pid)
            outcome.update(pid=process.pid, pgid=process.pid)
            write(directory / "started.json", outcome)
            reason = None
            try:
                while process.poll() is None:
                    minimum = min(minimum, shutil.disk_usage(self.root).free)
                    if capacity and minimum < FLOOR:
                        reason = "OWNED_RESOURCE_FLOOR"
                    elif time.time() - started > timeout:
                        reason = "OWNED_TIMEOUT"
                    if reason:
                        raise TimeoutError(reason)
                    time.sleep(1)
            except BaseException as exc:
                reason = reason or str(exc)
                self.stop(process.pid)
                process.wait()
                outcome["interruption"] = error(exc)
            code = process.wait()
        outcome.update(exitCode=code, finishedAt=time.time(), minimumFreeBytes=minimum,
                       logSHA256=digest(log), logBytes=log.stat().st_size,
                       status="PASS_COMMAND" if code == 0 and reason is None else "FAIL_COMMAND")
        outcome["ownedGroupPresentAfterExit"] = self.present(process.pid)
        if not outcome["ownedGroupPresentAfterExit"]:
            self.absent_groups.add(process.pid)
        write(directory / "result.json", outcome)
        if checked:
            require(outcome["status"] == "PASS_COMMAND", label + " failed: " + str(reason or code))
        return log, outcome

    @staticmethod
    def present(group):
        try:
            os.killpg(group, 0)
            return True
        except ProcessLookupError:
            return False

    @staticmethod
    def stop(group):
        try:
            os.killpg(group, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 15
        while Commands.present(group) and time.monotonic() < deadline:
            time.sleep(0.2)
        if Commands.present(group):
            os.killpg(group, signal.SIGKILL)


def source_admission(source, expected, producer, destination):
    require(re.fullmatch("[0-9a-f]{40}", expected), "exact source SHA required")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(source), *args], env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), timeout=60)
    require(git("rev-parse", "HEAD").decode().strip() == expected and not git("status", "--porcelain").strip(),
            "producer source is not clean exact frozen commit")
    for ancestor in ("781340ad1efb62fb4d8515345b501081c3f22c21", "c42f7062f2a58c73d1630201ad01af5b5e399179",
                     "4b9b381d3f9b8d5a9a358d626a69333c145e3282"):
        git("merge-base", "--is-ancestor", ancestor, expected)
    require(producer["commit"] == expected and producer["status"] == "" and
            git("rev-parse", "HEAD^{tree}").decode().strip() == producer["tree"], "producer source receipt differs")
    require(isinstance(producer["files"], dict) and len(producer["files"]) > 1000, "complete producer source inventory required")
    for name, row in producer["files"].items():
        path = source / name
        require(path.resolve().is_relative_to(source) and path.is_file() and not path.is_symlink(), "source escaped root")
        require(path.stat().st_size == row["bytes"] and digest(path) == row["sha256"], "producer source changed: " + name)
    # Freeze only the pure validators here; compiled source remains recoverable by
    # its Git commit and the complete before/after producer inventory.
    destination.mkdir(mode=0o700)
    for name, expected_hash in HELPERS.items():
        value = raw(source / name)
        require(sha(value) == expected_hash and value == git("show", expected + ":" + name), "reviewed helper changed: " + name)
        write_bytes(destination / name, value)
    return {"commit": expected, "tree": producer["tree"], "verifiedSourceFiles": len(producer["files"]),
            "sourceStateSHA256": sha(json.dumps(producer, sort_keys=True).encode()), "helpers": HELPERS}


def product_integrity(built):
    current = inventory(built["products"])
    expected = dict(built["inventory"])
    expected.update(built["copies"])
    require(current == expected, "owned original product bytes changed")
    return {"verifiedEntries": len(current), "extraBoundDescriptors": len(built["copies"])}


def bind_descriptor(built, app, selector, additions):
    original = plistlib.loads(raw(built["descriptor"]))
    copied = copy.deepcopy(original)
    native = selector.startswith("AnytypeTests/")
    blueprint, suite, method = selector.split("/")
    require(original.get("__xctestrun_metadata__", {}).get("FormatVersion") == (2 if native else 1), "descriptor version changed")
    if native:
        configs = copied.get("TestConfigurations")
        require(isinstance(configs, list) and len(configs) == 1 and configs[0].get("IsEnabled", True) is True,
                "one native configuration required")
        targets = configs[0]["TestTargets"]
        matches = [t for t in targets if t.get("BlueprintName") == blueprint]
        require(len(matches) == 1, "exact native test target required")
        target = matches[0]
    else:
        require(set(copied) == {"__xctestrun_metadata__", blueprint}, "one UI blueprint required")
        target = copied[blueprint]
        require(target.get("IsUITestBundle") is True and target.get("UseUITargetAppProvidedByTests") is True
                and "UITargetAppPath" not in target and "UITargetAppBundleIdentifier" not in target,
                "original explicit-bundle launch mode required")
    require(target.get("IsEnabled", True) is True and not target.get("SkipTestIdentifiers"), "original selection excludes tests")
    require(target.get("OnlyTestIdentifiers", []) == built["originalSelection"], "admitted original selector inventory differs")
    before = copy.deepcopy(target)
    host = common.product_path(target["TestHostPath"], built["products"])
    bundle = common.product_path(target["TestBundlePath"], built["products"], host)
    require(bundle == host / "PlugIns" / (blueprint + ".xctest"), "original compiled test bundle differs")
    require((native and host == app) or (not native and host.name == blueprint + "-Runner.app"), "test host differs")
    if not native:
        require(target.get("DependentProductPaths") == [target["TestHostPath"], target["TestHostPath"] + "/PlugIns/" + blueprint + ".xctest"],
                "UI dependencies differ")
    env = target.get("EnvironmentVariables", {})
    require(isinstance(env, dict) and all(isinstance(k, str) and isinstance(v, str) for k, v in env.items())
            and not any(k.startswith(("PINKHA_", "TEST_RUNNER_PINKHA_")) for k in env), "stale environment")
    target["EnvironmentVariables"] = dict(env, **additions)
    target["OnlyTestIdentifiers"] = [suite + "/" + method]
    if native:
        copied["TestConfigurations"][0]["TestTargets"] = [target]
    else:
        target["UITargetAppPath"] = str(app)
    # No injection or hidden test configuration is changed. Both original and
    # copied Products live on this same Mac/runtime. If a token needs relocation,
    # fail here and review that concrete original token separately.
    testing = target.get("TestingEnvironmentVariables", {})
    require(isinstance(testing, dict) and all(isinstance(v, str) for v in testing.values()), "invalid testing environment")
    for token in testing.get("DYLD_INSERT_LIBRARIES", "").split(":"):
        if token and token.startswith("/"):
            require(Path(token).is_file(), "original runtime injection token is unavailable: " + token)
    reverse = copy.deepcopy(target)
    for key in ("EnvironmentVariables", "OnlyTestIdentifiers", "UITargetAppPath"):
        if key in before:
            reverse[key] = before[key]
        else:
            reverse.pop(key, None)
    require(reverse == before, "unreviewed descriptor target mutation")
    inverse = copy.deepcopy(copied)
    if native:
        inverse["TestConfigurations"][0]["TestTargets"] = original["TestConfigurations"][0]["TestTargets"]
    else:
        inverse[blueprint] = reverse
    require(inverse == original and target.get("TestingEnvironmentVariables") == before.get("TestingEnvironmentVariables"),
            "unreviewed original descriptor mutation")
    return plistlib.dumps(copied, sort_keys=False), {"originalSHA256": digest(built["descriptor"]), "selector": selector,
            "exactInverse": True, "testingEnvironmentUnchanged": True, "environmentKeys": sorted(additions)}


def qualify_enumeration(value, selector):
    require(isinstance(value, dict) and value.get("errors") == [], "enumeration errors or unknown schema")
    configs = value.get("values")
    require(isinstance(configs, list) and len(configs) == 1 and isinstance(configs[0].get("testPlan"), str), "one enumeration config required")
    config = configs[0]
    normalized = lambda s: s.removeprefix(selector.split("/")[0] + "/").removesuffix("()")
    actual = {}
    for key in ("enabledTests", "disabledTests"):
        rows = config.get(key)
        require(isinstance(rows, list) and all(isinstance(r, dict) and isinstance(r.get("identifier"), str) for r in rows), "enumeration schema differs")
        names = [r["identifier"] for r in rows]
        require(len(names) == len(set(names)), "duplicate compiled method")
        actual[key] = names
    require([normalized(s) for s in actual["enabledTests"]] == ["/".join(selector.split("/")[1:])]
            and not set(actual["enabledTests"]).intersection(actual["disabledTests"]), "exact one compiled method required")
    if selector.startswith("AnytypeTests/"):
        require(config["testPlan"] == "AnytypeTests", "native plan differs")
    return {"plan": config["testPlan"], **actual}


def qualify_execution(summary, tree, selector, udid, log):
    counts = {k: summary.get(k) for k in ("totalTestCount", "passedTests", "failedTests", "skippedTests")}
    require(all(type(v) is int for v in counts.values()) and counts ==
            {"totalTestCount": 1, "passedTests": 1, "failedTests": 0, "skippedTests": 0}
            and summary.get("result") == "Passed", "one real PASS without failures/skips required")
    destinations = summary.get("devicesAndConfigurations", [])
    require(len(destinations) == 1, "one actual destination required")
    device = destinations[0].get("device", {})
    require(str(device.get("deviceId", "")).lower() == udid.lower() and device.get("architecture") == "arm64"
            and device.get("platform") == "iOS Simulator" and device.get("osVersion") == OS_VERSION
            and device.get("osBuildNumber") == OS_BUILD, "actual owned simulator differs")
    cases = []
    def walk(node):
        if isinstance(node, dict):
            if node.get("nodeType") == "Test Case":
                cases.append((node.get("nodeIdentifier"), node.get("result")))
            for item in node.values():
                if isinstance(item, (dict, list)):
                    walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(tree)
    require(len(cases) == 1 and isinstance(cases[0][0], str) and cases[0][0].removeprefix(selector.split("/")[0] + "/").removesuffix("()") ==
            "/".join(selector.split("/")[1:]) and cases[0][1] == "Passed", "actual test name differs")
    suite, method = selector.split("/")[1:]
    pattern = r"Test Case '-\[(?:[^.\] ]+\.)?(\w+) (\w+)\]' (started|passed|failed|skipped)"
    text = raw(log, 64 * 1024**2).decode("utf-8", "replace")
    observed = re.findall(pattern, text)
    require(observed == [(suite, method, "started"), (suite, method, "passed")]
            and "** TEST EXECUTE SUCCEEDED **" in text, "original named XCTest stdout not proven")
    return {"selector": selector, "counts": counts, "cases": cases, "device": device, "rawNamedLogVerified": True}


def stage(commands, root, name, built, app, binding, udid, additions):
    selector = STAGES[name]
    directory = root / name
    directory.mkdir(mode=0o700)
    outcome = {"status": "FAIL", "selector": selector, "testInvoked": False, "errors": []}
    primary = None
    try:
        product_integrity(built)
        descriptor, proof = bind_descriptor(built, app, selector, additions)
        copy_path = built["products"] / ("E-Combined-Heart-" + name + ".xctestrun")
        write_bytes(copy_path, descriptor)
        built["copies"][copy_path.name] = {"kind": "file", "bytes": len(descriptor), "mode": 0o600, "sha256": sha(descriptor)}
        write(directory / "descriptor-binding.json", proof)
        write_bytes(directory / "bound.xctestrun", descriptor)
        base = ["xcodebuild", "test-without-building", "-xctestrun", str(copy_path), "-destination",
                "platform=iOS Simulator,id=" + udid, "-parallel-testing-enabled", "NO", "-only-testing", selector]
        listing = directory / "enumeration.json"
        commands.run(base + ["-enumerate-tests", "-test-enumeration-style", "flat", "-test-enumeration-format", "json",
                            "-test-enumeration-output-path", str(listing)], name + "-enumerate", 180)
        outcome["enumeration"] = qualify_enumeration(decode(raw(listing)), selector)
        product_integrity(built)
        require(digest(copy_path) == sha(descriptor), "enumerated descriptor changed")
        argv = base + ["-resultBundlePath", str(directory / "original.xcresult"), "-collect-test-diagnostics", "never"]
        write(directory / "invocation.json", {"argv": argv, "binding": binding, "enumerationSHA256": digest(listing), "descriptorSHA256": sha(descriptor)})
        outcome["testInvoked"] = True
        test_log, result = commands.run(argv, name + "-test", 900, checked=False)
        outcome["command"] = result
        require(result["status"] == "PASS_COMMAND", "original XCTest command failed")
    except BaseException as exc:
        primary = exc
        outcome["firstFailure"] = error(exc)
    result_bundle = directory / "original.xcresult"
    if result_bundle.is_dir():
        for kind in ("summary", "tests"):
            try:
                output, _ = commands.run(["xcrun", "xcresulttool", "get", "test-results", kind,
                    "--path", str(result_bundle), "--format", "json"], name + "-" + kind, capacity=False)
                value = raw(output)
                decode(value)
                write_bytes(directory / (kind + ".json"), value)
            except BaseException as exc:
                outcome["errors"].append({"phase": kind, **error(exc)})
        try:
            commands.run(["xcrun", "xcresulttool", "export", "attachments", "--path", str(result_bundle),
                          "--output-path", str(directory / "private-attachments")], name + "-attachments", 180, capacity=False)
        except BaseException as exc:
            outcome["errors"].append({"phase": "attachments", **error(exc)})
    try:
        outcome["productIntegrity"] = product_integrity(built)
        if primary is None and not outcome["errors"]:
            outcome["actual"] = qualify_execution(decode(raw(directory / "summary.json")), decode(raw(directory / "tests.json")), selector, udid, test_log)
            outcome["status"] = "PASS"
    except BaseException as exc:
        primary = primary or exc
        outcome["errors"].append({"phase": "qualification", **error(exc)})
    write(directory / "result.json", outcome)
    return outcome


def app_file(commands, udid, root, filename, label, maximum=4 * 1024**2):
    require(Path(filename).name == filename, "unscoped app filename")
    log, _ = commands.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"], label + "-container", 30, capacity=False)
    container = Path(raw(log, 4096).decode().strip())
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
    require(container.is_absolute() and container.resolve() == container and container.is_relative_to(owner), "wrong simulator app sandbox")
    path = container / "Library/Application Support" / filename
    require(path.resolve() == path and path.stat().st_nlink == 1, "app receipt link or alias")
    value = raw(path, maximum)
    write_bytes(root / filename, value)
    require(digest(path) == sha(value), "app receipt changed during preservation")
    return value


def continuation_ui(value, phase, fixture, capture, capture_raw, reopen_raw):
    require(value.get("protocol") == "heart-semantic-source-ui-continuation-v1" and value.get("status") == "PASS_UI"
            and value.get("phase") == phase, "actual UI receipt outcome differs")
    for key in ("sourceSHA", "runID", "runAttempt", "nonce", "accountID", "spaceID", "objectID", "blockID"):
        require(value.get(key) == fixture[key], "UI continuation owner differs: " + key)
    require(value.get("expectedText") == "Changed" and value.get("reference") == "Genesis 1:1"
            and value.get("markerSHA256") == sha(capture["native"]["marker"].encode())
            and value.get("captureReceiptSHA256") == sha(capture_raw) and value.get("reopenReceiptSHA256") == sha(reopen_raw)
            and value.get("realColdAppRelaunches") == 1 and value.get("originalMountedObserverEnabled") is False
            and value.get("independentNativeReadback") == "REQUIRED_SEPARATELY", "UI continuation proof incomplete")
    return {"phase": phase, "status": "PASS_UI_ONLY", "receiptSHA256": sha(json.dumps(value, sort_keys=True).encode()),
            "independentNativeReadback": "REQUIRED_SEPARATELY"}


def continuation_native(value, attached, original_raw, phase, fixture, capture, fixture_raw, capture_raw, reopen_raw, ui_raw, previous):
    require(value.get("protocol") == "heart-semantic-source-native-readback-v1" and value.get("status") == "PASS_NATIVE_READBACK"
            and value.get("phase") == phase and value.get("runtimeVersion") == VERSION, "native continuation outcome/runtime differs")
    for key in ("sourceSHA", "runID", "runAttempt", "nonce", "accountID", "spaceID", "objectID", "blockID"):
        require(value.get(key) == fixture[key], "native continuation owner differs: " + key)
    for key, payload in (("fixtureSHA256", fixture_raw), ("captureReceiptSHA256", capture_raw), ("reopenReceiptSHA256", reopen_raw), ("uiReceiptSHA256", ui_raw)):
        require(value.get(key) == sha(payload), "native continuation original receipt differs: " + key)
    require(all(type(value.get(k)) is int for k in ("contentMutationCallsIssuedByTest", "nativeCaptureOrApplyCallsIssuedByTest", "canonicalRecordCount"))
            and value.get("markerSHA256") == sha(capture["native"]["marker"].encode())
            and value.get("contentMutationCallsIssuedByTest") == 0 and value.get("nativeCaptureOrApplyCallsIssuedByTest") == 0
            and value.get("accountStoppedWithoutRemovingData") is True and value.get("appShutdownCompleted") is True
            and value.get("canonicalRecordCount") == (1 if phase == "linked" else 0), "native continuation required checks differ")
    require(type(value.get("processID")) is int and value["processID"] > 1 and native.uuid(str(value.get("generation", "")).lower()),
            "real native continuation owner absent")
    for prefix in ("canonicalRecords", "firstObjectShow", "secondObjectShow"):
        payload = native.decode64(value[prefix + "Base64"])
        require(sha(payload) == value[prefix + "SHA256"], "native payload hash differs")
    canonical = decode(native.decode64(value["canonicalRecordsBase64"]))
    require(type(canonical.get("version")) is int and canonical["version"] == 2
            and isinstance(canonical.get("records"), list)
            and len(canonical["records"]) == value["canonicalRecordCount"], "actual canonical record count/version differs")
    if phase == "linked":
        record = canonical["records"][0]
        require(record.get("spaceId") == fixture["spaceID"] and record.get("objectId") == fixture["objectID"]
                and "blockId" not in record, "actual canonical storage address differs")
        item = record["item"]
        require(isinstance(item.get("id"), str) and item["id"] and item.get("kind") == "ref"
                and item.get("providerID") == "sefaria" and item.get("externalID") == item.get("canonicalKey") == "Genesis 1:1",
                "actual canonical reference/item identity differs")
        metadata = item["customMetadata"]["pinkha.semanticTextAnchor"]
        require(isinstance(metadata, str) and len(metadata.encode()) <= 4096, "actual semantic metadata is not bounded JSON text")
        semantic = decode(metadata)
        require(type(semantic.get("version")) is int and semantic["version"] == 1
                and semantic.get("marker") == capture["native"]["marker"], "actual canonical semantic marker differs")
    first, first_block = boundary.shown(native.decode64(value["firstObjectShowBase64"]), fixture)
    second, second_block = boundary.shown(native.decode64(value["secondObjectShowBase64"]), fixture)
    require(first_block == second_block and sha(first_block) == value["targetBlockSHA256"], "actual independent target bytes differ")
    block = mounted.native_block(first_block, fixture["blockID"], "Changed")
    markers = [m for m in block["marks"] if m["kind"] == 5 and m["param"] == capture["native"]["marker"]]
    require(markers == [{"from": 0, "to": 7, "kind": 5, "param": capture["native"]["marker"]}], "edited anchor range/identity differs")
    excluded_original = native.decode64(fixture["excludedBlockBase64"])
    require(value["excludedBlockSHA256"] == sha(excluded_original), "excluded native block changed")
    for key in ("firstObjectShowBase64", "secondObjectShowBase64"):
        _, excluded = boundary.shown(native.decode64(value[key]), dict(fixture, blockID=fixture["excludedBlockID"]))
        require(excluded == excluded_original, "independent original excluded block bytes differ")
    if previous is not None:
        require(previous["targetBlockSHA256"] == value["targetBlockSHA256"] and previous["processID"] != value["processID"]
                and previous["generation"] != value["generation"], "unlink changed text or reused native owner")
    sanitized = {k: v for k, v in value.items() if not k.endswith("Base64")}
    require(attached == dict(sanitized, privateReadbackSHA256=sha(original_raw), privateReadbackBytes=len(original_raw)),
            "original native attachment does not match private response")
    return dict(sanitized, privateReadbackSHA256=sha(original_raw), independentRawComparison="PASS")


def preserve_final_sandbox(commands, udid, directory, *, application_invoked=False):
    """Retain originals on failure too, before any owned simulator deletion."""
    directory.mkdir(mode=0o700)
    log, result = commands.run(["xcrun", "simctl", "get_app_container", udid, BUNDLE, "data"],
                               "final-private-sandbox-container", 30, checked=False, capacity=False)
    if result["exitCode"] != 0:
        require(not application_invoked, "application ran but its original private sandbox is unavailable")
        return {"status": "NO_APPLICATION_CONTAINER", "commandExitCode": result["exitCode"]}
    container = Path(raw(log, 4096).decode().strip())
    owner = Path.home() / "Library/Developer/CoreSimulator/Devices" / udid
    require(container.is_absolute() and container.resolve() == container and container.is_relative_to(owner), "final sandbox owner differs")
    names = [FIXTURE, CAPTURE, REOPEN, "pinkha-semantic-page154-preflight.pb", "pinkha-semantic-page154-native-reply.json",
             "pinkha-semantic-page154-readback.pb", "pinkha-semantic-source-linked-native-readback.json",
             "pinkha-semantic-source-unlinked-native-readback.json"]
    rows = {}
    for name in names:
        source = container / "Library/Application Support" / name
        if not source.exists():
            rows[name] = {"status": "NOT_PRESENT"}
            continue
        require(source.resolve() == source and source.stat().st_nlink == 1, "final private file alias")
        value = raw(source, 4 * 1024**2)
        write_bytes(directory / name, value)
        require(digest(source) == sha(value), "final private evidence changed during capture")
        rows[name] = {"status": "COPIED_ORIGINAL", "bytes": len(value), "sha256": sha(value)}
    # Preserve diagnostics as separate originals. Their presence is never an
    # acceptance predicate and their content is not emitted in public receipts.
    observer_rows = {}
    observer_files = sorted((container / "Library/Application Support").glob("pinkha-semantic-source-entry-*.json"))
    require(len(observer_files) <= 64, "bounded private source-entry observations required")
    for source in observer_files:
        require(re.fullmatch(r"pinkha-semantic-source-entry-[1-9][0-9]{0,9}\.json", source.name)
                and source.resolve() == source and source.stat().st_nlink == 1,
                "private source-entry observation filename or alias differs")
        value = raw(source, 65536)
        write_bytes(directory / source.name, value)
        require(digest(source) == sha(value), "source-entry observation changed during capture")
        observer_rows[source.name] = {"status": "COPIED_ORIGINAL", "bytes": len(value), "sha256": sha(value)}
    return {"status": "PRESERVED_ORIGINAL_PRIVATE_FILES", "files": rows, "sourceEntryObservers": observer_rows,
            "engineCalls": 0, "rawPayloadsUploaded": False}


def qualify_external_producer(admission, source, receipt):
    """Bind the actual external producer; compiled App/UI remain one exact source."""
    external = admission.get("externalProducer")
    require(isinstance(external, dict) and set(external) == {"commit", "controller", "delta"},
            "closed external App14 producer provenance required")
    require(external["commit"] == "b9e9d2f3cce9adfe6ffd45a6cce6c19f8bbce421"
            and external["controller"]["sha256"] == "850de05de95f4ddeeef5349781f4ea7c4b72f85a42186b0e448c769e8afd43db"
            and external["delta"]["sha256"] == "2f818200a64ab777d296e00df531d7947506befb315d8b53ae22c136fa270583"
            and receipt.get("controllerSHA256") == external["controller"]["sha256"]
            and receipt.get("assemblyReceiptSHA256") == "a27b5f2f955d85b31157d7aedf7733e7d32e0acdac59920c0bd142ed304484bd",
            "actual producer and assembly pins differ")
    def git_bytes(commit, path):
        return subprocess.check_output(["git", "-C", str(source), "show", commit + ":" + path],
            env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), timeout=60)
    control, delta_raw = pinned(external["controller"]), pinned(external["delta"])
    require(control == git_bytes(external["commit"], "Tools/PinkhaDualEngineRuntime/build_main_immutable.py")
            and delta_raw == git_bytes(external["commit"], "docs/validation/20261126-native11619-apple-slices/app14-controller-delta.json"),
            "external source Git bytes differ")
    delta = decode(delta_raw)
    require(delta["sourceCommit"] == admission["sourceCommit"] and delta["newControllerSHA256"] == sha(control)
            and delta["fullInverseRestoresOriginal"] is True
            and delta["originalAppAndCompleteUITargetGatesUnchanged"] is True
            and delta["applicationBuilds"] == delta["testsExecuted"] == 0
            and len(delta["substitutions"]) == 11, "closed reviewed producer delta differs")
    restored = control.decode("utf8")
    for change in reversed(delta["substitutions"]):
        require(set(change) == {"old", "new", "occurrences"} and type(change["occurrences"]) is int
                and change["occurrences"] > 0 and restored.count(change["new"]) == change["occurrences"],
                "producer inverse occurrence differs")
        restored = restored.replace(change["new"], change["old"])
    original = git_bytes(admission["sourceCommit"], "Tools/PinkhaDualEngineRuntime/build_main_410b.py")
    require(restored.encode() == original and sha(original) == delta["originalControllerSHA256"]
            == "96a8c38d3ae29bc4d7f2999520fe925d3cc8f4be0541562cb04ce59de450e7f1",
            "full original App/fullUI producer inverse differs")
    return {"commit": external["commit"], "controllerSHA256": sha(control), "deltaSHA256": sha(delta_raw),
            "appSourceCommit": admission["sourceCommit"], "fullOriginalProducerInverse": True}

def admit_and_clone_products(admission, root, evidence, commands):
    """Shared E/F product admission. Never installs, launches, tests or builds."""
    original_source = Path(admission["sourceRoot"])
    built = {}
    build_receipt = decode(pinned(admission["producerReceipt"]))
    require(build_receipt.get("status") == "PASS_COMBINED_MAIN_AND_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and build_receipt.get("sourceCommit") == admission["sourceCommit"] and build_receipt.get("sourceUnchanged") is True
            and build_receipt.get("testsExecuted") == 0, "successful source-bound original combined build required")
    external_proof = qualify_external_producer(admission, original_source, build_receipt)
    inputs = build_receipt["inputs"]
    require(inputs["nativeSourceManifestSHA256"] == MANIFEST and inputs["nativeSHA256"] == NATIVE_BINARY
            and inputs["lockSHA256"] == LOCK and inputs["sdkReceiptSHA256"] == SDK_RECEIPT, "compiled native/SDK dependency identity differs")
    for kind in ("app", "ui"):
        step = build_receipt[kind]
        require(step["status"] == "PASS_BUILD_EXIT_0" and step["exitCode"] == 0
                and step["sourceCommit"] == admission["sourceCommit"] and step["ownedProcessGroup"] == "ABSENT_ESRCH"
                and "build-for-testing" in step["argv"] and all(any("-D " + flag in token for token in step["argv"]) for flag in FLAGS),
                "actual combined build flags/outcome differ")
        log = pinned(admission["producerLogs"][kind])
        require(sha(log) == step["logSHA256"] and len(log) == step["logBytes"] and b"** TEST BUILD SUCCEEDED **" in log,
                "original successful build stdout required")
    before_raw, after_raw = pinned(admission["sourceBefore"]), pinned(admission["sourceAfter"])
    require(decode(before_raw) == decode(after_raw), "producer source changed during build")
    write_bytes(evidence / "producer-source-before.json", before_raw)
    write_bytes(evidence / "producer-source-after.json", after_raw)
    source_proof = source_admission(original_source, admission["sourceCommit"], decode(before_raw), root / "helpers")
    source_proof["externalProducer"] = external_proof
    require(digest(original_source / "Tools/PinkhaDualEngineRuntime/source-manifest.json") == MANIFEST, "combined original source manifest differs")
    require(digest(original_source / "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib") == NATIVE_BINARY,
            "materialized native bytes differ from producer")
    require(admission["sourceCommit"] == "76f59f1e838991d1bbc7a07ecd08c6a2f15915c7"
            and admission["producerReceipt"]["sha256"] == "b6b3ba75809a9bebe6fbf2dbf77149def27cb1eabe1771f9d5d73108c56e00d6"
            and admission["sourceBefore"]["sha256"] == admission["sourceAfter"]["sha256"] == "fe01408dac1397de8aef9e1eb8a16d9bf637cd30303404bbca1810bede58f959"
            and admission["completeProducerProducts"]["sha256"] == "1941073f958baf7285b83ed411aef2b1a0d5dee75c2ff830510fb47b50d60109",
            "Only the exact original App14 producer and full source closure are admitted")
    require(not any(key in admission for key in ("menuPagingUIOverride", "sourceFocusUIOverride", "replacementSelectionUIOverride", "linkTargetUIOverride", "freshWarningUIOverride")),
            "Older product/UI pairing cannot be admitted as App14")
    full = decode(pinned(admission["completeProducerProducts"]))
    for kind in ("app", "ui"):
        declared = decode(pinned(admission["products"][kind]["manifest"]))
        files = {name: {k: v for k, v in row.items() if k != "mode"}
                 for name, row in declared.items() if row["kind"] != "directory"}
        expected = {row["path"]: {k: v for k, v in row.items() if k != "path"}
                    for row in full[kind + "-derived"]["entries"]}
        require(files == expected, "Complete product entries must equal the actual original producer")
    for kind in ("app", "ui"):
        row = admission["products"][kind]
        original = Path(row["root"])
        manifest = decode(pinned(row["manifest"]))
        require(inventory(original) == manifest, "original producer products changed")
        destination = root / (kind + "-products")
        commands.run(["cp", "-cR", str(original), str(destination)], "clone-" + kind + "-products", 180)
        require(inventory(destination) == manifest, "APFS retained original products differ")
        desc = destination / row["descriptorRelativePath"]
        require(desc.parent == destination and desc.suffix == ".xctestrun" and digest(desc) == row["descriptorSHA256"], "original descriptor pin differs")
        built[kind] = {"products": destination, "inventory": manifest, "copies": {}, "descriptor": desc,
                       "originalSelection": row["originalSelection"]}
        write(evidence / (kind + "-original-products.json"), manifest)
    app = built["app"]["products"] / "Debug-Anytype-iphonesimulator/Anytype.app"
    require(plistlib.loads(raw(app / "Info.plist"))["CFBundleIdentifier"] == BUNDLE, "actual app bundle differs")
    return source_proof, built, app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--admission", type=Path, required=True)
    parser.add_argument("--admission-sha256", required=True)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--keep-owned-simulator", action="store_true",
                        help="Retain the shutdown account for a separately verified private backup.")
    args = parser.parse_args()
    require(platform.system() == "Darwin" and platform.machine() == "arm64", "actual Apple Silicon host required")
    admission_raw = raw(args.admission)
    require(sha(admission_raw) == args.admission_sha256, "reviewed admission bytes differ")
    admission = decode(admission_raw)
    require(admission.get("schema") == "pinkha-combined-heart-semantics-admission-v1" and admission.get("executionEnvironment") == "SentinelX-owned-Mac"
            and admission.get("nativeManifestSHA256") == MANIFEST and admission.get("heartOverlaySHA256") == OVERLAY,
            "explicit combined native/source admission required")
    require(sha(raw(Path(__file__))) == admission["controllerSHA256"]
            and digest(Path(__file__).with_name("combined_heart_observations_gateway.py")) == OBSERVATION_HELPER,
            "exact reviewed controller files required")
    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "fresh owned execution root required")
    args.root.mkdir(mode=0o700)
    evidence, private = args.root / "evidence", args.root / "private"
    evidence.mkdir(mode=0o700); private.mkdir(mode=0o700)
    write_bytes(evidence / "admission.json", admission_raw)
    commands = Commands(args.root / "commands", args.root)
    result = {"status": "FAIL", "executionEnvironment": "SentinelX-owned-Mac", "sourceCommit": admission["sourceCommit"],
              "controllerSHA256": admission["controllerSHA256"], "observationHelperSHA256": OBSERVATION_HELPER,
              "nativeManifestSHA256": MANIFEST, "heartOverlaySHA256": OVERLAY, "stages": {},
              "appBuilds": 0, "uiBuilds": 0, "nativeBuilds": 0, "factoryMethodsExecuted": 0,
              "originalSimulatorStateReused": False, "physicalDevice": "NOT_RUN", "fullEAcceptance": False}
    device = None
    built = {}
    original_source = Path(admission["sourceRoot"])
    binding = {"sourceSHA": admission["sourceCommit"], "runID": str(time.time_ns() // 1000), "runAttempt": "1", "nonce": uuid.uuid4().hex}
    result["binding"] = binding
    result["bindingIdentityKind"] = "unique local microsecond receipt identity, not a GitHub Actions run ID"
    try:
        source_proof, built, app = admit_and_clone_products(admission, args.root, evidence, commands)
        result["sourceAdmission"] = source_proof
        for name in ("Tools/CurrentAppleValidation", "Tools/PinkhaSemanticAnchorWire/apple_consumer", "Tools/PinkhaSemanticAnchorWire/apple_mounted"):
            sys.path.insert(0, str(args.root / "helpers" / name))
        global common, native, mounted, boundary
        common = importlib.import_module("contracts")
        native = importlib.import_module("consumer_contract")
        mounted = importlib.import_module("mounted_contract")
        boundary = importlib.import_module("page154_boundary")
        policy = importlib.import_module("page154_contract")
        warning = importlib.import_module("warning_profile")
        specialized = importlib.import_module("combined_heart_observations_gateway")
        require(specialized.COMBINED_VERSION == VERSION and specialized.ORIGINAL_OVERLAY == OVERLAY, "combined observation profile differs")
        native.binding(binding)
        write(evidence / "execution-intent.json", {"binding": binding, "selectors": STAGES, "builds": 0, "purpose": "combined runtime requalification and new Heart source continuations"})
        log, _ = commands.run(["xcodebuild", "-version"], "xcode-version", 30)
        require(raw(log).decode().startswith("Xcode 27."), "Xcode 27 required")
        help_log, _ = commands.run(["xcodebuild", "-help"], "xcode-help", 30)
        help_text = raw(help_log).decode()
        require("-collect-test-diagnostics" in help_text and "never" in help_text, "documented diagnostic control unavailable")
        log, _ = commands.run(["xcrun", "simctl", "list", "runtimes", "--json"], "runtime-inventory", 30)
        rows = decode(raw(log))["runtimes"]
        runtime = [r for r in rows if r.get("identifier") == RUNTIME]
        require(len(runtime) == 1 and runtime[0].get("version") == OS_VERSION and runtime[0].get("buildversion") == OS_BUILD
                and runtime[0].get("isAvailable") is True, "exact installed runtime required")
        log, _ = commands.run(["xcrun", "simctl", "create", "E-Combined-Heart-" + binding["nonce"], DEVICE, RUNTIME], "create-owned-simulator", 60)
        device = raw(log, 4096).decode().strip()
        require(re.fullmatch(r"[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}", device), "actual owned simulator UUID required")
        write(evidence / "owned-simulator.json", {"udid": device, "runtime": runtime[0], "deviceType": DEVICE})
        result["ownedSimulator"] = device
        commands.run(["xcrun", "simctl", "boot", device], "boot-owned-simulator", 60)
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "await-owned-boot", 180)
        # Register the exact already-built App before the native fixture exists.
        # This uses the normal simulator installer and cannot relocate a prepared
        # account. XCTest still executes all six original methods unchanged.
        _, result["originalAppInstallation"] = commands.run(
            ["xcrun", "simctl", "install", device, str(app)], "install-original-before-preparation", 120)
        base = {"PINKHA_SIMULATOR_UI_DISPOSABLE": "1"}
        for key, suffix in (("sourceSHA", "SOURCE_SHA"), ("runID", "RUN_ID"), ("runAttempt", "RUN_ATTEMPT"), ("nonce", "NONCE")):
            base["PINKHA_SEMANTIC_MOUNTED_" + suffix] = binding[key]
        def run(name, additions):
            kind = "app" if STAGES[name].startswith("AnytypeTests/") else "ui"
            value = stage(commands, evidence, name, built[kind], app, binding, device, dict(base, **additions))
            result["stages"][name] = value
            require(value["status"] == "PASS", name + " actual method failed")
        run("preparation", {"PINKHA_SEMANTIC_MOUNTED_PREPARE": "1"})
        fixture_raw = app_file(commands, device, private, FIXTURE, "preserve-fixture", 65536)
        fixture = decode(fixture_raw)
        mounted.fixture(fixture, binding)
        ui_env = {"PINKHA_SEMANTIC_MOUNTED_TESTING": "1", "PINKHA_SEMANTIC_MOUNTED_FIXTURE_JSON": fixture_raw.decode()}
        run("mounted", ui_env)
        capture_raw = app_file(commands, device, private, CAPTURE, "preserve-capture", 65536)
        reopen_raw = app_file(commands, device, private, REOPEN, "preserve-reopen", 65536)
        capture, reopen = decode(capture_raw), decode(reopen_raw)
        result["mountedProof"] = specialized.observations(fixture, capture, reopen, capture_raw, binding)
        witness = capture.get("nativeBoundaryEvidence")
        require(isinstance(witness, dict) and witness.get("protocolVersion") == 1 and witness.get("extraNativeCalls") == 0
                and witness.get("source") == "actual-client-call-results" and set(witness["files"]) == set(boundary.FILES), "original three native boundaries required")
        boundaries = {}
        for role, filename in boundary.FILES.items():
            row = witness["files"][role]
            require(row["filename"] == filename, "native boundary filename differs")
            payload = app_file(commands, device, private, filename, "preserve-boundary-" + role.lower(), boundary.MAXIMUM)
            require(len(payload) == row["bytes"] and sha(payload) == row["sha256"], "native boundary original hash differs")
            boundaries[role] = payload
        result["nativeBoundaryComparison"] = boundary.verify(boundaries, fixture, capture, native, mounted)
        require(result["nativeBoundaryComparison"]["projectionFieldCount"] == 9, "full original nine-field projection required")
        result["originalAttachments"] = policy.mounted_attachments(evidence / "mounted/private-attachments", device, capture, reopen, binding, warning)
        write(evidence / "actual-mounted-qualified.json", {"binding": binding, "mounted": result["mountedProof"], "boundary": result["nativeBoundaryComparison"]})
        source_env = {"PINKHA_SEMANTIC_MOUNTED_FIXTURE_SHA256": sha(fixture_raw)}
        for key, payload in (("CAPTURE", capture_raw), ("REOPEN", reopen_raw)):
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_JSON"] = payload.decode()
            source_env["PINKHA_SEMANTIC_SOURCE_" + key + "_SHA256"] = sha(payload)
        previous, previous_raw = None, None
        for phase in ("linked", "unlinked"):
            if previous_raw is not None:
                source_env["PINKHA_SEMANTIC_SOURCE_LINKED_READBACK_SHA256"] = sha(previous_raw)
            run(phase + "-ui", dict(ui_env, **source_env, PINKHA_SEMANTIC_SOURCE_UI_PHASE=phase))
            ui_raw, ui_origin = policy.attachment(evidence / (phase + "-ui") / "private-attachments", "heart-semantic-source-ui-" + phase,
                                                STAGES[phase + "-ui"], device, maximum=65536)
            result[phase + "UIProof"] = continuation_ui(decode(ui_raw), phase, fixture, capture, capture_raw, reopen_raw)
            native_env = dict(source_env, PINKHA_SEMANTIC_SOURCE_READBACK_PHASE=phase,
                              PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_JSON=ui_raw.decode(), PINKHA_SEMANTIC_SOURCE_UI_RECEIPT_SHA256=sha(ui_raw))
            run(phase + "-native", native_env)
            native_raw = app_file(commands, device, private, "pinkha-semantic-source-" + phase + "-native-readback.json", "preserve-" + phase + "-readback")
            attached, origin = policy.attachment(evidence / (phase + "-native") / "private-attachments", "heart-semantic-source-native-" + phase,
                                                 STAGES[phase + "-native"], device, maximum=65536)
            value = decode(native_raw)
            proof = continuation_native(value, decode(attached), native_raw, phase, fixture, capture, fixture_raw, capture_raw, reopen_raw, ui_raw, previous)
            result[phase + "NativeProof"] = proof
            write(evidence / (phase + "-independent-native-qualified.json"), proof)
            previous, previous_raw = value, native_raw
        result["status"] = "PASS_SIX_ACTUAL_COMBINED_HEART_METHODS"
    except BaseException as exc:
        result["firstFailure"] = error(exc)
        write(private / "controller-failure.json", {"error": error(exc), "traceback": traceback.format_exc()})
    finally:
        cleanup = {"status": "PASS", "groups": [], "device": device, "errors": []}
        if device:
            try:
                result["finalPrivateSandbox"] = preserve_final_sandbox(commands, device, private / "final-sandbox-originals",
                    application_invoked=(any(value.get("testInvoked") is True for value in result["stages"].values())
                        or any((args.root / "commands" / (name + "-test") / "started.json").is_file() for name in STAGES)))
            except BaseException as exc:
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"phase": "private-evidence-retention", **error(exc)})
        # These are only process groups created by this controller. Do not kill
        # historical/reused PIDs after they have already been observed absent.
        for group in commands.groups:
            if group in commands.absent_groups:
                cleanup["groups"].append({"pgid": group, "absentAtOriginalExit": True,
                    "historicalGroupReprobed": False})
                continue
            present = Commands.present(group)
            cleanup["groups"].append({"pgid": group, "present": present})
            if present:
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"ownedGroupStillPresent": group})
        if device:
            for action in ("shutdown",):
                try:
                    log, row = commands.run(["xcrun", "simctl", action, device], "cleanup-" + action, 60, checked=False, capacity=False)
                    require(row["exitCode"] == 0, "owned simulator cleanup failed: " + action)
                except BaseException as exc:
                    cleanup["status"] = "FAIL"
                    cleanup["errors"].append(error(exc))
        try:
            result["finalProducts"] = {kind: product_integrity(value) for kind, value in built.items()}
            for name, expected_hash in HELPERS.items():
                require(digest(args.root / "helpers" / name) == expected_hash, "frozen pure helper changed")
            result["finalHelperIntegrity"] = "PASS"
        except BaseException as exc:
            cleanup["status"] = "FAIL"
            cleanup["errors"].append(error(exc))
        # Keep a failed continuation's original account and any uncopied private
        # evidence available for recovery. Only a fully accepted six-stage run
        # with complete final retention may delete its own simulator.
        if device:
            retained = result.get("finalPrivateSandbox", {})
            complete = (retained.get("status") == "PRESERVED_ORIGINAL_PRIVATE_FILES"
                        and retained.get("files")
                        and all(row.get("status") == "COPIED_ORIGINAL" for row in retained["files"].values()))
            if (result["status"] == "PASS_SIX_ACTUAL_COMBINED_HEART_METHODS" and cleanup["status"] == "PASS"
                    and complete and not args.keep_owned_simulator):
                try:
                    _, row = commands.run(["xcrun", "simctl", "delete", device], "cleanup-delete", 60, checked=False, capacity=False)
                    require(row["exitCode"] == 0, "owned simulator deletion failed")
                    cleanup["ownedSimulatorDeleted"] = True
                except BaseException as exc:
                    cleanup["status"] = "FAIL"
                    cleanup["errors"].append(error(exc))
            else:
                cleanup["ownedSimulatorDeleted"] = False
                cleanup["ownedSimulatorRetainedForRecovery"] = device
                cleanup["retentionComplete"] = bool(complete)
                if result["status"] == "PASS_SIX_ACTUAL_COMBINED_HEART_METHODS" and not complete:
                    cleanup["status"] = "FAIL"
                    cleanup["errors"].append({"phase": "private-evidence-retention", "message": "complete original final witnesses required"})
        if cleanup["status"] != "PASS":
            result["status"] = "FAIL"
        result["cleanup"] = cleanup
        write(evidence / "cleanup.json", cleanup)
        write(evidence / "execution.json", result)
    print(json.dumps({"status": result["status"], "sourceCommit": result["sourceCommit"], "stages": {k: v["status"] for k, v in result["stages"].items()},
                      "receipt": str(evidence / "execution.json"), "firstFailure": result.get("firstFailure")}, sort_keys=True))
    return 0 if result["status"] == "PASS_SIX_ACTUAL_COMBINED_HEART_METHODS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
