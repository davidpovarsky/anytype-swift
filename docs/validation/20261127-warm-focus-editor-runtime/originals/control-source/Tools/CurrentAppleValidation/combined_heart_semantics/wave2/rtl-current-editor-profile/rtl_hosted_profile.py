"""Exact new RTL UIKit components; source/compiler/result checks, no runner.

Call only after the shared producer/product admission has succeeded. The
native compilation pin comes from that admitted producer receipt. This
module does not admit an application, build, start a simulator or run tests.
"""
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess

import run_host_tests as host
import wave15_core_profile as core
import shared_editor_existing_build as existing

TARGET = "AnytypeTests"
METHOD_COUNT = 6
CASE_COUNT = 10
SUITES = {
    "PinkhaTextBlockLeadingMarkerTests": {
        "source_path": "AnyTypeTests/Pinkha/PinkhaTextBlockLeadingMarkerTests.swift",
        "source_sha256": "dafd3d25b80cfdec01f5b47f70adc59d52d03db36ac9a673b70059e46637ac21",
        "methods": {
            "oppositeDirectionAttachmentRefreshesMarker": {
                "parameters": [{"name": "isRTL", "type": "Bool"}],
                "argument_collections": [[False, True]], "case_count": 2},
            "directionChangeAndReusePreserveMarkerPolicy": {
                "parameters": [{"name": "number", "type": "Int"}],
                "argument_collections": [[1, 20]], "case_count": 2},
        },
    },
    "AnyNativeEmptyParagraphDirectionTests": {
        "source_path": "AnyTypeTests/Pinkha/AnyNativeEmptyParagraphDirectionTests.swift",
        "source_sha256": "656ab17484da23139005fb84a36376802f23c5fdf66c9766c7860a895c27e999",
        "methods": {
            "emptyRenderAndFirstFocus": {
                "parameters": [{"name": "isRTL", "type": "Bool"}],
                "argument_collections": [[False, True]], "case_count": 2},
            "emptyAttributeAndSelectionReset": {
                "parameters": [{"name": "isRTL", "type": "Bool"}],
                "argument_collections": [[False, True]], "case_count": 2},
            "compositionAndNonemptyInputAreUntouched": {
                "parameters": [], "argument_collections": [], "case_count": 1},
            "reuseClearsPriorBlockPresentation": {
                "parameters": [], "argument_collections": [], "case_count": 1},
        },
    },
}
PRODUCT_SOURCES = {
    "Anytype/Sources/Pinkha/RTL/PinkhaTextBlockLeadingMarkerAdapter.swift":
        "45c659a2923733421c9760d95dbe5b1560d1aa7b3123813ab93f86c2d313d38c",
    "Anytype/Sources/PresentationLayer/TextEditor/BlocksViews/Blocks/Text/Base/Stylers/TextBlockLeadingView.swift":
        "2f2bf0a7bd83c6deccf0f9efc531950dca3fb739eea012a949d559e98c0468cd",
    "Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift":
        "8b461efe44868904b826da7b601c1537fd1c164705f861b15920143a556caac5",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def validate_source(text, suite):
    specification = SUITES[suite]
    core.require(sha(text.encode("utf-8")) == specification["source_sha256"],
                 "Exact reviewed RTL component source required: " + suite)
    core.require(core.inspect_declarations(text) == specification["methods"],
                 "RTL declarations or literal cases changed: " + suite)
    return {suite + "/" + name for name in specification["methods"]}


def declared_contract(app):
    """Source inventory only. This does not authorize component execution."""
    app = Path(app)
    tracked = subprocess.check_output(["git", "-C", str(app), "ls-files", "-z"]).decode().split("\0")
    sources = dict(PRODUCT_SOURCES)
    sources.update({spec["source_path"]: spec["source_sha256"] for spec in SUITES.values()})
    for relative, expected in sources.items():
        candidates = [name for name in tracked if name.casefold() == relative.casefold()]
        core.require(len(candidates) == 1, "Missing or case-colliding tracked RTL source: " + relative)
        actual, selected = app / candidates[0], app / relative
        core.require(selected.is_file() and not selected.is_symlink() and actual.samefile(selected)
                     and selected.resolve().is_relative_to(app.resolve()), "RTL source is outside the synchronized root")
        core.require(sha(actual.read_bytes()) == expected, "Reviewed RTL source changed: " + relative)
    methods, identifiers = set(), []
    for suite, specification in SUITES.items():
        methods.update(validate_source((app / specification["source_path"]).read_bytes().decode("utf-8"), suite))
        identifiers.extend(TARGET + "/" + suite + "/" + name + "("
                           + "".join(parameter["name"] + ":" for parameter in definition["parameters"]) + ")"
                           for name, definition in specification["methods"].items())
    core.require(len(methods) == METHOD_COUNT and sum(method["case_count"] for spec in SUITES.values()
                 for method in spec["methods"].values()) == CASE_COUNT, "RTL method/case scope differs")
    return dict(kind="rtl-hosted", methods=sorted(methods), compiled_identifiers=sorted(identifiers),
                source_hashes={spec["source_path"]: spec["source_sha256"] for spec in SUITES.values()},
                product_source_hashes=PRODUCT_SOURCES, expected_methods=METHOD_COUNT, declared_cases=CASE_COUNT)


def _pinned_bytes(pin, label):
    core.require(isinstance(pin, dict) and isinstance(pin.get("path"), str)
                 and re.fullmatch(r"[0-9a-f]{64}", pin.get("sha256", "")), "Missing admitted " + label + " pin")
    path = Path(pin["path"])
    core.require(path.is_absolute() and path.is_file() and not path.is_symlink(), "Missing regular " + label)
    data = path.read_bytes()
    core.require(sha(data) == pin["sha256"], "Pinned " + label + " changed")
    return data


def source_contract(app, *, source_commit, native_compilation_proof):
    """Bind both selected suites to actual AnytypeTests compiler-use evidence.

    native_compilation_proof is the exact {path, sha256} in the previously
    admitted producer receipt. All full source, Native, SDK and product
    admission remains in the shared qualifier; this adds the RTL selection.
    """
    app = Path(app)
    core.require(re.fullmatch(r"[0-9a-f]{40}", source_commit) is not None, "Exact admitted source commit required")
    contract = declared_contract(app)
    proof = json.loads(_pinned_bytes(native_compilation_proof, "native compilation proof"))
    core.require(proof.get("schema") == "pinkha-exact-native-compiler-inputs-v1"
                 and proof.get("status") == "PASS_EXACT_NATIVE_COMPILER_INPUTS_NOT_TEST_EXECUTION"
                 and proof.get("sourceCommit") == source_commit and proof.get("testsExecuted") == 0,
                 "Exact Wave3 native compiler proof required; UI/package proof is not a substitute")
    rows = proof.get("requiredSources")
    core.require(isinstance(rows, list) and all(isinstance(row, dict) for row in rows), "Missing actual compiled source rows")
    paths = [row.get("repositoryPath") for row in rows]
    core.require(all(isinstance(path, str) for path in paths) and len(paths) == len(set(paths)),
                 "Duplicate or malformed compiled repository source")
    compiled = []
    for relative, expected in contract["source_hashes"].items():
        selected = [row for row in rows if row["repositoryPath"] == relative]
        core.require(len(selected) == 1, "Required RTL test absent from native compiler proof: " + relative)
        row = selected[0]
        original, actual = app / relative, Path(row.get("compiledPath", ""))
        core.require(actual.is_absolute() and actual.is_file() and not actual.is_symlink()
                     and actual.samefile(original) and row.get("sha256") == expected
                     and row.get("bytes") == original.stat().st_size,
                     "RTL compiler source is not the exact synchronized test source")
        compiled.append(str(actual))
    log = _pinned_bytes(proof.get("buildLog"), "native build log").decode("utf-8").splitlines()
    lists = proof.get("actualCompilerFileLists")
    core.require(isinstance(lists, list) and lists, "No actual native compiler FileList")
    witnesses = []
    for item in lists:
        original = Path(item.get("originalPath", ""))
        core.require(original.is_absolute() and any(part.casefold() == "anytypetests.build" for part in original.parts),
                     "RTL compiler FileList is not from AnytypeTests")
        lines = _pinned_bytes(item, "retained native compiler FileList").decode("utf-8").splitlines()
        lines = [line.strip().strip('"') for line in lines]
        folded = [line.casefold() for line in lines]
        for path in compiled:
            core.require(folded.count(path.casefold()) == 1, "RTL test missing or duplicated in actual native FileList")
            found = Path(lines[folded.index(path.casefold())])
            core.require(found.is_file() and found.samefile(path), "FileList test path names a different physical source")
        invocations = item.get("compilerInvocations")
        core.require(isinstance(invocations, list) and invocations and item.get("compilerInvocation") == invocations[0],
                     "Original compiler invocation witness is absent or inconsistent")
        for witness in invocations:
            number = witness.get("lineNumber")
            core.require(type(number) is int and 1 <= number <= len(log), "Compiler log line is absent")
            line = log[number - 1]
            core.require(witness.get("moduleName") == TARGET and sha(line.encode("utf-8")) == witness.get("lineSHA256"),
                         "Actual native compiler log witness differs")
            tokens = shlex.split(line)
            modules = [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "-module-name"]
            inputs = [token[1:] for token in tokens if token.startswith("@")]
            core.require(any(Path(token).name == "swiftc" for token in tokens) and modules == [TARGET]
                         and any(path.casefold() == str(original).casefold() for path in inputs),
                         "Actual swiftc invocation does not use the selected AnytypeTests FileList")
        witnesses.append(dict(retainedFileList=item["path"], retainedSHA256=item["sha256"],
                              originalPath=str(original), compilerInvocations=invocations))
    return dict(contract, source_commit=source_commit, native_compilation_proof=native_compilation_proof,
                actual_native_compiler_witnesses=witnesses, tests_executed=0)


def invocation_selectors(selectors, contract):
    """Select both complete source-qualified suites, then enumerate six methods.

    Preserve the existing Xcode27 workaround: parameterized Swift Testing
    display signatures must not be passed directly as method filters.
    """
    expected = sorted(TARGET + "/" + suite + "/" + name + "("
                      + "".join(parameter["name"] + ":" for parameter in spec["parameters"]) + ")"
                      for suite, value in SUITES.items() for name, spec in value["methods"].items())
    core.require(contract.get("kind") == "rtl-hosted" and contract.get("expected_methods") == METHOD_COUNT
                 and contract.get("declared_cases") == CASE_COUNT
                 and contract.get("compiled_identifiers") == expected and sorted(selectors) == expected
                 and len(selectors) == len(set(selectors)) == METHOD_COUNT
                 and contract.get("source_hashes") == {value["source_path"]: value["source_sha256"] for value in SUITES.values()}
                 and contract.get("actual_native_compiler_witnesses") and contract.get("native_compilation_proof"),
                 "Complete source/compiler-qualified RTL suites required before suite filtering")
    return [TARGET + "/" + suite for suite in sorted(SUITES)]


def validate_enumeration(payload, contract):
    plan, enabled, disabled = existing.enumerated_identifiers(payload)
    core.require(plan == TARGET and enabled == set(contract["compiled_identifiers"])
                 and not enabled.intersection(disabled), "Compiled RTL selection differs from six exact declarations")
    return dict(test_plan=plan, identifiers=sorted(enabled), tests_executed=0)


def validate_results(summary, tree, udid):
    expected = {suite + "/" + method for suite, spec in SUITES.items() for method in spec["methods"]}
    actual = host.validate_results(summary, tree, expected, udid)
    cases = core.validate_arguments(tree, expected, SUITES)
    core.require(actual["counts"]["totalTestCount"] in {METHOD_COUNT, CASE_COUNT}
                 and cases["actual_method_count"] == METHOD_COUNT and cases["declared_case_count"] == CASE_COUNT,
                 "RTL actual named/argument execution is incomplete")
    return dict(actual, **cases)
