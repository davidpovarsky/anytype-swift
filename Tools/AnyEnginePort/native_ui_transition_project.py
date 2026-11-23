#!/usr/bin/env python3
"""Fixed native UI-runner project projection; the original App is never a target.

The separately qualified Anytype UI-only generator supplies the design pattern,
not an interchangeable project: this adapter admits the exact native project.
No xcodebuild, installation, test or network operation occurs in this module.
"""
from __future__ import annotations
import copy
import hashlib
import os
from pathlib import Path
import re
import stat
import xml.etree.ElementTree as ET

PROJECT_SHA = "7282befe3104df28a3e0f5feef05a018bc515c68cf443307de65dbe977e33532"
SCHEME_SHA = "f208c605b78e849e18defc7c759f3588dc9ab9b3f3bdd7502257c605da9db308"
HISTORY_SHA = "f104bcd9722dfac94c90c947e4879447f081f2898149809966f0fb4ccea6230b"
TARGET = "PinkhaAnyNativeUITests"
TARGET_ID = "A50000000000000000000002"
PROJECT_ID = "A60000000000000000000001"
PROJECT_NAME = "AnyNativeTransitionUI.xcodeproj"
SCHEME_NAME = "PinkhaAnyNativeTransitionUI"
OBJECTS = (
    "A10000000000000000000003", "A10000000000000000000005",
    "A20000000000000000000003", "A20000000000000000000006",
    "A20000000000000000000004", "A30000000000000000000001",
    "A30000000000000000000002", "A40000000000000000000004",
    "A40000000000000000000005", "A40000000000000000000006",
    TARGET_ID, PROJECT_ID, "A90000000000000000000001",
    "A90000000000000000000003", "AA0000000000000000000001",
    "AA0000000000000000000002", "AA0000000000000000000005",
    "AA0000000000000000000006",
)
SOURCE_NAMES = ("NativeLaunchTests.swift", "NativeHistoryTests.swift")


def require(value, reason):
    if not value:
        raise ValueError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def brace_end(text, start):
    require(text[start] == "{", "expected_openstep_brace")
    level = 0
    quoted = escaped = False
    for offset in range(start, len(text)):
        char = text[offset]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
            continue
        if char == '"':
            quoted = True
        elif char == "{":
            level += 1
        elif char == "}":
            level -= 1
            if level == 0:
                return offset + 1
    raise ValueError("unterminated_original_project_object")


def objects(raw):
    require(sha(raw) == PROJECT_SHA, "exact_original_native_project_required")
    text = raw.decode("utf-8")
    result = {}
    for match in re.finditer(r"(?m)^  ([A-F0-9]{24}) = \{", text):
        identifier = match[1]
        require(identifier not in result, "duplicate_original_project_object")
        end = brace_end(text, text.index("{", match.start()))
        require(text[end:end + 1] == ";", "original_project_object_terminator_changed")
        result[identifier] = text[match.start():end + 1]
    require(set(OBJECTS) <= result.keys(), "required_original_ui_object_missing")
    return text, result


def replace_once(text, old, new, label, changes):
    require(text.count(old) == 1, "fixed_project_replacement_missing:" + label)
    changes.append({"label": label, "before": old, "after": new})
    return text.replace(old, new, 1)


