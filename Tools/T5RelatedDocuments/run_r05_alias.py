#!/usr/bin/env python3
"""Prove one new resolver→shared-selection→T5 identity journey on macOS."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

PACKAGE = "PinkhaTorahPresentation"
SUITE = "T5ResolvedAliasIdentityTests"
METHOD = "testResolvedAliasesRemainDistinctFromOtherVersesAndProviders"
PIN = "511454e49450cb2581ddf77f644146ff3e30dbef"
FIXTURE = "Modules/PinkhaTorahPresentation/Tests/PinkhaTorahPresentationTests/Fixtures/reference-resolved.json"
ORIGINAL_FIXTURE = "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/reference-resolved.json"
RETAINED_COMMIT = "653aa1aac2e61987999d1a54fcdd91e1cfcae228"
RETAINED_LOG = "docs/pinkha/torah-integration/evidence/2026-11-02/retry-fix-windows.log"
RETAINED_LOG_SHA256 = "d097a391c458af6b92bc86a579a97264cd6a3e82260e895a39a68fa117e0ac16"
RETAINED_BLOBS = {
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/Providers/SefariaReferenceProvider.swift": "b96e245bdcb1231ffb1cd8ca55fe24cb83996bc6",
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/Providers/SefariaClient.swift": "bd6e6fca06c878a81b1d5dd5a772ba15288c971f",
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/Providers/TorahHTTPTransport.swift": "6014694433fe21c76543ca2e41798a310c235e35",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/SefariaReferenceProviderTests.swift": "4a5fde87dab8e93589edb02bdecf20258b7d5490",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/reference-name.json": "20261cc926c9508d6d226e362792176eaf17a679",
    ORIGINAL_FIXTURE: "d2cca022eb886cda56c5cf2533fbf3db65556bd2",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/Fixtures/reference-rosh-hashanah.json": "6f329f9fd2a138c3a2dd5df3d2a0b34cd26cf8e2",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True).strip()


def require_source(root: Path, expected: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("source must be one exact immutable commit")
    if command(root, "git", "rev-parse", "HEAD") != expected:
        raise ValueError("reviewed source does not match checkout")
    if command(root, "git", "diff", "--name-only", "HEAD"):
        raise ValueError("tracked inputs changed during qualification")


def resolved_pin(path: Path) -> str:
    pins = json.loads(path.read_text())["pins"]
    if len(pins) != 1 or pins[0]["identity"] != "torahinspectorkit" or pins[0]["state"]["revision"] != PIN:
        raise ValueError("package dependency differs from the reviewed exact pin")
    return PIN


def original_cases(path: Path, log: str) -> dict:
    root = ET.parse(path).getroot()
    cases = list(root.iter("testcase"))
    if len(cases) != 1 or any(list(root.iter(tag)) for tag in ("failure", "error", "skipped")):
        raise ValueError("exact one new case must pass, with no failure, omission or skip")
    case = cases[0]
    classname, name = case.get("classname", ""), case.get("name", "")
    if classname not in {SUITE, f"{PACKAGE}Tests.{SUITE}"}:
        raise ValueError("an unrelated class was executed")
    if name.startswith(classname + "."):
        name = name[len(classname) + 1:]
    if name != METHOD:
        raise ValueError("an unrelated method was executed")
    # SwiftPM's xUnit can describe process success while hiding a skip. Require
    # the original exact terminal XCTest record independently of its XML.
    pattern = (r"^\s*Test Case '(?:-\[)?(?:" + re.escape(PACKAGE + "Tests.") + r")?"
               + re.escape(SUITE) + r"[. /](test\w+)\]?' (passed|failed|skipped)(?:\s|$)")
    all_terminal = re.findall(r"^\s*Test Case '[^']+' (passed|failed|skipped)(?:\s|$)", log, re.MULTILINE)
    if all_terminal != ["passed"] or re.findall(pattern, log, re.MULTILINE) != [(METHOD, "passed")]:
        raise ValueError("original terminal output does not prove the selected method passed exactly once")
    return {"class": classname, "method": METHOD, "status": "passed", "durationSeconds": case.get("time", "")}


def retained_provider_proof(root: Path) -> dict:
    actual = {name: command(root, "git", "rev-parse", "HEAD:" + name) for name in RETAINED_BLOBS}
    if actual != RETAINED_BLOBS:
        raise ValueError("unchanged provider proof cannot be reused after source drift")
    log = subprocess.check_output(["git", "show", "HEAD:" + RETAINED_LOG], cwd=root)
    if hashlib.sha256(log).hexdigest() != RETAINED_LOG_SHA256:
        raise ValueError("retained provider original log changed")
    fixture = subprocess.check_output(["git", "show", "HEAD:" + ORIGINAL_FIXTURE], cwd=root)
    if (root / FIXTURE).read_bytes() != fixture:
        raise ValueError("alias proof must reuse the exact retained canonical fixture bytes")
    return {"sourceCommit": RETAINED_COMMIT, "originalLog": RETAINED_LOG,
            "logSHA256": RETAINED_LOG_SHA256, "sourceBlobs": actual,
            "retainedProviderMethods": 6, "providerMethodsRerun": 0}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "build/t5-r05-alias"
    output.mkdir(parents=True, exist_ok=False)
    package = root / "Modules" / PACKAGE
    lock = package / "Package.resolved"
    receipt = {"schemaVersion": 1, "status": "FAILED", "sourceCommit": args.source_sha,
               "expectedNewMethodCount": 1, "liveSefariaServerProof": False,
               "nativeQueryOrSimulatorProof": False, "fullT5Complete": False}
    try:
        if platform.system() != "Darwin":
            raise ValueError("the actual shared selection mapper requires the reviewed Apple platform")
        require_source(root, args.source_sha)
        receipt["retainedProviderProof"] = retained_provider_proof(root)
        receipt["swiftVersion"] = command(root, "swift", "--version")
        receipt["xcodeVersion"] = command(root, "xcodebuild", "-version")
        receipt["sourceTrees"] = {name: command(root, "git", "rev-parse", "HEAD:Modules/" + name)
                                  for name in (PACKAGE, "PinkhaKit", "Loc")}
        before = lock.read_bytes()
        (output / "Package.resolved.before").write_bytes(before)
        resolve_log = output / "resolve.log"
        argv = ["swift", "package", "--package-path", str(package), "resolve"]
        with resolve_log.open("w") as stream:
            run = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=180)
        receipt["resolve"] = {"command": argv, "returncode": run.returncode, "logSHA256": digest(resolve_log)}
        if run.returncode:
            raise ValueError("resolve-only preflight failed before selecting the new case")
        receipt["resolvedDependency"] = resolved_pin(lock)
        require_source(root, args.source_sha)
        if lock.read_bytes() != before:
            raise ValueError("tracked package lock was rewritten during resolve-only preflight")
        log, xunit = output / "original-xctest.log", output / "original-xunit.xml"
        selected = f"^{PACKAGE}Tests\\.{SUITE}/{METHOD}$"
        argv = ["swift", "test", "--verbose", "--package-path", str(package), "--jobs", "2",
                "--force-resolved-versions", "--parallel", "--num-workers", "1", "--filter", selected,
                "--xunit-output", str(xunit)]
        print("Running the one new resolver/selection/T5 alias connection; old provider cases remain unselected", flush=True)
        with log.open("w") as stream:
            run = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
        receipt["execution"] = {"command": argv, "returncode": run.returncode, "logSHA256": digest(log)}
        if run.returncode:
            raise ValueError("new alias connection build or method failed; see original log")
        receipt["case"] = original_cases(xunit, log.read_text())
        receipt["xunitSHA256"] = digest(xunit)
        receipt["resolvedDependency"] = resolved_pin(lock)
        require_source(root, args.source_sha)
        receipt["status"] = "PASS_T5_R05_SHARED_ALIAS_CONNECTION_1"
        print(receipt["status"], flush=True)
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if lock.is_file():
            (output / "Package.resolved.after").write_bytes(lock.read_bytes())
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
