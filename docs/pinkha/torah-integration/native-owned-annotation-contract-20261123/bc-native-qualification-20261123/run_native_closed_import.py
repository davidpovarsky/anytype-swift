#!/usr/bin/env python3
"""One genuine original native closed-annotation import qualification."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
import zipfile

PACKET = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123/bc-native-qualification-20261123"
CANDIDATE = "docs/pinkha/torah-integration/native-owned-annotation-contract-20261123/bc-candidate-20261123"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
CANDIDATE_REVISION = "62e5f1c9d62c99cc00debfe7e1975557eeec32fa"
FIXTURE_REVISION = "1159fbaf4b223515676a95b30b3600d210b71417"
SUPPORT_SHA256 = "017778c096eca985774bd1a4f1e1e117ac3dee6ac08082c2a9793273826aa196"
COMPOSITION_SHA256 = "8815e407d60607903bfb4b340dd86a1229c521d10e6fb993108cd97c747a02a9"
OBSERVER_REPAIR = "observer-repair-20261123"
OBSERVER_REPAIR_SHA256 = "5dce16285bf28001e330ca3879d2661644f517a284a0423d4250daea1032e2fa"
SCHEMA_DIAGNOSTIC = "schema-diagnostic-20261123"
SCHEMA_DIAGNOSTIC_SHA256 = "89290dfe5b13676fac85f4048752d055e2ae4c0af544cab6e100e23ac07161fd"
SEMANTIC_REUSE_SHA256 = "690fed460572eb6facdf66ae9447ee9b34e28d4cccf3a901fbe49638a14d3aa6"
SEMANTIC_PARENT = "TestOwnedAnnotationBundledPersistedDefinitionContract"
SEMANTIC_LEAVES = ("ot-objectType", "ot-participant", "rel-name", "rel-sourceObject",
                   "rel-revision", "unsupported-bundled-key")
SPECIMENS = ("text", "format", "nested", "attachment")
PARENT = "TestOtzariaOwnedAnnotationClosedNativeImport"
LEAVES = SPECIMENS + (
    "ExistingGraphIdentityRefused", "CapturedAccountMismatchRefused",
    "ActualFreshCreatorCollisionRefused", "SignedReaderRevocationAfterPrepareRefused",
    "RegisteredCancellationAndHistoricalAppRefusal",
)
COMPILED_ORIGINAL_MODELS = ("pb/snapshot.pb.go", "pb/changes.pb.go",
                           "pkg/lib/pb/model/models.pb.go", "pb/commands.pb.go")


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], timeout=60)


def safe(root, relative):
    relative = Path(relative)
    require(not relative.is_absolute() and relative.parts and ".." not in relative.parts,
            "Unsafe retained relative path")
    path = root / relative
    require(path.resolve().is_relative_to(root.resolve()), "Aliased retained path")
    cursor = path
    while cursor != root:
        require(not cursor.is_symlink(), "Retained path contains a symlink")
        cursor = cursor.parent
    return path


def read_bound(root, path, row, require_head=True):
    source = safe(root, path)
    require(source.is_file(), "Missing/nonregular source input: " + path)
    raw = source.read_bytes()
    require(len(raw) == row["bytes"] and sha(raw) == row["sha256"]
            and blob(raw) == row["git_blob"], "Source bytes differ: " + path)
    if require_head:
        require(raw == git(root, "show", "HEAD:" + path), "Dirty source input: " + path)
    return raw


def read_observer_repair(control, manifest):
    raw = read_bound(control, PACKET + "/" + OBSERVER_REPAIR + "/REPAIR_INPUTS.json",
                     manifest["observer_repair"])
    require(sha(raw) == OBSERVER_REPAIR_SHA256, "Reviewed observer repair differs")
    repair = json.loads(raw)
    require(repair["schema"] == 1
            and repair["previous_control"] == "9934ccf396139fd8ff4367dd416b0460f23d49df"
            and repair["previous_native_run"] == 45225259295
            and repair["semantic_selector"] == "^" + SEMANTIC_PARENT + "$",
            "Wrong observer repair lineage or semantic selector")
    expected = {
        "core/block/object/objectcreator/owned_annotation_observer.go":
            "73de2d6301d7715bc2f2efaa3df90f26b5dc8f10b8739b87240205ea541b9441",
        "core/application/owned_annotation_import_native_test.go":
            "0a2974ab89ca2dd701e36b823a33a5aa6d4b54659faa647c323cea0b1f7fe924",
        "core/block/object/objectcreator/owned_annotation_bundled_persistence_test.go": None,
    }
    require(len(repair["inputs"]) == 3
            and {row["native_path"]: row["base_sha256"] for row in repair["inputs"]} == expected,
            "Observer repair changed an unreviewed native path")
    for row in repair["inputs"]:
        require(row["path"] == OBSERVER_REPAIR + "/native/" + row["native_path"],
                "Observer repair source path differs")
        after = read_bound(control, PACKET + "/" + row["path"], row)
        if row["base_sha256"] is None:
            continue
        before = safe(control, row["base_source_path"]).read_bytes()
        require(sha(before) == row["base_sha256"]
                and before == git(control, "show", "HEAD:" + row["base_source_path"]),
                "Frozen observer/fixture preimage changed")
        if row["native_path"].endswith("owned_annotation_observer.go"):
            old = "\trequired := domain.NewDetails()\n\trequired.SetString(bundle.RelationKeyUniqueKey, key.Marshal())\n".encode()
            new = "\t// Native signed headers already establish the exact kind and internal key.\n\t// uniqueKey is an original derived/local field, never persisted Details.\n\trequired := domain.NewDetails()\n".encode()
        else:
            old = "\t\t\tt.Fatal(\"uncertain/conflicting native prerequisite cannot be installed again or treated as ready\")\n".encode()
            new = "\t\t\tf.receipt(t, \"schema-prerequisite-failure.json\", map[string]any{\n\t\t\t\t\"schema_key\": key.Marshal(), \"disposition\": uint8(actual.Disposition),\n\t\t\t\t\"require_persisted_match\": require,\n\t\t\t\t\"persisted_head_count\":    len(actual.PersistedHeads), \"archive_head_count\": len(actual.ArchiveHeads),\n\t\t\t\t\"installer_retry_performed\": false, \"readiness_accepted\": false,\n\t\t\t})\n\t\t\tt.Fatalf(\"uncertain/conflicting native prerequisite cannot be installed again or treated as ready: key=%s disposition=%d\", key.Marshal(), actual.Disposition)\n".encode()
        require(before.count(old) == 1 and after == before.replace(old, new, 1),
                "Observer/fixture changed outside its exact reviewed inverse")
    return repair


def read_schema_diagnostic(control, manifest):
    raw = read_bound(control, PACKET + "/" + SCHEMA_DIAGNOSTIC + "/DIAGNOSTIC_INPUTS.json",
                     manifest["schema_diagnostic"])
    require(sha(raw) == SCHEMA_DIAGNOSTIC_SHA256, "Reviewed diagnostic overlay differs")
    diagnostic = json.loads(raw)
    require(diagnostic["schema"] == 1
            and diagnostic["previous_control"] == "32103fc9a1930def33bac4f09c4bd5b6a2deca5c"
            and diagnostic["previous_native_run"] == 45235615911
            and diagnostic["native_selector"] == "^" + PARENT + "$/^text$"
            and diagnostic["original_refusal_preserved"] is True
            and diagnostic["body_mapping_drain_assertions_unchanged"] is True,
            "Diagnostic lineage or unchanged refusal scope differs")
    expected = {
        "core/block/import/owned_annotation_comparison.go":
            "3f0f0f1145d26c193a0498c900612705678f00fa0dfae7545855165145748ae2",
        "core/application/owned_annotation_import_native_test.go":
            "3f54464ab2dc860e79f41f55d6b4a0813409828a4e3d8c5d5a596e4666ffc422",
    }
    require(len(diagnostic["inputs"]) == 2 and
            {row["native_path"]: row["base_sha256"] for row in diagnostic["inputs"]} == expected,
            "Diagnostic overlay changed an unreviewed native path")
    for row in diagnostic["inputs"]:
        require(row["path"] == SCHEMA_DIAGNOSTIC + "/native/" + row["native_path"],
                "Diagnostic native source path differs")
        before = safe(control, row["base_source_path"]).read_bytes()
        require(sha(before) == row["base_sha256"]
                and before == git(control, "show", diagnostic["previous_control"] + ":" + row["base_source_path"])
                and before == git(control, "show", "HEAD:" + row["base_source_path"]),
                "Accepted diagnostic preimage differs")
        expected_after = before.decode()
        for change in row["changes"]:
            require(expected_after.count(change["before"]) == 1, "Diagnostic inverse is not unique")
            expected_after = expected_after.replace(change["before"], change["after"], 1)
        expected_after += row["append"]
        require(read_bound(control, PACKET + "/" + row["path"], row) == expected_after.encode(),
                "Diagnostic source escaped its exact inverse")
    proof_raw = read_bound(control, PACKET + "/" + SCHEMA_DIAGNOSTIC + "/SEMANTIC_REUSE.json",
                           manifest["semantic_reuse"])
    require(sha(proof_raw) == SEMANTIC_REUSE_SHA256, "Accepted prior semantic evidence differs")
    proof = json.loads(proof_raw)
    require(proof["source_sha"] == diagnostic["previous_control"]
            and proof["run_id"] == 45235615911 and proof["run_attempt"] == 1
            and proof["artifact_id"] == 14850421633
            and proof["artifact_sha256"] == "ad8fe006be11b093e93e1a04c59b14a01a14c0b1f656fef7f014c92d83cc360e"
            and proof["semantic_control"]["status"] == "PASS"
            and proof["semantic_control"]["leaf_count"] == 6,
            "Prior semantic success is not the authenticated accepted execution")
    return diagnostic


def reuse_semantic_control(control, manifest, listing, closure, heart, evidence):
    path = SCHEMA_DIAGNOSTIC + "/semantic_reuse.py"
    row = next(row for row in manifest["controls"] if row["path"] == path)
    read_bound(control, PACKET + "/" + path, row)
    spec = importlib.util.spec_from_file_location("accepted_semantic_input_equality", safe(control, PACKET + "/" + path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    proof = json.loads(read_bound(control, PACKET + "/" + SCHEMA_DIAGNOSTIC + "/SEMANTIC_REUSE.json",
                                  manifest["semantic_reuse"]))
    actual = module.semantic_dependency_fingerprint(listing, closure, heart)
    require(actual == proof["semantic_dependency_fingerprint"],
            "Actual semantic dependency inputs differ; prior six passes cannot be reused")
    toolchains = {}
    for name in ("03-go-version.stdout", "04-xcode-version.stdout", "05-clang-version.stdout"):
        raw = safe(evidence, name).read_bytes()
        actual_identity = {"bytes": len(raw), "sha256": sha(raw)}
        require(actual_identity == proof["authenticated_source_files"][name],
                "Actual semantic toolchain differs from accepted native execution: " + name)
        toolchains[name] = actual_identity
    return {
        "status": "REUSED_PASS", "executed_this_run": False,
        "previous_source": proof["source_sha"], "previous_run": proof["run_id"],
        "previous_artifact_id": proof["artifact_id"],
        "previous_artifact_sha256": proof["artifact_sha256"],
        "actual_declared_input_equality": actual, "actual_toolchain_equality": toolchains,
        "prior_actual_six_leaf_control": proof["semantic_control"],
        "production_import_activated": False,
    }


def source_admission(control, manifest, original_repository=None, original_heart=None):
    require(manifest["schema"] == 1 and manifest["heart_base"] == HEART
            and manifest["candidate_revision"] == CANDIDATE_REVISION
            and manifest["fixture_revision"] == FIXTURE_REVISION,
            "Native source identities differ")
    require(manifest["native_selector"] == "^" + PARENT + "$/^text$"
            and manifest["expected_leaf_cases"] == list(LEAVES)
            and manifest["selected_leaf_cases"] == ["text"]
            and manifest["diagnostic_only"] is True
            and manifest["historical_selectors_replayed"] is False
            and manifest["production_import_activated"] is False
            and manifest["new_rpc_or_generated_source"] is False,
            "Native qualification scope differs")
    composition_raw = read_bound(control, CANDIDATE + "/SOURCE_COMPOSITION.json",
                                 manifest["composition"])
    require(sha(composition_raw) == COMPOSITION_SHA256, "Reviewed twelve-file composition differs")
    composition = json.loads(composition_raw)
    require(len(composition["original_input_rows"]) == 43
            and len(composition["candidate_inputs"]) == 12
            and len(composition["r14"]["preimages"]) == 35
            and len(composition["ordered_afterimages"]) == 90
            and len(composition["final_composed_changed_native_files"]) == 83,
            "Reviewed complete original source composition differs")
    require(len(manifest["source_inputs"]) == 48
            and len({row["materialized_path"] for row in manifest["source_inputs"]}) == 48
            and len(manifest["test_inputs"]) == 2
            and len(manifest["original_model_and_rpc_inputs"]) == 11
            and manifest["original_module_hashes"] == composition["original_module_hashes"],
            "Original source/support/model/test inventory differs")
    repair = read_observer_repair(control, manifest)
    diagnostic = read_schema_diagnostic(control, manifest)
    required = {row["path"]: row["sha256"]
                for row in composition["final_composed_changed_native_files"]
                if not row["path"].endswith("_test.go")}
    required.update({row["native_path"]: row["sha256"] for row in manifest["test_inputs"]})
    required.update({row["path"]: row["sha256"] for row in manifest["original_model_and_rpc_inputs"]
                     if row["path"] in COMPILED_ORIGINAL_MODELS})
    required.update({row["native_path"]: row["sha256"] for row in repair["inputs"]})
    required.update({row["native_path"]: row["sha256"] for row in diagnostic["inputs"]})
    require(required == manifest["required_compiler_inputs"]
            and len(required) == manifest["required_compiler_input_count"] == 88,
            "Actual required original compiler input inventory differs")
    for row in manifest["controls"]:
        read_bound(control, PACKET + "/" + row["path"], row)
    for row in manifest["source_inputs"]:
        raw = read_bound(control, PACKET + "/" + row["retained_path"], row)
        if original_repository is not None:
            require(raw == git(original_repository, "show", row["revision"] + ":" + row["source_path"]),
                    "Actual original revision:path source differs")
    for row in manifest["candidate_inputs"]:
        raw = read_bound(control, CANDIDATE + "/" + row["path"], row)
        if original_repository is not None:
            require(raw == git(original_repository, "show", CANDIDATE_REVISION + ":" + CANDIDATE + "/" + row["path"]),
                    "Frozen candidate revision differs")
    for row in manifest["test_inputs"]:
        raw = read_bound(control, PACKET + "/" + row["path"], row)
        if original_repository is not None:
            require(raw == git(original_repository, "show", FIXTURE_REVISION + ":" + PACKET + "/" + row["path"]),
                    "Sealed genuine fixture revision differs")
    require(manifest["candidate_inputs"] == composition["candidate_inputs"],
            "Candidate allowlist is not the reviewed twelve source files")
    product_rows = [row for row in manifest["source_inputs"] if row["role"] == "ordered-native-input"]
    require(len(product_rows) == 43, "Original native overlay input count differs")
    for actual, original in zip(product_rows, composition["original_input_rows"]):
        require(all(actual[key] == original[key] for key in
                    ("revision", "source_path", "native_path", "bytes", "sha256", "git_blob")),
                "Original overlay order/source changed")
    for row in manifest["original_model_and_rpc_inputs"]:
        if original_heart is not None:
            raw = git(original_heart, "show", HEART + ":" + row["path"])
            require(len(raw) == row["bytes"] and sha(raw) == row["sha256"]
                    and blob(raw) == row["git_blob"], "Original model/proto/RPC source differs")
    if original_heart is not None:
        for name, digest in manifest["original_module_hashes"].items():
            require(sha(git(original_heart, "show", HEART + ":" + name)) == digest,
                    "Original module/native dependency checksum differs")
        new_tests = manifest["test_inputs"] + [row for row in repair["inputs"]
                                                if row["base_sha256"] is None]
        for row in new_tests:
            result = subprocess.run(["git", "-C", str(original_heart), "cat-file", "-e",
                                     HEART + ":" + row["native_path"]],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            require(result.returncode != 0, "Qualification test path collides with original source")
    return composition


def load_support(control, manifest, work):
    inputs = work / "retained-inputs"
    inputs.mkdir()
    seen = set()
    for row in manifest["source_inputs"]:
        name = row["materialized_path"]
        require(name not in seen, "Duplicate retained materialization destination")
        seen.add(name)
        raw = read_bound(control, PACKET + "/" + row["retained_path"], row)
        target = safe(inputs, name)
        require(not target.exists(), "Refuse retained-source overwrite")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
    path = inputs / "support/run_original_application_compile.py"
    require(sha(path.read_bytes()) == SUPPORT_SHA256, "Original bounded command owner differs")
    spec = importlib.util.spec_from_file_location("original_native_process_owner", path)
    support = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(support)
    return support, inputs


def original_models(heart, manifest):
    for row in manifest["original_model_and_rpc_inputs"]:
        raw = safe(heart, row["path"]).read_bytes()
        require(len(raw) == row["bytes"] and sha(raw) == row["sha256"]
                and blob(raw) == row["git_blob"], "Unchanged original model/proto/RPC input differs")


def compose_native(control, heart, inputs, manifest, composition, support, commands, evidence):
    require(git(heart, "rev-parse", "HEAD").decode().strip() == HEART,
            "Exact original Heart checkout required")
    require(not git(heart, "status", "--porcelain", "--untracked-files=all").strip(),
            "Original Heart checkout is not fresh")
    for name, digest in manifest["original_module_hashes"].items():
        require(support.digest(heart / name) == digest, "Original module input differs")
    original_models(heart, manifest)
    patch = inputs / "r14/native-heart-integration.patch"
    require(support.digest(patch) == composition["r14"]["sha256"], "Original r14 patch differs")
    for row in composition["r14"]["preimages"]:
        path = safe(heart, row["native_path"])
        require((path.is_file() and support.digest(path) == row["sha256"])
                if row["sha256"] is not None else not path.exists(),
                "Original r14 source preimage differs")
    commands.require("r14-check", ["git", "apply", "--check", str(patch)], heart, 30)
    commands.require("r14-apply", ["git", "apply", str(patch)], heart, 30)
    composed = {}
    steps = composition["ordered_afterimages"]
    for row in steps[:35]:
        require(row["stage"] == "r14" and support.digest(heart / row["native_path"]) == row["after_sha256"],
                "Original r14 actual afterimage differs")
        composed[row["native_path"]] = row["after_sha256"]
    overlays = [(row, safe(inputs, row["materialized_path"]))
                for row in manifest["source_inputs"] if row["role"] == "ordered-native-input"]
    overlays += [(row, safe(control, CANDIDATE + "/" + row["path"]))
                 for row in manifest["candidate_inputs"]]
    require(len(overlays) == 55, "Native overlay count differs")
    for (row, source), step in zip(overlays, steps[35:]):
        name = row["native_path"]
        require(name == step["native_path"] and row["sha256"] == step["after_sha256"],
                "Native overlay order differs")
        path = safe(heart, name)
        before = step["before_sha256"]
        require((path.is_file() and support.digest(path) == before)
                if before is not None else not path.exists(),
                "Native overlay preimage differs: " + name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(source.read_bytes())
        require(support.digest(path) == row["sha256"], "Native overlay bytes changed")
        composed[name] = row["sha256"]
    final = {row["path"]: row["sha256"] for row in composition["final_composed_changed_native_files"]}
    require(composed == final, "Actual final83-file native composition differs")
    for row in manifest["test_inputs"]:
        path = safe(heart, row["native_path"])
        require(not path.exists(), "Preserve an existing original test path")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(safe(control, PACKET + "/" + row["path"]).read_bytes())
        require(support.digest(path) == row["sha256"], "Sealed native test afterimage differs")
        composed[row["native_path"]] = row["sha256"]
    repair = read_observer_repair(control, manifest)
    diagnostic = read_schema_diagnostic(control, manifest)
    for row in repair["inputs"]:
        path = safe(heart, row["native_path"])
        before = row["base_sha256"]
        require((path.is_file() and support.digest(path) == before)
                if before is not None else not path.exists(),
                "Reviewed observer repair preimage differs: " + row["native_path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(read_bound(control, PACKET + "/" + row["path"], row))
        require(support.digest(path) == row["sha256"], "Reviewed observer repair bytes differ")
        composed[row["native_path"]] = row["sha256"]
    for row in diagnostic["inputs"]:
        path = safe(heart, row["native_path"])
        require(path.is_file() and support.digest(path) == row["base_sha256"],
                "Diagnostic overlay preimage differs: " + row["native_path"])
        path.write_bytes(read_bound(control, PACKET + "/" + row["path"], row))
        require(support.digest(path) == row["sha256"], "Diagnostic overlay afterimage differs")
        composed[row["native_path"]] = row["sha256"]
    require(len(composed) == 86, "Explicit native afterimage inventory differs")
    required = {name: digest for name, digest in composed.items()
                if not name.endswith("_test.go")}
    required.update({row["native_path"]: row["sha256"] for row in manifest["test_inputs"]})
    required.update({row["path"]: row["sha256"] for row in manifest["original_model_and_rpc_inputs"]
                     if row["path"] in COMPILED_ORIGINAL_MODELS})
    required.update({row["native_path"]: row["sha256"] for row in repair["inputs"]})
    required.update({row["native_path"]: row["sha256"] for row in diagnostic["inputs"]})
    require(required == manifest["required_compiler_inputs"]
            and len(required) == manifest["required_compiler_input_count"],
            "Complete required native compiler coverage differs")
    status = git(heart, "status", "--porcelain", "--untracked-files=all").decode().splitlines()
    require(all(row[:2] in (" M", "??") and row[3:] in composed for row in status),
            "Unexpected native source mutation")
    for name, digest in composed.items():
        require(support.digest(heart / name) == digest, "Composed product/test source differs")
    original_models(heart, manifest)
    support.write_json(evidence / "COMPOSED_NATIVE_SOURCES.json", {
        "reviewed_candidate_revision": CANDIDATE_REVISION,
        "sealed_fixture_revision": FIXTURE_REVISION,
        "all_native_afterimages": composed, "required_actual_compiler_coverage": required,
        "explicit_post_base_observer_repair": repair,
        "observer_repair_manifest_sha256": OBSERVER_REPAIR_SHA256,
        "explicit_post_repair_schema_diagnostic": diagnostic,
        "schema_diagnostic_manifest_sha256": SCHEMA_DIAGNOSTIC_SHA256,
        "original_selected_tests_not_replayed": True,
        "new_generated_or_rpc_inputs": False, "production_import_activated": False,
    })
    return composed, required


def semantic_case_intake(path):
    require(path.is_file() and path.stat().st_size <= 8 * 1024 * 1024,
            "Focused semantic JSON log missing or beyond intake bound")
    events = [json.loads(line) for line in path.read_text().splitlines()]
    expected = {SEMANTIC_PARENT} | {SEMANTIC_PARENT + "/" + leaf for leaf in SEMANTIC_LEAVES}
    rows = {}
    for name in sorted(expected):
        actions = [event.get("Action") for event in events if event.get("Test") == name]
        rows[name] = {"run_count": actions.count("run"),
                      "terminal_actions": [value for value in actions if value in ("pass", "fail", "skip")]}
    unexpected = sorted({event["Test"] for event in events if event.get("Test") and event["Test"] not in expected})
    package = [event["Action"] for event in events
               if not event.get("Test") and event.get("Action") in ("pass", "fail", "skip")]
    passed = not unexpected and package == ["pass"] and all(
        row["run_count"] == 1 and row["terminal_actions"] == ["pass"] for row in rows.values())
    return {"status": "PASS" if passed else "FAIL_OR_INCOMPLETE", "cases": rows,
            "leaf_count": len(SEMANTIC_LEAVES), "unexpected_test_names": unexpected,
            "package_terminal_actions": package, "scope": "New original bundled persistence semantic control only",
            "historical_selectors_replayed": False}


def native_case_intake(path):
    require(path.is_file() and path.stat().st_size <= 128 * 1024 * 1024,
            "Native JSON log missing or beyond retained intake bound")
    events = [json.loads(line) for line in path.read_text().splitlines()]
    expected = {PARENT + "/" + name for name in LEAVES}
    rows = {}
    for name in sorted(expected | {PARENT}):
        actions = [event.get("Action") for event in events if event.get("Test") == name]
        terminals = [value for value in actions if value in ("pass", "fail", "skip")]
        rows[name] = {"run_count": actions.count("run"), "terminal_actions": terminals,
                      "status": (terminals[0].upper() if len(terminals) == 1 else
                                 ("NOT_RUN" if "run" not in actions else "NO_UNIQUE_TERMINAL"))}
    return {
        "leaf_pass": sum(rows[name]["status"] == "PASS" for name in expected),
        "leaf_fail": sum(rows[name]["status"] == "FAIL" for name in expected),
        "leaf_skip": sum(rows[name]["status"] == "SKIP" for name in expected),
        "leaf_not_run": sum(rows[name]["status"] == "NOT_RUN" for name in expected),
        "parent": rows[PARENT], "cases": rows, "json_events": len(events),
        "unexpected_test_names": sorted({event["Test"] for event in events
                                        if event.get("Test") and event["Test"] not in rows}),
        "package_terminal_actions": [event["Action"] for event in events
                                     if not event.get("Test") and event.get("Action") in ("pass", "fail", "skip")],
        "historical_selectors_replayed": False,
    }


def require_all_native_pass(intake):
    require(intake["leaf_pass"] == 9 and intake["leaf_fail"] == 0
            and intake["leaf_skip"] == 0 and intake["leaf_not_run"] == 0
            and not intake["unexpected_test_names"]
            and intake["package_terminal_actions"] == ["pass"],
            "Actual new original native cases did not all pass once")
    require(all(row["run_count"] == 1 and row["terminal_actions"] == ["pass"]
                for row in intake["cases"].values()),
            "Original native parent or leaf completion is missing/repeated")


def json_file(root, name, maximum=512 * 1024):
    path = safe(root, name)
    require(path.is_file() and path.stat().st_size <= maximum,
            "Native fixture JSON file kind/size differs: " + name)
    return json.loads(path.read_bytes())


def zip_inventory(root, name):
    path = safe(root, name)
    require(path.is_file() and 0 < path.stat().st_size <= 1048576,
            "Original annotation archive exceeds accepted source policy")
    rows, seen, expanded = [], set(), 0
    with zipfile.ZipFile(path) as archive:
        require(0 < len(archive.infolist()) <= 512, "Original archive member count differs")
        for member in archive.infolist():
            name = member.filename
            parts = Path(name).parts
            require(name and not name.startswith("/") and "\\" not in name and ":" not in name
                    and parts and all(x not in ("", ".", "..") for x in name.split("/"))
                    and not any(ord(x) < 32 for x in name)
                    and name not in seen and not member.is_dir(),
                    "Unsafe/duplicate original archive member")
            seen.add(name)
            require(expanded + member.file_size <= 8 * 1024 * 1024, "Expanded original archive exceeds policy")
            body = archive.read(member)  # The standard reader verifies the actual CRC.
            require(len(body) == member.file_size, "Original archive member size differs")
            expanded += len(body)
            rows.append({"name": name, "bytes": len(body), "sha256": sha(body)})
    return {"bytes": path.stat().st_size, "sha256": sha(path.read_bytes()),
            "members": sorted(rows, key=lambda row: row["name"]), "expanded_bytes": expanded}


def verify_fixture_evidence(fixtures):
    expected_dirs = {"source"} | {"target-" + name for name in (*SPECIMENS, "reader", "cancel")}
    require({path.name for path in fixtures.iterdir()} == expected_dirs | {"native-import-cleanup.json"},
            "Unexpected/missing native fixture top-level evidence")
    outcomes, archives, registrations = {}, {}, {}
    for folder in sorted(expected_dirs):
        directory = safe(fixtures, folder)
        require(directory.is_dir(), "Native fixture folder is not real")
        phase_summary = json_file(directory, "schema-registration.json")
        phases = phase_summary.get("registration_calls")
        require(isinstance(phases, int) and not isinstance(phases, bool) and 1 <= phases <= 21,
                "Original bounded registration phase count differs")
        require(phase_summary.get("registration_complete") is True
                and phase_summary.get("unique_actual_creates") == 18
                and phase_summary.get("actual_type_apply_calls") == 1
                and phase_summary.get("matching_native_definitions") == 18,
                "Actual original fixture registration did not complete")
        expected = {"schema-registration.json"} | {
            "schema-registration-%02d.json" % index for index in range(phases)}
        if folder == "source":
            expected |= {kind + suffix for kind in SPECIMENS
                         for suffix in (".zip", "-export-report.json", "-manifest.json")}
            expected.add("actual-native-creator-collision.json")
        else:
            expected |= {"bundled-preparation-call.json", "readonly-prerequisites.json"}
            kind = folder.removeprefix("target-")
            if kind in SPECIMENS:
                expected |= {kind + "-outcome.json", kind + "-native-readback.zip",
                             "accepted-roundtrip.json"}
            if kind == "text":
                expected |= {"existing-identity-refusal-outcome.json",
                             "existing-identity-accepted-refusal.json", "account-mismatch-refusal.json"}
            elif kind == "reader":
                expected |= {"signed-acl-change.json", "signed-reader-refusal-outcome.json",
                             "signed-reader-accepted-refusal.json"}
            elif kind == "cancel":
                expected |= {"registered-cancellation-outcome.json", "cancellation-and-retirement.json"}
        require({path.name for path in directory.iterdir()} == expected,
                "Unexpected/missing native fixture files in " + folder)
        # Preserve the accepted collector repair: every admitted expected name
        # must itself resolve to an owned regular file, including all phases.
        for name in expected:
            require(safe(directory, name).is_file(), "Native fixture expected file is not regular")
        history = []
        for phase in range(phases):
            value = json_file(directory, "schema-registration-%02d.json" % phase, 128 * 1024)
            require(value.get("phase") == phase and value.get("app_admitted") is True
                    and value.get("historical_call_phase_only") is True,
                    "Original native phase history differs")
            history.append(value)
        registrations[folder] = {"summary": phase_summary, "history": history}
    source = fixtures / "source"
    for kind in SPECIMENS:
        actual = zip_inventory(source, kind + ".zip")
        manifest = json_file(source, kind + "-manifest.json")
        require(manifest.get("archive_sha256") == actual["sha256"]
                and manifest.get("archive_bytes") == actual["bytes"]
                and manifest.get("native_text_format_nested_attachment_checks_passed") is True
                and manifest.get("original_export_report_success") is True
                and manifest.get("native_import_activated") is False,
                "Actual same-account original source specimen differs")
        declared = [{"name": row["name"], "bytes": row["bytes"], "sha256": row["sha256"]}
                    for row in manifest["members"]]
        require(sorted(declared, key=lambda row: row["name"]) == actual["members"],
                "Actual source archive complete member payload inventory differs")
        target = fixtures / ("target-" + kind)
        outcome = json_file(target, kind + "-outcome.json")
        readback = zip_inventory(target, kind + "-native-readback.zip")
        require(outcome.get("actual_done_observed") is True
                and outcome.get("returned_error") is False
                and outcome.get("cancellation_requested") is False
                and outcome.get("native_mapping_observed") is True
                and outcome.get("native_mapping_complete") is True
                and outcome.get("readback_observed") is True
                and outcome.get("readback_stage") == 3
                and outcome.get("readback_archive_sha256") == readback["sha256"]
                and outcome.get("readback_archive_bytes") == readback["bytes"],
                "Actual same-owner native mapping/readback completion differs")
        require(outcome.get("readback_source_snapshots") == len(manifest["generated_snapshot_ids"])
                and len(outcome.get("source_assignments", [])) == len(manifest["generated_snapshot_ids"]),
                "Whole source graph disappeared across native import")
        accepted = json_file(target, "accepted-roundtrip.json")
        require(accepted.get("mapping_aware_body_comparison") is True
                and accepted.get("independent_native_block_checks") is True
                and accepted.get("readonly_schema_heads_unchanged") is True,
                "Genuine original roundtrip acceptance receipt differs")
        archives[kind] = {"genuine_source": actual, "actual_native_readback": readback}
        outcomes[kind] = outcome
    accounts = {json_file(source, kind + "-manifest.json")["account_id"] for kind in SPECIMENS}
    spaces = {json_file(source, kind + "-manifest.json")["space_id"] for kind in SPECIMENS}
    require(len(accounts) == 1 and len(spaces) == 1,
            "Current-account genuine producer inputs are not from one actual native owner")
    collision = json_file(source, "actual-native-creator-collision.json")
    require(collision.get("actual_tree_exists_error") is True
            and collision.get("second_create_returned_details") is False
            and collision.get("second_create_returned_id") == ""
            and collision.get("native_provider_id") == collision.get("native_payload_root_id")
            and collision.get("native_provider_id") == collision.get("actual_first_create_returned_id")
            and collision.get("first_native_heads") == collision.get("after_second_native_heads")
            and bool(collision.get("first_native_heads")),
            "Actual lower-layer original creator collision disposition differs")
    for folder, name in (("target-text", "existing-identity-refusal"),
                         ("target-reader", "signed-reader-refusal"),
                         ("target-cancel", "registered-cancellation")):
        value = json_file(fixtures / folder, name + "-outcome.json")
        require(value.get("actual_done_observed") is True
                and value.get("returned_error") is True
                and value.get("readback_observed") is False,
                "Original adverse operation manufactured successful readback")
        outcomes[name] = value
    require(outcomes["registered-cancellation"].get("cancellation_requested") is True,
            "Actual original cancellation history was lost")
    cleanup = json_file(fixtures, "native-import-cleanup.json")
    require(cleanup.get("original_operations_prepared") == 7
            and cleanup.get("test_start_invocations") == 7
            and cleanup.get("actual_done_observed") == 7
            and cleanup.get("all_original_operations_drained") is True
            and cleanup.get("original_account_stop_returned_or_app_absent") is True
            and cleanup.get("owned_annotation_stages_absent") is True
            and cleanup.get("owned_directory_removed") is True,
            "Actual original native operation/app/byte-owner cleanup did not complete")
    return {"actual_original_archives": archives, "actual_original_outcomes": outcomes,
            "actual_original_schema_histories": registrations,
            "actual_native_creator_collision": collision, "actual_native_fixture_cleanup": cleanup,
            "new_native_leaf_count": 9, "actual_owned_import_operations": 7,
            "scope": "Historical local native qualification only; no production RPC/Swift/Host ACK/cold reopen."}


def compile_only_binary_stability(binary_info, support):
    if binary_info is None:
        return False
    binary, record = binary_info
    require(binary.is_file() and not binary.is_symlink(),
            "Original core compile-only output is not an owned regular file")
    require(binary.stat().st_size == record["bytes"]
            and support.digest(binary) == record["sha256"],
            "Actual original core compile-only binary changed")
    return True


def stability(control, head, heart, manifest, composition, composed, closure, native_libraries, binary_info, support, core_binary_info=None):
    checked_files = 0
    if closure is not None:
        for row in closure["files"]:
            require(support.digest(row["path"]) == row["sha256"],
                    "Declared original native compilation input changed after execution")
            checked_files += 1
    for name, digest in composed.items():
        require(support.digest(heart / name) == digest,
                "Composed product/test source changed after execution")
    original_models(heart, manifest)
    for name, digest in manifest["original_module_hashes"].items():
        require(support.digest(heart / name) == digest, "Original module/native checksum changed")
    if native_libraries is not None:
        require(support.native_library_inputs(heart) == native_libraries, "Actual native link inputs changed")
    if binary_info is not None:
        binary, record = binary_info
        require(support.digest(binary) == record["sha256"], "Actual compiled/executed native binary changed")
    core_checked = compile_only_binary_stability(core_binary_info, support)
    require(source_admission(control, manifest) == composition, "Control source composition changed")
    require(git(control, "rev-parse", "HEAD").decode().strip() == head, "Exact control revision changed")
    return {"status": "PASS", "declared_dependency_files_checked": checked_files,
            "declared_dependency_closure_available": closure is not None,
            "composed_native_files_checked": len(composed),
            "unchanged_original_model_proto_rpc_files_checked": len(manifest["original_model_and_rpc_inputs"]),
            "original_module_checksums_checked": sorted(manifest["original_module_hashes"]),
            "actual_link_inputs_checked": native_libraries is not None,
            "actual_native_binary_checked": binary_info is not None,
            "actual_core_compile_only_binary_checked": core_checked,
            "original_core_tests_executed": False,
            "control_source_rechecked": True}


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--control-root", type=Path, required=True)
    parser.add_argument("--control-head", required=True)
    parser.add_argument("--execution-manifest-sha256", required=True)
    parser.add_argument("--source-only", action="store_true")
    parser.add_argument("--original-repository", type=Path)
    parser.add_argument("--original-heart-repository", type=Path)
    parser.add_argument("--heart", type=Path)
    parser.add_argument("--work", type=Path)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--job-deadline-unix", type=int)
    args = parser.parse_args()
    control = args.control_root.resolve()
    require(re.fullmatch(r"[0-9a-f]{40}", args.control_head)
            and git(control, "rev-parse", "HEAD").decode().strip() == args.control_head,
            "Exact triggered control source differs")
    packet = safe(control, PACKET)
    manifest_raw = safe(packet, "EXECUTION_INPUTS.json").read_bytes()
    require(sha(manifest_raw) == args.execution_manifest_sha256
            and manifest_raw == git(control, "show", "HEAD:" + PACKET + "/EXECUTION_INPUTS.json"),
            "Exact workflow execution-manifest binding differs")
    manifest = json.loads(manifest_raw)
    composition = source_admission(control, manifest, args.original_repository,
                                   args.original_heart_repository)
    template = safe(packet, "workflow.template.yml").read_text()
    require(template.count("__EXECUTION_MANIFEST_SHA256__") == 1,
            "Native workflow template binding differs")
    expected_workflow = template.replace("__EXECUTION_MANIFEST_SHA256__", sha(manifest_raw)).encode()
    workflow = safe(control, ".github/workflows/otzaria-owned-annotation-import.yml")
    workflow_published = workflow.exists()
    if workflow_published:
        require(workflow.is_file() and workflow.read_bytes() == expected_workflow
                and workflow.read_bytes() == git(control, "show", "HEAD:.github/workflows/otzaria-owned-annotation-import.yml"),
                "Exact dedicated workflow differs")
    changes = git(control, "diff", "--name-status", "--no-renames",
                  CANDIDATE_REVISION, args.control_head).decode().splitlines()
    require(all(row.split("\t", 1)[0] in ("A", "M") and
                (row.split("\t", 1)[1].startswith(PACKET + "/") or
                 row.split("\t", 1)[1] == ".github/workflows/otzaria-owned-annotation-import.yml")
                for row in changes), "Change outside the owned qualification allowlist")
    if args.source_only:
        print(json.dumps({"status": "SOURCE_ONLY_PASS", "checkout_sha": args.control_head,
                          "checkout_tree": git(control, "rev-parse", "HEAD^{tree}").decode().strip(),
                          "manifest_sha256": sha(manifest_raw), "frozen_original_native_inputs": 43,
                          "frozen_candidate_source_files": 12, "new_native_test_files": 3,
                           "explicit_observer_repair_manifest_sha256": OBSERVER_REPAIR_SHA256,
                           "required_compiler_inputs": manifest["required_compiler_input_count"],
                          "sealed_candidate_revision": CANDIDATE_REVISION,
                          "sealed_fixture_revision": FIXTURE_REVISION,
                          "original_git_source_bytes_checked": args.original_repository is not None,
                          "original_heart_bytes_checked": args.original_heart_repository is not None,
                          "workflow_published": workflow_published,
                          "diagnostic_only": True, "selected_native_leaves": ["text"],
                          "schema_diagnostic_manifest_sha256": SCHEMA_DIAGNOSTIC_SHA256,
                          "workflow_sha256": sha(expected_workflow),
                          "native_compilation": False, "native_execution": False,
                          "production_import_activated": False, "historical_selectors_replayed": False,
                          "changes": changes}, indent=2))
        return 0
    require(workflow_published, "Actual native gate requires its exact published workflow")
    require(all(value is not None for value in
                (args.heart, args.work, args.evidence, args.job_deadline_unix)),
            "Native gate requires explicit fresh owned roots and deadline")
    require(platform.system() == "Darwin" and platform.machine() == "arm64",
            "Original native qualification requires actual Darwin ARM64")
    heart, work, evidence = (path.resolve() for path in (args.heart, args.work, args.evidence))
    for path in (heart, work, evidence):
        require(path.is_relative_to(control) and path != control, "Owned native path escapes checkout")
    roots = (packet, heart, work, evidence)
    require(not any(a == b or a.is_relative_to(b) or b.is_relative_to(a)
                    for i, a in enumerate(roots) for b in roots[i+1:]), "Owned native roots overlap")
    require(not work.exists() and not evidence.exists(), "Native work/evidence roots must be fresh")
    require(time.time() < args.job_deadline_unix <= time.time() + 7100, "Native absolute deadline differs")
    work.mkdir(parents=True)
    evidence.mkdir(parents=True)
    fixtures = evidence / "fixtures"
    fixtures.mkdir(mode=0o700)
    (fixtures / "source").mkdir(mode=0o700)
    temporary = work / "native-temporary"
    temporary.mkdir(mode=0o700)
    support, inputs = load_support(control, manifest, work)
    allowed = ("PATH", "HOME", "LANG", "LC_ALL", "DEVELOPER_DIR", "SDKROOT", "GOCACHE", "GOMODCACHE")
    env = {name: os.environ[name] for name in allowed if name in os.environ}
    env.update(TMPDIR=str(temporary), CGO_ENABLED="1", GOMAXPROCS="2", GOTOOLCHAIN="local",
               GOWORK="off", GOENV="off", GOFLAGS="-mod=readonly",
               OTZARIA_NATIVE_CLOSED_IMPORT_EVIDENCE=str(fixtures / "source"))
    commands = support.Commands(evidence, env, args.job_deadline_unix - 180)
    result = {"status": "STARTED_NOT_ACCEPTED", "control_head": args.control_head,
              "candidate_revision": CANDIDATE_REVISION, "fixture_revision": FIXTURE_REVISION,
              "heart_base": HEART, "execution_manifest_sha256": sha(manifest_raw),
              "native_cases": "NOT_RUN", "fixture_evidence": "NOT_REACHED",
               "bundled_persistence_semantic_control": "NOT_RUN",
               "observer_repair_manifest_sha256": OBSERVER_REPAIR_SHA256,
               "schema_diagnostic_manifest_sha256": SCHEMA_DIAGNOSTIC_SHA256,
               "diagnostic_only": True, "selected_native_leaves": ["text"],
              "post_execution_source_module_link_stability": "NOT_REACHED",
              "historical_selectors_replayed": False, "production_import_activated": False,
              "swift_invocation_qualified": False, "cold_reopen_qualified": False,
              "body_ack_authority": False}
    support.write_json(evidence / "RESULT.json", result)
    composed, closure, native_libraries, binary_info, core_binary_info = {}, None, None, None, None
    native_started, native_all_pass, all_gates_pass = False, False, False
    try:
        composed, required = compose_native(control, heart, inputs, manifest, composition,
                                             support, commands, evidence)
        go = shutil.which("go")
        require(go, "Original Go compiler is absent")
        go = str(Path(go).resolve())
        version = commands.require("go-version", [go, "version"], heart, 30).read_text().strip()
        require(version == "go version go1.26.5 darwin/arm64", "Original Go version differs")
        xcode = commands.require("xcode-version", ["xcodebuild", "-version"], heart, 30).read_text()
        require(xcode.startswith("Xcode 27"), "Original Apple native compiler family differs")
        commands.require("clang-version", ["xcrun", "--sdk", "macosx", "clang", "--version"], heart, 30)
        result["actual_toolchain"] = {"go": version, "go_path": go,
                                     "go_sha256": support.digest(go), "xcode": xcode}
        repair = read_observer_repair(control, manifest)
        diagnostic = read_schema_diagnostic(control, manifest)
        format_names = sorted({row["native_path"] for row in
                               manifest["candidate_inputs"] + manifest["test_inputs"] + repair["inputs"] + diagnostic["inputs"]})
        formatting = commands.require("new-native-source-format",
                                      [str(Path(go).with_name("gofmt")), "-l",
                                       *[str(heart / name) for name in format_names]], heart, 30)
        require(not formatting.read_text().strip(), "New native sources are not exact gofmt")
        commands.require("original-tantivy", [
            sys.executable, "-I", str(inputs / "support/bootstrap/prepare_original_tantivy.py"),
            "--heart", str(heart), "--helper", str(inputs / "support/bootstrap/build_custom_heart.py"),
            "--helper-sha256", "0ebbe2f6227418eac2c532b0058290158319ba9f786baaf445de444887e8c669",
            "--receipt", str(evidence / "TANTIVY_SETUP.json")], heart, 600)
        native_libraries = support.native_library_inputs(heart)
        require(native_libraries == manifest["expected_tantivy_inputs"], "Actual original link bytes differ")
        env["CGO_LDFLAGS"] = "-L" + str(heart / "deps/libs/darwin-arm64")
        listing = commands.require("declared-native-inputs",
                                   [go, "list", "-deps", "-test", "-json", "./core/application", "./core",
                                     "./core/block/object/objectcreator"],
                                   heart, 1200)
        closure = support.dependency_inputs(listing, heart,
                                           [{"path": name, "sha256": digest}
                                            for name, digest in sorted(required.items())])
        selected = {"github.com/anyproto/anytype-heart/core/application",
                    "github.com/anyproto/anytype-heart/core",
                    "github.com/anyproto/anytype-heart/core/block/object/objectcreator"}
        require(selected.issubset({row["import_path"] for row in closure["packages"]}),
                "Actual Go declaration omits an original selected compile package")
        closure["selected_original_packages"] = sorted(selected)
        support.write_json(evidence / "DECLARED_NATIVE_INPUTS.json", closure)
        core_binary = work / "original-core-compile-only.test"
        commands.require("compile-original-core-only",
                         [go, "test", "-c", "-p", "2", "-o", str(core_binary), "./core"],
                         heart, 3600)
        require(core_binary.is_file() and not core_binary.is_symlink()
                and core_binary.stat().st_size > 0,
                "Actual original compiler emitted no core compile-only test binary")
        core_record = {"name": core_binary.name, "bytes": core_binary.stat().st_size,
                       "sha256": support.digest(core_binary), "retained_in_artifact": False,
                       "package": "github.com/anyproto/anytype-heart/core",
                       "execution": "NOT_EXECUTED_COMPILE_ONLY"}
        core_binary_info = (core_binary, core_record)
        result["actual_core_compile_only_binary"] = core_record
        commands.require("core-compile-only-binary-buildinfo",
                         [go, "version", "-m", str(core_binary)], heart, 30)
        binary = work / "owned-annotation-import.test"
        commands.require("compile-original-closed-import",
                         [go, "test", "-c", "-p", "2", "-o", str(binary), "./core/application"],
                         heart, 3600)
        require(binary.is_file() and binary.stat().st_size > 0, "Actual original compiler emitted no native test")
        record = {"name": binary.name, "bytes": binary.stat().st_size,
                  "sha256": support.digest(binary), "retained_in_artifact": False}
        binary_info = (binary, record)
        result["actual_native_binary"] = record
        commands.require("native-binary-buildinfo", [go, "version", "-m", str(binary)], heart, 30)
        semantic = reuse_semantic_control(control, manifest, listing, closure, heart, evidence)
        result["bundled_persistence_semantic_control"] = semantic
        support.write_json(evidence / "BUNDLED_PERSISTENCE_CONTROL.json", semantic)
        support.write_json(evidence / "RESULT.json", result)
        result["native_cases"] = "EXECUTION_REQUESTED"
        support.write_json(evidence / "RESULT.json", result)
        native_started = True
        code, output, _ = commands.run("execute-original-closed-import", [
            go, "tool", "test2json", "-t", "-p", "github.com/anyproto/anytype-heart/core/application",
            str(binary), "-test.v=test2json", "-test.run=" + manifest["native_selector"],
            "-test.count=1", "-test.timeout=30m"], heart, 1950)
        # Preserve actual per-leaf/parent data before requiring success. The
        # finally block checks global source stability even when this fails.
        intake = native_case_intake(output)
        result["native_cases"] = intake
        support.write_json(evidence / "NATIVE_CASES.json", intake)
        support.write_json(evidence / "RESULT.json", result)
        require(support.digest(binary) == record["sha256"], "Actually executed native binary changed")
        require(code == 0, "Original native closed-import command returned failure")
        require_all_native_pass(intake)
        native_all_pass = True
        result["native_all_new_cases_passed"] = True
        support.write_json(evidence / "RESULT.json", result)
        inventory = verify_fixture_evidence(fixtures)
        support.write_json(evidence / "ACTUAL_NATIVE_FIXTURE_INTAKE.json", inventory)
        result["fixture_evidence"] = "PASS"
        all_gates_pass = True
    except BaseException as error:
        result.update(status="FAIL", error_type=type(error).__name__, error=str(error))
    finally:
        # Run this closure independently of the collector result. A collector
        # failure cannot skip or retrospectively manufacture this native gate.
        if composed:
            try:
                check = stability(control, args.control_head, heart, manifest, composition,
                                  composed, closure, native_libraries, binary_info, support, core_binary_info)
                result["post_execution_source_module_link_stability"] = check
                support.write_json(evidence / "POST_EXECUTION_STABILITY.json", check)
            except BaseException as error:
                result["post_execution_source_module_link_stability"] = {
                    "status": "FAIL", "error_type": type(error).__name__, "error": str(error)}
                all_gates_pass = False
        else:
            all_gates_pass = False
        try:
            require(commands.owned_groups_drained, "Preserve native state: owned process group not drained")
            cleanup_ok = not native_started
            if native_started:
                cleanup_path = fixtures / "native-import-cleanup.json"
                if cleanup_path.is_file():
                    cleanup = json_file(fixtures, "native-import-cleanup.json")
                    cleanup_ok = (cleanup.get("all_original_operations_drained") is True and
                                  cleanup.get("original_account_stop_returned_or_app_absent") is True and
                                  cleanup.get("owned_annotation_stages_absent") is True and
                                  cleanup.get("owned_directory_removed") is True)
            require(cleanup_ok, "Preserve native disposable account data: actual fixture cleanup is incomplete")
            shutil.rmtree(temporary)
            result["owned_native_temporary_removed"] = True
        except BaseException as error:
            result["owned_native_temporary_removed"] = False
            result["cleanup_error_type"] = type(error).__name__
            result["cleanup_error"] = str(error)
            all_gates_pass = False
        result["native_all_new_cases_passed"] = native_all_pass
        result["owned_command_groups_drained"] = commands.owned_groups_drained
        result["commands"] = len(commands.items)
        result["finished_unix"] = time.time()
        result["status"] = ("PASS_ORIGINAL_NATIVE_CLOSED_ANNOTATION_QUALIFICATION_ONLY"
                            if all_gates_pass else "FAIL")
        support.write_json(evidence / "RESULT.json", result)
        indexed = []
        for path in sorted(evidence.rglob("*")):
            require(not path.is_symlink(), "Native evidence contains an unexpected symlink")
            if path.is_file() and path != evidence / "EVIDENCE_INDEX.json":
                indexed.append({"path": path.relative_to(evidence).as_posix(),
                                "bytes": path.stat().st_size, "sha256": support.digest(path)})
        support.write_json(evidence / "EVIDENCE_INDEX.json", {
            "scope": "Genuine disposable native exports, closed original import/readback and adverse lifecycle. "
                     "No account database, wallet seed, production API/SDK/Host ACK or cold reopen.",
            "files": indexed})
    return 0 if all_gates_pass else 1


if __name__ == "__main__":
    def interrupted(signum, frame):
        raise KeyboardInterrupt("Original native workflow interrupted: " + str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    sys.exit(main())