def project_bytes(original):
    text, all_objects = objects(original)
    selected = {name: all_objects[name] for name in OBJECTS}
    changes = []
    root = "A30000000000000000000001"
    selected[root] = replace_once(selected[root],
        "children = (A20000000000000000000005, A20000000000000000000001, "
        "A20000000000000000000003, A20000000000000000000006, "
        "B30000000000000000000001, B30000000000000000000002, A30000000000000000000002);",
        "children = (A20000000000000000000003, A20000000000000000000006, A30000000000000000000002);",
        "root_group_contains_two_ui_sources_and_products_only", changes)
    products = "A30000000000000000000002"
    selected[products] = replace_once(selected[products],
        "children = (A20000000000000000000002, A20000000000000000000004, "
        "B20000000000000000000003, B20000000000000000000004);",
        "children = (A20000000000000000000004);",
        "one_ui_test_product", changes)
    selected[TARGET_ID] = replace_once(selected[TARGET_ID],
        "dependencies = (AB0000000000000000000002);", "dependencies = ();",
        "remove_native_app_target_dependency", changes)
    project = selected[PROJECT_ID]
    marker = "TargetAttributes = {"
    require(project.count(marker) == 1, "one_original_target_attributes_map_required")
    start = project.index(marker)
    end = brace_end(project, project.index("{", start))
    project = replace_once(project, project[start:end],
        "TargetAttributes = { A50000000000000000000002 = {CreatedOnToolsVersion = 27.0; }; }",
        "only_ui_target_attributes_without_test_target_app", changes)
    matches = list(re.finditer(r"packageReferences = \([^;]*\);", project))
    require(len(matches) == 1, "one_original_package_references_field_required")
    project = replace_once(project, matches[0][0], "packageReferences = ();",
                           "no_package_references", changes)
    project = replace_once(project,
        "targets = (A50000000000000000000001, A50000000000000000000002, "
        "B50000000000000000000001, B50000000000000000000002);",
        "targets = (A50000000000000000000002);",
        "only_ui_test_target", changes)
    selected[PROJECT_ID] = project
    for identifier in ("AA0000000000000000000005", "AA0000000000000000000006"):
        selected[identifier] = replace_once(selected[identifier],
            "TEST_TARGET_NAME = PinkhaAnyNativeApp;", 'TEST_TARGET_NAME = "";',
            "no_implicit_app_in_" + identifier, changes)
    marker = "objects = {"
    require(text.count(marker) == 1, "one_original_objects_map_required")
    start = text.index("{", text.index(marker))
    end = brace_end(text, start)
    projected = text[:start + 1] + "\n" + "\n".join(selected.values()) + "\n " + text[end - 1:]
    validate_project(projected)
    proof = {
        "originalProjectSHA256": PROJECT_SHA,
        "projectSHA256": sha(projected.encode("utf-8")),
        "selectedObjectCount": len(selected),
        "selectedObjectIDs": list(OBJECTS),
        "discardedOriginalObjectCount": len(all_objects) - len(selected),
        "selectedObjectSource": {
            name: {"originalSHA256": sha(all_objects[name].encode()),
                   "projectedSHA256": sha(selected[name].encode())}
            for name in OBJECTS
        },
        "exactTransformations": changes,
        "applicationTargets": 0, "uiTestTargets": 1,
        "packageReferences": 0, "targetDependencies": 0,
    }
    # Every selected source object is mechanically reversible. Original source
    # files are never edited, and discarded App/host/package objects never enter
    # the generated build graph.
    reverse = dict(selected)
    for change in reversed(changes):
        owners = [name for name, value in reverse.items() if change["after"] in value]
        if change["label"].startswith("no_implicit_app_in_"):
            owners = [change["label"].removeprefix("no_implicit_app_in_")]
        require(len(owners) == 1, "ambiguous_project_inverse_owner")
        name = owners[0]
        reverse[name] = reverse[name].replace(change["after"], change["before"], 1)
    require(reverse == {name: all_objects[name] for name in OBJECTS}, "project_inverse_changed_original_ui_objects")
    proof["selectedObjectInverse"] = "EXACT_ORIGINAL_BYTES"
    return projected.encode("utf-8"), proof


def validate_project(text):
    require(text.count("isa = PBXNativeTarget;") == 1
            and text.count('productType = "com.apple.product-type.bundle.ui-testing";') == 1,
            "exactly_one_ui_test_target_required")
    for forbidden in ("com.apple.product-type.application", "PinkhaAnyNativeApp",
                      "PBXTargetDependency", "PBXContainerItemProxy",
                      "XCLocalSwiftPackageReference", "XCRemoteSwiftPackageReference",
                      "XCSwiftPackageProductDependency", "packageProductDependencies",
                      "TestTargetID"):
        require(forbidden not in text, "forbidden_app_or_package_reference:" + forbidden)
    require(text.count("packageReferences = ();") == 1
            and text.count("dependencies = ();") == 1
            and text.count('TEST_TARGET_NAME = "";') == 2,
            "ui_only_dependency_or_configuration_shape_changed")
    references = set(re.findall(r"\b[A-F0-9]{24}\b", text))
    require(references == set(OBJECTS), "project_contains_an_unadmitted_reference")


