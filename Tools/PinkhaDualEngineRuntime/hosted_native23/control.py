"""Finite source materialization and failure custody for same-job Native23.

The old closed Mac entry point is neither configured nor changed. The emitted
runtime has an explicit literal inverse to that original; its run(), bind(),
selectors and assertion/observation collectors remain the original bytes.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import types

PREFIX = "Tools/PinkhaDualEngineRuntime/hosted_native23/"
ORIGINAL_PREFIX = "Tools/CurrentAppleValidation/native23_accessibility_closed/"
RUNTIME = ORIGINAL_PREFIX + "materialized/run_prebuilt_native_ui16.py"
RUNTIME_SHA = "e4515cc6cd36424c607ee1e986ea9f0cfdcb0db516bf6e91276eef685ba29a22"
PROFILE = ORIGINAL_PREFIX + "native23_profile_closed.py"
PROFILE_SHA = "3fd3049737f4be72f4257a04e5ca94085e6d9e11cd3916257ced4bf2e8943aa6"
# Fixed reviewed product-source compatibility only; the original profile file stays immutable.
PROFILE_COMPATIBLE_SHA256 = '4bef306e554cacb216af82fe1eb94ab068884fb35358735d5907e3dbab84e6f5'
PROFILE_COMPATIBLE_BYTES = 56268
PROFILE_SOURCE_COMPATIBILITY = ({'path': 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift": "422eed9e20b72f673e7b2b3fed303a314c2bd402ae2fd3cf74bd2d4f7727b67a",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift": "7582d4ee5f6ae5a9ba06e371b4143a1f8db10afda7c213a7263559fe30559a1f",', 'sourceBeforeSHA256': '422eed9e20b72f673e7b2b3fed303a314c2bd402ae2fd3cf74bd2d4f7727b67a', 'sourceAfterSHA256': '7582d4ee5f6ae5a9ba06e371b4143a1f8db10afda7c213a7263559fe30559a1f', 'sourceAfterBytes': 73025}, {'path': 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift": "8a2a18ad56ac7fde85223bf24bc8c104204e2031eddf9548ad810832aa8a673f",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift": "beea22b4d19484f6dad508f819d874ece31d43a91d36fa0d03805c527c9332da",', 'sourceBeforeSHA256': '8a2a18ad56ac7fde85223bf24bc8c104204e2031eddf9548ad810832aa8a673f', 'sourceAfterSHA256': 'beea22b4d19484f6dad508f819d874ece31d43a91d36fa0d03805c527c9332da', 'sourceAfterBytes': 35988})

RUN_SHA = "5ea092b2a4d7159e8dec45b264224811e24e64265493a1e4958e4937b5fecaad"
PLANS = ("sharing-owner", "archive", "rtl", "library-search", "source-drag",
         "styled-blocks", "styled-live-type", "accessibility-audit-large",
         "accessibility-audit-expanded", "accessibility-voiceover-large")


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def regular(path):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
            and not path.is_symlink(), "Canonical original regular input required: " + str(path))
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def load_json(path):
    regular(path)
    def pairs(rows):
        value = {}
        for key, item in rows:
            require(key not in value, "Duplicate JSON key in original evidence")
            value[key] = item
        return value
    def constant(value):
        raise ValueError("Nonfinite original JSON value: " + value)
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs, parse_constant=constant)


def exclusive(path, value):
    path = Path(path)
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def retain_native23_failure(writer, path, record, first, diagnostics):
    """A failed attempt to retain the original failure never replaces it."""
    try:
        writer(path, record)
    except BaseException as error:
        diagnostics.append({"phase": "first-failure-retention", "type": type(error).__name__,
                            "reason": str(error)})
        first.add_note("Original first-failure receipt also failed: " + repr(error))


def retain_native23_receipt(writer, path, receipt, first, diagnostics):
    """Return the earliest original failure, including a prior cleanup failure."""
    if first is None and diagnostics:
        item = diagnostics[0]
        first = RuntimeError("Original Native23 finalization failed: " + str(item))
    if first is not None:
        receipt["status"] = "FAIL"
        if receipt.get("firstFailure") is None:
            receipt["firstFailure"] = {"type": type(first).__name__, "reason": str(first)}
    try:
        writer(path, receipt)
    except BaseException as error:
        receipt["status"] = "FAIL"
        receipt.setdefault("receiptFailures", []).append({"path": str(path),
            "type": type(error).__name__, "reason": str(error)})
        if first is None:
            first = error
            receipt["firstFailure"] = {"type": type(error).__name__, "reason": str(error)}
        else:
            first.add_note("Original Native23 final receipt also failed: " + repr(error))
    return first


def final_input_boundary(bridge, source, evidence, original, expected, diagnostics):
    """After unresolved c249 ownership, permit file reads only, never new commands."""
    bridge.file_only_postflight()
    if bridge.styled_process_closed():
        require(bridge.qualify_runtime_inputs(source, evidence, original) == expected,
                "Original same-job runtime inputs changed during UI execution")
    else:
        diagnostics.append({"phase": "shared-command-requalification-withheld",
            "reason": "Unresolved original c249 custody; no Git, new subprocess or device work permitted"})


def load_module(path, name, expected):
    require(regular(path)["sha256"] == expected and name not in sys.modules,
            "Exact original source or unique module name differs: " + name)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def materialize(source, destination):
    """Create one reviewable derivative; no test source or product is projected."""
    inverse_path = Path(__file__).with_name("runtime_inverse.json")
    inverse = load_json(inverse_path)
    path = Path(source) / RUNTIME
    raw = path.read_bytes()
    require(regular(path)["sha256"] == inverse["originalSHA256"] == RUNTIME_SHA
            and len(raw) == inverse["originalBytes"], "Exact original materialized runner differs")
    text = raw.decode()
    for item in inverse["patches"]:
        require(text.count(item["before"]) == 1, "One exact literal source preimage required: " + item["label"])
        text = text.replace(item["before"], item["after"])
    candidate = text.encode()
    require(sha(candidate) == inverse["candidateSHA256"] and len(candidate) == inverse["candidateBytes"],
            "Exact separate same-job runtime derivative differs")
    restored = text
    for item in reversed(inverse["patches"]):
        require(restored.count(item["after"]) == 1, "One inverse source hunk required")
        restored = restored.replace(item["after"], item["before"])
    require(restored.encode() == raw, "Full inverse must restore every original controller byte")
    tree = ast.parse(text)
    run = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run"]
    require(len(run) == 1 and sha(ast.get_source_segment(text, run[0]).encode()) == RUN_SHA,
            "Original c249-bound run declaration changed")
    destination.mkdir(mode=0o700, exist_ok=False)
    runtime_path = destination / "run_hosted_native23_original.py"
    with runtime_path.open("xb") as stream:
        stream.write(candidate)
    # This is a new CONTROL materialization record, not an old compiler or test receipt.
    metadata = {"schema": "pinkha-hosted-native23-original-runtime-materialization-v1",
                "status": "SOURCE_DERIVATIVE_NOT_RUNTIME_ACCEPTANCE",
                "controllers": {runtime_path.name: {"candidateSHA256": sha(candidate),
                    "originalSHA256": RUNTIME_SHA, "inverseRestoresEveryOriginalByte": True}},
                "files": {runtime_path.name: {"sha256": sha(candidate), "bytes": len(candidate)}},
                "original": regular(path), "literalInverse": regular(inverse_path),
                "originalRunDeclarationSHA256": RUN_SHA, "testsExecuted": 0}
    exclusive(destination / "nativeui16-materialization.json", metadata)
    module = types.ModuleType("hosted_native23_original_runtime")
    module.__file__ = str(runtime_path)
    exec(compile(candidate, str(runtime_path), "exec"), module.__dict__)
    module.SAME_JOB_BRIDGE = None
    module.retain_native23_failure = retain_native23_failure
    module.retain_native23_receipt = retain_native23_receipt
    module.final_input_boundary = final_input_boundary
    require(tuple(name for name in PLANS if name in module.STAGES) == PLANS,
            "All ten original plans must remain present")
    return module, metadata


def compatible_profile_source(raw):
    """Derive only two reviewed SOURCE_FILES literals; preserve all original code."""
    require(sha(raw) == PROFILE_SHA, "Exact original closed profile required")
    text = raw.decode()
    candidate = text
    expected_paths = {
        "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift",
        "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift",
    }
    require(len(PROFILE_SOURCE_COMPATIBILITY) == 2
            and {row["path"] for row in PROFILE_SOURCE_COMPATIBILITY} == expected_paths,
            "Only the two reviewed product-source pins may change")
    for row in PROFILE_SOURCE_COMPATIBILITY:
        require(candidate.count(row["beforeUTF8"]) == 1,
                "One exact original source-pin line required")
        candidate = candidate.replace(row["beforeUTF8"], row["afterUTF8"], 1)
    changed = candidate.encode()
    require(len(changed) == PROFILE_COMPATIBLE_BYTES and sha(changed) == PROFILE_COMPATIBLE_SHA256,
            "Exact source-compatible profile bytes differ")
    restored = candidate
    for row in reversed(PROFILE_SOURCE_COMPATIBILITY):
        require(restored.count(row["afterUTF8"]) == 1, "One exact inverse source-pin line required")
        restored = restored.replace(row["afterUTF8"], row["beforeUTF8"], 1)
    require(restored.encode() == raw, "Every original profile byte must be restored by the finite inverse")
    original_tree, changed_tree = ast.parse(text), ast.parse(candidate)
    require(len(original_tree.body) == len(changed_tree.body), "Original top-level source closure changed")
    source_maps = 0
    for original, revised in zip(original_tree.body, changed_tree.body):
        if (isinstance(original, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "SOURCE_FILES" for target in original.targets)):
            source_maps += 1
            before, after = ast.literal_eval(original.value), ast.literal_eval(revised.value)
            require(set(before) == set(after) and len(before) == 27
                    and {path for path in before if before[path] != after[path]} == expected_paths,
                    "Only the two reviewed map entries may differ")
        else:
            require(ast.dump(original, include_attributes=False) == ast.dump(revised, include_attributes=False)
                    and ast.get_source_segment(text, original) == ast.get_source_segment(candidate, revised),
                    "Original profile declarations, assertions and other constants must remain byte-identical")
    require(source_maps == 1, "One original source guard map is required")
    return changed, {"schema": "pinkha-native23-two-source-compatibility-v1",
        "status": "SOURCE_DERIVATIVE_NOT_RUNTIME_ACCEPTANCE", "originalSHA256": sha(raw),
        "compatibleSHA256": sha(changed), "compatibleBytes": len(changed),
        "sourcePinChanges": list(PROFILE_SOURCE_COMPATIBILITY),
        "fullInverseRestoresEveryOriginalByte": True, "allOriginalFunctionBodiesUnchanged": True,
        "runtimeAdmission": False}


def selected_profile(source):
    """Reuse original collectors and source guards, not the closed Mac admission."""
    path = Path(source) / PROFILE
    raw = path.read_bytes()
    require(regular(path)["sha256"] == PROFILE_SHA, "Exact closed original profile differs")
    compatible, source_compatibility = compatible_profile_source(raw)
    tree = ast.parse(compatible.decode())
    omitted = {"configure", "qualify_main", "qualify_runtime_inputs", "admit",
               "compile_sharing_source", "bind_source", "reviewed_builder", "seal_ui_build"}
    nodes = [node for node in tree.body if not isinstance(node, ast.FunctionDef) or node.name not in omitted]
    require(not any(isinstance(n, ast.If) and isinstance(n.test, ast.Compare) for n in tree.body),
            "Original profile unexpectedly gained an executable entry point")
    module = types.ModuleType("hosted_native23_original_collectors")
    module.__file__ = str(path)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), module.__dict__)
    require(module.READY_FOR_EXECUTION is False and module.FUTURE_SOURCE_COMMIT is None,
            "Historical source preparation must remain closed")
    declarations = {}
    for node in nodes:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            body = ast.get_source_segment(raw.decode(), node).encode()
            declarations[node.name] = {"bytes": len(body), "sha256": sha(body)}
    return module, {"source": regular(path), "sourceCompatibility": source_compatibility,
                    "reusedDeclarations": declarations,
                    "omittedHistoricalEntries": sorted(omitted), "historicalReadyFlagUnchanged": True, "historicalReadyFlag": False}
