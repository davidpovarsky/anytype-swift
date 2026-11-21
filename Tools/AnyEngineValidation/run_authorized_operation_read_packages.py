#!/usr/bin/env python3
"""Run only the reviewed 14 shared/Any operation-read package methods on macOS."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path


SUITES = {
    "PinkhaKit": ("TorahAuthorizedOperationReadTests", (
        "testCompleteConflictClosurePreservesExactCanonicalBytesAndProvenance",
        "testAbsenceRequiresCompleteVerifiedLocalSnapshotAndNeverMissingPayload",
        "testRejectsPartialScopeDuplicateAndUnsortedClosures",
        "testAuthorityIdentityUsesExactUTF8InsteadOfUnicodeEquivalentSpelling",
        "testInvalidOperationIdentityAndBoundedResponseFailClosed",
    )),
    "PinkhaAnyEngine": ("AnyGuardedOperationReadTests", (
        "testCompleteConflictClosureRetainsBothExactCanonicalVariants",
        "testMissingBlockStatePreservesHistoryWithoutClaimingWholeObjectDeletion",
        "testTamperedCanonicalBytesIdentityAndProvenanceAreRejected",
        "testAbsenceAndScopeAlwaysRequireAnExactCompleteNativeEnvelope",
        "testDuplicateUnsortedAndOversizedFullEnvelopesAreRejected",
        "testRetainedRuntimeAndIncompleteCapabilityNeverActivateNewRead",
    )),
    "PinkhaAnyIntegration": ("AnyAuthorizedTorahOperationReaderTests", (
        "testMapsNativeReadToSharedScopeWithoutChangingBytesOrAuthority",
        "testInvalidatedOrCancelledInFlightReadCannotReleaseAcquiredPrivatePayload",
        "testInactiveSessionNeverCallsNativeLoaderAndErrorsHaveNoPayload",
    )),
}
PINS = {
    "swift-asn1": "917b472dbe53ba699cbb0495f9a95a084bc6364d",
    "swift-crypto": "e8d6eba1fef23ae5b359c46b03f7d94be2f41fed",
    "torahinspectorkit": "158acb295f832e96907cdadc813a1c2a4bb6a03c",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(root: Path, *args: str) -> str:
    return subprocess.check_output(args, cwd=root, text=True).strip()


def require_exact_source(root: Path, expected: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", expected):
        raise ValueError("source SHA must be one immutable lowercase commit")
    if command(root, "git", "rev-parse", "HEAD") != expected:
        raise ValueError("checkout does not match the reviewed source")
    if command(root, "git", "diff", "--name-only", "HEAD"):
        raise ValueError("tracked source or lock files changed during the proof")


def resolved_pins(path: Path, package: str) -> dict[str, str]:
    data = json.loads(path.read_text())
    pins = data["pins"]
    actual = {pin["identity"]: pin["state"]["revision"] for pin in pins}
    names = ({"torahinspectorkit"} if package == "PinkhaKit" else
             {"swift-asn1", "swift-crypto"} if package == "PinkhaAnyEngine" else set(PINS))
    if len(actual) != len(pins) or actual != {name: PINS[name] for name in names}:
        raise ValueError("resolved dependency revisions differ from the reviewed manifests")
    return actual


def qualified_cases(path: Path, package: str) -> list[dict[str, str]]:
    """Require original SwiftPM xUnit case records, with no skip or omission."""
    suite, expected = SUITES[package]
    root = ET.parse(path).getroot()
    if any(list(root.iter(tag)) for tag in ("failure", "error", "skipped")):
        raise ValueError("a selected method failed, errored or skipped")
    result = []
    for case in root.iter("testcase"):
        classname, name = case.get("classname", ""), case.get("name", "")
        if classname not in {suite, f"{package}Tests.{suite}"}:
            raise ValueError("an unreviewed test class was executed")
        # SwiftPM writes method names; tolerate its fully-qualified spelling.
        if name.startswith(classname + "."):
            name = name[len(classname) + 1:]
        if name not in expected:
            raise ValueError("an unreviewed test method was executed")
        result.append({"class": classname, "method": name, "status": "passed",
                       "durationSeconds": case.get("time", "")})
    names = [case["method"] for case in result]
    if len(names) != len(expected) or len(set(names)) != len(names) or set(names) != set(expected):
        raise ValueError("the complete exact selected method set did not execute")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / "build/authorized-operation-read-packages"
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"schemaVersion": 1, "status": "FAILED", "sourceCommit": args.source_sha,
               "expectedMethodCount": 14, "suites": [], "fullT2Complete": False,
               "nativeRuntimeOrIOSAdapterProof": False}
    try:
        if platform.system() != "Darwin":
            raise ValueError("this isolated proof requires the reviewed Apple runner")
        require_exact_source(root, args.source_sha)
        receipt["swiftVersion"] = command(root, "swift", "--version")
        receipt["xcodeVersion"] = command(root, "xcodebuild", "-version")
        receipt["packageSourceTrees"] = {
            name: command(root, "git", "rev-parse", f"HEAD:Modules/{name}") for name in SUITES
        }
        for package, (suite, methods) in SUITES.items():
            package_path = root / "Modules" / package
            log = output / f"{package}.log"
            xunit = output / f"{package}.xml"
            # Fixed exact reviewed methods; one worker avoids redundant parallel
            # processes and enables original SwiftPM xUnit evidence.
            selected = f"^{package}Tests\\.{suite}/({'|'.join(methods)})$"
            argv = ["swift", "test", "--package-path", str(package_path), "--jobs", "2",
                    "--parallel", "--num-workers", "1", "--filter", selected,
                    "--xunit-output", str(xunit)]
            row = {"package": package, "suite": suite, "command": argv,
                   "expectedMethods": list(methods), "status": "FAILED"}
            receipt["suites"].append(row)
            print(f"Running {len(methods)} reviewed methods in {package}", flush=True)
            with log.open("w") as stream:
                run = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
            row.update(returncode=run.returncode, logSHA256=digest(log))
            if run.returncode:
                raise ValueError(f"{package} build or selected tests failed; see original log")
            row["cases"] = qualified_cases(xunit, package)
            row["xunitSHA256"] = digest(xunit)
            row["resolvedPins"] = resolved_pins(package_path / "Package.resolved", package)
            row["resolvedSHA256"] = digest(package_path / "Package.resolved")
            require_exact_source(root, args.source_sha)
            row["status"] = "PASSED"
        receipt["status"] = "PASS_FOCUSED_SHARED_AND_ANY_READ_PACKAGES_14"
        print(receipt["status"], flush=True)
    except Exception as error:
        receipt["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
