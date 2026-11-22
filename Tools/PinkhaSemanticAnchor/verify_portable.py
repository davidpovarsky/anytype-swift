#!/usr/bin/env python3
"""Retain the original 20 portable Swift controls without executing them again.

This is a source/evidence verifier. It does not qualify native persistence,
mounted editor behavior, Apple execution, or the complete EDITOR-02 feature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

PROOF = Path("docs/validation/20261122-semantic-anchor-portable")
PINNED = {
    "result.json": "f8fd5704a31cdd1b465e87e6850e3819ebb4573701474e3a52474e71bb776aef",
    "swift-test.log": "47c22d98702c2e1dd176a268066a5585e4d6a3911ea7537873a5a356fe0e2c29",
    "any-codec-result.json": "dd3beddc81911787c4e37b5ec402b833d3186de138c122bba949795cda5d70a5",
    "any-codec-test.log": "502ab876df7d01742348fc7ff795b6319f70488172950e9fba5df3c5d8091aea",
    "association-result.json": "d0a42ccb4ec5769d969b50f11a358037a02f87db980af84e2c5d5ae13c085e81",
    "association-test.log": "13d35abcdcef0458046910fa152221e5781dd72632dfdee8dae61a4044eec3c9",
}
SOURCE_MAP = {
    "Sources/PinkhaKit/PinkhaSemanticTextAnchor.swift": "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSemanticTextAnchor.swift",
    "Tests/PinkhaKitTests/PinkhaSemanticTextAnchorTests.swift": "Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaSemanticTextAnchorTests.swift",
    "Sources/PinkhaAnyHost/AnyInlineMarkdown.swift": "Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyInlineMarkdown.swift",
    "Tests/PinkhaAnyHostTests/AnySemanticAnchorCodecTests.swift": "Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnySemanticAnchorCodecTests.swift",
    "Sources/PinkhaKit/TorahAssociationIdentity.swift": "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationIdentity.swift",
    "Sources/PinkhaKit/TorahAssociationModels.swift": "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationModels.swift",
    "Sources/PinkhaKit/TorahAssociationRepository.swift": "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationRepository.swift",
    "Sources/PinkhaKit/TorahSemanticAnchorAssociation.swift": "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahSemanticAnchorAssociation.swift",
    "Tests/PinkhaKitTests/TorahSemanticAnchorAssociationTests.swift": "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahSemanticAnchorAssociationTests.swift",
    "Sources/TorahInspectorCore/Models.swift": str(PROOF / "dependency/TorahInspectorCoreModels.swift"),
}
SCOPES = (
    ("semantic_core", "result.json", "swift-test.log", 10,
     "Tests/PinkhaKitTests/PinkhaSemanticTextAnchorTests.swift", None,
     {"Sources/PinkhaKit/PinkhaSemanticTextAnchor.swift", "Tests/PinkhaKitTests/PinkhaSemanticTextAnchorTests.swift"}),
    ("any_inline_codec", "any-codec-result.json", "any-codec-test.log", 6,
     "Tests/PinkhaAnyHostTests/AnySemanticAnchorCodecTests.swift", "AnySemanticAnchorCodecTests",
     {"Sources/PinkhaAnyHost/AnyInlineMarkdown.swift", "Tests/PinkhaAnyHostTests/AnySemanticAnchorCodecTests.swift"}),
    ("semantic_association", "association-result.json", "association-test.log", 4,
     "Tests/PinkhaKitTests/TorahSemanticAnchorAssociationTests.swift", "TorahSemanticAnchorAssociationTests", set(SOURCE_MAP)),
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def verify(control: Path) -> dict:
    proof = control / PROOF
    for relative, expected in PINNED.items():
        require(sha(proof / relative) == expected, f"Original evidence changed: {relative}")
    originals = {name: json.loads((proof / name).read_bytes())
                 for name in PINNED if name.endswith(".json")}
    combined = originals["association-result.json"]["sourceBefore"]
    require(set(combined) == set(SOURCE_MAP), "Original complete source closure differs")
    current = {key: sha(control / relative) for key, relative in SOURCE_MAP.items()}
    require(current == combined, "Current portable source/dependency differs from original executed source")

    dependency = json.loads((proof / "dependency/SOURCE.json").read_bytes())
    require(dependency == {
        "repository": "davidpovarsky/TorahInspectorKit",
        "revision": "511454e49450cb2581ddf77f644146ff3e30dbef",
        "path": "Sources/TorahInspectorCore/Models.swift",
        "git_blob": "66fcf7be3fffe1fa78ed9aa0d4dd0205b4bf92f3",
        "sha256": "9e2341edbad496cda0710b7a5b48fb3a1ac85ffa0bd0cfae876f566205586706",
    }, "Actual external model source provenance differs")
    model = (proof / "dependency/TorahInspectorCoreModels.swift").read_bytes()
    require(hashlib.sha1(b"blob " + str(len(model)).encode() + b"\0" + model).hexdigest()
            == dependency["git_blob"], "External model Git blob differs")
    first = originals["result.json"]
    require(first["version"].startswith("Swift version 6.3.3 (swift-6.3.3-RELEASE)\nTarget: x86_64-unknown-windows-msvc\n"),
            "Original compiler/platform differs")
    scopes = []
    for label, receipt_name, log_name, count, test_key, selected_filter, closure in SCOPES:
        receipt = originals[receipt_name]
        require(receipt["exitCode"] == 0 and receipt["sourceStable"] is True,
                f"Original scope did not pass unchanged: {label}")
        require(receipt["sourceBefore"] == receipt["sourceAfter"]
                == {key: combined[key] for key in closure}, f"Original scope closure differs: {label}")
        require(receipt["logSHA256"] == PINNED[log_name], f"Original log binding differs: {label}")
        expected_command = [first["swift"], "test", "--package-path", first["root"]]
        if selected_filter:
            expected_command += ["--filter", selected_filter]
        require(receipt["root"] == first["root"] and receipt["command"] == expected_command,
                f"Original execution command differs: {label}")
        source = (control / SOURCE_MAP[test_key]).read_text(encoding="utf-8")
        declared = re.findall(r"@Test\s+func\s+(\w+)\s*\(", source)
        log = (proof / log_name).read_text(encoding="utf-8")
        started = re.findall(r"^◊ Test (\w+)\(\) started\.$", log, flags=re.MULTILINE)
        passed = re.findall(r"^√ Test (\w+)\(\) passed after [\d.]+ seconds\.$", log, flags=re.MULTILINE)
        summary = re.findall(r"^√ Test run with (\d+) tests in 1 suite passed after [\d.]+ seconds\.$", log, flags=re.MULTILINE)
        require(len(declared) == len(set(declared)) == count, f"Named declarations differ: {label}")
        require(sorted(started) == sorted(passed) == sorted(declared) and summary == [str(count)],
                f"Exact original named Swift Testing outcomes differ: {label}")
        require(not re.search(r"(?:failed|skipped|recorded an issue)", log, re.IGNORECASE),
                f"Original failure/skip/issue present: {label}")
        scopes.append({"scope": label, "retained_passed_methods": sorted(passed), "passed": count,
                       "failed": 0, "skipped": 0, "executed_again": False,
                       "receipt_sha256": PINNED[receipt_name], "log_sha256": PINNED[log_name],
                       "original_direct_source_pins": sorted(closure)})
    return {
        "status": "PASS_RETAINED_PORTABLE_COMPONENT_CONTROLS_ONLY",
        "compiler": first["version"], "framework": "Swift Testing", "passed": 20,
        "failed": 0, "skipped": 0, "rerun_count": 0, "scopes": scopes,
        "current_source_sha256": {SOURCE_MAP[key]: current[key] for key in sorted(current)},
        "original_evidence_sha256": PINNED,
        "harness_provenance": "Observed final Package.swift is retained for review; no original before/after harness hash was recorded.",
        "dependency_closure_note": "Core and codec receipts directly pin their own source/test pairs; the later association receipt pins all ten staged source files. No historical complete package manifest claim is made.",
        "limits": {
            "full_modules_compiled": False, "native_any_write_reopen": "NOT_RUN",
            "native_heart_write_reopen": "NOT_RUN", "mounted_editor_acceptance": "NOT_RUN",
            "apple_execution": "NOT_RUN", "whole_block_clipboard_policy": "NOT_MOUNTED",
            "editor_02_complete": False, "engine_capability_enabled": False,
        },
        "verifier_sha256": sha(Path(__file__)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args.control.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: receipt[key] for key in ("status", "passed", "failed", "skipped", "rerun_count")}))


if __name__ == "__main__":
    main()
