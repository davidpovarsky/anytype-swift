"""Source and evidence contract for the separately built coherent Apple proof."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NATIVE_RUN = "45026227924"
NATIVE_SOURCE = "b2fc3804426067dd1ec8318d6ea92a4bcb8e9545"
NATIVE_ARTIFACT = "Pinkha-Coherent-Heart-Native-45026227924-1"
NATIVE_ZIP_SHA = "52f293d77c7d1bcf9b94c0c0cd0cf0a2cbb8cdeca7a83ab5dde1506635b12783"
HEART = "d98420b1113536afd08cde6de9a5816f6d27ffff"
PATCH = "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00"
INVENTORY = "05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0"
VARIANT = "r15-attachment-authorized-current-read-v1"
ORIGINAL_FIXTURE = "be8136a6108c00b5b687d3e587cacce611b8f2ac7dcde01efc5cb11bdd59786d"
FIXTURE_TAG = "pinkha_coherent_apple_fixture"
PRODUCTION_ARTIFACT = "Pinkha-Coherent-Heart-Production-Simulator-v1"
FIXTURE_ARTIFACT = "Pinkha-Coherent-Heart-Fixture-Simulator-v1"
PACKAGE = "CoherentHeartAuthorityHarness"
TARGET = PACKAGE + "Tests"
METHOD = "CoherentHeartAuthorityTests/testActualCombinedLibSignedAuthorityAndSharedSwiftDecoding"
PASS = "PASS_COHERENT_HEART_IOS_FIXTURE_AND_SWIFT_CODEC"


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular file: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(name):
    value = PurePosixPath(name)
    require(value.parts and not value.is_absolute() and ".." not in value.parts and "\\" not in name and ":" not in name,
            "Unsafe artifact path")
    return Path(*value.parts)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf8")


def qualified_native(directory):
    expected = json.loads((HERE / "native-proof.json").read_bytes())
    require(expected["run_id"] == NATIVE_RUN and expected["source_sha"] == NATIVE_SOURCE
            and expected["artifact_zip_sha256"] == NATIVE_ZIP_SHA, "Wrong frozen native proof manifest")
    files = {path.relative_to(directory).as_posix(): digest(path) for path in directory.rglob("*") if path.is_file()}
    require(files == expected["files_sha256"] and len(files) == 43, "Native proof is missing, extra or changed")
    receipt = json.loads((directory / "receipt.json").read_bytes())
    require(receipt["status"] == "PASS_COHERENT_SIGNED_AUTHORITY" and receipt["run_id"] == NATIVE_RUN
            and receipt["run_attempt"] == "1" and receipt["app_sha"] == NATIVE_SOURCE
            and receipt["actual_top_level_methods"] == 10 and receipt["actual_terminal_cases"] == 19
            and receipt["actual_fail"] == receipt["actual_skip"] == 0
            and receipt["patch_sha256"] == PATCH and receipt["inventory_sha256"] == INVENTORY,
            "Native source was not qualified by the exact original result")
    patch = directory / "runtime-source/native-heart-integration.patch"
    inventory_path = directory / "runtime-source/native-heart-integration.json"
    require(digest(patch) == PATCH and digest(inventory_path) == INVENTORY, "Frozen composed source differs")
    inventory = json.loads(inventory_path.read_bytes())
    before = json.loads((directory / "native-source-before.json").read_bytes())
    after = json.loads((directory / "native-source-after.json").read_bytes())
    require(before == after == {row["path"]: row["after_sha256"] for row in inventory["files"]}
            and len(before) == 139 and inventory["runtime_variant"] == VARIANT,
            "Original complete native source changed during proof")
    generation = json.loads((directory / "generation/generation-receipt.json").read_bytes())
    require(generation["heart_sha"] == HEART and generation["status"] == "PASS_PINNED_RPC_GENERATION",
            "Original generated source is unqualified")
    build = json.loads((directory / "build.json").read_bytes())
    require(build["fixture_sha256"] == ORIGINAL_FIXTURE, "Original assertion fixture differs")
    return dict(receipt=receipt, inventory=inventory, patch=patch, generation=generation,
                original_fixture_files=build["fixture_source_sha256"], version=build["runtime_version"],
                source_sha256=before)


def validate_native_run(value):
    require(str(value.get("id")) == NATIVE_RUN and value.get("run_attempt") == 1
            and value.get("head_sha") == NATIVE_SOURCE and value.get("status") == "completed"
            and value.get("conclusion") == "success" and value.get("event") == "workflow_dispatch"
            and value.get("head_branch") == "codex/chatgpt-wave15-shared-20261121"
            and value.get("path") == ".github/workflows/torah-inspector-ipados27.yml"
            and value.get("display_title") == "Pinkha coherent-heart-native · " + NATIVE_SOURCE,
            "Wrong actual successful native producer run")


def validate_build_receipt(value, app_sha, run_id):
    require(value.get("status") == "BUILT_DISTINCT_COHERENT_APPLE_FRAMEWORKS_NOT_EXECUTED"
            and value.get("app_sha") == app_sha and value.get("run_id") == run_id
            and value.get("native_run") == NATIVE_RUN and value.get("native_source") == NATIVE_SOURCE
            and value.get("patch_sha256") == PATCH and value.get("inventory_sha256") == INVENTORY
            and value.get("native_source_count") == 139 and value.get("old_tests_executed") == 0,
            "Combined Apple source/build receipt is incomplete")
    require(set(value.get("frameworks", {})) == {"production", "fixture"}, "Need distinct production and fixture binaries")
    p, f = value["frameworks"]["production"], value["frameworks"]["fixture"]
    require(p.get("fixture_compiled") is False and f.get("fixture_compiled") is True
            and p.get("binary_sha256") != f.get("binary_sha256")
            and f.get("fixture_tag") == FIXTURE_TAG and p.get("fixture_tag") is None,
            "Fixture binary must never be passed off as the production binary")
    require(re.fullmatch(r"[0-9a-f]{64}", value.get("bridge_sha256", "")), "Missing fixture source identity")


def verify_framework(directory, receipt):
    observed = {p.relative_to(directory).as_posix(): digest(p) for p in directory.rglob("*") if p.is_file()}
    require(observed == receipt["files_sha256"], "Built framework bytes changed")
    require(observed.get("ios-arm64-simulator/Lib.framework/Lib") == receipt["binary_sha256"],
            "Actual simulator slice does not match build receipt")
