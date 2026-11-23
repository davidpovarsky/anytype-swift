#!/usr/bin/env python3
"""Read-only replay of the original six semantic-host XCTest receipts."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import zipfile

BASE = "e7fd39b763d3d0244996c207552096f169de85ed"
EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[2]
ORIGINALS = EVIDENCE / "originals"
SOURCE = "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnySemanticAnchorDocument.swift"
TEST = "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnySemanticAnchorDocumentTests.swift"
EXPECTED_METHODS = {
    "testCaptureAndResolveRefuseUnsupportedNativeSyntaxInsteadOfRetargetingOffsets",
    "testCaptureRejectsExistingSameIdentityElsewhereAndUnreachableCopies",
    "testCaptureUsesExistingVersionRunCASAndPreservesExactInverseAndOpaqueFields",
    "testPrepareRejectsVersionOwnerRunScopeDatasetAndUnknownFieldChanges",
    "testReadbackRequiresExactMarkerFieldOneFragmentAndCurrentNativeOwner",
    "testResolveUsesCompleteCurrentNativeGraphAndReportsMissingAmbiguousOrForeign",
}
EXPECTED_ADDITIONS = {
    "Modules/PinkhaAnyIntegration/Sources/PinkhaAnyIntegration/AnyHeartSpaceArchive.swift",
    "Modules/PinkhaAnyIntegration/Tests/PinkhaAnyIntegrationTests/HeartSpaceArchiveInspectionTests.swift",
    "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativePreparedMigration.swift",
    "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnySemanticAnchorCodecTests.swift",
    "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativePreparedMigrationTests.swift",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahSemanticAnchorAssociationTests.swift",
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaSemanticTextAnchorTests.swift",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def audit():
    manifest = json.loads((EVIDENCE / "ORIGINALS_MANIFEST.json").read_text())
    for item in manifest["files"]:
        path = ORIGINALS / item["path"]
        data = path.read_bytes()
        require(len(data) == item["bytes"] and sha(data) == item["sha256"],
                "Original transfer changed: " + item["path"])
    result = json.loads((ORIGINALS / "result.json").read_text())
    before = json.loads((ORIGINALS / "source-before.json").read_text())
    staged = json.loads((ORIGINALS / "STAGED.json").read_text())
    require(result["exit_code"] == 0, "Original execution failed")
    require(result["source_stable"] and
            before == result["source_before_sha256"] == result["source_after_sha256"] ==
            staged["source_before_sha256"], "Original source snapshots disagree")
    require(result["expected_new_methods"] == 6 and result["old_test_methods_executed"] == 0,
            "Original scope differs")
    require(result["apple_execution"] is False and result["native_engine_started"] is False,
            "Original scope metadata differs")
    require(sha((ORIGINALS / "baseline-modules.zip").read_bytes()) == result["archive_sha256"],
            "Original baseline archive changed")
    with zipfile.ZipFile(ORIGINALS / "baseline-modules.zip") as archive:
        original = {entry.filename: archive.read(entry)
                    for entry in archive.infolist() if not entry.is_dir()}
    for path, expected in result["overlay_source_sha256"].items():
        data = (ORIGINALS / "candidate" / Path(path).name).read_bytes()
        require(sha(data) == expected, "Original candidate changed: " + path)
        original[path] = data
    original["Package.swift"] = (ORIGINALS / "Package.swift").read_bytes()
    original["Package.resolved"] = (ORIGINALS / "Package.resolved").read_bytes()
    original["Tests/PinkhaSemanticHostControls/AnySemanticAnchorDocumentTests.swift"] = original[TEST]
    for path, expected in before.items():
        require(path in original and sha(original[path]) == expected,
                "Cannot reconstruct original source: " + path)
    log_bytes = (ORIGINALS / "swift-test.log").read_bytes()
    require(sha(log_bytes) == result["log_sha256"], "Original execution log changed")
    log = log_bytes.decode("utf-8", errors="replace")
    terminals = re.findall(r"Test Case 'AnySemanticAnchorDocumentTests\.([^']+)' "
                           r"(passed|failed|skipped) \(([^)]+)\)", log)
    require(len(terminals) == 6 and {name for name, _, _ in terminals} == EXPECTED_METHODS,
            "Missing, duplicate, or unexpected XCTest methods")
    require(all(state == "passed" for _, state, _ in terminals), "Nonpassing XCTest")
    require("Executed 6 tests, with 0 failures (0 unexpected)" in log,
            "Original XCTest total missing")
    declared = set(re.findall(r"func (test\w+)\(", original[TEST].decode()))
    require(declared == EXPECTED_METHODS, "Declared test methods differ")
    require(sha((ROOT / SOURCE).read_bytes()) == result["overlay_source_sha256"][SOURCE] and
            sha((ROOT / TEST).read_bytes()) == result["overlay_source_sha256"][TEST],
            "Integrated candidate differs from original tested bytes")
    current = []
    for path, expected in before.items():
        if not path.startswith("Modules/"):
            continue
        data = (ROOT / path).read_bytes()
        raw = original[path]
        equivalence = "EXACT" if raw == data else "CRLF_TO_LF_ONLY"
        require(raw == data or raw.replace(b"\r\n", b"\n") == data,
                "Current dependency changed materially: " + path)
        current.append({"path": path, "original_sha256": expected,
                        "current_sha256": sha(data), "equivalence": equivalence})
    extra = set()
    for module in ("PinkhaAnyEngine", "PinkhaAnyIntegration", "PinkhaAnyHost", "PinkhaKit"):
        for path in (ROOT / "Modules" / module).rglob("*.swift"):
            relative = path.relative_to(ROOT).as_posix()
            if relative not in before:
                extra.add(relative)
    require(extra == EXPECTED_ADDITIONS, "Current unqualified additions changed")
    pins = {pin["identity"]: pin["state"]["revision"] for pin in
            json.loads((ORIGINALS / "Package.resolved").read_text())["pins"]}
    for name, dependency in result["dependencies"].items():
        require(dependency["commit"] == dependency["expected_commit"] and dependency["tracked_clean"],
                "Original dependency identity not qualified: " + name)
        require(pins[name.lower()] == dependency["commit"], "Original lock differs: " + name)
    return {
        "schema": "pinkha-semantic-any-host-original-audit-v1",
        "status": "RETAINED_ORIGINAL_SIX_PASS",
        "integration_base": BASE,
        "original_baseline": result["baseline_commit"],
        "original_xctest_methods": [{"name": name, "result": state, "duration": duration}
                                   for name, state, duration in terminals],
        "originals_verified": len(manifest["files"]),
        "original_source_files_reconstructed": len(before),
        "current_module_source_equivalence": current,
        "current_source_counts": {
            "exact": sum(entry["equivalence"] == "EXACT" for entry in current),
            "crlf_to_lf_only": sum(entry["equivalence"] == "CRLF_TO_LF_ONLY" for entry in current),
            "material_changes": 0,
        },
        "current_additive_swift_files_not_in_original_execution": sorted(extra),
        "original_toolchain": result["swift_version"],
        "original_dependencies": result["dependencies"],
        "original_log_sha256": result["log_sha256"],
        "original_staging_failed_job": result["original_staging_failed_job"],
        "product_tests_rerun_by_this_audit": 0,
        "limits": {
            "integrated_full_module_compile": "NOT_RUN",
            "apple": "NOT_RUN",
            "native_engine": "NOT_RUN",
            "http": "NOT_RUN",
            "page_apply": "NOT_RUN",
            "process_reopen": "NOT_RUN",
            "mounted_editor": "NOT_RUN",
            "capability": "OFF",
        },
    }


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2, sort_keys=True))
