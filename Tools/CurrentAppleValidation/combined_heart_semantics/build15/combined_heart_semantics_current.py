#!/usr/bin/env python3
"""Execute the six exact Heart semantic journeys on qualified combined Products.

This is an owned Sentinel execution, never a fabricated GitHub Actions run.
It builds nothing, preserves original results, and uses a fresh simulator.
The immutable admission JSON is separately hashed on the command line after
the sole app/UI producer has finished. Every source and product is verified
against the actual producer before any XCTest invocation.
"""
from __future__ import annotations

import ast

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
MANIFEST = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
APP15_SOURCE = "379ca3568f247d2fc218ed63df24796d461713c0"
BUILD15_PROOF = {'receipt': '0f0a1241dc76b6585a42866f5d129ea8f5aaa722addc74873245ebe71a09b735', 'source': 'b4fd4069ed3846797bde854caef134c4c7343e475ade555f8daffc34e8a3dc38', 'products': 'd4846f9c640dcb03e56626425ec0ec5649496de885ed464d5258cdfb9431424b', 'uiCopy': 'de23ccb4a8af6580a9348891ccbbd21289c75dc1e83addeb3d0ed5f045015fec', 'runtimeIdentity': '571f3148422dff2cf589060647e98981e337ef906d1c3a79ad8bd86de8872fa8'}  # Refuses execution until the actual terminal producer is pinned.
OVERLAY = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
VERSION = "pinkha-dual-runtime-v1-" + MANIFEST
NATIVE_BINARY = "f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763"
LOCK = "e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd"
SDK_RECEIPT = "b5b2ce165c1217140fcddd9289f6f496acb2e7fbd41ccd82fb3bc0a368002150"
OBSERVATION_HELPER = "425783c76858b542cb908e5d4c606e3d27b54d6e5bbc1e28a163cc18f13cf4de"
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
    # Positive ESRCH is the only absence proof. Permission denial is recorded,
    # bounded, and never converted into absence by a process-list heuristic.
    _group_observation_delays = (0, 0.05, 0.1, 0.2, 0.4, 0.8, 1.0)
    _termination_waits = ((signal.SIGTERM, 15), (signal.SIGKILL, 5))

    def __init__(self, root, cwd):
        self.root, self.cwd = Path(root), Path(cwd)
        self.root.mkdir(mode=0o700)
        self.groups = []
        self.absent_groups = set()
        self.cancelled = False
        self.environment = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
        self.environment["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

    def _terminate_owned_process(self, process, outcome):
        """Signal only this unreaped Popen child; always attempt bounded reaping."""
        for sig, wait_seconds in self._termination_waits:
            try:
                if process.poll() is not None:
                    return
            except BaseException as exc:
                outcome["cleanupErrors"].append({"phase": "owned-child-poll", **error(exc)})
                return
            event = {"signal": int(sig), "pid": process.pid, "at": time.time()}
            try:
                os.killpg(process.pid, sig)
                event["status"] = "SIGNAL_SENT_TO_OWNED_LIVE_CHILD_GROUP"
            except ProcessLookupError:
                event["status"] = "ABSENT_ESRCH"
            except BaseException as exc:
                event.update(status="SIGNAL_FAILED", error=error(exc))
                outcome["cleanupErrors"].append({"phase": "owned-child-signal", **error(exc)})
            outcome["termination"].append(event)
            # Reap even when signaling was denied. An exited zombie must not be
            # mistaken for a still-running command by a group-only poll.
            try:
                process.wait(timeout=wait_seconds)
                event["waitStatus"] = "CHILD_REAPED"
                return
            except subprocess.TimeoutExpired:
                event["waitStatus"] = "BOUNDED_WAIT_EXPIRED"
            except BaseException as exc:
                event["waitStatus"] = "WAIT_FAILED"
                outcome["cleanupErrors"].append({"phase": "owned-child-wait", **error(exc)})

    def _observe_exited_group(self, group):
        require(type(group) is int and group > 1, "positive owned process group required")
        observations = []
        for delay in self._group_observation_delays:
            if delay:
                time.sleep(delay)
            row = {"at": time.time()}
            try:
                present = self.present(group)
                require(type(present) is bool, "group observation must be explicit")
                row["status"] = "PRESENT" if present else "ABSENT_ESRCH"
            except PermissionError as exc:
                row.update(status="UNRESOLVED_PERMISSION_DENIED", error=error(exc))
            except BaseException as exc:
                row.update(status="UNRESOLVED_OBSERVATION_ERROR", error=error(exc))
                observations.append(row)
                return {"status": row["status"], "present": None, "observations": observations}
            observations.append(row)
            if row["status"] == "ABSENT_ESRCH":
                # Stop immediately: an absent historical PGID must not be
                # queried again after it could have been reused.
                return {"status": "ABSENT_ESRCH", "present": False, "observations": observations}
        last = observations[-1]["status"]
        return {"status": last, "present": True if last == "PRESENT" else None,
                "observations": observations}

    def run(self, argv, label, timeout=120, *, checked=True, capacity=True):
        require(re.fullmatch(r"[a-z0-9-]+", label), "scoped command label required")
        require(not self.cancelled, "owned execution cancelled")
        require(type(timeout) in (int, float) and 0 < timeout < float("inf"), "bounded positive timeout required")
        directory = self.root / label
        directory.mkdir(mode=0o700)
        started, minimum = time.time(), shutil.disk_usage(self.root).free
        started_monotonic = time.monotonic()
        require(not capacity or minimum >= FLOOR, "free space below owned 2 GiB guard")
        log = directory / "original.log"
        outcome = {"argv": list(map(str, argv)), "cwd": str(self.cwd), "startedAt": started,
                   "timeoutSeconds": timeout, "freeBytesBefore": minimum, "status": "FAIL",
                   "cleanupErrors": [], "termination": []}
        reason, process, spawn_failure, code = None, None, None, None
        with log.open("xb") as stream:
            try:
                process = subprocess.Popen(argv, cwd=self.cwd, env=self.environment, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
            except BaseException as exc:
                spawn_failure = exc
                outcome["spawnError"] = error(exc)
            if process is not None:
                self.groups.append(process.pid)
                # This is a newly created generation, even if the kernel reused
                # an older, positively absent PID within this controller.
                self.absent_groups.discard(process.pid)
                outcome.update(pid=process.pid, pgid=process.pid)
                try:
                    write(directory / "started.json", outcome)
                    while process.poll() is None:
                        minimum = min(minimum, shutil.disk_usage(self.root).free)
                        if capacity and minimum < FLOOR:
                            reason = "OWNED_RESOURCE_FLOOR"
                        elif time.monotonic() - started_monotonic > timeout:
                            reason = "OWNED_TIMEOUT"
                        if reason:
                            raise TimeoutError(reason)
                        time.sleep(1)
                except BaseException as exc:
                    reason = reason or str(exc)
                    outcome["interruption"] = error(exc)
                    # Preserve the first error before cleanup can fail.
                    try:
                        write(directory / "interruption.json",
                              {"pid": process.pid, "reason": reason, "at": time.time(),
                               "interruption": outcome["interruption"]})
                    except BaseException as receipt_exc:
                        outcome["cleanupErrors"].append(
                            {"phase": "interruption-receipt", **error(receipt_exc)})
                    self._terminate_owned_process(process, outcome)
                try:
                    code = process.wait(timeout=1)
                except BaseException as exc:
                    outcome["cleanupErrors"].append({"phase": "final-owned-child-wait", **error(exc)})
        command_status = ("PASS_COMMAND" if code == 0 and reason is None and spawn_failure is None
                          and not outcome["cleanupErrors"] else "FAIL_COMMAND")
        outcome.update(exitCode=code, finishedAt=time.time(), minimumFreeBytes=minimum,
                       logSHA256=digest(log), logBytes=log.stat().st_size,
                       commandStatus=command_status, status="EXIT_RECORDED_PENDING_GROUP_OBSERVATION")
        if process is None:
            outcome["status"] = "SPAWN_FAILURE_RECORDED"
        # This exclusive receipt exists before any read-only killpg probe.
        # An EPERM cannot erase the original exit code, log, or interruption.
        exit_receipt = directory / "process-exit.json"
        write(exit_receipt, outcome)
        outcome["processExitReceipt"] = {"path": str(exit_receipt), "sha256": digest(exit_receipt),
                                         "bytes": exit_receipt.stat().st_size}
        if process is None:
            group = {"status": "NOT_CREATED", "present": None, "observations": []}
        else:
            group = self._observe_exited_group(process.pid)
        outcome.update(ownedGroupPresentAfterExit=group["present"],
                       ownedGroupObservationStatus=group["status"],
                       ownedGroupObservations=group["observations"])
        if group["status"] == "ABSENT_ESRCH":
            self.absent_groups.add(process.pid)
        outcome["status"] = ("PASS_COMMAND" if command_status == "PASS_COMMAND"
                             and group["status"] == "ABSENT_ESRCH" else "FAIL_COMMAND")
        write(directory / "result.json", outcome)
        if spawn_failure is not None:
            raise spawn_failure
        require(group["status"] == "ABSENT_ESRCH", label + " owned group absence unresolved")
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
    """Bind the actual App15 producer and its complete reviewed byte inverse."""
    external = admission.get("externalProducer")
    require(isinstance(external, dict) and set(external) == {"commit", "controller", "delta"},
            "closed external App15 producer provenance required")
    require(admission["sourceCommit"] == APP15_SOURCE
            and external["commit"] == "08ed46041a4d45164e000212eb26fd1c98fee966"
            and external["controller"]["sha256"] == "617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68"
            and external["delta"]["sha256"] == "a51a979919a5dbe37dd174cdd89e8772ed58c1130b3fd34276d88e6a909bba8d"
            and receipt.get("controllerSHA256") == APP15_CONTINUATION["controllerSHA256"]
            and receipt.get("originalProducer") == {"path": "/Users/m1/development/anytype-d-active-20261125/main15/control-main617/build_main_permission.py",
                "sha256": external["controller"]["sha256"], "gitCommit": external["commit"]}
            and receipt.get("assemblyReceiptSHA256") == "c9c90e3a12868bcedf5f0a4f116c4dc1c388bdcddd0e9f0170c047684c500231",
            "actual producer and assembly pins differ")
    def git_bytes(commit, path):
        return subprocess.check_output(["git", "-C", str(source), "show", commit + ":" + path],
            env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), timeout=60)
    control, delta_raw = pinned(external["controller"]), pinned(external["delta"])
    require(control == git_bytes(external["commit"], "Tools/PinkhaDualEngineRuntime/build_main_permission.py")
            and delta_raw == git_bytes(external["commit"], "Tools/PinkhaDualEngineRuntime/build_main_permission_delta.json"),
            "external source Git bytes differ")
    delta = decode(delta_raw)
    require(delta["protocol"] == "App15-original-main-builder-byte-inverse-v1"
            and delta["candidateSHA256"] == sha(control)
            and delta["originalSHA256"] == "850de05de95f4ddeeef5349781f4ea7c4b72f85a42186b0e448c769e8afd43db"
            and delta["actualStagingReceiptSHA256"] == "dc0617be03813129b76a09a347c15f835611e6520f4f261825abacab16a71781"
            and delta["inverseRestoresEveryOriginalByte"] is True
            and delta["builds"] == delta["tests"] == 0 and len(delta["changes"]) == 29,
            "closed reviewed producer delta differs")
    restored = control.decode("utf8")
    for change in reversed(delta["changes"]):
        require(set(change) == {"old", "new", "count", "newPositions"}
                and type(change["count"]) is int and change["count"] > 0
                and isinstance(change["newPositions"], list)
                and len(change["newPositions"]) == change["count"]
                and all(type(x) is int and x >= 0 for x in change["newPositions"])
                and change["newPositions"] == sorted(set(change["newPositions"])),
                "producer inverse occurrence contract differs")
        for position in reversed(change["newPositions"]):
            require(restored[position:position + len(change["new"])] == change["new"],
                    "producer inverse exact byte position differs")
            restored = restored[:position] + change["old"] + restored[position + len(change["new"]):]
    original = git_bytes(APP15_SOURCE, "Tools/PinkhaDualEngineRuntime/build_main_immutable.py")
    require(restored.encode() == original and sha(original) == delta["originalSHA256"],
            "full original App/fullUI producer inverse differs")
    require(receipt["inputs"]["stagingReceiptSHA256"] == delta["actualStagingReceiptSHA256"]
            and receipt["inputs"]["sourceRoot"] == "/Users/m1/development/anytype-d-active-20261125/main14/source"
            and receipt["inputs"]["appDerived"] == "/Users/m1/development/anytype-d-active-20261125/main14/app-derived",
            "actual retained warm workspace provenance differs")
    return {"commit": external["commit"], "controllerSHA256": sha(control), "deltaSHA256": sha(delta_raw),
            "appSourceCommit": APP15_SOURCE, "fullOriginalProducerInverse": True}

def qualify_app15_continuation(admission, source, receipt):
    """Retain the failed producer and qualify its actual App/UI continuation separately."""
    require(isinstance(BUILD15_PROOF, dict), "Actual App15 terminal proof has not been pinned")
    row = admission.get("uiContinuation")
    require(isinstance(row, dict) and set(row) == {"commit", "controller", "admission", "compilerInputs",
            "compilerFileList", "originalInputs", "appProductsBefore", "appProductsAfter"},
            "closed original App/UI-continuation provenance required")
    require(row["commit"] == APP15_CONTINUATION["commit"]
            and row["controller"]["sha256"] == APP15_CONTINUATION["controllerSHA256"],
            "exact UI-only continuation source required")
    control = pinned(row["controller"])
    git_control = subprocess.check_output(["git", "-C", str(source), "show",
        row["commit"] + ":Tools/PinkhaDualEngineRuntime/resume_main_permission_ui.py"],
        env=dict(os.environ, GIT_OPTIONAL_LOCKS="0"), timeout=60)
    require(control == git_control, "continuation controller differs from its actual Git bytes")
    require(receipt["protocol"] == "pinkha-app15-original-app-ui-continuation-v1"
            and receipt["status"] == "PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
            and receipt["controllerSHA256"] == sha(control)
            and receipt["originalEvidence"] == "/Users/m1/development/anytype-d-active-20261125/main15/build15"
            and receipt["appBuildsThisInvocation"] == receipt["nativeBuildsThisInvocation"] == receipt["testsExecuted"] == 0
            and receipt["uiBuildsThisInvocation"] == 1 and receipt["originalAppProductsPreserved"] is True,
            "actual separate UI continuation scope differs")
    originals = row["originalInputs"]
    require(isinstance(originals, dict) and set(originals) == set(APP15_ORIGINAL_PINS),
            "all original failed-producer inputs must be retained")
    original_bytes = {}
    for name, expected in APP15_ORIGINAL_PINS.items():
        value = pinned(originals[name])
        require(sha(value) == expected, "original producer evidence differs: " + name)
        original_bytes[name] = value
    failure = decode(original_bytes["failure.json"])
    require(failure["status"] == "FAIL" and failure["sourceCommit"] == APP15_SOURCE
            and failure["error"] == "The actual AnytypeTests compiler input list must contain both new UIKit test sources"
            and receipt["originalFailedProducerOutcomeSHA256"] == APP15_ORIGINAL_PINS["failure.json"],
            "the original compiler-input collector failure must remain failed")
    require(original_bytes["source-before.json"] == original_bytes["source-after.json"]
            == pinned(admission["sourceBefore"]) == pinned(admission["sourceAfter"]),
            "continuation must retain the exact original App source")
    original_app = decode(original_bytes["app/result.json"])
    original_exit = decode(original_bytes["app/process-exit.json"])
    require(receipt["app"] == original_app
            and all(original_app.get(key) == value for key, value in original_exit.items())
            and original_app["status"] == original_exit["status"] == "PASS_BUILD_EXIT_0"
            and original_app["exitCode"] == original_exit["exitCode"] == 0
            and original_app["phase"] == "app" and original_app["sourceCommit"] == APP15_SOURCE
            and original_app["ownedProcessGroup"] == "ABSENT_ESRCH"
            and original_app["cleanupErrors"] == original_app["termination"] == []
            and original_app["processExitReceiptSHA256"] == APP15_ORIGINAL_PINS["app/process-exit.json"]
            and receipt["originalAppResultSHA256"] == APP15_ORIGINAL_PINS["app/result.json"]
            and receipt["originalProcessExitSHA256"] == APP15_ORIGINAL_PINS["app/process-exit.json"]
            and receipt["originalAppLogSHA256"] == original_app["logSHA256"] == APP15_ORIGINAL_PINS["app/original.log"]
            and original_app["logBytes"] == len(original_bytes["app/original.log"])
            and pinned(admission["producerLogs"]["app"]) == original_bytes["app/original.log"],
            "actual successful original App exit/log must remain independently bound")
    require(decode(original_bytes["input-and-resource-admission.json"]) == receipt["inputs"]
            and original_bytes["runtime-identity-before.json"] == pinned(admission["runtimeIdentity"]["before"]),
            "original compiled inputs/runtime boundary differs")
    admission_raw = pinned(row["admission"])
    admitted = decode(admission_raw)
    require(sha(admission_raw) == receipt["continuationAdmissionSHA256"]
            and admitted["status"] == "PASS_EXACT_ORIGINAL_APP_AND_UNEXECUTED_UI_PHASE_ADMISSION"
            and admitted["sourceCommit"] == APP15_SOURCE
            and admitted["originalPinnedFiles"] == APP15_ORIGINAL_PINS
            and admitted["originalProducer"] == receipt["originalProducer"]
            and admitted["originalEvidence"] == receipt["originalEvidence"]
            and admitted["stagingReceiptSHA256"] == "dc0617be03813129b76a09a347c15f835611e6520f4f261825abacab16a71781"
            and all(admitted[key] == 0 for key in ("uiPhaseInvocations", "appPhaseInvocations", "nativeBuilds", "testsExecuted")),
            "original UI-continuation admission differs")
    producer_raw = pinned(admission["externalProducer"]["controller"])
    producer_text = producer_raw.decode("utf8")
    tree = ast.parse(producer_text)
    outer = [node for node in tree.body if isinstance(node, ast.Try)]
    require(len(outer) == 1 and tree.body[-1] is outer[0], "original producer shape differs")
    starts = [i for i, node in enumerate(outer[0].body) if isinstance(node, ast.Assign)
              and any(isinstance(target, ast.Name) and target.id == "ui_source" for target in node.targets)]
    require(len(starts) == 1, "one original complete UI body required")
    ui_nodes = outer[0].body[starts[0]:-1]
    calls = [node for item in ui_nodes for node in ast.walk(item)
             if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_phase"]
    require(len(calls) == 1 and ast.literal_eval(calls[0].args[0]) == "ui",
            "continuation must execute only the original complete UI phase")
    body = "\n".join(ast.get_source_segment(producer_text, node) for node in ui_nodes).encode()
    require(admitted["originalUIStatements"] == len(ui_nodes) == 26
            and sha(body) == admitted["originalUIBodySHA256"] == receipt["originalUIBodySHA256"],
            "complete original UI statement bytes differ")
    compiler_raw, list_raw = pinned(row["compilerInputs"]), pinned(row["compilerFileList"])
    compiler = decode(compiler_raw)
    require(sha(compiler_raw) == admitted["compilerInputQualificationSHA256"] == receipt["compilerInputQualificationSHA256"]
            and sha(list_raw) == compiler["originalFileListSHA256"] == APP15_CONTINUATION["fileListSHA256"]
            and compiler["status"] == "PASS_EXACT_SAME_FILE_COMPILER_INPUTS_NOT_TEST_EXECUTION"
            and compiler["testsExecuted"] == 0
            and compiler["originalFailureSHA256"] == APP15_ORIGINAL_PINS["failure.json"]
            and compiler["originalAppResultSHA256"] == APP15_ORIGINAL_PINS["app/result.json"]
            and compiler["originalFileList"] == APP15_CONTINUATION["fileList"],
            "actual compiler-input qualification differs")
    pairs = compiler["sourceFiles"]
    require(isinstance(pairs, list) and len(pairs) == len(APP15_UIKIT_INPUTS) == 2,
            "both actual new UIKit compiler inputs required")
    by_name = {Path(pair["gitPath"]).name: pair for pair in pairs}
    require(set(by_name) == set(APP15_UIKIT_INPUTS), "compiler qualification names differ")
    original_source = Path(receipt["inputs"]["sourceRoot"])
    source_files = decode(original_bytes["source-before.json"])["files"]
    for name, expected in APP15_UIKIT_INPUTS.items():
        pair = by_name[name]
        git_name, compiler_name = "AnyTypeTests/Pinkha/" + name, "AnytypeTests/Pinkha/" + name
        git_path, compiler_path = source / git_name, source / compiler_name
        source_raw = raw(git_path)
        require(pair["gitPath"] == str(original_source / git_name)
                and pair["compilerPath"] == str(original_source / compiler_name)
                and pair["sameActualFile"] is True
                and pair["sha256"] == sha(source_raw) == expected and pair["bytes"] == len(source_raw)
                and source_files[git_name] == {"bytes": len(source_raw), "sha256": expected}
                and not git_path.is_symlink() and not compiler_path.is_symlink()
                and git_path.samefile(compiler_path) and raw(compiler_path) == source_raw
                and list_raw.decode("utf8").splitlines().count(pair["compilerPath"]) == 1,
                "same actual original compiler input identity differs")
        marker = "SwiftCompile normal arm64 " + pair["compilerPath"] + " (in target 'AnytypeTests' from project 'Anytype')"
        require(pair["exactOriginalSwiftCompileLine"] == marker
                and marker.encode() in original_bytes["app/original.log"].splitlines(),
                "original actual SwiftCompile line is absent")
        require(set(pair["fileIdentity"]) == {"device", "inode", "mode"}
                and all(type(pair["fileIdentity"][key]) is int and pair["fileIdentity"][key] > 0
                        for key in ("device", "inode", "mode")),
                "original observed filesystem identity missing")
    product_before, product_after = pinned(row["appProductsBefore"]), pinned(row["appProductsAfter"])
    require(product_before == product_after
            and sha(product_before) == receipt["originalAppProductsBeforeSHA256"]
            and sha(product_after) == receipt["originalAppProductsAfterSHA256"],
            "original successful App Products were changed during UI continuation")
    snapshot = decode(product_before)
    entries = snapshot["entries"]
    require(snapshot["base"] == str(Path(receipt["inputs"]["appDerived"]) / "Build/Products")
            and len(entries) == admitted["existingAppProductEntries"]
            and len({item["path"] for item in entries}) == len(entries),
            "complete original App product snapshot differs")
    portable = {item["path"]: {key: value for key, value in item.items() if key != "path"}
                for item in entries if item["path"] != "."}
    require(portable == decode(pinned(admission["products"]["app"]["manifest"])),
            "retained full App bytes/modes/links differ from the original successful App")
    return {"protocol": receipt["protocol"], "continuationCommit": row["commit"],
            "continuationControllerSHA256": sha(control), "originalProducerOutcome": "FAIL",
            "originalFailureSHA256": APP15_ORIGINAL_PINS["failure.json"],
            "originalAppResultSHA256": APP15_ORIGINAL_PINS["app/result.json"],
            "compilerInputQualificationSHA256": sha(compiler_raw), "originalUIBodySHA256": sha(body),
            "originalAppProductsPreserved": True, "appBuildsThisContinuation": 0,
            "uiBuildsThisContinuation": 1, "testsExecuted": 0}


def qualify_app15_runtime(admission, source):
    """Compare the compiled consumer with the exact actual two-slice identity proof."""
    require(isinstance(BUILD15_PROOF, dict), "Actual App15 terminal proof has not been pinned")
    helper = source / "Tools/PinkhaDualEngineRuntime/runtime_identity.py"
    require(digest(helper) == "306c0cabcf39c6de55470d642cf5b9e6e9176d73351966330b90cf333b9359b0",
            "original strict runtime identity validator differs")
    spec = importlib.util.spec_from_file_location("app15_original_runtime_identity", helper)
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    manifest = raw(source / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json")
    require(sha(manifest) == MANIFEST, "exact current native manifest required")
    expected = runtime.identity(manifest, "2026-11-26")
    require(expected["sourcePins"]["any"] == "8fbd1e819fb132ac0e0a848d2ddf5c5714189b81"
            and expected["heartVersion"] == VERSION,
            "current native authoring source/date/version differs")
    consumer = runtime.qualify_consumer(
        raw(source / "Modules/ProtobufMessages/Sources/PinkhaAnyEmbeddedBridge.swift"), expected)
    values = admission.get("runtimeIdentity")
    require(isinstance(values, dict) and set(values) == {"before", "after-app", "after-ui"},
            "every actual producer runtime identity boundary required")
    originals = [pinned(values[phase]) for phase in ("before", "after-app", "after-ui")]
    require(all(sha(value) == BUILD15_PROOF["runtimeIdentity"] for value in originals)
            and originals[0] == originals[1] == originals[2],
            "actual before/after runtime identity proof differs")
    proof = decode(originals[0])
    require(proof["status"] == "PASS_EXACT_CONSUMER_AND_ORIGINAL_LINKER_IDENTITIES_NOT_RUNTIME_ACCEPTANCE"
            and proof["identity"] == expected and proof["consumer"] == consumer
            and proof["nativeVersionExecutedByThisCheck"] is False
            and proof["applicationBuilds"] == 0 and proof["applicationAcceptanceClaimed"] is False
            and set(proof["slices"]) == {"device", "simulator"},
            "closed original consumer and two-slice proof differs")
    for kind, identifier in (("simulator", "ios-arm64-simulator"), ("device", "ios-arm64")):
        binary = source / "Dependencies/Middleware/Lib.xcframework" / identifier / "Lib.framework/Lib"
        require(digest(binary) == proof["slices"][kind]["binarySHA256"]
                and binary.stat().st_size == proof["slices"][kind]["binaryBytes"],
                "materialized exact runtime slice differs")
    return {"identity": expected, "producerRuntimeProofSHA256": sha(originals[0]),
            "consumer": consumer, "nativeRuntimeExecutedByThisCheck": False}

def admit_and_clone_products(admission, root, evidence, commands):
    """Shared E/F product admission. Never installs, launches, tests or builds."""
    require(isinstance(BUILD15_PROOF, dict), "Actual App15 terminal proof has not been pinned")
    require(root.resolve() == root and stat.S_IMODE(root.lstat().st_mode) == 0o700,
            "Exact product clones require the existing private execution root")
    original_source = Path(admission["sourceRoot"])
    built = {}
    build_receipt = decode(pinned(admission["producerReceipt"]))
    require(build_receipt.get("status") == "PASS_ORIGINAL_APP_AND_CONTINUED_COMPLETE_UI_BUILD_NOT_ACCEPTANCE"
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
    source_proof["uiContinuation"] = qualify_app15_continuation(admission, original_source, build_receipt)
    require(digest(original_source / "Tools/PinkhaDualEngineRuntime/source-permission-manifest.json") == MANIFEST, "combined original source manifest differs")
    require(digest(original_source / "Dependencies/Middleware/Lib.xcframework/ios-arm64-simulator/Lib.framework/Lib") == NATIVE_BINARY,
            "materialized native bytes differ from producer")
    require(admission["sourceCommit"] == APP15_SOURCE
            and admission["producerReceipt"]["sha256"] == BUILD15_PROOF["receipt"]
            and admission["sourceBefore"]["sha256"] == admission["sourceAfter"]["sha256"] == BUILD15_PROOF["source"]
            and admission["completeProducerProducts"]["sha256"] == BUILD15_PROOF["products"]
            and admission["originalUICopy"]["sha256"] == BUILD15_PROOF["uiCopy"],
            "Only the exact original App15 producer and full source closure are admitted")
    require(not any(key.endswith("UIOverride") for key in admission),
            "Older product/UI pairing cannot be admitted as App15")
    source_proof["runtimeIdentity"] = qualify_app15_runtime(admission, original_source)
    ui_copy = decode(pinned(admission["originalUICopy"]))
    require(ui_copy["generatorSHA256"] == "7bf69636b42875aa7dd0fa39c11393e02e6760ef502cf68ef47b740f3bd066c0"
            and len(ui_copy["copiedFiles"]) == 12
            and digest(original_source / "PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift")
                == "8834541f5a47da80b460ecb96b20c930813b743d94f285fc1efba8a93f65ee4d",
            "Exact same-source complete UI and reviewed Link-glyph method required")
    for copied in ui_copy["copiedFiles"]:
        require(digest(original_source / copied["path"]) == copied["sha256"],
                "Original complete UI source differs")
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
        previous_mask = os.umask(0)
        try:
            commands.run(["cp", "-cR", str(original), str(destination)], "clone-" + kind + "-products", 180)
        finally:
            os.umask(previous_mask)
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
            try:
                present = Commands.present(group)
                cleanup["groups"].append({"pgid": group, "present": present})
                if present:
                    cleanup["status"] = "FAIL"
                    cleanup["errors"].append({"ownedGroupStillPresent": group})
                else:
                    commands.absent_groups.add(group)
            except BaseException as exc:
                cleanup["status"] = "FAIL"
                cleanup["errors"].append({"phase": "owned-group-observation",
                                          "pgid": group, **error(exc)})
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
