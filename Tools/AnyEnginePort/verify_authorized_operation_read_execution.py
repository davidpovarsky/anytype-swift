#!/usr/bin/env python3
"""Qualify exactly one candidate iOS native/owned-host/shared-reader journey."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess

import prepare_native_runtime as native
import verify_native_test_execution as named

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "Tools/AnyEngineValidation/evidence/native-authorized-operation-read-v10-candidate-source.json"
PROFILE = "authorized-read-runtime"
SUITE = "AnyAuthorizedOperationReadRuntimeTests"
METHOD = "testManagedNativeAuthorizedReadPreservesBytesAcrossBlockDeletionAndColdReopen"
SOURCES = [
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAuthorizedOperationRead.swift",
    "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyGuardedTorahOperationRead.swift",
    "Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyGuardedTorahContract.swift",
    "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyAuthorizedTorahOperationReader.swift",
    "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyApplicationSession.swift",
    "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyHostAuthorizedTorahOperationReader.swift",
    "Modules/PinkhaAnyRuntime/Package.swift",
    "Modules/PinkhaAnyRuntime/Sources/PinkhaAnyRuntime/AnyEmbeddedRuntime.swift",
    "Modules/PinkhaAnyRuntime/Tests/PinkhaAnyRuntimeTests/AnyAuthorizedOperationReadRuntimeTests.swift",
    "Tools/AnyEnginePort/prepare_native_runtime.py",
    "Tools/AnyEnginePort/verify_native_test_execution.py",
    "Tools/AnyEnginePort/verify_authorized_operation_read_execution.py",
    ".github/workflows/pinkha-any-engine-port.yml",
]
CAPABILITIES = {
    "nativeAuthorizedOperationRead": 1,
    "authorizedOperationReadContract": "pinkha-authorized-operation-read-v1",
    "authorizedOperationReadMaxVariants": 256,
    "authorizedOperationReadMaxBytes": 4 * 1024 * 1024,
}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_execution(summary, tree, udid):
    # Register only in this verifier process; retained profiles remain unchanged.
    named.PROFILES[PROFILE] = {SUITE: [METHOD]}
    result = named.validate(summary, tree, PROFILE, udid)
    require(result["counts"]["totalTestCount"] == result["counts"]["passedTests"] == 1,
            "Candidate must execute exactly one newly selected method")
    require(len(result["actualCases"]) == 1, "Unrelated methods were also executed")
    return result


def validate_candidate(manifest):
    require(manifest.get("qualificationCandidate") is True, "Not the explicitly reviewed candidate")
    wire = manifest.get("wireCompatibility", {})
    require(wire.get("advertisedFields") == CAPABILITIES and wire.get("runtimeCapabilityAdvertised") is True,
            "Candidate capabilities differ from the exact authorized-read contract")
    require(wire.get("canonicalOperationVersionChanged") is False and
            wire.get("existingAppendOrTargetReadChanged") is False, "Existing wire/append contract changed")
    acceptance = manifest.get("acceptance", {})
    require(all(acceptance.get(key) is False for key in
                ("fullT2Complete", "twoClientReadAcceptanceComplete", "defaultRuntimeActivation")),
            "Candidate must not claim broad acceptance or default activation")
    proof = manifest.get("retainedNativeProof", {})
    require(proof.get("componentImplementationAndTestsSourceIdentical") is True and
            proof.get("testResultsRelabeled") is False, "Frozen native evidence boundary is missing")


def verify_installed_files(vendor, receipt):
    expected = receipt.get("filesSHA256")
    require(isinstance(expected, dict) and expected, "Missing installed native inventory")
    observed = {}
    for path in vendor.rglob("*"):
        require(not path.is_symlink(), "Symlink inside installed native tree")
        if path.is_file():
            relative = path.relative_to(vendor).as_posix()
            if relative in ("native-artifact.json", "consumer-binding.json"):
                continue
            observed[relative] = sha(path)
    for path in expected:
        native.safe_relative(path)
    require(observed == expected, "Installed native members differ from the source-bound artifact")
    return observed


def verify_artifact():
    manifest = native.read_manifest(MANIFEST)
    validate_candidate(manifest)
    vendor = ROOT / "Modules/PinkhaAnyRuntime/Vendor"
    receipt_path = vendor / "native-artifact.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(receipt.get("schemaVersion") == 1 and receipt.get("version") == native.VERSION,
            "Unrecognized native artifact")
    # An earlier v9/v10 artifact has a different manifest and cannot qualify.
    # A candidate binary may survive a Swift-only correction, but its explicit
    # installed producer binding, ancestry and complete native inputs must match.
    installed_binding = json.loads((vendor / "consumer-binding.json").read_text(encoding="utf-8"))
    binding = native.validate_artifact_source(receipt, manifest, MANIFEST,
                                              producer_commit=installed_binding.get("producerCommit"))
    binding["artifactReceiptSHA256"] = sha(receipt_path)
    require(installed_binding == binding, "Installed consumer/source binding differs")
    verify_installed_files(vendor, receipt)
    source_paths = SOURCES + [MANIFEST.relative_to(ROOT).as_posix()]
    for name in ("any", "sdk"):
        source_paths.append((MANIFEST.parent / native.safe_relative(manifest[name]["patch"])).relative_to(ROOT).as_posix())
    subprocess.run(["git", "ls-files", "--error-unmatch", "--", *source_paths],
                   cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "diff", "--quiet", "HEAD", "--", *source_paths], cwd=ROOT, check=True)
    return {"nativeBinding": binding, "nativeManifestSHA256": sha(MANIFEST),
            "sourceSHA256": {path: sha(ROOT / path) for path in source_paths},
            "verifiedInstalledMemberCount": len(receipt["filesSHA256"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--udid", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    record = {"schemaVersion": 1, "status": "FAIL", "profile": PROFILE,
              "scope": "actual_iOS_C_runtime_managed_account_space_owned_host_shared_reader",
              "fullT2Acceptance": False, "twoClientAcceptance": False,
              "defaultRuntimeActivation": False, "runnerSHA256": sha(Path(__file__))}
    try:
        require(os.environ.get("PINKHA_ANY_NATIVE_ARTIFACT") == "verified-v1" and
                os.environ.get("PINKHA_ANY_AUTHORIZED_READ_ACCEPTANCE") == "candidate-v10",
                "Candidate artifact and acceptance selectors must both be explicit")
        require(bool(args.udid), "Owned simulator was not created")
        record["commit"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        record["summarySHA256"], record["testTreeSHA256"] = sha(args.summary), sha(args.tests)
        record.update(verify_artifact())
        record.update(validate_execution(json.loads(args.summary.read_text(encoding="utf-8")),
                                         json.loads(args.tests.read_text(encoding="utf-8")), args.udid))
        record["status"] = "PASS_REAL_IOS_AUTHORIZED_OPERATION_READ"
    except Exception as error:
        record["failure"] = {"kind": type(error).__name__, "description": str(error)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, indent=2))
    return 0 if record["status"] == "PASS_REAL_IOS_AUTHORIZED_OPERATION_READ" else 1


if __name__ == "__main__":
    raise SystemExit(main())
