#!/usr/bin/env python3
"""Add one finite, CLOSED Renderer3 lane to the exact published Core13 controls.

No App, test, PBX, package, compiler-inventory or product file is modified.
This is source preparation, not permission to execute the future lane.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

CORE_COMMIT = "dc001f2f09c64997515b77147fca4bacbac31397"
INPUTS = {
    "native_core_hosted_profile.py": "b3dc895536c615c453f2856cd33c29b1394a6e954c218e4e7c67b59dfdb211ee",
    "combined_host_acceptance_app15.py": "c286f736483d78c7e066f0483f678b7d9deddd942e4734238d3f9e502d2dc7e3",
    "native-core-closed-profile.json": "b9ff365cb71d8b44b45572f8dd806c4345fa8605f5777772c811977928fe8f0f",
}
RENDERER_PATH = "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift"
RENDERER_SHA256 = "695c89e5c8d5ad8e41f8ec525486836e42338bcc063d13f0945080c169fd7eaa"
RENDERER_GIT_BLOB = "c8372f370ff3cba7bc6f9563c4e522f919081662"
OBSERVED_SOURCE_COMMIT = "6e3e25194bca7b117989135f3cc4c6d2dd1cf878"
RENDERER_METHODS = (
    "testEqualNativeTextChangesAttributesWithoutReplacingCharactersOrSelection",
    "testChangedNativeTextReplacesCharactersAndKeepsValidSelection",
    "testMarkedTextKeepsCharactersSelectionAndAttributesUntilCommit",
)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def definitions(text):
    return {node.name: ast.dump(node, include_attributes=False)
            for node in ast.parse(text).body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def apply_edits(original, changes):
    value = original
    for change in changes:
        require(value.count(change["before"]) == 1, "Expected unique original literal: " + change["label"])
        value = value.replace(change["before"], change["after"], 1)
    restored = value
    for change in reversed(changes):
        require(restored.count(change["after"]) == 1, "Expected unique inverse literal: " + change["label"])
        restored = restored.replace(change["after"], change["before"], 1)
    require(restored == original, "Complete original source inverse failed")
    return value


def edit(label, before, after):
    return {"label": label, "before": before, "after": after}


def profile_edits():
    old_xctest = r'''        # This is deliberately one pinned XCTest class, not a generic parser or
        # a count waiver. The full source hash above binds helpers and assertions.
        require(suite == "AnyNativeTextTypographyTests"
                     and text.count("@MainActor\nfinal class AnyNativeTextTypographyTests: XCTestCase {") == 1
                     and "@Test" not in text,
                     "Exact UIKit XCTest class declaration changed")
        methods = re.findall(r"^    func (test[A-Za-z0-9_]+)\(\) throws \{", text, flags=re.M)
        require(len(methods) == len(set(methods)) == 2
                     and set(methods) == set(specification["methods"])
                     and len(re.findall(r"\bfunc\s+test[A-Za-z0-9_]+", text)) == 2,
                     "Exact two UIKit XCTest declarations changed")'''
    new_xctest = r'''        # Only these two exact whole-source-pinned UIKit XCTest classes are
        # supported. Typography keeps its original throwing signature; the
        # existing Renderer3 methods are parameterless and non-throwing.
        exact_xctest = {
            "AnyNativeTextTypographyTests": (2, " throws"),
            "AnyNativeTextRendererTests": (3, ""),
        }
        require(suite in exact_xctest
                     and text.count("@MainActor\nfinal class " + suite + ": XCTestCase {") == 1
                     and "@Test" not in text,
                     "Exact UIKit XCTest class declaration changed")
        count, signature_suffix = exact_xctest[suite]
        methods = re.findall(r"^    func (test[A-Za-z0-9_]+)\(\)" + signature_suffix + r" \{", text, flags=re.M)
        require(len(methods) == len(set(methods)) == count
                     and set(methods) == set(specification["methods"])
                     and len(re.findall(r"\bfunc\s+test[A-Za-z0-9_]+", text)) == count,
                     "Exact fixed UIKit XCTest declarations changed")'''
    original_end = '''    },
}
PROFILES = {'''
    renderer = '''    },
    "AnyNativeTextRendererTests": {
        "source_path": "''' + RENDERER_PATH + '''",
        "source_sha256": "''' + RENDERER_SHA256 + '''",
        "framework": "XCTest",
        "methods": {name: single() for name in (
            "''' + '\",\n            "'.join(RENDERER_METHODS) + '''",
        )},
    },
}
PROFILES = {'''
    old_profile = '    "native-typography-hosted": {"suite": "AnyNativeTextTypographyTests", "methods": 2, "cases": 2},'
    return [
        edit("description-only", "Three exact future hosted suites;", "Four exact future hosted suites;"),
        edit("fourth-exact-source-suite", original_end, renderer),
        edit("one-finite-renderer-profile", old_profile, old_profile + '\n    "native-renderer-hosted": {"suite": "AnyNativeTextRendererTests", "methods": 3, "cases": 3},'),
        edit("closed-plan-diagnostic", "Only the three fixed future native-core plans are supported", "Only the four fixed future native-core plans are supported"),
        edit("suite-diagnostic", "Only the three fixed native-core suites are supported", "Only the four fixed native-core suites are supported"),
        edit("two-finite-XCTest-signatures", old_xctest, new_xctest),
    ]


def host_edits():
    old_plan = "    'native-typography-hosted-only': ('native-typography-hosted',),"
    old_series = "ORIGINAL_SERIES += ('native-properties-hosted', 'native-block-creation-hosted', 'native-typography-hosted')"
    return [
        edit("one-renderer-plan", old_plan, old_plan + "\n    'native-renderer-hosted-only': ('native-renderer-hosted',),"),
        edit("one-renderer-result-slot", old_series, old_series[:-1] + ", 'native-renderer-hosted')"),
    ]


def closed_edits():
    old_source = '    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextTypographyTests.swift": "fde5f3bd8da14f0f3e6502d60cacdf3304ea78aba9c41b35ca73317995cdff07"'
    old_dep = '    "AnyNativeTextTypographyTests": "33e31c64ca9e35e258a4d64cfe8690b08a6cbc39"'
    return [
        edit("existing-renderer-source", old_source, old_source + ',\n    "' + RENDERER_PATH + '": "' + RENDERER_SHA256 + '"'),
        edit("observed-renderer-source-commit", old_dep, old_dep + ',\n    "AnyNativeTextRendererTests": "' + OBSERVED_SOURCE_COMMIT + '"'),
        edit("finite-method-total", '"nativeMethods": 13,', '"nativeMethods": 16,'),
        edit("finite-case-total", '"nativeDeclaredCases": 13,', '"nativeDeclaredCases": 16,'),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-input", type=Path, required=True)
    parser.add_argument("--renderer-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "A fresh separate output directory is required")
    original = {}
    for name, expected in INPUTS.items():
        data = (args.core_input / name).read_bytes()
        require(sha(data) == expected, "Exact published Core13 input changed: " + name)
        original[name] = data.decode("utf-8")
    renderer = args.renderer_source.read_bytes()
    require(sha(renderer) == RENDERER_SHA256, "Original Renderer3 source changed")
    require(hashlib.sha1(b"blob " + str(len(renderer)).encode() + b"\0" + renderer).hexdigest() == RENDERER_GIT_BLOB,
            "Original Renderer3 Git object changed")
    changes = {
        "native_core_hosted_profile.py": profile_edits(),
        "combined_host_acceptance_app15.py": host_edits(),
        "native-core-closed-profile.json": closed_edits(),
    }
    output = {name: apply_edits(original[name], edits) for name, edits in changes.items()}
    host = "combined_host_acceptance_app15.py"
    require(definitions(original[host]) == definitions(output[host]), "An original F declaration changed")
    profile = "native_core_hosted_profile.py"
    old_defs, new_defs = definitions(original[profile]), definitions(output[profile])
    changed_defs = sorted(name for name in old_defs if old_defs[name] != new_defs[name])
    require(set(old_defs) == set(new_defs) and changed_defs == ["declared_contract", "require_runtime_ready", "selected"],
            "Unexpected profile function/class change")
    closed = json.loads(output["native-core-closed-profile.json"])
    require(closed["readyForExecution"] is False and closed["runtimeAccepted"] is False
            and all(closed[key] is None for key in ("futureSourceCommit", "actualProducerReceipt", "actualSharedAdmission")),
            "Future runtime admission must remain closed")
    inverse = {
        "schema": "pinkha-renderer3-core13-exact-inverse-v1",
        "originalCoreCommit": CORE_COMMIT,
        "files": {name: {"originalSHA256": INPUTS[name], "candidateSHA256": sha(output[name].encode()), "edits": edits}
                  for name, edits in changes.items()},
        "allOriginalFDefinitionsUnchanged": True,
        "profileChangedDefinitions": changed_defs,
        "originalCompilerWitnessStageValidatorsAndLifecycleUnchanged": True,
        "noAppTestPBXGateOrCompilerInventoryChange": True,
        "original13MethodsRetained": True,
        "rendererMethodsAdded": 3,
    }
    receipt = {
        "schema": "pinkha-renderer3-closed-materialization-v1",
        "status": "SOURCE_ONLY_RUNTIME_CLOSED",
        "materializerSHA256": sha(Path(__file__).read_bytes()),
        "originalCoreCommit": CORE_COMMIT,
        "observedRendererSource": {"repository": "davidpovarsky/anytype-swift", "commit": OBSERVED_SOURCE_COMMIT,
                                   "path": RENDERER_PATH, "gitBlob": RENDERER_GIT_BLOB,
                                   "bytes": len(renderer), "sha256": RENDERER_SHA256},
        "outputs": {name: sha(value.encode()) for name, value in output.items()},
        "sourceInverseSHA256": sha((json.dumps(inverse, indent=2) + "\n").encode()),
        "selectedMethods": list(RENDERER_METHODS),
        "originalMethods": 13, "addedMethods": 3, "totalAvailableMethods": 16,
        "actualCompleteFutureSourceInventory": None,
        "past46Native9UIInventoryIsNotCurrentProductProof": True,
        "readyForExecution": False, "appleInvocations": 0, "nativeCalls": 0, "testsExecuted": 0,
        "scope": "UIKit renderer components; no real keyboard/IME, native persistence, ACL, mounted UI or physical-device acceptance",
    }
    args.output.mkdir(parents=True)
    for name, value in output.items():
        (args.output / name).write_text(value)
    for name, value in (("source-inverse.json", inverse), ("materialization.json", receipt)):
        (args.output / name).write_text(json.dumps(value, indent=2) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
