#!/usr/bin/env python3
"""Inspect pinned producer contracts only; never admit or execute a product.

The expanded producer exists in memory only. The root-controlled build and
staging templates remain closed. No compiler, simulator or build subprocess is
invoked, and no executable candidate or product admission is written.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import types

PINS = {
    "wave3_shared_build.py": "47c66dde6122d19b12e5206a4a5f0b1841a026fb8088aa4bdb2c69d6a657cfcd",
    "stage_wave3_source.py": "374c863440dd7920d607191f2626ff06621d2bf8ae54a2fad05722874617058d",
    "wave3_build_admission.template.json": "74b3c368620f0ffccc54f067a9ce664107e977d0627623818588d603dff9fe97",
    "wave3_staging_plan.template.json": "cdaa2ceb93efa216593729f4a3a6df5d5b83df1b060815e703155122a0350b62",
    "build_wave2_app16_compiler_qualified.py": "9b1405ea44ba9cce3fca47a88127fc798fedab3d1b05f6e3728da3597d19929c",
    "build_wave2_app16_compiler_qualified_delta.json": "5e18f0a7cdb25cc30d010eb0c19819fe778cb338366763f06f76fef649189970",
    "build_main_permission.py": "617b163951a9692909bef38a4991ded8c53e8c21ad9278a9564222fce1a57a68",
    "combined_heart_semantics_current.py": "4ec8617c59da3183a68a53ea9f840e57738469f36f9a0bc5b5a00e806d73cd9c",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def definition(text, name):
    nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == name]
    require(len(nodes) == 1, "One original declaration required: " + name)
    return ast.get_source_segment(text, nodes[0])


def inverse_original(candidate, proof):
    spans = []
    for row in proof["changes"]:
        require(set(row) == {"old", "new", "count", "newPositions"}, "Original inverse shape changed")
        require(row["count"] == len(row["newPositions"]) and row["newPositions"] == sorted(set(row["newPositions"])),
                "Original inverse occurrence count changed")
        spans.extend((position, position + len(row["new"]), row["new"], row["old"]) for position in row["newPositions"])
    spans.sort()
    require(all(left[1] <= right[0] for left, right in zip(spans, spans[1:])), "Original inverse overlaps")
    for start, end, new, old in reversed(spans):
        require(candidate[start:end] == new, "Original inverse position changed")
        candidate = candidate[:start] + old + candidate[end:]
    return candidate, len(spans)


def inspect(inputs):
    inputs = Path(inputs)
    values = {}
    for name, expected in PINS.items():
        path = inputs / name
        require(path.is_file() and not path.is_symlink(), "Missing original physical input: " + name)
        values[name] = path.read_bytes()
        require(sha(values[name]) == expected, "Pinned contract input changed: " + name)
    template = json.loads(values["wave3_build_admission.template.json"])
    stage = json.loads(values["wave3_staging_plan.template.json"])
    require(template["readyForBuild"] is False and stage["readyForStaging"] is False,
            "Original templates must remain closed")
    adapter = types.ModuleType("pinned_wave3_contract_review_only")
    adapter.__file__ = str((inputs / "wave3_shared_build.py").resolve())
    exec(compile(values["wave3_shared_build.py"], adapter.__file__, "exec"), adapter.__dict__)
    rejected = False
    try:
        adapter.load_admission(inputs / "wave3_build_admission.template.json",
                               PINS["wave3_build_admission.template.json"], "0" * 40)
    except ValueError as error:
        require(str(error) == "A finalized build admission is required", "Unexpected template rejection")
        rejected = True
    require(rejected, "Unfrozen template unexpectedly admitted")

    # Deliberately not load_admission: this is a non-executable structural probe.
    # The path is nonexistent, source is synthetic, and readiness remains false.
    fixture = copy.deepcopy(template)
    fixture.update(appSourceSHA="0" * 40,
                   buildRoot="/Users/m1/development/anytype-d-active-20261125/main16-wave3-SYNTHETIC-UNADMITTED")
    fixture["sourceStaging"]["sha256"] = "1" * 64
    fixture["cacheQualification"]["sha256"] = "2" * 64
    fixture["pins"]["sdkMaterializationReceiptSHA256"] = "3" * 64
    fixture_raw = json.dumps(fixture, sort_keys=True).encode()
    base = values["build_wave2_app16_compiler_qualified.py"].decode()
    candidate, delta = adapter.expand_controller(base, fixture,
        Path("/__SYNTHETIC_UNADMITTED__/admission.json"), sha(fixture_raw), PINS["wave3_shared_build.py"])
    require(delta["schema"] == "pinkha-root-producer-byte-inverse-v1"
            and delta["originalSHA256"] == PINS["build_wave2_app16_compiler_qualified.py"]
            and delta["candidateSHA256"] == sha(candidate.encode())
            and delta["inverseRestoresEveryOriginalByte"] is True,
            "Wave3 inverse metadata differs")
    restored = candidate
    for row in reversed(delta["changes"]):
        require(set(row) == {"old", "new", "count"} and restored.count(row["new"]) == row["count"],
                "Wave3 inverse occurrence contract differs")
        restored = restored.replace(row["new"], row["old"])
    require(restored == base, "Wave3 inverse did not restore exact 204f producer")
    older = json.loads(values["build_wave2_app16_compiler_qualified_delta.json"])
    full_original, span_count = inverse_original(restored, older)
    require(full_original.encode() == values["build_main_permission.py"], "Two-stage inverse lost original617 bytes")
    require(all(definition(candidate, name) == definition(base, name) == definition(full_original, name)
                for name in ("run_phase", "source_state")), "Original lifecycle or source check changed")
    original_four = ("run_phase", "source_state", "verify_runtime_identity", "verify_dependencies")
    require(all(definition(base, name) == definition(full_original, name) for name in original_four),
            "Reviewed a089 producer no longer retains original four verification functions")
    for fragment in ("w3_native_proof()", "w3_ui_before(ui_source,ui_project,selected)",
                     "w3_ui_after(ui_snapshot,ui_source,ui_project)", "**w3_final_bindings()"):
        require(fragment in candidate, "Reviewed compiler/source receipt hook is missing")
    common = values["combined_heart_semantics_current.py"].decode()
    require('APP16_SOURCE = "a089ff29a5c0a7e415aac800844505f099a5561d"' in common,
            "Historical common qualifier was repinned")
    require('require("app16Producer" not in admission, "App16 producer contract used with a different source")' in common,
            "Historical different-source rejection changed")
    return {
        "schema": "pinkha-wave2-wave3-contract-compatibility-review-v1",
        "status": "REVIEWED_PINNED_CONTRACT_AND_TWO_STAGE_INVERSE_NOT_ADMISSION",
        "wave3ContractCommit": "d77bc5d2cea7503c7afa012978349951f72fa295",
        "inputSHA256": PINS, "templateBuildRejected": True, "templatesReady": False,
        "historicalA089QualifierUnchanged": True,
        "syntheticStructuralProbeOnly": True, "candidateWritten": False, "candidateExecuted": False,
        "twoStageInverse": {
            "wave3To204f": True, "secondLegOriginalSHA256": PINS["build_main_permission.py"],
            "secondLegSpans": span_count, "everyOriginalByteRestored": True,
            "runPhaseAndSourceStateByteIdenticalAcrossBothLegs": True,
            "runtimeAndDependencyBodies": "Preserved by exact original inverse plus reviewed explicit Wave3 input substitutions; raw equality is not claimed."
        },
        "acceptedSourceCommit": None, "actualProducerReceiptSHA256": None,
        "runtimeQualifierReady": False, "applicationBuilds": 0, "nativeBuilds": 0,
        "appleTestsExecuted": 0, "simulatorCommands": 0,
        "publicAPI": "admit_and_clone_products(admission, root, evidence, commands) -> (source_proof, built, app)",
        "note": "This receipt records control-source inspection only. It cannot qualify or dispatch a product."
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(args.output.is_absolute() and args.output.parent.is_dir() and not args.output.exists(),
            "Fresh output in an existing directory required")
    value = inspect(args.inputs)
    with args.output.open("x") as stream:
        stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value[key] for key in ("status", "runtimeQualifierReady", "applicationBuilds", "appleTestsExecuted")}))


if __name__ == "__main__":
    main()
