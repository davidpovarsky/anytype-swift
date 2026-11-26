#!/usr/bin/env python3
"""Bind the original six Page154 methods to the shared, admitted App16 product.

This prepares controller files only. It does not admit a build, create fixtures,
run XCTest, touch simulator data, or change any original result. The resulting
controller still verifies the complete original producer before execution.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SOURCE = "a089ff29a5c0a7e415aac800844505f099a5561d"
MANIFEST = "8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b"
OVERLAY = "2f76212f9fcd749aeb9e806b941e0fd0b54eba17e5cc842adb81c7eb3bae0f38"
ORIGINAL_ADMISSION = "87c47c356e591ee7f51e6c3fa21a4fe0cd903821cceec357ed11cfbfc582a366"
CORE = "combined_heart_semantics_replacement.py"
SHARED = "combined_heart_semantics_current.py"
SUPERVISOR = "run_retained_heart_semantics_replacement.py"
TYPED_HELPER = "semantic_link_route_typed_attachments.py"
TYPED_SHA = "39cb1d84f78efb922b71dc55ccb371647c90296093e365452b1291ef854aacf6"
ORIGINALS = {
    CORE: "6c1dea1ef571059291dc9d21c86d1558913a0153a67d719723b601ddcd2ac63c",
    SHARED: "1dcd02a4413b26c201e8a38772484eff48e448ae4398af2fd4ee1fc6a5675736",
    SUPERVISOR: "9f527c10e2c03c90925710680c143f5085754254e909d9afcc756dbd5bb95f73",
    "combined_heart_observations_gateway.py": "425783c76858b542cb908e5d4c606e3d27b54d6e5bbc1e28a163cc18f13cf4de",
    "replacement_selection_observation.py": "460937313a94977b121a4fb85d81be0d0e9617f96796b8afe15d248a84ea3f12",
    "retain_owned_heart_account.py": "c562f0b2297902efd62b3a92fdef68e658fb688bbd002d15db24609d47602f3b",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def read(path, expected):
    path = Path(path)
    require(re.fullmatch(r"[0-9a-f]{64}", expected), "An exact SHA-256 is required")
    before = path.lstat()
    require(path.is_absolute() and path.resolve() == path
            and stat.S_ISREG(before.st_mode) and before.st_size <= 2 * 1024**2,
            "A bounded, canonical original regular file is required: " + str(path))
    value = path.read_bytes()
    after = path.lstat()
    require((before.st_dev, before.st_ino, before.st_mtime_ns, before.st_size)
            == (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_size)
            and sha(value) == expected, "Original input changed: " + str(path))
    return value


def decode(value):
    def unique(pairs):
        result = {}
        for name, item in pairs:
            require(name not in result, "Duplicate JSON key")
            result[name] = item
        return result
    return json.loads(value, object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def definitions(value):
    text = value.decode("utf8")
    return {node.name: ast.get_source_segment(text, node)
            for node in ast.parse(text).body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}


def replace_exact(value, changes):
    text = value.decode("utf8")
    evidence = []
    for old, new, count in changes:
        require(text.count(old) == count, "Original controller occurrence contract differs")
        text = text.replace(old, new)
        positions = [match.start() for match in re.finditer(re.escape(new), text)]
        require(len(positions) == count, "Replacement would have ambiguous inverse positions")
        evidence.append({"old": old, "new": new, "count": count, "newPositions": positions})
    restored = text
    for row in reversed(evidence):
        for position in reversed(row["newPositions"]):
            require(restored[position:position + len(row["new"])] == row["new"],
                    "Controller inverse position changed")
            restored = restored[:position] + row["old"] + restored[position + len(row["new"]):]
    require(restored.encode() == value, "Every original controller byte must be recoverable")
    ast.parse(text)
    return text.encode(), evidence


def prepare(originals_root, shared_controller, shared_sha, canonical_admission,
            admission_sha, typed_helper, output):
    originals_root, output = Path(originals_root), Path(output)
    require(originals_root.is_absolute() and originals_root.resolve() == originals_root,
            "Canonical retained controller root is required")
    require(output.is_absolute() and output.parent.resolve() == output.parent
            and output.parent.is_dir() and not output.exists() and not output.is_symlink(),
            "A fresh controller directory with an existing canonical parent is required")
    originals = {name: read(originals_root / name, digest) for name, digest in ORIGINALS.items()}
    shared = read(shared_controller, shared_sha)
    admitted_raw = read(canonical_admission, admission_sha)
    typed = read(typed_helper, TYPED_SHA)
    admitted = decode(admitted_raw)
    require(isinstance(admitted, dict)
            and admitted.get("schema") == "pinkha-combined-heart-semantics-admission-v1"
            and admitted.get("executionEnvironment") == "SentinelX-owned-Mac"
            and admitted.get("sourceCommit") == SOURCE
            and admitted.get("controllerSHA256") == shared_sha
            and admitted.get("nativeManifestSHA256") == MANIFEST
            and admitted.get("heartOverlaySHA256") == OVERLAY
            and isinstance(admitted.get("app16Producer"), dict)
            and "sharedAdmission" not in admitted and "uiContinuation" not in admitted,
            "The exact current canonical App16 admission is required")
    before_shared, after_shared = definitions(originals[SHARED]), definitions(shared)
    require(before_shared["Commands"] == after_shared.get("Commands"),
            "Original owned command lifecycle, disk floor and timeouts must be retained")
    require(all(name in after_shared for name in
                ("admit_app16_and_clone_products", "qualify_app16_producer", "qualify_app16_runtime")),
            "The shared reviewed App16 intake is missing")

    binding_guard = ("    expected = decode(original)\n"
                     "    require(expected[\"sourceCommit\"] == \"" + SOURCE + "\"\n"
                     "            and expected[\"controllerSHA256\"] == \"" + shared_sha + "\",\n"
                     "            \"Canonical shared App16 source and controller differ\")\n")
    changes = [
        (ORIGINALS[SHARED], shared_sha, 1),
        ("Exact shared App15 admission and owned command outcomes required",
         "Exact shared App16 admission and original owned command outcomes required", 1),
        (ORIGINAL_ADMISSION, admission_sha, 1),
        ("Exact canonical App15 shared admission required", "Exact canonical App16 shared admission required", 1),
        ("    expected = decode(original)\n", binding_guard, 1),
        ("ed57e0df1b461fe559b8e82af1ad4c1a95e1100802c96fdd87cada9bbd1598a6", TYPED_SHA, 1),
        ("semantic_link_route_observation", "semantic_link_route_typed_attachments", 2),
    ]
    core, inverse = replace_exact(originals[CORE], changes)
    before_core, after_core = definitions(originals[CORE]), definitions(core)
    require(set(before_core) == set(after_core), "Six-stage controller definitions changed")
    preserved = sorted(set(before_core) - {"qualified_shared_controller", "admit_and_clone_products", "main"})
    require(all(before_core[name] == after_core[name] for name in preserved),
            "Original stage/result/source/retention validators changed")
    core_sha = sha(core)
    supervisor, supervisor_inverse = replace_exact(originals[SUPERVISOR], [(ORIGINALS[CORE], core_sha, 1)])
    shared_pin = {"path": str(output / "shared-admission.json"),
                  "bytes": len(admitted_raw), "sha256": admission_sha}
    specialized = copy.deepcopy(admitted)
    specialized["controllerSHA256"] = core_sha
    specialized["sharedAdmission"] = shared_pin
    files = {name: value for name, value in originals.items() if name != SHARED}
    files.update({CORE: core, SHARED: shared, SUPERVISOR: supervisor, TYPED_HELPER: typed,
                  "shared-admission.json": admitted_raw,
                  "admission-app16-page154.json": encoded(specialized)})
    receipt = {
        "schema": "pinkha-wave2-page154-profile-preparation-v1",
        "status": "PREPARED_EXACT_SIX_STAGE_PROFILE_NOT_BUILD_OR_ACCEPTANCE",
        "sourceCommit": SOURCE, "nativeManifestSHA256": MANIFEST,
        "originalControllerFiles": ORIGINALS, "typedAttachmentCollectorSHA256": TYPED_SHA,
        "sharedControllerSHA256": shared_sha, "sharedAdmissionSHA256": admission_sha,
        "controllerSHA256": core_sha, "controllerChanges": inverse,
        "supervisorChanges": supervisor_inverse, "inverseRestoresEveryOriginalByte": True,
        "unchangedControllerDefinitions": preserved,
        "fixtureDeadlineChanges": 0, "fixtureRestorations": 0, "testsExecuted": 0,
        "applicationBuilds": 0, "nativeCalls": 0,
        "originalEvidenceRewritten": False, "oldFixtureReused": False,
        "freshFixtureReason": "Original fixture expired under the unchanged 7200-second authority; App16 includes the focus correction.",
        "retainedPriorStages": {"preparation": "PASS", "mounted": "PASS", "linked-ui": "PASS"},
        "retainedPriorFailures": {
            "linked-ui-attachment-collection": "Original PNG was rejected by the JSON-only collector; typed evidence correction is separate.",
            "linked-native-enumerate": {"status": "OWNED_TIMEOUT", "timeoutSeconds": 180,
                "resultSHA256": "bcfa06bea94cc0ce89541dc3e165160d6574ce1c9f551c56857102a24d00a5e0"}},
        "physicalDevice": "NOT_RUN",
        "files": {name: {"bytes": len(value), "sha256": sha(value)} for name, value in sorted(files.items())},
    }
    files["prepared-profile.json"] = encoded(receipt)
    output.mkdir(mode=0o700)
    for name, value in files.items():
        with (output / name).open("xb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        (output / name).chmod(0o600)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-controller-root", type=Path, required=True)
    parser.add_argument("--shared-controller", type=Path, required=True)
    parser.add_argument("--shared-controller-sha256", required=True)
    parser.add_argument("--canonical-admission", type=Path, required=True)
    parser.add_argument("--canonical-admission-sha256", required=True)
    parser.add_argument("--typed-helper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.historical_controller_root, args.shared_controller,
                     args.shared_controller_sha256, args.canonical_admission,
                     args.canonical_admission_sha256, args.typed_helper, args.output)
    print(json.dumps({name: result[name] for name in
                      ("status", "sourceCommit", "controllerSHA256", "testsExecuted")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
