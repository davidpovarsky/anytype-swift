#!/usr/bin/env python3
"""Portable negative controls for the finite Library evidence boundary only."""
from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--shared-controller", type=Path, required=True)
    parser.add_argument("--shared-controller-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only-control")
    args = parser.parse_args()
    sha = lambda raw: hashlib.sha256(raw).hexdigest()
    if sha(args.shared_controller.read_bytes()) != args.shared_controller_sha256:
        raise ValueError("Exact shared utility source required")
    c = load(args.shared_controller, "library_control_shared")
    m = load(args.control_root / "native_library_search.py", "library_control_module")
    controls = []

    def control(name, action):
        if args.only_control is not None and args.only_control != name:
            return
        try:
            controls.append({"name": name, "status": "PASS", "detail": action()})
        except BaseException as error:
            controls.append({"name": name, "status": "FAIL", "reason": str(error)})

    def rejected(action):
        try:
            action()
        except (ValueError, RuntimeError):
            return
        raise AssertionError("An invalid Library evidence envelope was accepted")

    def inverse():
        current = (args.control_root / "NativeLaunchTests.swift").read_bytes()
        proof = (args.control_root / "source-proof.json").read_bytes()
        restored = m.qualify_source(c, current, proof)
        assert restored == (args.control_root / "NativeLaunchTests.frozen.swift").read_bytes()
        changed = current.replace(b'let documentName = "Drag document "', b'let documentName = "Changed document "', 1)
        assert changed != current
        rejected(lambda: m.qualify_source(c, changed, proof))
        return {"exactInsertionInverse": True, "oldMethodMutationRejected": True, "originalMethods": 18}

    control("one_insertion_restores_all_original_source", inverse)
    with tempfile.TemporaryDirectory(prefix="native-library-portable-") as temporary:
        directory = Path(temporary).resolve()
        device = "00000000-0000-4000-8000-000000000001"
        scope = "00000000-0000-4000-8000-000000000002"
        suffix = scope.replace("-", "").lower()
        pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jO1sAAAAASUVORK5CYII=")
        identities = {}
        for key, word in (("alpha", "ראשון"), ("beta", "שני")):
            query = "library" + key + suffix
            identities[key] = {"title": "Library " + key.capitalize() + " " + suffix,
                "query": query, "hierarchyRowIdentifier": "any-native-hierarchy-row-object-" + key,
                "objectIDFromHierarchy": "object-" + key, "blockIdentifier": "any-native-block-block-" + key,
                "bodySHA256": sha(("מסמך " + word + " לחיפוש " + query).encode())}
        records, attachments = {}, []
        for phase in m.PHASES:
            key = "beta" if phase in ("replacement-beta-result", "cold-beta-result", "cold-opened-beta") else "alpha"
            query = "" if phase == "cleared-hierarchy" else "libraryabsent" + suffix if phase == "no-match" else identities[key]["query"]
            opened = phase in ("opened-alpha", "cold-opened-beta")
            row = {"schema": "any-native-library-search-ui/v1", "phase": phase, "ownedScope": scope,
                "spaceName": "Library search UI " + suffix[:8], "requestedAppLanguage": "he",
                "queryExpected": query, "queryFieldExists": not opened,
                "queryObserved": None if opened else query, "completedColdReopens": 1 if phase.startswith("cold-") else 0,
                "nativeIdentityOrigin": "actual-mounted-hierarchy-and-editor-accessibility",
                "nativeReadExtraCallsByObserver": 0, "testStorageOverrides": False, "identities": copy.deepcopy(identities),
                "visibleNativeBlocks": [{"identifier": identities[key]["blockIdentifier"],
                    "bodySHA256": identities[key]["bodySHA256"]}] if opened else []}
            if not opened:
                if phase == "cleared-hierarchy":
                    row["visibleFixtureRows"] = [{"label": item["title"], "identifier": item["hierarchyRowIdentifier"],
                                                   "hittable": True} for item in identities.values()]
                elif phase == "no-match":
                    row["visibleFixtureRows"] = []
                else:
                    row["visibleFixtureRows"] = [{"label": identities[key]["title"] + "\nNative FTS snippet",
                                                   "identifier": "", "hittable": True}]
            records[phase] = row
            for kind in (".json", ".png", ".txt"):
                name = phase + kind
                raw = json.dumps(row).encode() if kind == ".json" else pixel if kind == ".png" else b"SYNTHETIC AX CONTROL ONLY"
                (directory / name).write_bytes(raw)
                label = m.PREFIX + phase + ("-private-ax" if kind == ".txt" else "")
                attachments.append({"suggestedHumanReadableName": label + "_1_" + device + kind,
                    "exportedFileName": name, "deviceId": device, "isAssociatedWithFailure": False})
        manifest = [{"testIdentifier": m.TARGET + "/" + m.SELECTOR + "()", "attachments": attachments}]
        write_manifest = lambda value: (directory / "manifest.json").write_text(json.dumps(value) + "\n")

        def typed_groups():
            write_manifest(manifest)
            proof = m.attachments(c, directory, device)
            assert set(proof["phases"]) == set(m.PHASES) and proof["visualReview"] == "PENDING"
            wrong_test = copy.deepcopy(manifest)
            wrong_test[0]["testIdentifier"] = "NativeLaunchTests/testHierarchyDragIntoFolderPersistsAfterColdReopen()"
            write_manifest(wrong_test); rejected(lambda: m.attachments(c, directory, device))
            wrong_device = copy.deepcopy(manifest)
            wrong_device[0]["attachments"][0]["deviceId"] = scope
            write_manifest(wrong_device); rejected(lambda: m.attachments(c, directory, device))
            return {"syntheticGroups": 7, "actualUIObservations": 0, "wrongTestAndDeviceRejected": True}

        control("typed_groups_require_one_test_and_owned_device", typed_groups)

        def missing_or_aliased():
            missing = copy.deepcopy(manifest); missing[0]["attachments"].pop(0)
            write_manifest(missing); rejected(lambda: m.attachments(c, directory, device))
            duplicate = copy.deepcopy(manifest); duplicate[0]["attachments"].append(copy.deepcopy(attachments[1]))
            write_manifest(duplicate); rejected(lambda: m.attachments(c, directory, device))
            escaped = copy.deepcopy(manifest); escaped[0]["attachments"][0]["exportedFileName"] = "../alpha-result.json"
            write_manifest(escaped); rejected(lambda: m.attachments(c, directory, device))
            failed = copy.deepcopy(manifest); failed[0]["attachments"][0]["isAssociatedWithFailure"] = True
            write_manifest(failed); rejected(lambda: m.attachments(c, directory, device))
            return {"missingMetadataDuplicatePNGEscapedPathAndFailureRejected": True}

        control("missing_aliased_or_failed_original_observation_rejected", missing_or_aliased)

        def identities_and_queries():
            assert m.validate_metadata(c, records)["completedColdReopens"] == 1
            mutations = []
            wrong_scope = copy.deepcopy(records); wrong_scope["cold-opened-beta"]["ownedScope"] = device
            mutations.append(wrong_scope)
            wrong_body = copy.deepcopy(records); wrong_body["opened-alpha"]["visibleNativeBlocks"][0]["bodySHA256"] = "0" * 64
            mutations.append(wrong_body)
            old_result = copy.deepcopy(records); old_result["replacement-beta-result"]["visibleFixtureRows"] = copy.deepcopy(records["alpha-result"]["visibleFixtureRows"])
            mutations.append(old_result)
            not_reopened = copy.deepcopy(records); not_reopened["cold-beta-result"]["completedColdReopens"] = 0
            mutations.append(not_reopened)
            wrong_clear = copy.deepcopy(records); wrong_clear["cleared-hierarchy"]["visibleFixtureRows"][0]["identifier"] = "different-object"
            mutations.append(wrong_clear)
            for mutation in mutations:
                rejected(lambda value=mutation: m.validate_metadata(c, value))
            return {"crossScopeWrongBodyOldResultMissingReopenAndChangedHierarchyRejected": len(mutations)}

        control("native_identity_current_query_and_cold_reopen_are_bound", identities_and_queries)

    if not controls or args.output.exists():
        raise ValueError("Selected portable controls and fresh output required")
    result = {"status": "PASS_PORTABLE_LIBRARY_PREPARATION_NOT_APPLE_ACCEPTANCE" if all(row["status"] == "PASS" for row in controls) else "FAIL",
        "controls": controls, "passed": sum(row["status"] == "PASS" for row in controls),
        "failed": sum(row["status"] == "FAIL" for row in controls),
        "collectorSHA256": sha((args.control_root / "native_library_search.py").read_bytes()),
        "validationScriptSHA256": sha(Path(__file__).read_bytes()),
        "sourceProofSHA256": sha((args.control_root / "source-proof.json").read_bytes()),
        "sharedUtilitySHA256": args.shared_controller_sha256, "onlyControl": args.only_control,
        "AppleCommands": 0, "XCTestMethodsExecuted": 0, "nativeCalls": 0,
        "syntheticEvidenceIsUIAcceptance": False, "physicalDevice": "NOT_RUN"}
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "passed", "failed", "AppleCommands")}))
    if result["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
