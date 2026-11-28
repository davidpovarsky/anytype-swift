#!/usr/bin/env python3
"""One owned Swift command for the exact Sharing role3 package.
Prepared source only. Runtime requires explicit current owner admission.
The unmodified f9de helper exclusively owns all child lifecycle handling.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import stat
import time
import traceback

ROOT = Path("/mnt/development/projects/evidence/pinkha-wave2-sharing-role3-component-20261128")
PREPARED = ROOT / "prepared"
PACKAGE = ROOT / "package"
OUT = ROOT / "attempt1"
RUNTIME = ROOT / "runtime"
BUILD = RUNTIME / "build"
SWIFT = Path("/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift")
TOOLCHAIN = SWIFT.parent.parent
CAP = 268435456
CHILD_SECONDS = 300
OUTER_SECONDS = 360
HELPER_SHA = "f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56"
INPUT_SHA = "b3d739b25605697acbf41a4ce97cd7dc0e9f125acc25e9cb774eaadab610dd66"
PLAN_SHA = "9b68fce7d225973e767f262fdabeca2aa9b0e1854d1079e7d09c60d1879c247c"
METHODS = (
    "testPerMemberRoleOptionsPreserveLegacyAndDenyMissingTargets",
    "testPerMemberRoleChangesStaySeparateFromApprovalAndRemoval",
    "testPerMemberRoleOptionsRejectMalformedEntries",
)
FILTER = r"^PinkhaSharingTests\.SharingAuthorityTests/(?:" + "|".join(METHODS) + r")$"


def regular_bytes(path, maximum=16777216, unique=False):
    path = Path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or (unique and before.st_nlink != 1):
        raise RuntimeError("expected a qualified regular physical file: " + str(path))
    if before.st_size > maximum:
        raise RuntimeError("file exceeds recorded bound: " + str(path))
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        opened = os.fstat(fd)
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise RuntimeError("file identity changed during open")
        with os.fdopen(fd, "rb", closefd=False) as stream:
            data = stream.read(maximum + 1)
        after = os.fstat(fd)
    finally:
        os.close(fd)
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if len(data) > maximum or identity(before) != identity(after):
        raise RuntimeError("file changed during bounded read: " + str(path))
    return data


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def digest(path):
    return sha_bytes(regular_bytes(path, CAP))


def save(path, value):
    path = Path(path)
    if not path.is_relative_to(OUT) or path.parent.resolve() != path.parent:
        raise RuntimeError("receipt path escaped fixed owned output")
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def pinned(path, size, expected):
    data = regular_bytes(path, unique=True)
    if len(data) != size or sha_bytes(data) != expected:
        raise RuntimeError("immutable input mismatch: " + str(path))
    return data


def source_snapshot(manifest):
    if PACKAGE.resolve() != PACKAGE:
        raise RuntimeError("package must be a physical owned directory")
    expected = {x["relativePath"]: x for x in manifest["files"]}
    actual = []
    for base, directories, files in os.walk(PACKAGE, followlinks=False):
        for name in directories:
            path = Path(base) / name
            if path.is_symlink():
                raise RuntimeError("package directory symlink refused")
        for name in files:
            actual.append(str((Path(base) / name).relative_to(PACKAGE)))
    if sorted(actual) != sorted(expected):
        raise RuntimeError("complete package inventory changed")
    rows = []
    for relative, item in sorted(expected.items()):
        path = PACKAGE / relative
        if path.resolve() != path or ".." in Path(relative).parts:
            raise RuntimeError("input path escaped physical package")
        data = pinned(path, item["bytes"], item["sha256"])
        info = path.stat()
        rows.append({"path": relative, "bytes": len(data), "sha256": sha_bytes(data),
                     "device": info.st_dev, "inode": info.st_ino,
                     "mode": stat.S_IMODE(info.st_mode), "uid": info.st_uid,
                     "gid": info.st_gid, "mtimeNs": info.st_mtime_ns})
    return rows


def owned_allocation():
    total = 0
    seen = set()
    entries = 0
    for owner in (OUT, RUNTIME):
        if not owner.exists():
            continue
        for base, directories, files in os.walk(owner, followlinks=False):
            paths = [Path(base)] + [Path(base) / name for name in directories + files]
            for path in paths:
                entries += 1
                if entries > 100000:
                    raise RuntimeError("owned output inventory exceeded finite bound")
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    continue
                key = (info.st_dev, info.st_ino)
                if key not in seen:
                    total += info.st_blocks * 512
                    seen.add(key)
                if stat.S_ISLNK(info.st_mode):
                    resolved = path.resolve()
                    if not resolved.is_relative_to(RUNTIME):
                        raise RuntimeError("generated link escaped owned runtime: " + str(path))
                elif not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                    raise RuntimeError("unexpected special owned output: " + str(path))
    return total


def memory_available():
    with open("/proc/meminfo", "r", encoding="ascii") as stream:
        for line in stream:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable observation unavailable")


def free_bytes(path):
    info = os.statvfs(path)
    return info.f_bavail * info.f_frsize


def qualify_tests(text):
    events = re.findall(r"^Test Case '([^']+)' (started|passed|failed|skipped)(?: |\().*$",
                        text, re.MULTILINE)
    allowed = {"SharingAuthorityTests." + name for name in METHODS}
    normalized = []
    for identity, phase in events:
        identity = identity.removeprefix("PinkhaSharingTests.")
        if identity not in allowed or phase not in ("started", "passed"):
            raise RuntimeError("unselected or nonpassing XCTest event: " + identity + " " + phase)
        normalized.append((identity, phase))
    if len(normalized) != 6:
        raise RuntimeError("expected exactly three start/pass XCTest pairs")
    for identity in allowed:
        if [phase for name, phase in normalized if name == identity] != ["started", "passed"]:
            raise RuntimeError("selected method did not start and pass exactly once: " + identity)
    summaries = re.findall(r"Executed ([0-9]+) tests?, with ([0-9]+) failures?(?: \(([0-9]+) unexpected\))?",
                           text)
    if not summaries or any(int(a) != 3 or int(b) != 0 or (c and int(c) != 0)
                            for a, b, c in summaries):
        raise RuntimeError("XCTest summary is not exactly three tests, zero failures")
    if re.search(r"^[◇✔✘].*(?:Test |Suite |Test run)", text, re.MULTILINE):
        raise RuntimeError("unexpected Swift Testing execution")
    return {"framework": "XCTest", "selectedMethods": list(METHODS),
            "events": normalized, "summaries": summaries,
            "passedMethods": 3, "oldMethodsExecuted": 0, "loopRowsAreTestLeaves": False}


def compiler_capture(text, manifest):
    """Capture actual generated/driver records; independent compiler review stays explicit."""
    source_paths = {str(PACKAGE / x["relativePath"]) for x in manifest["files"]
                    if x["relativePath"].endswith(".swift") and x["relativePath"] != "Package.swift"}
    seen_sources = set()
    response_paths = set()
    output_map_directories = set()
    commands = []
    for line in text.splitlines():
        if not any(token in line for token in ("builtin-SwiftDriver", "/swiftc ", "/swift-frontend ")):
            continue
        try:
            tokens = shlex.split(line)
        except ValueError:
            continue
        if "-module-name" in tokens:
            index = tokens.index("-module-name")
            if index + 1 < len(tokens):
                commands.append({"module": tokens[index + 1], "line": line})
        seen_sources.update(source_paths.intersection(tokens))
        response_paths.update(token[1:] for token in tokens if token.startswith("@"))
        if "-output-file-map" in tokens:
            index = tokens.index("-output-file-map")
            if index + 1 < len(tokens):
                output_map_directories.add(str(Path(tokens[index + 1]).parent))
    artifacts = []
    generated = []
    copied_bytes = 0
    for base, directories, files in os.walk(BUILD, followlinks=False):
        directories[:] = [name for name in directories if not (Path(base) / name).is_symlink()]
        for name in sorted(files):
            path = Path(base) / name
            if path.is_symlink():
                continue
            is_source_list = name.endswith("SwiftFileList") or (
                name == "sources" and (str(path) in response_paths or str(path.parent) in output_map_directories)
            )
            is_list = is_source_list or name.endswith("LinkFileList")
            is_map = name.endswith(("OutputFileMap.json", "output-file-map.json"))
            is_generated = name.endswith(".swift")
            info = path.lstat()
            is_product = name.endswith((".so", ".swiftmodule", ".xctest")) or bool(info.st_mode & 0o111)
            if not (is_list or is_map or is_generated or is_product):
                continue
            data = regular_bytes(path, CAP if is_product else 16777216)
            row = {"path": str(path), "bytes": len(data), "sha256": sha_bytes(data),
                   "isActualSourceFileList": is_source_list}
            if is_list or is_map or is_generated:
                copied_bytes += len(data)
                if copied_bytes > 16777216:
                    raise RuntimeError("compiler textual evidence exceeds bounded retention")
                body = data.decode("utf-8")
                row["content"] = body
                if is_list:
                    for item in body.splitlines():
                        seen_sources.add(item.strip().strip('"'))
                if is_generated:
                    generated.append(str(path))
            artifacts.append(row)
    if not re.search(r"Build complete!?", text) or not commands:
        raise RuntimeError("actual verbose build completion/driver witnesses missing")
    missing = sorted(source_paths - seen_sources)
    if missing:
        raise RuntimeError("whole original Swift inputs absent from actual compiler witnesses: " + repr(missing))
    if not generated or not any(x["isActualSourceFileList"] for x in artifacts):
        raise RuntimeError("actual generated Swift and source FileList witnesses missing")
    if not any(x["path"].endswith(".so") or ".xctest" in x["path"] for x in artifacts):
        raise RuntimeError("actual linked test-product evidence missing")
    return {"status": "CAPTURED_REQUIRES_INDEPENDENT_COMPILER_REVIEW",
            "knownWholeSwiftInputs": sorted(source_paths),
            "observedWholeSwiftInputs": sorted(source_paths & seen_sources),
            "driverCommands": commands, "artifacts": artifacts,
            "generatedSwiftInputs": generated,
            "unqualifiedClaims": ["exact generated-source semantics", "full final linker closure"]}


def positive(value):
    answer = int(value)
    if answer <= 0:
        raise argparse.ArgumentTypeError("explicit positive admission value required")
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--coordination-story", required=True)
    parser.add_argument("--expected-controller-sha256", required=True)
    parser.add_argument("--root-live-floor-bytes", type=positive, required=True)
    parser.add_argument("--development-live-floor-bytes", type=positive, required=True)
    parser.add_argument("--root-admission-reserve-bytes", type=positive, required=True)
    parser.add_argument("--development-admission-reserve-bytes", type=positive, required=True)
    parser.add_argument("--initial-memory-available-bytes", type=positive, required=True)
    parser.add_argument("--maximum-observation-interval-seconds", type=float, required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9]{10,30}", args.coordination_story):
        raise RuntimeError("actual explicit coordination story required")
    if not 0 < args.maximum_observation_interval_seconds <= 1:
        raise RuntimeError("observation interval must retain the admitted at-most-one-second bound")
    if ROOT.resolve() != ROOT or Path(__file__).resolve() != PREPARED / "run_shared_three_source2.py":
        raise RuntimeError("fixed physical source/root identity mismatch")
    if digest(Path(__file__)) != args.expected_controller_sha256:
        raise RuntimeError("controller source pin mismatch")
    manifest = json.loads(pinned(PREPARED / "input-manifest.original.json", 4893, INPUT_SHA))
    pinned(PREPARED / "route-plan.original.json", 7159, PLAN_SHA)
    helper_path = PREPARED / "owned_swift_commands_original.py"
    pinned(helper_path, 9527, HELPER_SHA)
    if manifest["fileCount"] != 8 or manifest["bytes"] != 56729 or manifest["dependencies"] != []:
        raise RuntimeError("complete package declaration mismatch")
    if RUNTIME.exists() or OUT.exists():
        raise RuntimeError("single-attempt runtime/output already exists; no retry")
    before = source_snapshot(manifest)
    OUT.mkdir(exist_ok=False)
    ledger = []
    samples = []
    result = {"schema": "pinkha.sharing-role3.one-command-result.v1",
              "status": "FAIL", "componentAcceptance": "NOT_QUALIFIED",
              "coordinationStory": args.coordination_story,
              "sourceInputManifestSHA256": INPUT_SHA, "inputBefore": before,
              "admissionParameters": vars(args), "ownedOutputCapBytes": CAP,
              "childDeadlineSeconds": CHILD_SECONDS, "outerEnvelopeSeconds": OUTER_SECONDS,
              "peakAllocationUnmeasuredBeforeExecution": True,
              "commands": ledger, "resourceSamples": samples,
              "safeToReleaseRuntimeSlot": False,
              "compilerOrTestsInvoked": False, "firstFailure": None}
    began = time.monotonic()
    last_observation = None
    helper = None

    def failure(error, phase):
        if result["firstFailure"] is None:
            result["firstFailure"] = {"phase": phase, "type": type(error).__name__,
                                      "message": str(error), "traceback": traceback.format_exc()}

    def observe(initial=False):
        nonlocal last_observation
        now = time.monotonic()
        row = {"atUnixSeconds": time.time(), "elapsedSeconds": now - began,
               "rootFreeBytes": free_bytes("/"), "developmentFreeBytes": free_bytes(ROOT),
               "memoryAvailableBytes": memory_available(), "ownedAllocatedBytes": owned_allocation()}
        samples.append(row)
        previous = last_observation
        last_observation = now
        if row["ownedAllocatedBytes"] >= CAP:
            return "fixed 256MiB owned-output allocation containment reached"
        if row["rootFreeBytes"] < args.root_live_floor_bytes:
            return "current caller-supplied root live floor failed"
        if row["developmentFreeBytes"] < args.development_live_floor_bytes:
            return "current caller-supplied development live floor failed"
        if initial:
            if row["rootFreeBytes"] < args.root_live_floor_bytes + args.root_admission_reserve_bytes:
                return "current caller-supplied root admission reserve failed"
            if row["developmentFreeBytes"] < args.development_live_floor_bytes + args.development_admission_reserve_bytes + CAP:
                return "development admission lacks supplied floor/reserve plus fixed output allowance"
            if row["memoryAvailableBytes"] < args.initial_memory_available_bytes:
                return "current caller-supplied initial memory admission failed"
        elif previous is not None and now - previous > args.maximum_observation_interval_seconds:
            return "actual resource-observation interval exceeded supplied bound"
        return None

    try:
        reason = observe(initial=True)
        if reason:
            raise RuntimeError(reason)
        RUNTIME.mkdir(exist_ok=False)
        for name in ("build", "cache", "config", "security", "tmp", "xdg-cache",
                     "xdg-config", "xdg-data", "manifest-module-cache"):
            (RUNTIME / name).mkdir(exist_ok=False)
        spec = importlib.util.spec_from_file_location("sharing_role3_owned_commands", helper_path)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        if Path(helper.__file__).resolve() != helper_path or digest(helper_path) != HELPER_SHA:
            raise RuntimeError("imported original owned helper custody mismatch")
        helper.install_interrupt_handlers()
        env = {"PATH": str(SWIFT.parent) + ":/usr/bin:/bin",
               "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "PWD": str(ROOT),
               "TMPDIR": str(RUNTIME / "tmp"), "TMP": str(RUNTIME / "tmp"), "TEMP": str(RUNTIME / "tmp"),
               "XDG_CACHE_HOME": str(RUNTIME / "xdg-cache"),
               "XDG_CONFIG_HOME": str(RUNTIME / "xdg-config"),
               "XDG_DATA_HOME": str(RUNTIME / "xdg-data"),
               "SWIFTPM_MODULECACHE_OVERRIDE": str(RUNTIME / "manifest-module-cache")}
        for key in ("HOME", "USER", "LOGNAME"):
            if key in os.environ:
                env[key] = os.environ[key]
        result["environment"] = {key: value for key, value in env.items() if key not in ("HOME", "USER", "LOGNAME")}
        result["homePreservedFromParent"] = env.get("HOME") == os.environ.get("HOME")
        argv = [str(SWIFT), "test", "--package-path", str(PACKAGE),
                "--scratch-path", str(BUILD), "--cache-path", str(RUNTIME / "cache"),
                "--config-path", str(RUNTIME / "config"), "--security-path", str(RUNTIME / "security"),
                "--manifest-cache", "local", "--jobs", "2",
                "--enable-xctest", "--disable-swift-testing", "--filter", FILTER, "-v"]
        result["argv"] = argv
        result["swiftExecutable"] = {"requestedPath": str(SWIFT), "resolvedPath": str(SWIFT.resolve()),
                                     "sha256": digest(SWIFT.resolve())}
        # Setup is outside the live sampling loop. The helper owns every sample thereafter.
        last_observation = None
        log, row = helper.run(OUT / "swift", argv, ROOT, env, CHILD_SECONDS,
                              observe, save, digest, ledger)
        result["compilerOrTestsInvoked"] = "pid" in row
        text = regular_bytes(log, CAP).decode("utf-8")
        capture = compiler_capture(text, manifest)
        save(OUT / "compiler-evidence.json", capture)
        result["compilerEvidenceSHA256"] = digest(OUT / "compiler-evidence.json")
        result["testQualification"] = qualify_tests(text)
        result["componentAcceptance"] = "PENDING_INDEPENDENT_COMPILER_EVIDENCE_REVIEW"
        result["status"] = "SELECTED_THREE_PASSED_WITH_CAPTURED_COMPILER_EVIDENCE"
    except BaseException as error:
        failure(error, "admission-or-owned-command-or-result-capture")
    finally:
        if helper is not None:
            helper.ignore_interrupts()
        try:
            after = source_snapshot(manifest)
            result["inputAfter"] = after
            if after != before:
                raise RuntimeError("immutable input identity/bytes changed")
            pinned(helper_path, 9527, HELPER_SHA)
            if digest(Path(__file__)) != args.expected_controller_sha256:
                raise RuntimeError("controller source changed")
            if "swiftExecutable" in result and digest(SWIFT.resolve()) != result["swiftExecutable"]["sha256"]:
                raise RuntimeError("Swift executable changed")
            # Post-command hashing is not part of the running-child sampling interval.
            last_observation = None
            reason = observe()
            if reason:
                raise RuntimeError(reason)
        except BaseException as error:
            failure(error, "final-input-resource-custody")
        result["compilerOrTestsInvoked"] = any("pid" in row for row in ledger)
        result["safeToReleaseRuntimeSlot"] = all(
            "pid" not in row or (row.get("processGroupAbsent") is True and not row.get("cleanupErrors"))
            for row in ledger
        )
        if result["firstFailure"] is not None:
            result["status"] = "FAIL"
            result["componentAcceptance"] = "NOT_QUALIFIED"
        result["seconds"] = time.monotonic() - began
        try:
            result["ownedAllocatedBytesBeforeReceipt"] = owned_allocation()
        except BaseException as error:
            failure(error, "final-allocation-retention")
            result["status"] = "FAIL"
            result["componentAcceptance"] = "NOT_QUALIFIED"
        try:
            save(OUT / "receipt.json", result)
        except BaseException as error:
            print(json.dumps({"status": "FAIL", "receiptRetentionError": str(error),
                              "firstFailure": result["firstFailure"],
                              "safeToReleaseRuntimeSlot": result["safeToReleaseRuntimeSlot"]}))
            return 1
    print(json.dumps({"status": result["status"], "receipt": str(OUT / "receipt.json"),
                      "safeToReleaseRuntimeSlot": result["safeToReleaseRuntimeSlot"],
                      "componentAcceptance": result["componentAcceptance"]}, sort_keys=True))
    return 0 if result["firstFailure"] is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
