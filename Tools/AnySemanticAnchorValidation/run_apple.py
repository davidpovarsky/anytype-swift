#!/usr/bin/env python3
"""Owned standalone Apple acceptance for actual Any semantic anchors.
The source checkout is isolated and exact; old products are compilation caches,
never acceptance results. Only the two new native methods and one new UI method
run. Original descriptors, products, process records, and xcresults survive.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import signal
import stat
import subprocess
import sys
import time
import uuid

NATIVE_PRODUCER = "31ae2e63890b6e10af8413625534f6234ed263bb"
NATIVE_ARCHIVE = "0c8933d9b8d6e290dff0577cac3450c1a32fad0a24ebdf7e353c00f333a6811e"
NATIVE_RECEIPT = "190cc5f18507f4e3ef5db57e0252f37d10184c0281752ad75b34388bf33e3ec2"
NATIVE_MANIFEST = "15906eb27afea68cc7ec99242bffd6a8ea69517edb608a4421cce90c9a99a070"
HANLIN_COMMIT = "6bd6036dbca16c969689a5722550a54bebc1e851"
HANLIN_TREE = "edb0ced2bb3bde3696ae91eaf5fd56ec4482ca4a"
HANLIN_RECEIPT = "16f87f619eb53aa8909ba06113a65507c8d335fe9015403fe513d639e20422dc"
STAGES = {
    "native": {
        "scheme": "PinkhaAnyNativeHostedTests", "target": "PinkhaAnyNativeHostedTests",
        "methods": [
            "NativeDocumentPublicationTests/testSemanticAnchorCancelCaptureEditsResolveAndUndoUseRealNativeStore",
            "NativeDocumentPublicationTests/testSemanticAnchorStaleIntentAndRetiredReadbackCannotWriteOrPublishAgain"],
    },
    "ui": {
        "scheme": "PinkhaAnyNativeApp", "target": "PinkhaAnyNativeUITests",
        "methods": ["NativeLaunchTests/testActualSemanticSelectionCancelCreateEditAndColdReopen"],
    },
}

def require(value, reason):
    if not value:
        raise RuntimeError(reason)

def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    temporary.replace(path)

def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def inventory(root):
    result = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[relative] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            result[relative] = {"bytes": path.stat().st_size, "sha256": sha(path)}
    return result

def source_state(source, expected):
    require(git(source, "rev-parse", "HEAD") == expected, "source_commit_changed")
    require(not git(source, "status", "--porcelain", "--untracked-files=no"), "tracked_source_dirty")
    raw = subprocess.check_output(["git", "-C", str(source), "ls-files", "-z", "--",
                                   "Modules", "NativeApp", "Tools/AnyEnginePort",
                                   "Tools/AnyEngineValidation", "Tools/AnySemanticAnchorValidation"])
    files = {}
    for name in raw.decode().split("\0"):
        if not name:
            continue
        path = source / name
        if path.is_symlink():
            files[name] = {"kind": "symlink", "target": os.readlink(path)}
        elif path.is_file():
            files[name] = {"bytes": path.stat().st_size, "sha256": sha(path)}
        else:
            require(path.is_dir(), "tracked_source_missing:" + name)
    hanlin = source / "Dependencies/Hanlin"
    marker = hanlin / ".pinkha-source.json"
    require(marker.is_file() and not marker.is_symlink() and sha(marker) == HANLIN_RECEIPT,
            "canonical_hanlin_receipt_changed")
    sdk = json.loads(marker.read_text())
    require(sdk.get("revision") == HANLIN_COMMIT and sdk.get("tree") == HANLIN_TREE
            and sdk.get("fileCount") == 5_103 and not sdk.get("symlinks"), "canonical_hanlin_origin_changed")
    for name, expected_hash in sdk["files"].items():
        path = hanlin / name
        require(path.resolve() == path and path.is_relative_to(hanlin) and path.is_file()
                and sha(path) == expected_hash, "canonical_hanlin_source_changed:" + name)
    return {"commit": expected, "tree": git(source, "rev-parse", "HEAD^{tree}"),
            "files": files, "hanlinCommit": HANLIN_COMMIT, "hanlinTree": HANLIN_TREE,
            "hanlinReceiptSHA256": HANLIN_RECEIPT, "hanlinSourceFiles": sdk["files"]}

class Commands:
    def __init__(self, source, evidence):
        self.source = source
        self.evidence = evidence
        self.sequence = 0
        self.groups = []
        self.active = None

    def run(self, argv, name, timeout=180, check=True):
        self.sequence += 1
        stem = self.evidence / "commands" / (str(self.sequence).zfill(3) + "-" + name)
        stem.parent.mkdir(parents=True, exist_ok=True)
        out, err = stem.with_suffix(".stdout"), stem.with_suffix(".stderr")
        start = time.time()
        with out.open("xb") as stdout, err.open("xb") as stderr:
            child = subprocess.Popen(argv, cwd=self.source, stdout=stdout, stderr=stderr,
                                     start_new_session=True)
            self.active = child
            self.groups.append(child.pid)
            write(self.evidence / "owned-processes.json", {"groups": self.groups,
                  "activePID": child.pid, "activeCommand": name, "source": str(self.source)})
            problem = None
            try:
                while True:
                    try:
                        code = child.wait(timeout=2)
                        break
                    except subprocess.TimeoutExpired:
                        if time.time() - start > timeout:
                            problem = "owned_command_deadline"
                        elif name.endswith("-build") and shutil.disk_usage(self.source).free < 2 * 1024**3:
                            problem = "owned_build_stopped_before_disk_exhaustion"
                        if problem:
                            self.stop(child)
                            code = child.returncode
                            break
            finally:
                self.active = None
        record = {"argv": argv, "cwd": str(self.source), "pid": child.pid, "pgid": child.pid,
                  "startedUnix": start, "elapsedSeconds": time.time() - start,
                  "exitCode": code, "error": problem, "stdout": out.name, "stderr": err.name,
                  "stdoutSHA256": sha(out), "stderrSHA256": sha(err)}
        write(stem.with_suffix(".json"), record)
        self.last_record = record
        if check:
            require(problem is None and code == 0, "command_failed:" + name)
        return out

    def stop(self, child):
        if child.poll() is not None:
            return
        os.killpg(child.pid, signal.SIGTERM)
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=10)

    def json(self, argv, name, timeout=180):
        return json.loads(self.run(argv, name, timeout).read_text())

def relocate_owned_alternates(original, derived, evidence):
    # SwiftPM shared clones record absolute Git object paths. Retaining D3 by
    # atomic rename leaves those paths pointing at the old runner root. Relocate
    # only our copied metadata after proving the corresponding copied object
    # database equals the original retained one byte for byte.
    old = Path("/Users/m1/builds/actions-anytype/anytype-swift/anytype-swift/"
               "build/current-apple-native-ui-failed-45539471031-1/work/derived/SourcePackages")
    original_packages = original / "work/derived/SourcePackages"
    packages = derived / "SourcePackages"
    records = []
    for path in sorted((packages / "checkouts").glob("*/.git/objects/info/alternates")):
        require(not path.is_symlink(), "alternate_metadata_symlink")
        lines = path.read_text().splitlines()
        require(len(lines) == 1, "unexpected_alternate_count")
        previous = Path(lines[0])
        require(previous.is_relative_to(old / "repositories") and previous.name == "objects",
                "foreign_alternate_path")
        relative = previous.relative_to(old)
        retained = original_packages / relative
        replacement = packages / relative
        require(retained.is_dir() and replacement.is_dir()
                and retained.resolve() == retained and replacement.resolve() == replacement,
                "retained_object_database_missing")
        original_objects = inventory(retained)
        require(original_objects == inventory(replacement), "copied_object_database_changed")
        metadata = path.stat()
        require(metadata.st_uid == os.getuid(), "alternate_copy_not_owned_by_controller")
        mode = stat.S_IMODE(metadata.st_mode)
        # SwiftPM makes this metadata read-only. Its verified, private COW copy
        # is ours to relocate; preserve the original mode after the write.
        path.chmod(mode | stat.S_IWUSR)
        try:
            path.write_text(str(replacement) + "\n")
        finally:
            path.chmod(mode)
        records.append({"metadata": str(path.relative_to(derived)), "preservedMode": mode,
                        "original": str(previous), "replacement": str(replacement),
                        "retainedObjectFiles": len(original_objects),
                        "objectInventorySHA256": hashlib.sha256(
                            json.dumps(original_objects, sort_keys=True).encode()).hexdigest()})
    require(len(records) == 9, "expected_nine_original_swiftpm_shared_clones")
    write(evidence / "cache-relocation.json", {"scope": "owned-copy-only", "entries": records,
          "originalInputsModified": False, "sourceOrResultRelabeled": False})

def dependency_state(packages):
    roots = packages / "checkouts"
    require(roots.is_dir(), "package_checkouts_missing")
    entries = {}
    for path in sorted(roots.iterdir()):
        if not path.is_dir():
            continue
        require(not path.is_symlink(), "foreign_dependency_symlink")
        entries[path.name] = {"commit": git(path, "rev-parse", "HEAD"),
                              "tree": git(path, "rev-parse", "HEAD^{tree}"),
                              "dirty": git(path, "status", "--porcelain", "--untracked-files=no")}
        require(not entries[path.name]["dirty"], "dirty_package_checkout:" + path.name)
    return entries

def collect_cases(value):
    cases = []
    if isinstance(value, dict):
        if value.get("nodeType") == "Test Case":
            cases.append(value)
        for child in value.values():
            cases.extend(collect_cases(child))
    elif isinstance(value, list):
        for child in value:
            cases.extend(collect_cases(child))
    return cases

def qualify_test(commands, result, evidence, spec):
    summary = commands.json(["xcrun", "xcresulttool", "get", "test-results", "summary",
                             "--path", str(result)], spec["scheme"] + "-summary")
    tests = commands.json(["xcrun", "xcresulttool", "get", "test-results", "tests",
                           "--path", str(result)], spec["scheme"] + "-tests")
    write(evidence / "summary.json", summary)
    write(evidence / "tests.json", tests)
    cases = collect_cases(tests)
    wanted = set(spec["methods"])
    actual = []
    for case in cases:
        identifier = case.get("nodeIdentifier", "")
        identifier = identifier.removeprefix(spec["target"] + "/").removesuffix("()")
        actual.append(identifier)
        require(case.get("result") == "Passed", "original_case_not_passed:" + identifier)
    require(len(actual) == len(wanted) and set(actual) == wanted, "actual_method_set_changed")
    require(summary.get("passedTests") == len(wanted) and summary.get("failedTests") == 0
            and summary.get("skippedTests") == 0, "original_summary_not_complete_pass")
    return {"status": "PASS", "methods": actual, "summarySHA256": sha(evidence / "summary.json"),
            "testsSHA256": sha(evidence / "tests.json"), "xcresult": str(result)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--controller-commit", required=True)
    parser.add_argument("--retained-d3", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    root = args.run_root.resolve()
    require(re.fullmatch("[0-9a-f]{40}", args.commit) and
            re.fullmatch("[0-9a-f]{40}", args.controller_commit), "exact_commits_required")
    require(source.is_dir() and not root.exists() and source != root, "fresh_owned_root_required")
    require(str(root).startswith("/Users/m1/builds/any-semantic-"), "unexpected_owned_root")
    require(shutil.disk_usage(root.parent).free >= 5 * 1024**3, "insufficient_free_build_space")
    root.mkdir(mode=0o700)
    evidence = root / "evidence"
    evidence.mkdir(mode=0o700)
    commands = Commands(source, evidence)
    outcome = {"schema": "any-semantic-anchor-apple/v1", "sourceCommit": args.commit,
               "controllerCommit": args.controller_commit,
               "controllerPath": str(Path(__file__).resolve()), "controllerSHA256": sha(Path(__file__)),
               "status": "RUNNING", "stages": {}, "acceptedOldTestsRerun": 0,
               "nativeLibraryBuilds": 0, "physicalDevice": "NOT_RUN",
               "plannedApplicationBuilds": 2, "plannedUIRunnerBuilds": 1}
    write(evidence / "execution.json", outcome)
    device = None
    before = None

    def interrupted(signum, frame):
        if commands.active is not None:
            commands.stop(commands.active)
        raise RuntimeError("owned_controller_interrupted:" + str(signum))
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, interrupted)

    try:
        before = source_state(source, args.commit)
        write(evidence / "source-before.json", before)
        original = args.retained_d3.resolve()
        require(original.is_dir() and str(original).startswith("/Users/m1/builds/_retained-anytype/45539471031-1/"),
                "exact_retained_d3_required")
        archive = original / "work/native-originals/any.xcframework.zip"
        receipt = original / "work/native-originals/native-artifact.json"
        require(sha(archive) == NATIVE_ARCHIVE and sha(receipt) == NATIVE_RECEIPT, "native_originals_changed")
        native = json.loads(receipt.read_text())
        require(native.get("sourceManifestSHA256") == NATIVE_MANIFEST
                and native.get("sourceCommit") == NATIVE_PRODUCER, "native_origin_changed")
        commands.run([sys.executable, "-B", str(source / "Tools/AnyEnginePort/prepare_native_runtime.py"),
                      "install", "--artifact", str(archive.parent), "--producer-commit", NATIVE_PRODUCER],
                     "install-source-identical-any", 300)
        binding = json.loads((source / "Modules/PinkhaAnyRuntime/Vendor/consumer-binding.json").read_text())
        require(binding.get("consumerCommit") == args.commit and binding.get("archiveSHA256") == NATIVE_ARCHIVE
                and binding.get("status") == "SOURCE_IDENTICAL_NATIVE_ARTIFACT", "native_binding_changed")
        native_files = inventory(source / "Modules/PinkhaAnyRuntime/Vendor")
        write(evidence / "native-binding.json", {"binding": binding, "files": native_files})
        os.environ["PINKHA_ANY_NATIVE_ARTIFACT"] = "verified-v1"
        os.environ["ANY_BUILD_VERSION"] = "v0.5.0-pinkha.1"
        os.environ["DEVELOPER_DIR"] = "/Applications/Xcode.app/Contents/Developer"
        commands.run(["xcodebuild", "-version"], "xcode-version")
        commands.run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-version"], "simulator-sdk")
        derived = root / "derived"
        commands.run(["/bin/cp", "-cR", str(original / "work/derived"), str(derived)], "clone-compatible-cache", 600)
        # Original old products remain under the retained D3 root. Remove the
        # copied descriptors so each selected scheme must produce a new original.
        for old in (derived / "Build/Products").glob("*.xctestrun"):
            old.unlink()
        relocate_owned_alternates(original, derived, evidence)
        dependencies_before = dependency_state(derived / "SourcePackages")
        old_dependencies = json.loads((original / "evidence/actual-dependencies.json").read_text())
        require({name: entry["commit"] for name, entry in dependencies_before.items()}
                == old_dependencies["actualPackageCommits"], "original_dependency_pins_changed")
        write(evidence / "dependencies-before.json", dependencies_before)
        devices = commands.json(["xcrun", "simctl", "list", "--json"], "available-simulators")
        runtimes = [r for r in devices.get("runtimes", []) if r.get("isAvailable") is True
                    and r.get("version") == "27.0" and r.get("name", "").startswith("iOS")]
        types = [d for d in devices.get("devicetypes", []) if d.get("name") == "iPad Pro 13-inch (M5)"]
        require(len(runtimes) == len(types) == 1, "exact_original_ipad_runtime_unavailable")
        name = "AnySemantic-" + args.commit[:10] + "-" + uuid.uuid4().hex[:8]
        device = commands.run(["xcrun", "simctl", "create", name, types[0]["identifier"],
                               runtimes[0]["identifier"]], "create-owned-simulator").read_text().strip()
        require(re.fullmatch("[A-Fa-f0-9-]{36}", device), "owned_device_id_invalid")
        write(evidence / "simulator.json", {"ownedUDID": device, "name": name,
              "runtime": runtimes[0], "deviceType": types[0]})
        commands.run(["xcrun", "simctl", "boot", device], "boot-owned-simulator")
        commands.run(["xcrun", "simctl", "bootstatus", device, "-b"], "wait-owned-boot", 240)
        flags = ["ARCHS=arm64", "ONLY_ACTIVE_ARCH=YES", "CODE_SIGNING_ALLOWED=YES",
                 "CODE_SIGNING_REQUIRED=YES", "CODE_SIGN_IDENTITY=-", "PROVISIONING_PROFILE_SPECIFIER="]
        destination = "platform=iOS Simulator,id=" + device
        for stage, spec in STAGES.items():
            require(shutil.disk_usage(root).free >= 3 * 1024**3, "stage_build_capacity")
            stage_evidence = evidence / stage
            stage_evidence.mkdir()
            selectors = ["-only-testing:" + spec["target"] + "/" + method for method in spec["methods"]]
            commands.run(["xcodebuild", "build-for-testing", "-jobs", "2",
                "-project", str(source / "NativeApp/AnyNative.xcodeproj"),
                "-scheme", spec["scheme"], "-configuration", "Debug",
                "-destination", destination, "-derivedDataPath", str(derived),
                "-parallel-testing-enabled", "NO", "-disableAutomaticPackageResolution",
                "-onlyUsePackageVersionsFromResolvedFile",
                "-resultBundlePath", str(stage_evidence / "build.xcresult"),
                *selectors, *flags], stage + "-build", 3_900)
            candidates = []
            for path in (derived / "Build/Products").glob("*.xctestrun"):
                value = plistlib.loads(path.read_bytes())
                targets = [t for c in value.get("TestConfigurations", []) for t in c.get("TestTargets", [])]
                if spec["target"] in value or any(t.get("BlueprintName") == spec["target"] for t in targets):
                    candidates.append(path)
            require(len(candidates) == 1, "one_current_original_descriptor_required:" + stage)
            descriptor = candidates[0]
            shutil.copy2(descriptor, stage_evidence / "original.xctestrun")
            products = inventory(derived / "Build/Products")
            write(stage_evidence / "original-products.json", products)
            result = stage_evidence / "original.xcresult"
            require(shutil.disk_usage(root).free >= 2 * 1024**3, "stage_test_capacity")
            commands.run(["xcodebuild", "test-without-building", "-xctestrun", str(descriptor),
                "-destination", destination, "-parallel-testing-enabled", "NO",
                "-maximum-concurrent-test-simulator-destinations", "1",
                "-resultBundlePath", str(result), *selectors], stage + "-test", 2_400, check=False)
            # A nonzero original test still yields its original xcresult and
            # actual failures. No second test or altered expectation is started.
            test_exit = commands.last_record["exitCode"]
            try:
                qualified = qualify_test(commands, result, stage_evidence, spec)
                require(test_exit == 0, "original_test_process_failed")
                outcome["stages"][stage] = qualified
            except BaseException as error:
                outcome["stages"][stage] = {"status": "FAIL", "xcresult": str(result),
                    "reason": str(error)[:1_024], "testExitCode": test_exit}
            require(inventory(derived / "Build/Products") == products, "test_modified_compiled_products")
            write(evidence / "execution.json", outcome)
        after = source_state(source, args.commit)
        write(evidence / "source-after.json", after)
        require(before == after, "compiled_source_changed_during_acceptance")
        require(native_files == inventory(source / "Modules/PinkhaAnyRuntime/Vendor"), "native_runtime_changed")
        dependencies_after = dependency_state(derived / "SourcePackages")
        write(evidence / "dependencies-after.json", dependencies_after)
        require(dependencies_before == dependencies_after, "dependency_sources_changed")
        outcome["status"] = "PASS" if all(
            entry.get("status") == "PASS" for entry in outcome["stages"].values()
        ) and set(outcome["stages"]) == set(STAGES) else "FAIL"
    except BaseException as error:
        outcome["status"] = "FAIL"
        outcome["failure"] = {"type": type(error).__name__, "reason": str(error)[:1_024]}
    finally:
        cleanup = {"ownedUDID": device, "status": "RUNNING"}
        if commands.active is not None:
            commands.stop(commands.active)
        if device is not None:
            try:
                commands.run(["xcrun", "simctl", "shutdown", device], "shutdown-owned-simulator", 90, check=False)
                commands.run(["xcrun", "simctl", "delete", device], "delete-owned-simulator", 90)
                cleanup["status"] = "PASS"
            except BaseException as error:
                cleanup["status"] = "FAIL"
                cleanup["error"] = str(error)[:1_024]
                outcome["status"] = "FAIL"
        else:
            cleanup["status"] = "NO_DEVICE_CREATED"
        remaining = []
        for group in commands.groups:
            try:
                os.killpg(group, 0)
                remaining.append(group)
            except ProcessLookupError:
                pass
        cleanup["remainingOwnedGroups"] = remaining
        if remaining:
            cleanup["status"] = "FAIL"; outcome["status"] = "FAIL"
        write(evidence / "cleanup.json", cleanup)
        write(evidence / "execution.json", outcome)
    print(json.dumps({"status": outcome["status"], "evidence": str(evidence),
                      "failure": outcome.get("failure")}, sort_keys=True))
    return 0 if outcome["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
