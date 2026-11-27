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
PROFILE_COMPATIBLE_SHA256 = '027820556d62c57c1010777ce4886143958cca3d7af70c90f2df8ee806e6f893'
PROFILE_COMPATIBLE_BYTES = 57360
PROFILE_SOURCE_COMPATIBILITY = ({'path': 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift": "422eed9e20b72f673e7b2b3fed303a314c2bd402ae2fd3cf74bd2d4f7727b67a",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift": "82b5b2dd0ac3978ec6a867cb3f9220527e1a111e89a601c4f4e9baf15d2c38fb",', 'sourceBeforeSHA256': '422eed9e20b72f673e7b2b3fed303a314c2bd402ae2fd3cf74bd2d4f7727b67a', 'sourceAfterSHA256': '82b5b2dd0ac3978ec6a867cb3f9220527e1a111e89a601c4f4e9baf15d2c38fb', 'sourceAfterBytes': 73179}, {'path': 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift": "8a2a18ad56ac7fde85223bf24bc8c104204e2031eddf9548ad810832aa8a673f",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift": "31f5200514b239b777679568c215a0ddb89fb0af9c41987d178deb2a06c408db",', 'sourceBeforeSHA256': '8a2a18ad56ac7fde85223bf24bc8c104204e2031eddf9548ad810832aa8a673f', 'sourceAfterSHA256': '31f5200514b239b777679568c215a0ddb89fb0af9c41987d178deb2a06c408db', 'sourceAfterBytes': 36414}, {'path': 'NativeApp/UITests/NativeLaunchTests.swift', 'beforeUTF8': '    "NativeApp/UITests/NativeLaunchTests.swift": "8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86",', 'afterUTF8': '    "NativeApp/UITests/NativeLaunchTests.swift": "e2979e777dd61f7eb8be06bd38028b15cc6f7e2d944fe6adce9603a3f7817358",', 'sourceBeforeSHA256': '8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86', 'sourceAfterSHA256': 'e2979e777dd61f7eb8be06bd38028b15cc6f7e2d944fe6adce9603a3f7817358', 'sourceAfterBytes': 295880}, {'path': 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryRecovery.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Package.swift": "298ef94254c6d8f17a389a5ff0efd02a5c03099e9a819b50886a5d9e8b3d9854",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryRecovery.swift": "2abe0317ede786772c8fb1f427f476d24605031fb7f929394f548cd9196e1155",\n    "Modules/PinkhaAnyUI/Package.swift": "298ef94254c6d8f17a389a5ff0efd02a5c03099e9a819b50886a5d9e8b3d9854",', 'sourceBeforeSHA256': None, 'sourceAfterSHA256': '2abe0317ede786772c8fb1f427f476d24605031fb7f929394f548cd9196e1155', 'sourceAfterBytes': 9956}, {'path': 'Modules/PinkhaAnyUI/Package.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Package.swift": "298ef94254c6d8f17a389a5ff0efd02a5c03099e9a819b50886a5d9e8b3d9854",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Package.swift": "173395dde0549705a14b51a7d36fb2799e80f659cc7211d13798710e1f0b1096",', 'sourceBeforeSHA256': '298ef94254c6d8f17a389a5ff0efd02a5c03099e9a819b50886a5d9e8b3d9854', 'sourceAfterSHA256': '173395dde0549705a14b51a7d36fb2799e80f659cc7211d13798710e1f0b1096', 'sourceAfterBytes': 2328}, {'path': 'NativeApp/AnyNative.xcodeproj/project.pbxproj', 'beforeUTF8': '    "NativeApp/AnyNative.xcodeproj/project.pbxproj": "7282befe3104df28a3e0f5feef05a018bc515c68cf443307de65dbe977e33532",', 'afterUTF8': '    "NativeApp/AnyNative.xcodeproj/project.pbxproj": "7a149b93087e0ebc14416b184708de4897e39c183d05e2f02241d5e59dd858ea",', 'sourceBeforeSHA256': '7282befe3104df28a3e0f5feef05a018bc515c68cf443307de65dbe977e33532', 'sourceAfterSHA256': '7a149b93087e0ebc14416b184708de4897e39c183d05e2f02241d5e59dd858ea', 'sourceAfterBytes': 23165}, {'path': 'Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift', 'beforeUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift": "8b461efe44868904b826da7b601c1537fd1c164705f861b15920143a556caac5",', 'afterUTF8': '    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift": "ec8f72a34e9823c7ba84ab8dbb013d9827c9302fc6143436de3ec8a3bfdf2f37",', 'sourceBeforeSHA256': '8b461efe44868904b826da7b601c1537fd1c164705f861b15920143a556caac5', 'sourceAfterSHA256': 'ec8f72a34e9823c7ba84ab8dbb013d9827c9302fc6143436de3ec8a3bfdf2f37', 'sourceAfterBytes': 61405})

PROFILE_DECLARATION_COMPATIBILITY = ({'label': 'three-additive-original-native-stage-identities', 'beforeUTF8': 'ALLOWED_STAGES = PENDING_ORIGINAL_STAGES + STYLED_STAGES + ACCESSIBILITY_STAGES', 'afterUTF8': 'ALLOWED_STAGES = PENDING_ORIGINAL_STAGES + STYLED_STAGES + ACCESSIBILITY_STAGES + ("unicode-latin", "unicode-hebrew") + ("properties-undo",)'}, {'label': 'full-Native26-and-both-original-prefixes-before-historical-validation', 'beforeUTF8': '    current = c.raw(source / "NativeApp/UITests/NativeLaunchTests.swift")\n', 'afterUTF8': '    current = c.raw(source / "NativeApp/UITests/NativeLaunchTests.swift")\n    # Authenticate the COMPLETE compiled source before the historical inverse witnesses.\n    # Only this local value is reduced; projected_files reads the complete Native26 file.\n    require(len(current) == 295880\n            and sha(current) == "e2979e777dd61f7eb8be06bd38028b15cc6f7e2d944fe6adce9603a3f7817358"\n            and sha(current[:281769]) == "7d7d60d61cabaf7e8c968c4d30cd584100e9d90217f6b1b66441146cbf5d943b"\n            and sha(current[281769:]) == "511ea437a499605d148720d992958fa71df89e14c5bfa7b864a6169b1546a386"\n            and sha(current[:271344]) == "8d58c41e8907019bf67088900bb5c35843562edd669422573c1280f800500e86"\n            and sha(current[271344:281769]) == "9a0880aebe30b7e2ac89794b75cdf049a792d3576bbfa1945c50693d9f78bcb1",\n            "Exact Native23 prefix, Native25 Unicode suffix and Native26 Properties suffix required")\n    current = current[:271344]\n'})

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
    """Authenticate Native26, then preserve the original historical validators."""
    require(sha(raw) == PROFILE_SHA, "Exact original closed profile required")
    text = raw.decode()
    candidate = text
    expected_changed = {
        "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyDocumentPresentation.swift",
        "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift",
        "NativeApp/UITests/NativeLaunchTests.swift",
        "Modules/PinkhaAnyUI/Package.swift",
        "NativeApp/AnyNative.xcodeproj/project.pbxproj",
        "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift",
    }
    expected_added = {"Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryRecovery.swift"}
    require(len(PROFILE_SOURCE_COMPATIBILITY) == 7
            and {row["path"] for row in PROFILE_SOURCE_COMPATIBILITY} == expected_changed | expected_added,
            "Only the exact reviewed Inspector/Unicode, Kit26 and render-cache source pins may change")
    for row in PROFILE_SOURCE_COMPATIBILITY:
        require(candidate.count(row["beforeUTF8"]) == 1,
                "One exact original source-pin context required")
        candidate = candidate.replace(row["beforeUTF8"], row["afterUTF8"], 1)
    require(len(PROFILE_DECLARATION_COMPATIBILITY) == 2,
            "Only the original allowed-stage tuple and full-source admission may change")
    for row in PROFILE_DECLARATION_COMPATIBILITY:
        require(candidate.count(row["beforeUTF8"]) == 1,
                "One exact historical validation context required")
        candidate = candidate.replace(row["beforeUTF8"], row["afterUTF8"], 1)
    changed = candidate.encode()
    require(len(changed) == PROFILE_COMPATIBLE_BYTES and sha(changed) == PROFILE_COMPATIBLE_SHA256,
            "Exact combined source-compatible profile bytes differ")
    restored = candidate
    for row in reversed(PROFILE_DECLARATION_COMPATIBILITY):
        require(restored.count(row["afterUTF8"]) == 1, "One exact declaration inverse required")
        restored = restored.replace(row["afterUTF8"], row["beforeUTF8"], 1)
    for row in reversed(PROFILE_SOURCE_COMPATIBILITY):
        require(restored.count(row["afterUTF8"]) == 1, "One exact source-pin inverse required")
        restored = restored.replace(row["afterUTF8"], row["beforeUTF8"], 1)
    require(restored.encode() == raw, "Every original profile byte must be restored by the finite inverse")
    original_tree, changed_tree = ast.parse(text), ast.parse(candidate)
    require(len(original_tree.body) == len(changed_tree.body), "Original top-level source closure changed")
    source_maps, source_checks, allowed_stages = 0, 0, 0
    for original, revised in zip(original_tree.body, changed_tree.body):
        names = ({target.id for target in original.targets if isinstance(target, ast.Name)}
                 if isinstance(original, ast.Assign) else set())
        if "SOURCE_FILES" in names:
            source_maps += 1
            before, after = ast.literal_eval(original.value), ast.literal_eval(revised.value)
            require(set(before) | expected_added == set(after) and len(before) == 27 and len(after) == 28
                    and {path for path in before if before[path] != after[path]} == expected_changed,
                    "Only six reviewed map values and one additional native recovery pin may differ")
        elif "ALLOWED_STAGES" in names:
            allowed_stages += 1
            before, after = ast.get_source_segment(text, original), ast.get_source_segment(candidate, revised)
            row = PROFILE_DECLARATION_COMPATIBILITY[0]
            require(before == row["beforeUTF8"] and after == row["afterUTF8"],
                    "The three reviewed native stages must be exact additions to the original allowed tuple")
        elif isinstance(original, ast.FunctionDef) and original.name == "check_source":
            source_checks += 1
            before, after = ast.get_source_segment(text, original), ast.get_source_segment(candidate, revised)
            row = PROFILE_DECLARATION_COMPATIBILITY[1]
            require(after.count(row["afterUTF8"]) == 1
                    and after.replace(row["afterUTF8"], row["beforeUTF8"], 1) == before,
                    "Only full-file admission and the exact historical-prefix witness may extend check_source")
        else:
            require(ast.dump(original, include_attributes=False) == ast.dump(revised, include_attributes=False)
                    and ast.get_source_segment(text, original) == ast.get_source_segment(candidate, revised),
                    "Every other original profile declaration and assertion must remain byte-identical")
    require((source_maps, source_checks, allowed_stages) == (1, 1, 1),
            "One original source map, admission function and allowed-stage tuple required")
    return changed, {"schema": "pinkha-native26-inspector-unicode-properties-source-compatibility-v1",
        "status": "SOURCE_DERIVATIVE_NOT_RUNTIME_ACCEPTANCE", "originalSHA256": sha(raw),
        "compatibleSHA256": sha(changed), "compatibleBytes": len(changed),
        "sourcePinChanges": list(PROFILE_SOURCE_COMPATIBILITY),
        "declarationChanges": list(PROFILE_DECLARATION_COMPATIBILITY),
        "fullInverseRestoresEveryOriginalByte": True,
        "historicalValidationOnlyUsesExactOriginalPrefix": True,
        "actualCompilerUsesCompleteNative26Swift": True, "runtimeAdmission": False}


def selected_profile(source):
    """Reuse original collectors; retain both original and derived declaration identities."""
    path = Path(source) / PROFILE
    raw = path.read_bytes()
    require(regular(path)["sha256"] == PROFILE_SHA, "Exact closed original profile differs")
    compatible, source_compatibility = compatible_profile_source(raw)
    original_text, candidate_text = raw.decode(), compatible.decode()
    original_tree, tree = ast.parse(original_text), ast.parse(candidate_text)
    original_declarations = {node.name: node for node in original_tree.body
                             if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
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
            original = original_declarations[node.name]
            body = ast.get_source_segment(original_text, original).encode()
            candidate_body = ast.get_source_segment(candidate_text, node).encode()
            require(body == candidate_body or node.name == "check_source",
                    "Only the authenticated full-source admission declaration may differ")
            declarations[node.name] = {"bytes": len(body), "sha256": sha(body),
                "selectedBytes": len(candidate_body), "selectedSHA256": sha(candidate_body),
                "originalDeclarationUnchanged": body == candidate_body}
    return module, {"source": regular(path), "sourceCompatibility": source_compatibility,
                    "reusedDeclarations": declarations,
                    "omittedHistoricalEntries": sorted(omitted),
                    "historicalReadyFlagUnchanged": True, "historicalReadyFlag": False}
