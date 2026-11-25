#!/usr/bin/env python3
"""Continue Apple execution from one exact, separately preserved framework build.

The original run failed before XCTest because its simulator pair was invalid.
Its two completed framework builds remain build-only evidence. This controller
never edits their receipts or substitutes the new execution source/run IDs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import coherent_runtime_admission as admission
import heart_runtime_profile as profiles
from build_custom_heart import contains, digest, git, verify_framework_slices

RUN = profiles.COHERENT_BUILT_RUN
SOURCE = profiles.COHERENT_BUILT_SHA
ATTEMPT = "1"
REPOSITORY = "davidpovarsky/anytype-swift"
BRANCH = "codex/chatgpt-wave15-shared-20261121"
WORKFLOW = ".github/workflows/torah-inspector-ipados27.yml"
STATUS = "VERIFIED_ORIGINAL_COHERENT_APPLE_BUILD_REUSE"
BUILD_SHA = "a269ce89ba874aa54776cea17c11f58195a6fbfa40554fe62f9ef5ee03bce1c8"
FAILED_HOST_SHA = "3a9b11af2c5dadceef7a964367df35bddd8820d76c4fec6459bc382efa473c7a"
PRODUCTION_RECEIPT_SHA = "f924c22b612bf456fafd754f66152905110e0e6556bf1b6f858dc09e2a6cc9a0"
FIXTURE_RECEIPT_SHA = "90f50a38cc02e0b1b50f2621fca9a73b02adc25081ab16eacdb8b1266505cec7"
ARTIFACTS = {
    "proof": dict(id=profiles.COHERENT_BUILT_PROOF_ARTIFACT,
                  name="Pinkha-Coherent-Heart-Apple-45035194823-1", size_in_bytes=3791782,
                  zip_sha256=profiles.COHERENT_BUILT_PROOF_SHA),
    "production": dict(id=profiles.COHERENT_BUILT_ARTIFACT,
                       name="Pinkha-Coherent-Heart-Production-Simulator-v1", size_in_bytes=88422351,
                       zip_sha256=profiles.COHERENT_BUILT_ARTIFACT_SHA,
                       tar_sha256="ac94393135cf044d1dd035d7c00fed8c6d0ba0c265d9b0e7b9b676d1f6abe3dc"),
    "fixture": dict(id=14760192199, name="Pinkha-Coherent-Heart-Fixture-Simulator-v1", size_in_bytes=88499174,
                    zip_sha256="5bd3b2dde6287dd648b69b4d6149293f60f454223e8be3a33ec1174d4f77e926",
                    tar_sha256="031e3e1893fb20dda22f197e52182112b1f28384302a27006b3faf2534d6c6ab"),
}
RECEIPTS = {"production": "PinkhaNativeHeartBuild.json", "fixture": "CoherentHeartFixtureBuild.json"}
ALLOWED_CONTROL_CHANGES = {
    ".github/workflows/pinkha-coherent-heart-apple.yml": "Orchestration for original artifact reuse and new host execution; not compiled into either original Go library.",
    "Tools/PinkhaNativeDerived/coherent_apple/run_host.py": "Host execution controller: compatible simulator selection and explicit immutable build lineage; not part of the completed Go builds.",
    "Tools/PinkhaSimulatorGate/simulator_selection.py": "New host-only runtime/device compatibility selector, bound into the actual new host source snapshot.",
    "Tools/PinkhaNativeDerived/coherent_apple/reuse_build.py": "New artifact lineage verifier and extraction controller; does not generate or compile native source.",
    "Tools/PinkhaNativeDerived/coherent_apple/test_build_reuse.py": "New controller-only regression controls for original-build retention; never compiled into the native libraries.",
    "Tools/PinkhaNativeDerived/coherent_apple/retain_controls.py": "Fresh-build retained-control qualification pins the exact unchanged executed host AST dependency closure; not compiled into the original libraries.",
    "Tools/PinkhaNativeDerived/coherent_runtime_admission.py": "Consumer-side original artifact admission, after native build and Apple host proof.",
    "Tools/PinkhaNativeDerived/heart_runtime_profile.py": "Consumer runtime source/receipt binding, after native build and Apple host proof.",
    "Tools/PinkhaNativeDerived/test_coherent_reuse_admission.py": "New Python admission controls, outside the original compiled native source and Swift module closure.",
}
require = profiles.require

# This is one explicitly reviewed Swift composition, not a general module
# exception. The native source/fixture/assertion closure remains immutable.
COMPOSITION_STATUS = "VERIFIED_ORIGINAL_NATIVE_BUILD_CURRENT_SWIFT_COMPOSITION_REQUIRED"
COMPOSITION_PROFILE = "semantic-anchor-shared-modules-20261123"
COMPOSITION_REVIEW_SOURCE = "1bfede896cc4876a6d757ca2c32b4a2805575c6e"
ORIGINAL_MODULE_MAP_SHA = "1e6825317bbef58779c170362ff7b76c785fd5389f6f2075e193dd4fb81b7cbd"
CURRENT_MODULE_MAP_SHA = "1e3e5dda474607a5bdd735aabdbee1f89107ead782352c4ae6595014a3592291"
COMPOSITION_CONTROL = "Tools/PinkhaNativeDerived/coherent_apple/test_current_composition.py"
REVIEWED_MODULE_CHANGES = {
    "Modules/PinkhaKit/Sources/PinkhaKit/Editor/PinkhaSemanticTextAnchor.swift": (
        None, "bfefc94965cfe6dbdf910452eaec3a9530854a6d5b6a09a1a9b10339c6c30274",
        "New Foundation semantic marker model; current Swift harness must compile this exact source."),
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahAssociationIdentity.swift": (
        "5f59d015f211169116c745718fc2ce6b752f5eefd359ec5382f707228994fb70",
        "85738df63c9ae987c1180c20e661cd21cd4acc20afcd376592f87ca32dcdb626",
        "Adds explicit semantic target identity while preserving legacy keys; no old Swift composition claim is reused."),
    "Modules/PinkhaKit/Sources/PinkhaKit/Torah/TorahSemanticAnchorAssociation.swift": (
        None, "17c469ea127bf01211c7e819c00a2e15ea07facbe2c6d86505a5f0fce82cb3f4",
        "New exact-scope semantic association metadata; malformed targets remain distinct from legacy identities."),
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Editor/PinkhaSemanticTextAnchorTests.swift": (
        None, "b9793ad7149a42d2d0941c1c038831faad1d8b5467be4df1583b0351e295f524",
        "Ten original portable component controls are retained separately, not rerun by the coherent harness."),
    "Modules/PinkhaKit/Tests/PinkhaKitTests/Torah/TorahSemanticAnchorAssociationTests.swift": (
        None, "382c6801606f5b6f0bd8e66443a08d7e79cce3e339398011ea76142b5f724426",
        "Four original portable association controls are retained separately, not rerun by the coherent harness."),
}
REVIEWED_COMPOSITION_CONTROLS = {'Tools/AnyEnginePort/verify_native_test_execution.py': ('cc768d66aaee9081f8ff0c882b7dd15eca1625454e324e03f07a257c1ee56575',
                                                         'af126a59d47fec07b0d465c0077c812fb5f52cfcadf71a2da22cebb969e21b91',
                                                         'Adds two NativeApp profile inventories; the '
                                                         'test_cases parser used by coherent execution is '
                                                         'unchanged.'),
 'Tools/PinkhaNativeDerived/install_verified_heart.py': ('0f3286d5c3f84c5b892234b557028eed3125935db8ba843a838cb28be641ab18',
                                                         'fe643439f65e1e20282607d95865c02937a5501d58125834a5cd4bef2532176a',
                                                         'Adds only the explicit acceptance-continuation '
                                                         'consumer branch; original native builder and '
                                                         'bytes are unchanged.'),
 'Tools/PinkhaNativeDerived/package_evidence.py': ('0faf11a18f2c8a220fab570ef3a199e2016091340c0b261148dd7c581294c895',
                                                   '8400bd4ac7bbc61871b51f1021c3dbbb1de5800094e07129417a784d24337309',
                                                   'Adds four exact early Products archive paths, '
                                                   'including nested SDK06 UI products, to evidence '
                                                   'packaging; no native build input changes.'),
 'Tools/PinkhaNativeDerived/test_acceptance_continuation_branch.py': (None,
                                                                      '8e675bab3796f3fcea6c7256e5f3e4200fae3ae219dd988f9dba7d42f78f7ee7',
                                                                      'Controller-only branch/source '
                                                                      'guards; these controls are not '
                                                                      'compiled into native or Swift '
                                                                      'products.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/README.md': (None,
                                                              '3b9b7588e59fbe4100e1a31d2036755e3d13f4caf60f88568b0c8eb936956973',
                                                              'Documentation for the separately built '
                                                              'Linux distinct-member ACL acceptance route; '
                                                              'not compiled into coherent Apple '
                                                              'libraries.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/build.py': (None,
                                                             '8ea19d7906f203d20ada802896f8a2583af724995234ff48a9b82501c699b8bc',
                                                             'Standalone Linux fixture builder applies '
                                                             'only additive test overlays and verifies the '
                                                             'original139 production source before and '
                                                             'after; not called by coherent Apple build or '
                                                             'host.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/contract.py': (None,
                                                                '9458a2365f0f1d5584bcd1c00b4eec271e9af45073321e422728ebb66500d180',
                                                                'Independent-member test-only result '
                                                                'contract; imported only by that separate '
                                                                'controller.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/core_fixture.go': (None,
                                                                    'd7183d066ffe1c8942afb893aa29ad200296b30b15e72be8e1191499b0b02031',
                                                                    'Additive '
                                                                    'pinkha_acl_transport_fixture-tagged '
                                                                    'Go overlay, installed only by the '
                                                                    'separate Linux test builder; absent '
                                                                    'from the original coherent Apple bind '
                                                                    'source.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/native_member_test.go': (None,
                                                                          'e9d3b6cc042212cc711ce0a958ad04eabe6efe2bcbf8a86e5b029db2ecfcc402',
                                                                          'Go test source over separate '
                                                                          'native processes; neither '
                                                                          'installed nor selected by '
                                                                          'coherent Apple production or '
                                                                          'fixture builds.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/run.py': (None,
                                                           '645dd38b3b4f7184bdee8d443721b8d6e07420db2b6795ac9227db50d22f4a42',
                                                           'Docker network/process coordinator for the '
                                                           'independent-member test executable; not a '
                                                           'coherent Apple build dependency.'),
 'Tools/PinkhaNativeDerived/member_acl_transport/source-review.json': (None,
                                                                       'f190966110a1267aa3e0f8b6c9c2452bf30b40e972a5712865e160c755273754',
                                                                       'Metadata for the separate '
                                                                       'independent-member fixture '
                                                                       'closure; does not generate or '
                                                                       'replace coherent production '
                                                                       'source.')}


def origin() -> dict:
    return profiles.validate_reuse_build_origin(dict(run_id=RUN, run_attempt=ATTEMPT, source_sha=SOURCE,
        source_branch=BRANCH, repository=REPOSITORY, workflow_path=WORKFLOW,
        workflow_conclusion="failure", scope="framework_build_only"))


def validate_original_metadata(run: dict, listing: dict) -> dict:
    require(type(run.get("id")) is int and str(run["id"]) == RUN
            and type(run.get("run_attempt")) is int and run["run_attempt"] == 1
            and run.get("head_sha") == SOURCE and run.get("head_branch") == BRANCH
            and run.get("status") == "completed" and run.get("conclusion") == "failure"
            and run.get("repository", {}).get("full_name") == REPOSITORY
            and run.get("event") == "workflow_dispatch" and run.get("path") == WORKFLOW
            and run.get("display_title") == "Pinkha coherent-heart-apple · " + SOURCE,
            "Only the pinned failed-before-XCTest build origin may be continued")
    items = listing.get("artifacts")
    require(type(listing.get("total_count")) is int and listing["total_count"] == 3
            and isinstance(items, list) and len(items) == 3, "Original artifact inventory is incomplete or changed")
    result = {}
    for kind, expected in ARTIFACTS.items():
        matches = [item for item in items if item.get("name") == expected["name"]]
        require(len(matches) == 1, "Original artifact is missing or duplicated: " + kind)
        item = matches[0]
        require(profiles.validate_artifact(item, run, expected["name"]) == expected["zip_sha256"]
                and item["id"] == expected["id"] and item["size_in_bytes"] == expected["size_in_bytes"]
                and item.get("workflow_run", {}).get("head_branch") == BRANCH,
                "Original artifact ID, source, branch, size or digest changed: " + kind)
        result[kind] = item
    return result


def verify_original_proof(directory: Path) -> tuple[dict, dict, dict]:
    proof = directory / "proof"
    require(len(admission._file_map(directory)) == 106, "Original build proof file inventory changed")
    require(digest(proof / "build.json") == BUILD_SHA and digest(proof / "host/receipt.json") == FAILED_HOST_SHA,
            "Original build or failed host receipt changed")
    build, failed = admission.read_json(proof / "build.json"), admission.read_json(proof / "host/receipt.json")
    require(build.get("status") == "BUILT_DISTINCT_COHERENT_APPLE_FRAMEWORKS_NOT_EXECUTED"
            and build.get("phase") == "COMPLETE" and build.get("app_sha") == SOURCE
            and build.get("run_id") == RUN and build.get("run_attempt") == ATTEMPT
            and build.get("production_binary_execution") == build.get("fixture_ios_execution") == "NOT_RUN",
            "Original frameworks were not both completed without execution")
    require(failed.get("status") == "FAIL" and failed.get("app_sha") == SOURCE
            and failed.get("run_id") == RUN and failed.get("run_attempt") == ATTEMPT
            and failed.get("build_receipt_sha256") == BUILD_SHA
            and "actual_execution" not in failed and "actual_attachment_sha256" not in failed,
            "Original failed host cannot be relabelled as Apple execution")
    commands = failed.get("commands", [])
    require(commands and commands[-1].get("name") == "create-owned-simulator"
            and commands[-1].get("status") == "FAIL"
            and all(entry.get("name") != "ios-coherent-tests" for entry in commands),
            "Original failure was not confined to simulator creation before XCTest")
    before = admission.read_json(proof / "host/control-source-before.json")
    require(failed.get("source_snapshot_sha256") == profiles.json_digest(before)
            and failed.get("copied_module_sha256") == {name: sha for name, sha in before.items()
                 if name.startswith(tuple(module + "/" for module in admission.MODULES))},
            "Original source/module closure is incomplete")
    profile = profiles.select(profiles.COHERENT)
    inventory = profiles.verify_source(profile,
        admission.read_bounded(proof / "native-source/native-heart-integration.patch"),
        admission.read_bounded(proof / "native-source/native-heart-integration.json"))
    require(digest(proof / "production/custom-heart-build.json") == PRODUCTION_RECEIPT_SHA
            and digest(proof / "fixture/custom-heart-build.json") == FIXTURE_RECEIPT_SHA,
            "Original packaged receipt bytes changed")
    admission.validate_build(proof, admission.read_bounded(proof / "production/custom-heart-build.json"),
                             inventory, profile, origin(), ARTIFACTS["production"]["tar_sha256"])
    for kind in ("production", "fixture"):
        require(build["frameworks"][kind]["artifact_sha256"] == ARTIFACTS[kind]["tar_sha256"],
                "Original framework archive identity changed")
    return build, before, failed["copied_module_sha256"]


def verify_control_maps(before: dict, after: dict) -> tuple[dict, list]:
    admission._sha_map(before, "original complete controller source")
    admission._sha_map(after, "current complete controller source")
    differences = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    require(differences <= ALLOWED_CONTROL_CHANGES.keys(),
            "Compiled native, assertion, harness, shared module or dependency source changed: " +
            ", ".join(sorted(differences - ALLOWED_CONTROL_CHANGES.keys())))
    modules = {name: sha for name, sha in before.items()
               if name.startswith(tuple(module + "/" for module in admission.MODULES))}
    require(modules and modules == {name: sha for name, sha in after.items()
               if name.startswith(tuple(module + "/" for module in admission.MODULES))},
            "New Apple execution must keep the exact original shared modules")
    return ({name: sha for name, sha in after.items() if name not in differences},
            [dict(path=name, before_sha256=before.get(name), after_sha256=after.get(name),
                  reason=ALLOWED_CONTROL_CHANGES[name]) for name in sorted(differences)])



def module_sources(snapshot: dict) -> dict:
    return {name: sha for name, sha in snapshot.items()
            if name.startswith(tuple(module + "/" for module in admission.MODULES))}


def reviewed_pairs(before: dict, after: dict, approved: dict, label: str) -> list:
    rows = []
    for name, (old, current, reason) in sorted(approved.items()):
        require(before.get(name) == old and after.get(name) == current,
                "Unreviewed " + label + " bytes: " + name)
        rows.append(dict(path=name, before_sha256=old, after_sha256=current, reason=reason))
    return rows


def current_module_lineage(before: dict, after: dict) -> dict:
    original, current = module_sources(before), module_sources(after)
    admission._sha_map(original, "original shared module closure")
    admission._sha_map(current, "current shared module closure")
    require(len(original) == 112 and profiles.json_digest(original) == ORIGINAL_MODULE_MAP_SHA,
            "Original shared module closure differs from the immutable reviewed origin")
    require(len(current) == 116 and profiles.json_digest(current) == CURRENT_MODULE_MAP_SHA,
            "Current shared module closure is not the exact reviewed composition")
    differences = {name for name in original.keys() | current.keys() if original.get(name) != current.get(name)}
    require(differences == REVIEWED_MODULE_CHANGES.keys(), "Unexpected shared module delta")
    changes = reviewed_pairs(original, current, REVIEWED_MODULE_CHANGES, "shared module")
    return dict(profile=COMPOSITION_PROFILE, reviewed_source_sha=COMPOSITION_REVIEW_SOURCE,
                original_module_sha256=original, original_module_map_sha256=ORIGINAL_MODULE_MAP_SHA,
                current_module_map_sha256=CURRENT_MODULE_MAP_SHA, reviewed_module_changes=changes,
                current_harness_build_required=True, actual_composition_method=admission.METHOD,
                previous_swift_acceptance_reused=False, full_app_acceptance="NOT_RUN")


def verify_current_composition(before: dict, after: dict) -> tuple[dict, list, dict]:
    admission._sha_map(before, "original complete controller source")
    admission._sha_map(after, "current complete controller source")
    composition = current_module_lineage(before, after)
    reviewed_pairs(before, after, REVIEWED_COMPOSITION_CONTROLS, "composition controller")
    require(COMPOSITION_CONTROL not in before and profiles.is_sha(after.get(COMPOSITION_CONTROL)),
            "Exact new composition control source must be present in the current snapshot")
    differences = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    permitted = (ALLOWED_CONTROL_CHANGES.keys() | REVIEWED_MODULE_CHANGES.keys()
                 | REVIEWED_COMPOSITION_CONTROLS.keys() | {COMPOSITION_CONTROL})
    require(differences <= permitted,
            "Compiled native, assertion, harness or unreviewed dependency changed: " +
            ", ".join(sorted(differences - permitted)))
    reasons = {**ALLOWED_CONTROL_CHANGES,
               **{name: row[2] for name, row in REVIEWED_COMPOSITION_CONTROLS.items()},
               COMPOSITION_CONTROL: "New Python controls for this exact native/current-Swift lineage; never compiled into the retained frameworks."}
    controls = [dict(path=name, before_sha256=before.get(name), after_sha256=after.get(name),
                     reason=reasons[name]) for name in sorted(differences - REVIEWED_MODULE_CHANGES.keys())]
    return ({name: sha for name, sha in after.items() if name not in differences}, controls, composition)


def verify_source_lineage(before: dict, after: dict) -> tuple[dict, list, dict | None]:
    if module_sources(before) == module_sources(after):
        unchanged, reviewed = verify_control_maps(before, after)
        return unchanged, reviewed, None
    return verify_current_composition(before, after)


def validate_current_composition_record(record: dict, build_raw: bytes,
                                        source_sha: str, run_id: str, attempt: str) -> dict:
    require(type(record.get("schemaVersion")) is int and record["schemaVersion"] == 2
            and record.get("status") == COMPOSITION_STATUS, "Unknown current composition lineage schema")
    lineage = record.get("shared_module_lineage", {})
    require(isinstance(lineage, dict), "Missing explicit current Swift composition lineage")
    current = record.get("current_control_source_sha256", {})
    admission._sha_map(current, "current composition source")
    modules = module_sources(current)
    require(record.get("copied_module_sha256") == modules
            and lineage == current_module_lineage(lineage.get("original_module_sha256", {}), modules),
            "Current composition record does not bind the exact newly executed module closure")
    # Validate the unchanged native metadata contract without editing either
    # archived original receipt. Schema 2 separately requires new Swift proof.
    native_metadata = dict(record, schemaVersion=1, status=STATUS)
    native_metadata.pop("shared_module_lineage")
    return validate_reuse_record(native_metadata, build_raw, source_sha, run_id, attempt)


def validate_reuse_record(record: dict, build_raw: bytes, source_sha: str, run_id: str, attempt: str) -> dict:
    if record.get("schemaVersion") == 2:
        return validate_current_composition_record(record, build_raw, source_sha, run_id, attempt)
    require(record.get("schemaVersion") == 1 and type(record.get("schemaVersion")) is int
            and record.get("status") == STATUS and record.get("build_origin") == origin()
            and record.get("execution_origin") == dict(source_sha=source_sha, run_id=run_id, run_attempt=attempt)
            and profiles.is_sha(source_sha, 40) and isinstance(run_id, str) and run_id.isascii() and run_id.isdigit()
            and int(run_id) > 0 and run_id != RUN and isinstance(attempt, str)
            and attempt.isascii() and attempt.isdigit() and int(attempt) > 0
            and record.get("original_build_receipt_sha256") == BUILD_SHA == profiles.digest_bytes(build_raw)
            and record.get("original_failed_host_receipt_sha256") == FAILED_HOST_SHA
            and record.get("original_artifacts") == ARTIFACTS
            and type(record.get("frameworks_built_this_run")) is int and record["frameworks_built_this_run"] == 0
            and type(record.get("native_tests_executed_this_run")) is int and record["native_tests_executed_this_run"] == 0
            and record.get("production_binary_execution") == "NOT_RUN"
            and record.get("apple_execution") == "SEPARATE_CURRENT_HOST_REQUIRED"
            and profiles.is_sha(record.get("runner_sha256"))
            and record["runner_sha256"] == record.get("current_control_source_sha256", {}).get(
                "Tools/PinkhaNativeDerived/coherent_apple/reuse_build.py"),
            "Reuse receipt conflates build and execution origins or changed immutable bytes")
    return origin()


def validate_host_lineage(control: Path, build_receipt: Path, reuse_receipt: Path,
                          source_sha: str, run_id: str, attempt: str) -> dict:
    require(reuse_receipt.resolve() == build_receipt.parent / "build-reuse.json",
            "Build lineage must be beside its immutable original build receipt")
    record = admission.read_json(reuse_receipt)
    result = validate_reuse_record(record, admission.read_bounded(build_receipt), source_sha, run_id, attempt)
    import run_host
    current = run_host.source_snapshot(control)
    require(record.get("current_control_source_sha256") == current
            and record.get("current_control_source_snapshot_sha256") == profiles.json_digest(current),
            "Current host controller source changed after build reuse qualification")
    return result


def extract_runtime(archive: Path, directory: Path, kind: str) -> None:
    require(kind in RECEIPTS and not directory.exists(), "Fresh, explicit framework staging required")
    with tarfile.open(archive, "r:gz") as packed:
        plan = admission._member_plan(packed.getmembers(), "tar")
        require({path.parts[0] for _, path, _, _ in plan} == {"Lib.xcframework", RECEIPTS[kind]},
                "Unexpected original framework payload")
        directory.mkdir()
        for item, path, is_dir, size in plan:
            target = directory / path
            if is_dir:
                target.mkdir(parents=True, exist_ok=True)
            else:
                source = packed.extractfile(item)
                require(source is not None, "Missing original framework member")
                with source:
                    admission._copy_member(source, target, size)


def verify_runtime(directory: Path, original_proof: Path, kind: str, build: dict) -> None:
    raw = admission.read_bounded(directory / RECEIPTS[kind])
    require(raw == admission.read_bounded(original_proof / kind / "custom-heart-build.json"),
            "Framework archive and original build proof have different packaged receipts")
    receipt = admission.json_value(raw, "original " + kind + " receipt")
    profile = profiles.select(profiles.COHERENT)
    framework = directory / "Lib.xcframework"
    if kind == "production":
        observed = admission.validate_framework(framework, receipt, profile)
    else:
        expected = build["frameworks"]["fixture"]
        observed = admission._file_map(framework)
        require(observed == expected["files_sha256"]
                and observed == {row["path"]: row["sha256"] for row in receipt["artifacts"]}
                and receipt.get("fixture_included") is True and receipt.get("selected_framework") == "fixture"
                and receipt.get("fixture_tag") == admission.FIXTURE_TAG
                and receipt.get("bridge_sha256") == build["bridge_sha256"]
                and receipt.get("fixture_source_sha256") == build["fixture_source_sha256"],
                "Original nonshipping fixture library identity changed")
        slices = verify_framework_slices(framework, profile.binary_marker)
        require(slices == receipt["binary_slices"] == expected["binary_slices"], "Wrong original fixture simulator slice")
        require(contains(framework / "ios-arm64-simulator/Lib.framework/Headers/Service.objc.h",
                         b"PinkhaCoherentAppleAuthorityFixture")
                and contains(framework / admission.BINARY, build["bridge_sha256"].encode()),
                "Fixture export or original bridge identity missing from actual library")
    require(observed == build["frameworks"][kind]["files_sha256"], "Original build/library hashes differ")


def copy_original_proof(original: Path, destination: Path) -> None:
    require(not destination.exists(), "Fresh proof destination required")
    shutil.copytree(original / "proof", destination, ignore=shutil.ignore_patterns("host"))
    for name, sha in admission._file_map(original / "proof").items():
        if not name.startswith("host/"):
            require(digest(destination / name) == sha, "Copied original proof changed")


def validate_admission_lineage(proof: Path, execution: dict, work: Path, evidence: Path, command) -> dict:
    record = admission.read_json(proof / "build-reuse.json")
    build_origin = validate_reuse_record(record, admission.read_bounded(proof / "build.json"),
        execution["source_sha"], execution["run_id"], execution["run_attempt"])
    require(execution.get("repository") == REPOSITORY and execution.get("source_branch") == BRANCH,
            "Execution origin belongs to another authorized repository/branch")
    run_path, list_path = evidence / "original-build-producer-run.json", evidence / "original-build-artifact-list.json"
    command(["gh", "api", "repos/" + REPOSITORY + "/actions/runs/" + RUN], run_path, timeout=120)
    command(["gh", "api", "repos/" + REPOSITORY + "/actions/runs/" + RUN + "/artifacts?per_page=100"], list_path, timeout=120)
    validate_original_metadata(admission.read_json(run_path), admission.read_json(list_path))
    archived = proof / "build-origin"
    validate_original_metadata(admission.read_json(archived / "original-producer-run.json"),
                               admission.read_json(archived / "original-artifact-list.json"))
    zip_path = archived / "proof-original.zip"
    require(zip_path.stat().st_size == ARTIFACTS["proof"]["size_in_bytes"]
            and digest(zip_path) == ARTIFACTS["proof"]["zip_sha256"], "Archived original build proof ZIP changed")
    original = work / "original-build-proof"
    admission.safe_zip(zip_path, original)
    _, before, modules = verify_original_proof(original)
    for name, sha in admission._file_map(original / "proof").items():
        if not name.startswith("host/"):
            require(digest(proof / name) == sha, "Continuation rewrote original build evidence")
    after = record.get("current_control_source_sha256", {})
    unchanged, reviewed, composition = verify_source_lineage(before, after)
    modules = module_sources(after)
    require(record.get("schemaVersion") == (2 if composition is not None else 1)
            and record.get("shared_module_lineage") == composition,
            "Actual module delta and recorded composition schema differ")
    require(record.get("unchanged_source_sha256") == unchanged
            and record.get("reviewed_control_changes") == reviewed
            and record.get("copied_module_sha256") == modules
            and record.get("current_control_source_snapshot_sha256") == profiles.json_digest(after),
            "Build reuse source/dependency closure is unqualified")
    return dict(build_producer=build_origin, receipt_sha256=digest(proof / "build-reuse.json"),
                current_source=after, modules=modules, original_artifacts=ARTIFACTS)


def execute(args, command) -> dict:
    require(args.source_run_id == RUN and args.repository == REPOSITORY,
            "Only the exact qualified completed build may be reused")
    require(git(args.control, "rev-parse", "HEAD") == args.expected_app_sha
            and not git(args.control, "status", "--porcelain"), "Exact clean current controller source required")
    run_id, attempt = os.environ.get("GITHUB_RUN_ID", ""), os.environ.get("GITHUB_RUN_ATTEMPT", "")
    require(run_id.isascii() and run_id.isdigit() and int(run_id) > 0 and run_id != RUN
            and attempt.isascii() and attempt.isdigit() and int(attempt) > 0, "Actual distinct current execution run required")
    require(not args.work.exists() and not args.frameworks.exists() and not args.artifacts.exists(),
            "Fresh owned reuse/framework/artifact directories required")
    args.work.mkdir(parents=True); args.frameworks.mkdir(); args.artifacts.mkdir()
    metadata = args.work / "metadata"; metadata.mkdir()
    run_path, list_path = metadata / "original-producer-run.json", metadata / "original-artifact-list.json"
    command(["gh", "api", "repos/" + REPOSITORY + "/actions/runs/" + RUN], run_path, 120)
    command(["gh", "api", "repos/" + REPOSITORY + "/actions/runs/" + RUN + "/artifacts?per_page=100"], list_path, 120)
    validate_original_metadata(admission.read_json(run_path), admission.read_json(list_path))
    archives, unpacked = {}, {}
    for kind, expected in ARTIFACTS.items():
        path = args.work / (kind + "-original.zip")
        command(["gh", "api", "repos/" + REPOSITORY + "/actions/artifacts/" + str(expected["id"]) + "/zip"], path, 600)
        require(path.stat().st_size == expected["size_in_bytes"] and digest(path) == expected["zip_sha256"],
                "Original GitHub artifact bytes differ: " + kind)
        target = args.work / (kind + "-unpacked")
        admission.safe_zip(path, target, None if kind == "proof" else expected["name"] + ".tar.gz")
        archives[kind], unpacked[kind] = path, target
    build, before, modules = verify_original_proof(unpacked["proof"])
    import run_host
    current = run_host.source_snapshot(args.control)
    unchanged, reviewed, composition = verify_source_lineage(before, current)
    modules = module_sources(current)
    for kind in ("production", "fixture"):
        tar_name = ARTIFACTS[kind]["name"] + ".tar.gz"
        tar_path = unpacked[kind] / tar_name
        require(digest(tar_path) == ARTIFACTS[kind]["tar_sha256"], "Original framework TAR bytes changed")
        extract_runtime(tar_path, args.frameworks / kind, kind)
        verify_runtime(args.frameworks / kind, unpacked["proof"] / "proof", kind, build)
        shutil.copyfile(tar_path, args.artifacts / tar_name)
        require(digest(args.artifacts / tar_name) == ARTIFACTS[kind]["tar_sha256"], "Copied framework TAR changed")
    proof = args.evidence / "proof"
    copy_original_proof(unpacked["proof"], proof)
    archived = proof / "build-origin"; archived.mkdir()
    shutil.copyfile(archives["proof"], archived / "proof-original.zip")
    shutil.copyfile(run_path, archived / run_path.name); shutil.copyfile(list_path, archived / list_path.name)
    shutil.copytree(unpacked["proof"] / "controls", args.evidence / "original-build-controls")
    require(run_host.source_snapshot(args.control) == current and not git(args.control, "status", "--porcelain"),
            "Current control source changed while reusing original frameworks")
    record = dict(schemaVersion=2 if composition is not None else 1,
        status=COMPOSITION_STATUS if composition is not None else STATUS, build_origin=origin(),
        execution_origin=dict(source_sha=args.expected_app_sha, run_id=run_id, run_attempt=attempt),
        original_build_receipt_sha256=BUILD_SHA, original_failed_host_receipt_sha256=FAILED_HOST_SHA,
        original_artifacts=ARTIFACTS, frameworks_built_this_run=0, native_tests_executed_this_run=0,
        production_binary_execution="NOT_RUN", apple_execution="SEPARATE_CURRENT_HOST_REQUIRED",
        unchanged_source_sha256=unchanged, reviewed_control_changes=reviewed, copied_module_sha256=modules,
        current_control_source_sha256=current, current_control_source_snapshot_sha256=profiles.json_digest(current),
        runner_sha256=digest(Path(__file__)), finished_at=datetime.now(timezone.utc).isoformat(),
        claim_boundary="Original frameworks and packaged receipts retain their failed-run build origin. No native build or test is repeated; current Apple execution must qualify separately.")
    if composition is not None:
        record["shared_module_lineage"] = composition
        record["claim_boundary"] = ("Original native framework bytes and 139-source evidence retain their build origin. "
            "The exact current Swift module closure requires a new harness build and actual one-method composition proof. "
            "No previous Swift composition or full application acceptance is reused.")
    validate_reuse_record(record, admission.read_bounded(proof / "build.json"), args.expected_app_sha, run_id, attempt)
    (proof / "build-reuse.json").write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("control", "work", "frameworks", "evidence", "artifacts"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-app-sha", required=True)
    args = parser.parse_args()
    for name in ("control", "work", "frameworks", "evidence", "artifacts"):
        setattr(args, name, getattr(args, name).resolve())
    args.evidence.mkdir(parents=True, exist_ok=True)
    failure = args.evidence / "build-reuse-failure.json"
    def command(argv, output, timeout):
        with output.open("xb") as stream:
            completed = subprocess.run(argv, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout, cwd=args.control)
        require(completed.returncode == 0, "Original artifact command failed: " + output.name)
    try:
        record = execute(args, command)
        print(json.dumps({key: value for key, value in record.items()
                          if key not in ("unchanged_source_sha256", "current_control_source_sha256", "copied_module_sha256", "shared_module_lineage")}, indent=2))
        return 0
    except Exception as error:
        value = dict(status="FAIL_BUILD_REUSE", error_type=type(error).__name__, error=str(error),
                     frameworks_built_this_run=0, apple_execution="NOT_RUN")
        failure.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(value, indent=2)); return 1


if __name__ == "__main__":
    raise SystemExit(main())
