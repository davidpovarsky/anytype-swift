#!/usr/bin/env python3
"""Materialize a closed, exact future native-core source/control successor."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

PINS = {
    "host": "2e57294dc7a00d4302a9dd5f316b2419e75d6a08a4f55b47451d6c822335ec44",
    "gate": "9ce1288feb8f3c534bb7eb784909624fc66168473e93eedff2f2945583d6a18d",
    "project": "7affc23dc69eea0cc33d59335bdf2a359930ebb66b4b4b665e9fc4ebf4c95e68",
    "inventory": "18cdc4b1d90898db1f054fb8ca0446be0e33c6d548010820c854dc649e0f44e0",
    "profile": "b3dc895536c615c453f2856cd33c29b1394a6e954c218e4e7c67b59dfdb211ee",
}
BASE = "ff6836a6d4db7f1a19b94280d3b2f548e8d7d622"
BASELINE = "8f2c11713fb8a40ae13444104723666ffef68afe"
TESTS = (
    ("AnyNativePropertyPresentationTests", "7df1a45aa85cd71bc7ec8353b98150609bc2d2fb07a2aa1ebf08f7fb40fdab61",
     "54079356628487f7ecedf5cfe87434c8cc57ea36", 9),
    ("AnyNativeTextBlockCreationTests", "e36af9a049013d2e19453849170ee2deac65d189d1c9603cf75c3f47b71a037e",
     "dc582ba3239d6dcb66dbe1f7098b95349e4289f9", 2),
    ("AnyNativeTextTypographyTests", "fde5f3bd8da14f0f3e6502d60cacdf3304ea78aba9c41b35ca73317995cdff07",
     "33e31c64ca9e35e258a4d64cfe8690b08a6cbc39", 2),
)


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path, label):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Exact physical original required: " + label)
    value = path.read_bytes()
    require(sha(value) == PINS[label], "Reviewed original bytes changed: " + label)
    return value


def replace_exact(original, edits):
    value = original
    records = []
    for before, after in edits:
        require(before != after and value.count(before) == 1, "Exact unique edit preimage required")
        value = value.replace(before, after, 1)
        records.append({"before": before, "after": after})
    restored = value
    for change in reversed(records):
        require(restored.count(change["after"]) == 1, "Exact unique inverse required")
        restored = restored.replace(change["after"], change["before"], 1)
    require(restored == original, "Complete original-byte inverse failed")
    return value, {"originalSHA256": sha(original.encode()), "candidateSHA256": sha(value.encode()),
                   "edits": records, "exactOriginalRestored": True}


def declarations(text):
    lines = text.splitlines(keepends=True)
    result = {}
    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                key = prefix + node.name
                if not isinstance(node, ast.ClassDef):
                    result[key] = "".join(lines[node.lineno - 1:node.end_lineno])
                visit(node.body, key + ".")
    visit(ast.parse(text).body)
    return result


def project_edits(original):
    for index in range(1, 4):
        for prefix in ("FA9D000", "FA9D010"):
            require(prefix + str(index) + "2F112700006805CC" not in original, "New PBX identifier already exists")
    require("FA9D02012F112700006805CC" not in original, "New Frameworks identifier already exists")
    builds, refs, group, sources = [], [], [], []
    for index, (suite, _, _, _) in enumerate(TESTS, 1):
        name = suite + ".swift"
        file_id, build_id = "FA9D000" + str(index) + "2F112700006805CC", "FA9D010" + str(index) + "2F112700006805CC"
        builds.append(f"\t\t{build_id} /* {name} in Sources */ = {{isa = PBXBuildFile; fileRef = {file_id} /* {name} */; }};\n")
        refs.append(f"\t\t{file_id} /* {name} */ = {{isa = PBXFileReference; lastKnownFileType = sourcecode.swift; name = {name}; path = Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/{name}; sourceTree = SOURCE_ROOT; }};\n")
        group.append(f"\t\t\t\t{file_id} /* {name} */,\n")
        sources.append(f"\t\t\t\t{build_id} /* {name} in Sources */,\n")
    anchors = (
        ("\t\tFA9C01012F112700006805CC /* AnyNativeTextRendererTests.swift in Sources */ =", "".join(builds)),
        ("\t\tFA9C00012F112700006805CC /* AnyNativeTextRendererTests.swift */ =", "".join(refs)),
        ("\t\t\t\tFA9C00012F112700006805CC /* AnyNativeTextRendererTests.swift */,\n", "".join(group)),
        ("\t\t\t\tFA9C01012F112700006805CC /* AnyNativeTextRendererTests.swift in Sources */,\n", "".join(sources)),
        ("\t\t746F06012DB8E712005795F7 /* DesignKit in Frameworks */ =",
         "\t\tFA9D02012F112700006805CC /* DesignKit in Frameworks */ = {isa = PBXBuildFile; productRef = 746F06002DB8E712005795F7 /* DesignKit */; };\n"),
        ("\t\t\t\tFA9B02022F112500006805CC /* PinkhaAnyUI in Frameworks */,\n",
         "\t\t\t\tFA9D02012F112700006805CC /* DesignKit in Frameworks */,\n"),
        ("\t\t\t\tFA9B01022F112500006805CC /* PinkhaAnyUI */,\n",
         "\t\t\t\t746F06002DB8E712005795F7 /* DesignKit */,\n"),
    )
    return [(anchor, addition + anchor) for anchor, addition in anchors]


def host_edits():
    lanes = ("native-properties-hosted", "native-block-creation-hosted", "native-typography-hosted")
    return [
        ("import torah_ui_consumer as torah_ui\n", "import torah_ui_consumer as torah_ui\nimport native_core_hosted_profile as native_core\n"),
        ("PLANS = {\n", "PLANS = {\n" + "".join(f"    {lane + '-only'!r}: ({lane!r},),\n" for lane in lanes)),
        ("\nEXPECTED_TEST_PROFILES = {", "\nORIGINAL_SERIES += " + repr(lanes) + "\nEXPECTED_TEST_PROFILES = {"),
        ('    if host_contract.get("kind") == "rtl-hosted":',
         '    if host_contract.get("kind") in native_core.HOSTED_LANES:\n        return native_core.invocation_selectors(selectors, host_contract)\n    if host_contract.get("kind") == "rtl-hosted":'),
        ('    if contract.get("kind") == "rtl-hosted":',
         '    if contract.get("kind") in native_core.HOSTED_LANES:\n        return native_core.validators(contract["kind"])\n    if contract.get("kind") == "rtl-hosted":'),
        ('            elif lane in ("properties-hosted", "related-hosted", "inspector-hosted", "library-hosted", "rtl-hosted"):',
         '            elif lane in native_core.HOSTED_LANES:\n                result["actual"] = native_core.run_hosted(self, lane, directory, udid)\n            elif lane in ("properties-hosted", "related-hosted", "inspector-hosted", "library-hosted", "rtl-hosted"):'),
        ("'native_compiler_witness.py'}", "'native_compiler_witness.py', 'native_core_hosted_profile.py', 'native-core-closed-profile.json'}"),
        ('    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")',
         '    if admission["plan"] in native_core.PLANS:\n        native_core.require_runtime_ready(admission, parent)\n    require(args.root.is_absolute() and args.root.parent.resolve() == args.root.parent and not args.root.exists(), "Fresh owned execution root required")'),
    ]


def materialize(originals, output, profile):
    output = Path(output)
    require(not output.exists() and output.parent.resolve() == output.parent, "Fresh canonical output directory required")
    raw = {label: read(path, label) for label, path in originals.items()}
    require(set(raw) == {"host", "gate", "project", "inventory"}, "Exact four original inputs required")
    module = read(profile, "profile")
    native_sources = {"Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/" + suite + ".swift": digest for suite, digest, _, _ in TESTS}
    donor = json.loads(raw["inventory"])
    native, ui = donor["selectedNativeTestSources"], donor["selectedUITestSources"]
    require(len(native) == len(set(native)) == 43 and len(ui) == len(set(ui)) == 9
            and not set(native_sources).intersection(native), "Exact inherited43/native and9/UI path inventories required")
    project, project_inverse = replace_exact(raw["project"].decode(), project_edits(raw["project"].decode()))
    gate_anchor = '    "Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyLibrarySearchPublicationTests.swift",\n'
    gate, gate_inverse = replace_exact(raw["gate"].decode(),
                                     [(gate_anchor, gate_anchor + "".join("    " + json.dumps(path) + ",\n" for path in native_sources))])
    require(declarations(gate) == declarations(raw["gate"].decode()), "An original receipt-validator declaration changed")
    host, host_inverse = replace_exact(raw["host"].decode(), host_edits())
    old, new = declarations(raw["host"].decode()), declarations(host)
    require(old.keys() == new.keys(), "An original host declaration was added/removed")
    changed = {key for key in old if old[key] != new[key]}
    require(changed == {"invocation_selectors", "host_validation_module", "Consumer.execute_lane", "main"},
            "Unreviewed original host function changed")
    for source in (gate, host, module.decode()):
        ast.parse(source)
    inventory = {
        "schema": "pinkha-future-native-core-compiler-path-inventory-v1",
        "status": "CLOSED_SOURCE_PREPARATION_NOT_A_PRODUCER",
        "immutablePreparationBase": BASE, "historicalSource": BASELINE,
        "historicalInventorySHA256": PINS["inventory"],
        "selectedNativeTestSources": sorted(native + list(native_sources)),
        "selectedUITestSources": ui,
        "requiredNewTestSources": native_sources,
        "requiredSourceDependencies": {suite: commit for suite, _, commit, _ in TESTS},
        "historical43PathsRetained": True, "historical43ContentHashesReused": False,
        "futureSourceCommit": None, "futureSourceTree": None, "futureCompleteNativeSourceHashes": None,
        "requireEverySelectedPathFromActualFutureFreeze": True,
        "requireActualAnytypeTestsSwiftcAndFileList": True,
        "nativeSourceCount": 46, "stage1UISourceCount": 9,
        "appBuilds": 0, "nativeBuilds": 0, "testsExecuted": 0,
    }
    closed = {
        "schema": "pinkha-future-native-core-hosted-closed-v1",
        "readyForExecution": False, "runtimeAccepted": False,
        "futureSourceCommit": None, "actualProducerReceipt": None, "actualSharedAdmission": None,
        "requiredTestSources": native_sources, "requiredSourceDependencies": inventory["requiredSourceDependencies"],
        "existingPropertiesHosted15Unchanged": True,
        "nativeMethods": 13, "nativeDeclaredCases": 13,
        "uiAcceptance": False, "nativePersistenceAcceptance": False,
        "physicalDeviceAcceptance": False,
    }
    output.mkdir(mode=0o700)
    files = {
        "project.pbxproj": project.encode(),
        "receipt_admission_native_core.py": gate.encode(),
        "combined_host_acceptance_app15.py": host.encode(),
        "native_core_hosted_profile.py": module,
        "future-compiler-inputs.closed.json": (json.dumps(inventory, indent=2) + "\n").encode(),
        "native-core-closed-profile.json": (json.dumps(closed, indent=2) + "\n").encode(),
    }
    for name, data in files.items():
        (output / name).write_bytes(data)
    inverse = {"schema": "pinkha-native-core-hosted-inverse-v1",
               "project": project_inverse, "gate": gate_inverse, "host": host_inverse,
               "originalReceiptValidatorDeclarationsByteIdentical": True,
               "changedHostDeclarations": sorted(changed),
               "unchangedHostDeclarations": sorted(set(old) - changed),
               "originalCommonModuleChanged": False, "current13FileClosureChanged": False,
               "currentG02ClosureChanged": False}
    (output / "source-inverse.json").write_text(json.dumps(inverse, indent=2) + "\n")
    proof = {
        "schema": "pinkha-native-core-hosted-materialization-v1",
        "status": "PASS_CLOSED_SOURCE_MATERIALIZATION_NOT_BUILD_OR_ACCEPTANCE",
        "controllerSHA256": sha(Path(__file__).read_bytes()),
        "inputSHA256": {key: sha(value) for key, value in raw.items()},
        "profileSHA256": sha(module),
        "outputSHA256": {name: sha(value) for name, value in files.items()},
        "inverseSHA256": sha((output / "source-inverse.json").read_bytes()),
        "runtimeReady": False, "appleInvocations": 0, "testsExecuted": 0,
    }
    (output / "materialization.json").write_text(json.dumps(proof, indent=2) + "\n")
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for label in ("host", "gate", "project", "inventory"):
        parser.add_argument("--original-" + label, type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = {label: getattr(args, "original_" + label) for label in ("host", "gate", "project", "inventory")}
    proof = materialize(inputs, args.output, Path(__file__).resolve().with_name("native_core_hosted_profile.py"))
    print(json.dumps(proof, sort_keys=True))


if __name__ == "__main__":
    main()
