#!/usr/bin/env python3
"""Compile the actual creation model with complete, unchanged package dependencies.

This Linux component proof is deliberately narrower than an Apple/UI/native pass.
The dedicated root/cache is handed to the parent for later sequential model work.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
import traceback

BASE = "8f2c11713fb8a40ae13444104723666ffef68afe"
WORKTREE = Path("/mnt/development/projects/worktrees/anytype-wave2-native-block-menu-20261127")
ROOT = Path("/var/lib/pinkha-wave2-native-block-menu-20261127")
DEPENDENCIES = ["PinkhaAnyEngine", "PinkhaAnyHost", "PinkhaAnyIntegration", "PinkhaKit"]
SOURCE_PINS = {
    "AnyNativeTextBlockKind.swift": "61f1fe2d2d2a282dd846279db9be519c00628bf6d2b2f4771bb52350ec889275",
    "AnyNativeTextBlockCreationTests.swift": "e36af9a049013d2e19453849170ee2deac65d189d1c9603cf75c3f47b71a037e",
}
TESTS = [
    "existingParagraphAndInspectorQuoteKeepTheirOriginalStyleCarrier",
    "distinctChoicesRoundTripThroughNativeIntentAndExistingDisplayPolicies",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def run(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess:
    return subprocess.run(argv, check=True, capture_output=True, text=True, **kwargs)


def git(*args: str) -> str:
    return run(["git", "--no-optional-locks", "-C", str(WORKTREE), *args]).stdout


def dependency_closure() -> dict[str, object]:
    paths = ["Modules/" + name for name in DEPENDENCIES]
    assert git("rev-parse", "HEAD").strip() == BASE
    assert not git("status", "--short", "--", *paths).strip(), "Dependency worktree is modified"
    files = git("ls-files", "-z", "--", *paths).split("\0")
    rows = []
    for relative in sorted(filter(None, files)):
        path = WORKTREE / relative
        assert path.is_file() and not path.is_symlink(), relative
        data = path.read_bytes()
        rows.append({"path": relative, "bytes": len(data), "sha256": sha(data)})
    assert len(rows) > 100
    return {"baseCommit": BASE, "dependencies": DEPENDENCIES, "files": rows}


def main() -> None:
    # The caller creates only this dedicated directory, owned by the compiler user.
    assert ROOT.is_dir() and not ROOT.is_symlink() and not list(ROOT.iterdir())
    assert shutil.disk_usage(ROOT).free >= 2_200_000_000, "Insufficient free space before component build"
    package = ROOT / "component"
    evidence = ROOT / "attempt1"
    source_dir = package / "Sources/PinkhaAnyUI"
    test_dir = package / "Tests/PinkhaAnyUITests"
    source_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)
    evidence.mkdir()
    receipt = {
        "schema": "pinkha-native-block-creation-component-v1", "status": "FAIL",
        "startedAtUTC": now(), "baseCommit": BASE, "worktree": str(WORKTREE),
        "componentPackage": str(package), "scratchPath": str(ROOT / "build"),
        "cachePath": str(ROOT / "cache"), "methodNames": TESTS,
        "runnerPath": str(Path(__file__).resolve()), "runnerSHA256": sha(Path(__file__).read_bytes()),
        "scope": "LINUX_ACTUAL_MODEL_WITH_COMPLETE_ORIGINAL_DEPENDENCIES",
        "AppleCompilation": "NOT_RUN", "UIAcceptance": "NOT_RUN",
        "native8acRuntime": "NOT_RUN", "productSourceMutatedByRunner": False,
        "sourceTransformations": [], "dependencyTransformations": [],
    }
    started = time.monotonic()
    try:
        before = dependency_closure()
        write_json(evidence / "dependency-sources-before.json", before)
        copied = []
        for name in ["AnyNativeTextBlockKind.swift", "AnyNativeBlockMarkerPolicy.swift", "AnyNativeWritingPolicy.swift"]:
            src = WORKTREE / "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI" / name
            data = src.read_bytes()
            if name in SOURCE_PINS:
                assert sha(data) == SOURCE_PINS[name], name
            else:
                original = subprocess.run(["git", "--no-optional-locks", "-C", str(WORKTREE), "show",
                    BASE + ":Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/" + name], check=True, capture_output=True).stdout
                assert original == data, name
            (source_dir / name).write_bytes(data)
            copied.append({"source": str(src), "component": str(source_dir / name), "sha256": sha(data), "bytes": len(data)})
        name = "AnyNativeTextBlockCreationTests.swift"
        src = WORKTREE / "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests" / name
        data = src.read_bytes()
        assert sha(data) == SOURCE_PINS[name]
        (test_dir / name).write_bytes(data)
        copied.append({"source": str(src), "component": str(test_dir / name), "sha256": sha(data), "bytes": len(data)})
        dependencies = ",\n        ".join('.package(path: "' + str(WORKTREE / "Modules" / name) + '")' for name in DEPENDENCIES)
        products = ", ".join('"' + name + '"' for name in DEPENDENCIES)
        manifest = '''// swift-tools-version: 6.0
import PackageDescription
let package = Package(
    name: "PinkhaNativeBlockCreationComponent",
    dependencies: [
        DEPENDENCIES
    ],
    targets: [
        .target(name: "PinkhaAnyUI", dependencies: [PRODUCTS]),
        .testTarget(name: "PinkhaAnyUITests", dependencies: ["PinkhaAnyUI", PRODUCTS])
    ]
)
'''.replace("DEPENDENCIES", dependencies).replace("PRODUCTS", products)
        (package / "Package.swift").write_text(manifest)
        write_json(evidence / "component-source-envelope.json", {
            "entireModelFilesByteIdentical": True, "compiledUIModelFiles": copied,
            "entireDependencyPackagesUnchanged": True, "dependencySourceCount": len(before["files"]),
            "componentManifestSHA256": sha(manifest.encode()),
            "excludedAppleUIFiles": ["AnyDocumentPresentation.swift", "AnyNativeDocumentView.swift", "AnyNativeEditor.swift", "AnyNativeBlockCreationMenu.swift"],
            "nativeServiceCalled": False,
        })
        argv = ["/usr/local/bin/swift", "test", "--package-path", str(package),
                "--scratch-path", str(ROOT / "build"), "--cache-path", str(ROOT / "cache"),
                "--jobs", "2", "--no-parallel", "--disable-experimental-prebuilts", "-v",
                "--filter", "AnyNativeTextBlockCreationTests"]
        receipt["argv"] = argv
        receipt["toolchain"] = run(["/usr/local/bin/swift", "--version"]).stdout.strip()
        environment = dict(os.environ)
        # Existing authenticated Git helper, scoped to this process. No token is read or logged.
        environment.update({"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "",
                            "GIT_CONFIG_KEY_1": "credential.helper", "GIT_CONFIG_VALUE_1": "!gh auth git-credential",
                            "GIT_TERMINAL_PROMPT": "0", "CLANG_MODULE_CACHE_PATH": str(ROOT / "clang-module-cache")})
        write_json(evidence / "invocation.json", {"argv": argv, "startedAtUTC": now(), "timeoutSeconds": 1200,
            "credentialHelper": "EXISTING_GH_HELPER_PROCESS_SCOPED_NO_SECRET_CAPTURE", "jobs": 2})
        with (evidence / "stdout.log").open("wb") as stdout, (evidence / "stderr.log").open("wb") as stderr:
            process = subprocess.Popen(argv, stdout=stdout, stderr=stderr, env=environment, start_new_session=True)
            write_json(evidence / "process.json", {"pid": process.pid, "processGroup": process.pid, "startedAtUTC": now()})
            try:
                result = process.wait(timeout=1200)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
                receipt["timeout"] = "OWNED_PROCESS_GROUP_TIMEOUT"
                result = process.returncode
        receipt["processExit"] = result
        after = dependency_closure()
        write_json(evidence / "dependency-sources-after.json", after)
        assert before == after, "Dependency source changed during compile"
        for row in copied:
            assert sha(Path(row["source"]).read_bytes()) == row["sha256"]
            assert sha(Path(row["component"]).read_bytes()) == row["sha256"]
        resolved = package / "Package.resolved"
        if resolved.exists():
            shutil.copyfile(resolved, evidence / "Package.resolved")
            receipt["resolvedPackages"] = json.loads(resolved.read_bytes())
        checkouts = []
        for checkout in sorted((ROOT / "build/checkouts").glob("*")):
            if checkout.is_dir():
                head = run(["git", "--no-optional-locks", "-C", str(checkout), "rev-parse", "HEAD"]).stdout.strip()
                status = run(["git", "--no-optional-locks", "-C", str(checkout), "status", "--porcelain", "--untracked-files=no"]).stdout
                checkouts.append({"path": str(checkout), "head": head, "trackedClean": not status})
        receipt["dependencyCheckouts"] = checkouts
        text = (evidence / "stdout.log").read_text(errors="replace") + "\n" + (evidence / "stderr.log").read_text(errors="replace")
        receipt["observedTestPassLines"] = [line for line in text.splitlines() if any(name + "() passed" in line for name in TESTS)]
        assert result == 0 and "timeout" not in receipt, "Actual compiler/test process failed"
        assert len(receipt["observedTestPassLines"]) == 2, "Both exact Swift Testing methods must actually pass"
        assert all(sum(name + "() passed" in line for line in receipt["observedTestPassLines"]) == 1 for name in TESTS)
        assert re.search(r"Test run with 2 tests in .* passed", text), "Exact two-test completion required"
        assert all(row["trackedClean"] for row in checkouts)
        receipt["status"] = "PASS_COMPONENT_2_METHODS_NOT_APP_OR_NATIVE_ACCEPTANCE"
    except Exception:
        receipt["failure"] = traceback.format_exc()
    finally:
        receipt["finishedAtUTC"] = now()
        receipt["elapsedSeconds"] = round(time.monotonic() - started, 3)
        receipt["diskFreeBytes"] = shutil.disk_usage(ROOT).free
        receipt["artifacts"] = [{"path": str(p), "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                                for p in sorted(evidence.iterdir()) if p.is_file() and p.name != "receipt.json"]
        write_json(evidence / "receipt.json", receipt)
        print(json.dumps({"status": receipt["status"], "receipt": str(evidence / "receipt.json"),
                          "receiptSHA256": sha((evidence / "receipt.json").read_bytes()),
                          "elapsedSeconds": receipt["elapsedSeconds"], "processExit": receipt.get("processExit"),
                          "failure": receipt.get("failure", "")[-3000:]}), flush=True)
    raise SystemExit(0 if receipt["status"].startswith("PASS_") else 1)


if __name__ == "__main__":
    main()