def scheme_bytes(original):
    require(sha(original) == SCHEME_SHA, "exact_original_native_scheme_required")
    root = ET.fromstring(original)
    build = root.find("BuildAction")
    entries = root.find("BuildAction/BuildActionEntries")
    test_reference = root.find("TestAction/Testables/TestableReference/BuildableReference")
    require(build is not None and entries is not None and len(entries) == 1
            and test_reference is not None
            and test_reference.get("BlueprintIdentifier") == TARGET_ID
            and test_reference.get("BlueprintName") == TARGET,
            "original_native_scheme_shape_changed")
    build.set("buildImplicitDependencies", "NO")
    build.set("parallelizeBuildables", "NO")
    for entry in list(entries):
        entries.remove(entry)
    entry = ET.SubElement(entries, "BuildActionEntry", {
        "buildForTesting": "YES", "buildForRunning": "NO", "buildForProfiling": "NO",
        "buildForArchiving": "NO", "buildForAnalyzing": "NO"})
    entry.append(copy.deepcopy(test_reference))
    for parent in root.iter():
        for child in list(parent):
            if child.tag in ("MacroExpansion", "BuildableProductRunnable"):
                parent.remove(child)
    references = list(root.iter("BuildableReference"))
    require(len(references) == 2, "one_ui_build_entry_and_one_testable_required")
    for reference in references:
        require(reference.get("BlueprintName") == TARGET
                and reference.get("BlueprintIdentifier") == TARGET_ID,
                "non_ui_scheme_reference_forbidden")
        reference.set("ReferencedContainer", "container:" + PROJECT_NAME)
    require(root.find(".//TestPlans") is None, "new_named_test_plan_forbidden")
    raw = ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
    require(b"PinkhaAnyNativeApp" not in raw and b"buildImplicitDependencies=\"NO\"" in raw,
            "app_or_implicit_build_remains_in_scheme")
    return raw


def generate(directory, *, original_project, original_scheme,
             launch_source, expected_launch_sha256, history_source):
    require(re.fullmatch("[0-9a-f]{64}", expected_launch_sha256) is not None
            and sha(launch_source) == expected_launch_sha256
            and sha(history_source) == HISTORY_SHA, "frozen_ui_source_bytes_required")
    directory = Path(directory)
    require(directory.is_absolute() and directory.resolve() == directory
            and not directory.exists(), "fresh_disjoint_runner_source_directory_required")
    project, proof = project_bytes(original_project)
    scheme = scheme_bytes(original_scheme)
    files = {
        PROJECT_NAME + "/project.pbxproj": project,
        PROJECT_NAME + "/xcshareddata/xcschemes/" + SCHEME_NAME + ".xcscheme": scheme,
        "UITests/NativeLaunchTests.swift": launch_source,
        "UITests/NativeHistoryTests.swift": history_source,
    }
    directory.mkdir(mode=0o700)
    observed = {}
    for relative, raw in files.items():
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        path.chmod(0o400)
        value = path.lstat()
        require(stat.S_ISREG(value.st_mode) and value.st_nlink == 1
                and path.read_bytes() == raw, "generated_ui_input_write_changed")
        observed[relative] = {"sha256": sha(raw), "bytes": len(raw), "mode": 0o400}
    return {"project": str(directory / PROJECT_NAME), "scheme": SCHEME_NAME,
            "generatedInputs": observed, "projection": proof,
            "originalSchemeSHA256": SCHEME_SHA, "newSchemeSHA256": sha(scheme),
            "testsExecuted": 0, "applicationBuilds": 0, "nativeLibraryBuilds": 0}
