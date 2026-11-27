from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time

ROOT = Path("/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127")
CACHE = Path("/tmp/pinkha-w1-migration-swift-20261127")
CACHE_TARGET = Path("/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127")
EVIDENCE = Path("/var/lib/pinkha-w1-functional-migration-20261127")
MIB = 1024 ** 2
MEMBERS = {
    "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift": "6bea1d2f1108cf737d68f91cf891c901e0140212b574aaf9e42fa63b392fd652",
    "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyNativeBlockLocationLimitTests.swift": "e6cff2307e52553701cc9559b04b87f07f07b6d471b816714b739102f6a91a60",
}
METHODS = [
    "inclusiveNativeParentAndPositionLimitsSurviveEncoding",
    "oversizedLocationsAreRefusedBeforeAnIntentCanBeDispatched",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def inventory():
    result = {}
    for name in ["PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"]:
        for path in sorted((ROOT / "Modules" / name).rglob("*")):
            if path.is_file() and (path.suffix == ".swift" or path.name == "Package.resolved"):
                result[path.relative_to(ROOT).as_posix()] = sha(path)
    return result


def products():
    result = {str(p.relative_to(CACHE)): sha(p) for p in sorted(CACHE.rglob("*"))
              if p.is_file() and p.name in ["PinkhaAnyHostTests-test-runner", "PinkhaAnyHostTests.so"]}
    assert len(result) == 2
    return result


def allocated_tree(root):
    total, seen = 0, set()
    for directory, _, names in os.walk(root, followlinks=False):
        for name in [None] + names:
            path = Path(directory) if name is None else Path(directory) / name
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            identity = (info.st_dev, info.st_ino)
            if identity not in seen:
                seen.add(identity)
                total += info.st_blocks * 512
    return total


def main():
    parser = argparse.ArgumentParser(description="Run only two newly compiled SwiftTesting location-boundary methods")
    parser.add_argument("--swift-receipt", type=Path, required=True)
    parser.add_argument("--swift-receipt-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert re.fullmatch(r"[0-9a-f]{64}", args.swift_receipt_sha)
    assert args.output.is_absolute() and args.output.parent == EVIDENCE
    assert args.output.parent.resolve() == EVIDENCE
    assert args.swift_receipt.resolve().is_relative_to(EVIDENCE)
    os.umask(0o077)
    args.output.mkdir(mode=0o700, exist_ok=False)
    result = {"status": "RUNNING", "scope": "Exactly two new public block-location boundary methods, reusing the qualified source-facts compilation; no compiler or native process is dispatched", "testFramework": "SwiftTesting", "errors": [], "nativeProcessesLaunched": False}
    started = time.monotonic()
    child = None
    before = None
    build = None
    temporary = CACHE / ("block-location-temporary-" + args.output.name)
    controller_sha = sha(Path(__file__))
    minimum_root = shutil.disk_usage("/").free
    minimum_development = shutil.disk_usage(CACHE).free

    def save():
        result["seconds"] = round(time.monotonic() - started, 3)
        result["minimumRootFreeBytes"] = minimum_root
        result["minimumDevelopmentFreeBytes"] = minimum_development
        write(args.output / "result.json", result)

    def guard():
        nonlocal minimum_root, minimum_development
        minimum_root = min(minimum_root, shutil.disk_usage("/").free)
        minimum_development = min(minimum_development, shutil.disk_usage(CACHE).free)
        assert minimum_root >= 2 * 1024 ** 3, "root2GiB emergency floor"
        assert minimum_development >= 512 * MIB, "development512MiB emergency floor"
        assert time.monotonic() - started < 120, "bounded two-method skip-build run"
        assert not (args.output / "abort").exists(), "owned block-location abort"
        assert allocated_tree(args.output) <= 8 * MIB, "bounded control/log output"
        if temporary.exists():
            assert allocated_tree(temporary) <= 16 * MIB, "bounded noncompiler temporary output"

    def interrupted(*_):
        raise RuntimeError("owned block-location component run interrupted")

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    signal.pthread_sigmask(signal.SIG_UNBLOCK, {signal.SIGTERM, signal.SIGINT})
    try:
        (args.output / "controller.py").write_bytes(Path(__file__).read_bytes())
        assert CACHE.is_symlink() and CACHE.resolve() == CACHE_TARGET
        guard()
        assert minimum_root >= 2 * 1024 ** 3 + 16 * MIB
        assert minimum_development >= 512 * MIB + 16 * MIB
        assert sha(args.swift_receipt) == args.swift_receipt_sha
        build = json.loads(args.swift_receipt.read_bytes())
        assert build["status"] == "PASS" and build["compiled"] and build["sourceUnchanged"]
        assert build["exitCode"] == 0 and build["ownedGroupAbsent"]
        assert len(build["startLines"]) == len(build["passLines"]) == 3 and not build["failLines"]
        assert sha(args.swift_receipt.with_name("source-before.json")) == build["sourceBeforeSHA256"]
        assert sha(args.swift_receipt.with_name("source-after.json")) == build["sourceAfterSHA256"]
        assert build["sourceBeforeSHA256"] == build["sourceAfterSHA256"]
        head = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        assert head == build["sourceCommit"]
        before = inventory()
        assert before == json.loads(args.swift_receipt.with_name("source-after.json").read_bytes())
        assert all(before[path] == expected for path, expected in MEMBERS.items())
        assert products() == build["compiledProducts"]
        result.update(sourceCommit=head, sourceFactsBuildReceiptSHA256=args.swift_receipt_sha,
                      sourceClosureSHA256=build["sourceAfterSHA256"], members=MEMBERS,
                      compiledProducts=build["compiledProducts"])
        temporary.mkdir(mode=0o700, exist_ok=False)
        command = ["/usr/local/bin/swift", "test", "--package-path", str(ROOT / "Modules/PinkhaAnyHost"),
                   "--scratch-path", str(CACHE), "--disable-automatic-resolution", "--skip-build",
                   "--filter", "AnyNativeBlockLocationLimitTests"]
        env = {k: v for k, v in os.environ.items() if not k.startswith("PINKHA_NATIVE_")}
        env["TMPDIR"] = str(temporary)
        result["command"] = command
        save()
        with (args.output / "test.log").open("wb") as log:
            guard()
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True, env=env)
            result["pid"] = child.pid
            save()
            while child.poll() is None:
                guard()
                time.sleep(.25)
            result["exitCode"] = child.wait(timeout=10)
        guard()
        log = (args.output / "test.log").read_text(errors="replace")
        result["logSHA256"] = sha(args.output / "test.log")
        result["startLines"] = [line for line in log.splitlines() if re.search(r"\bTest \w+\(\) started", line)]
        result["passLines"] = [line for line in log.splitlines() if re.search(r"\bTest \w+\(\) passed", line)]
        result["failLines"] = [line for line in log.splitlines() if " failed" in line.lower() or "recorded an issue" in line.lower()]
        assert len(result["startLines"]) == len(result["passLines"]) == 2
        assert not result["failLines"] and "skipped" not in log.lower()
        for method in METHODS:
            assert sum(method + "()" in line for line in result["startLines"]) == 1
            assert sum(method + "()" in line for line in result["passLines"]) == 1
        assert "Build complete!" not in log
        assert not re.search(r"^\[\d+/\d+\].*(Compiling|Linking|Emitting module)", log, re.M)
        result["sourceUnchanged"] = before == inventory()
        result["compiledProductsUnchanged"] = products() == build["compiledProducts"]
        assert result["sourceUnchanged"] and result["compiledProductsUnchanged"]
        try:
            os.killpg(child.pid, 0)
            result["ownedGroupAbsent"] = False
        except ProcessLookupError:
            result["ownedGroupAbsent"] = True
        assert result["exitCode"] == 0 and result["ownedGroupAbsent"]
        result["status"] = "PASS"
    except BaseException as error:
        result["status"] = "FAIL"
        result["errors"].append({"type": type(error).__name__, "message": str(error)})
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if child is not None:
            try:
                try:
                    os.killpg(child.pid, 0)
                    alive = True
                except ProcessLookupError:
                    alive = False
                result["cleanupRequired"] = alive
                result["cleanupForcedKill"] = False
                if alive:
                    result["status"] = "FAIL"
                    os.killpg(child.pid, signal.SIGTERM)
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        child.poll()
                        try:
                            os.killpg(child.pid, 0)
                        except ProcessLookupError:
                            break
                        time.sleep(.1)
                    try:
                        os.killpg(child.pid, 0)
                        result["cleanupForcedKill"] = True
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    child.wait(timeout=10)
                try:
                    os.killpg(child.pid, 0)
                    result["ownedGroupAbsent"] = False
                except ProcessLookupError:
                    result["ownedGroupAbsent"] = True
                if not result["ownedGroupAbsent"]:
                    result["status"] = "FAIL"
            except BaseException as error:
                result["status"] = "FAIL"
                result["errors"].append({"type": type(error).__name__, "message": "cleanup: " + str(error)})
        try:
            assert sha(Path(__file__)) == controller_sha
            result["controllerSHA256"] = controller_sha
            if before is not None:
                result["sourceUnchanged"] = before == inventory()
                assert result["sourceUnchanged"]
            if build is not None and "compiledProducts" in result:
                result["compiledProductsUnchanged"] = products() == build["compiledProducts"]
                assert result["compiledProductsUnchanged"]
            if (args.output / "test.log").exists():
                result["logSHA256"] = sha(args.output / "test.log")
        except BaseException as error:
            result["status"] = "FAIL"
            result["errors"].append({"type": type(error).__name__, "message": "final integrity: " + str(error)})
        save()
    print(json.dumps({key: result[key] for key in ["status", "scope", "seconds", "errors"]}))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
