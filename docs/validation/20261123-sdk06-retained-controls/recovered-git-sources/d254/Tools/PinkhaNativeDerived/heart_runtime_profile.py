"""Exact Heart runtime admission shared by installers and actual-process observers."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re

import attachment_runtime as attachment

LEGACY_PATCH = attachment.VARIANTS["r14-attachment-v1"]["patch_sha256"]
LEGACY_INVENTORY = attachment.VARIANTS["r14-attachment-v1"]["inventory_sha256"]
CORRECTED = "r15-attachment-v1"
COHERENT = "r15-attachment-authorized-current-read-v1"
COHERENT_PATCH = "2e898ac9aac29c0f53dd777492be6b47f14784949313364ff47439de93cd3c00"
COHERENT_INVENTORY = "05ee31723508599e228d28e132ce5b89af886f5095c908362b2348d07c80d0f0"
COHERENT_NATIVE_RUN = "45026227924"
COHERENT_BUILT_RUN = "45035194823"
COHERENT_BUILT_SHA = "78b8b6168f0a750d2b742d94b78c95aa4abf579a"
COHERENT_BUILT_ARTIFACT = 14759749573
COHERENT_BUILT_ARTIFACT_SHA = "9129d5b08a52f48422c2494b195ec6f32128948a0a578f3af0785102d35c925e"
COHERENT_BUILT_PROOF_ARTIFACT = 14759749585
COHERENT_BUILT_PROOF_SHA = "ff35f54d028057cccc3125d63e681a257e371d37cacd3e7a5ea0aadf1b69b358"
COHERENT_BUILT_RECEIPT_SHA = "f924c22b612bf456fafd754f66152905110e0e6556bf1b6f858dc09e2a6cc9a0"
COHERENT_VERSION = attachment.HEART_TAG + "-" + "-".join(
    part + COHERENT_PATCH for part in (
        "pinkha-native-derived-v1-", "pinkha-native-t5-lookup-v1-",
        "pinkha-torah-attachment-v1-", "pinkha-current-read-v1-", "pinkha-authorized-read-v1-"))
PROFILE_NAMES = ("r14", CORRECTED, COHERENT)
BINDING_KEYS = (
    "runtime_profile", "native_marker", "heart_patch_sha256", "heart_inventory_sha256",
    "heart_source_run_id", "heart_source_sha", "heart_source_attempt",
    "heart_build_receipt_sha256", "heart_artifact_id", "heart_artifact_sha256",
    "heart_proof_artifact_id", "heart_proof_artifact_sha256",
)
REUSE_BINDING_KEYS = (
    "heart_build_source_run_id", "heart_build_source_sha", "heart_build_source_attempt",
    "heart_build_reuse_receipt_sha256", "heart_original_build_artifact_id",
    "heart_original_build_artifact_sha256", "heart_original_build_proof_artifact_id",
    "heart_original_build_proof_artifact_sha256",
)
REUSE_INSTALLATION_KEYS = (
    "build_producer", "build_reuse_receipt_sha256", "original_build_artifact_id",
    "original_build_artifact_sha256", "original_build_proof_artifact_id", "original_build_proof_artifact_sha256",
)


def require(condition, reason):
    if not condition:
        raise RuntimeError(reason)


def digest_bytes(value):
    return hashlib.sha256(value).hexdigest()


def json_digest(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def is_sha(value, length=64):
    return isinstance(value, str) and re.fullmatch("[0-9a-f]{" + str(length) + "}", value) is not None


@dataclass(frozen=True)
class RuntimeProfile:
    name: str
    patch_sha256: str
    inventory_sha256: str
    version: str
    binary_marker: str

    @property
    def receipt_marker(self):
        return "pinkha-native-derived-v1-" + self.patch_sha256

    @property
    def artifact_name(self):
        if self.name == COHERENT:
            return "Pinkha-Coherent-Heart-Production-Simulator-v1"
        return "Pinkha-Universal-Verified-Heart-" + self.name

    @property
    def archive_name(self):
        return self.artifact_name + ".tar.gz"


def select(name="r14"):
    require(name in PROFILE_NAMES, "Unsupported explicit Heart runtime profile")
    if name == COHERENT:
        return RuntimeProfile(name, COHERENT_PATCH, COHERENT_INVENTORY,
                              COHERENT_VERSION, COHERENT_VERSION)
    if name == "r14":
        marker = "pinkha-native-derived-v1-" + LEGACY_PATCH
        return RuntimeProfile(name, LEGACY_PATCH, LEGACY_INVENTORY,
                              attachment.HEART_TAG + "-" + marker, marker)
    config = attachment.VARIANTS[CORRECTED]
    version = attachment.runtime_version(CORRECTED, config["corrected_patch_sha256"])
    return RuntimeProfile(name, config["corrected_patch_sha256"],
                          config["corrected_inventory_sha256"], version, version)


def verify_source(profile, patch, inventory_bytes):
    require(digest_bytes(patch) == profile.patch_sha256
            and digest_bytes(inventory_bytes) == profile.inventory_sha256,
            "Runtime source bytes differ from the explicit frozen profile")
    inventory = json.loads(inventory_bytes)
    require(inventory.get("heart_sha") == attachment.HEART_SHA
            and inventory.get("patch_sha256") == profile.patch_sha256,
            "Wrong native base or corrected patch identity")
    if profile.name == CORRECTED:
        require(inventory.get("runtime_variant") == CORRECTED
                and inventory.get("expected_app_get_version") == profile.version
                and inventory.get("features", {}).get("t5_related_lookup") == 1
                and inventory["features"].get("ordinary_details_preserve_torah_attachment") == 1,
                "The corrected runtime inventory is incomplete")
    elif profile.name == COHERENT:
        require(inventory.get("runtime_variant") == COHERENT
                and inventory.get("expected_app_get_version") == profile.version
                and len(inventory.get("files", [])) == 139
                and all(inventory.get("features", {}).get(name) == 1 for name in (
                    "t5_related_lookup", "ordinary_details_preserve_torah_attachment",
                    "authorized_operation_read", "coherent_read_publication", "current_authority_read_fence")),
                "The coherent runtime must retain the exact combined source and all five features")
    return inventory


def validate_producer(run, run_id, repository, expected_branch, profile_name=CORRECTED):
    require(profile_name in (CORRECTED, COHERENT), "Unsupported source-bound producer profile")
    require(isinstance(run_id, str) and run_id.isdigit()
            and str(run.get("id")) == run_id
            and run.get("status") == "completed" and run.get("conclusion") == "success",
            "Corrected runtime requires its original successful producer run")
    require(is_sha(run.get("head_sha"), 40)
            and type(run.get("run_attempt")) is int and run["run_attempt"] > 0
            and run.get("path") == ".github/workflows/torah-inspector-ipados27.yml"
            and run.get("event") == "workflow_dispatch"
            and run.get("head_branch") == expected_branch
            and run.get("repository", {}).get("full_name") == repository,
            "Corrected runtime producer source, workflow, repository or attempt differs")
    route = "coherent-heart-apple" if profile_name == COHERENT else "t5-r15-attachment-runtime"
    require(run.get("display_title") == "Pinkha " + route + " · " + run["head_sha"],
            "Producer was not the explicitly selected runtime route")
    return dict(run_id=run_id, run_attempt=str(run["run_attempt"]), source_sha=run["head_sha"],
                source_branch=run["head_branch"], repository=repository,
                workflow_path=run["path"])


def validate_artifact(item, run, name):
    require(item.get("name") == name and item.get("expired") is False
            and type(item.get("id")) is int and item["id"] > 0
            and type(item.get("size_in_bytes")) is int and item["size_in_bytes"] > 0
            and str(item.get("workflow_run", {}).get("id")) == str(run["id"])
            and item.get("workflow_run", {}).get("head_sha") == run["head_sha"],
            "Original corrected artifact has another producer or is unavailable")
    value = item.get("digest", "")
    require(isinstance(value, str) and value.startswith("sha256:") and is_sha(value[7:]),
            "Original GitHub artifact digest is unavailable")
    return value[7:]


def validate_build(profile, receipt, inventory, source_run_id, producer=None):
    require(receipt.get("status") == "PASS" and receipt.get("target") == "ios"
            and receipt.get("heart_sha") == attachment.HEART_SHA
            and receipt.get("patch_sha256") == profile.patch_sha256
            and receipt.get("marker") == profile.receipt_marker
            and receipt.get("files") == inventory["files"],
            "Artifact does not bind this exact native source inventory")
    if profile.name == CORRECTED:
        require(producer is not None and producer.get("run_id") == source_run_id
                and receipt.get("github_run_id") == producer["run_id"]
                and receipt.get("github_run_attempt") == producer["run_attempt"]
                and receipt.get("integration_sha") == producer["source_sha"]
                and receipt.get("source_sha") == attachment.SOURCE_SHA,
                "Corrected archive does not belong to the original producer run/head/attempt")
        require(receipt.get("runtime_variant") == CORRECTED
                and receipt.get("inventory_sha256") == profile.inventory_sha256
                and receipt.get("expected_app_get_version") == profile.version
                and receipt.get("capability_marker") == "pinkha-native-t5-lookup-v1-" + profile.patch_sha256
                and receipt.get("build_status") == "APPLE_FRAMEWORK_BUILT_NOT_EXECUTED"
                and receipt.get("app_get_version_status") == "NOT_RUN_BUILD_ONLY"
                and receipt.get("native_tests") == "PASS_FOCUSED_ATTACHMENT_FIXTURES"
                and receipt.get("native_test_invocations") == 2
                and receipt.get("correction_provenance") == inventory["correction_provenance"],
                "Corrected runtime build, native fixtures or full version is unverified")
    elif profile.name == COHERENT:
        require(producer is not None and producer.get("run_id") == source_run_id
                and receipt.get("github_run_id") == producer["run_id"]
                and receipt.get("github_run_attempt") == producer["run_attempt"]
                and receipt.get("integration_sha") == producer["source_sha"],
                "Coherent archive does not belong to the admitted producer run/head/attempt")
        require(receipt.get("runtime_variant") == COHERENT
                and receipt.get("inventory_sha256") == profile.inventory_sha256
                and receipt.get("expected_app_get_version") == profile.version
                and receipt.get("fixture_included") is False
                and receipt.get("target_architecture") == "arm64"
                and receipt.get("target_environment") == "simulator"
                and receipt.get("build_status") == "APPLE_FRAMEWORK_BUILT_NOT_EXECUTED"
                and receipt.get("app_get_version_status") == "NOT_RUN_BUILD_ONLY",
                "Coherent admission requires the production-only simulator artifact and honest build scope")
    return profile.binary_marker


def validate_reuse_build_origin(origin):
    expected = dict(run_id=COHERENT_BUILT_RUN, run_attempt="1", source_sha=COHERENT_BUILT_SHA,
                    source_branch="codex/chatgpt-wave15-shared-20261121",
                    repository="davidpovarsky/anytype-swift",
                    workflow_path=".github/workflows/torah-inspector-ipados27.yml",
                    workflow_conclusion="failure", scope="framework_build_only")
    require(origin == expected, "Unqualified or relabelled original coherent build origin")
    return expected


def verify_binding(value):
    profile = select(value.get("runtime_profile", "r14"))
    require(value.get("native_marker") == profile.binary_marker,
            "Runtime observer identity differs from the selected exact full marker")
    if profile.name in (CORRECTED, COHERENT):
        require(value.get("heart_patch_sha256") == profile.patch_sha256
                and value.get("heart_inventory_sha256") == profile.inventory_sha256
                and str(value.get("heart_source_run_id", "")).isdigit()
                and str(value.get("heart_source_attempt", "")).isdigit()
                and is_sha(value.get("heart_source_sha"), 40)
                and is_sha(value.get("heart_build_receipt_sha256"))
                and is_sha(value.get("heart_artifact_sha256"))
                and is_sha(value.get("heart_proof_artifact_sha256"))
                and type(value.get("heart_artifact_id")) is int
                and type(value.get("heart_proof_artifact_id")) is int,
                "Actual-process observation lost the corrected runtime producer proof")
    build_keys = set(REUSE_BINDING_KEYS)
    if build_keys & value.keys() or value.get("heart_build_receipt_sha256") == COHERENT_BUILT_RECEIPT_SHA:
        require(profile.name == COHERENT and build_keys <= value.keys()
                and value.get("heart_source_run_id") != COHERENT_BUILT_RUN
                and value.get("heart_build_source_run_id") == COHERENT_BUILT_RUN
                and value.get("heart_build_source_sha") == COHERENT_BUILT_SHA
                and value.get("heart_build_source_attempt") == "1"
                and value.get("heart_build_receipt_sha256") == COHERENT_BUILT_RECEIPT_SHA
                and is_sha(value.get("heart_build_reuse_receipt_sha256"))
                and type(value.get("heart_original_build_artifact_id")) is int
                and value["heart_original_build_artifact_id"] == COHERENT_BUILT_ARTIFACT
                and value.get("heart_original_build_artifact_sha256") == COHERENT_BUILT_ARTIFACT_SHA
                and type(value.get("heart_original_build_proof_artifact_id")) is int
                and value["heart_original_build_proof_artifact_id"] == COHERENT_BUILT_PROOF_ARTIFACT
                and value.get("heart_original_build_proof_artifact_sha256") == COHERENT_BUILT_PROOF_SHA,
                "Actual-process observation lost the distinct immutable build origin")
    return profile.binary_marker


def installed_binding(app, installation, head, profile_name="r14", source_run_id=""):
    profile = select(profile_name)
    require(installation.get("status") == "PASS" and installation.get("app_source_sha") == head
            and installation.get("marker") == profile.receipt_marker
            and installation.get("runtime_profile", "r14") == profile_name,
            "Installed runtime does not match the explicit consumer profile/source")
    if source_run_id:
        require(installation.get("source_run_id") == source_run_id, "Installed runtime producer run differs")
    value = dict(runtime_profile=profile.name, native_marker=profile.binary_marker)
    if profile.name in (CORRECTED, COHERENT):
        require(source_run_id and installation.get("source_run_id") == source_run_id,
                "Corrected consumer requires an explicit original producer run")
        path = app / "Dependencies/Middleware/PinkhaNativeHeartBuild.json"
        raw = path.read_bytes()
        receipt = json.loads(raw)
        producer = installation.get("producer", {})
        build_producer = producer
        if set(REUSE_INSTALLATION_KEYS) & installation.keys():
            require(set(REUSE_INSTALLATION_KEYS) <= installation.keys(), "Incomplete distinct build-origin installation binding")
        if "build_producer" in installation:
            require(profile.name == COHERENT and producer.get("run_id") == source_run_id
                    and source_run_id != COHERENT_BUILT_RUN
                    and installation.get("original_build_app_sha") == COHERENT_BUILT_SHA,
                    "Build reuse requires a distinct successful coherent execution origin")
            build_producer = validate_reuse_build_origin(installation["build_producer"])
        require(digest_bytes(raw) == installation.get("heart_build_receipt_sha256")
                and producer.get("run_id") == source_run_id
                and receipt.get("github_run_id") == build_producer.get("run_id")
                and receipt.get("github_run_attempt") == build_producer.get("run_attempt")
                and receipt.get("integration_sha") == build_producer.get("source_sha")
                and receipt.get("runtime_variant") == profile.name
                and receipt.get("expected_app_get_version") == profile.version
                and receipt.get("inventory_sha256") == profile.inventory_sha256
                and receipt.get("patch_sha256") == profile.patch_sha256,
                "Installed corrected runtime receipt changed after verified admission")
        if profile.name == COHERENT:
            require(receipt.get("fixture_included") is False
                    and receipt.get("target_architecture") == "arm64"
                    and receipt.get("target_environment") == "simulator",
                    "A fixture runtime or another platform cannot become the coherent app runtime")
        value.update(
            heart_patch_sha256=profile.patch_sha256, heart_inventory_sha256=profile.inventory_sha256,
            heart_source_run_id=source_run_id, heart_source_sha=producer["source_sha"],
            heart_source_attempt=producer["run_attempt"], heart_build_receipt_sha256=digest_bytes(raw),
            heart_artifact_id=installation.get("heart_artifact_id"),
            heart_artifact_sha256=installation.get("heart_artifact_sha256"),
            heart_proof_artifact_id=installation.get("heart_proof_artifact_id"),
            heart_proof_artifact_sha256=installation.get("heart_proof_artifact_sha256"),
        )
        if build_producer is not producer:
            value.update(
                heart_build_source_run_id=build_producer["run_id"],
                heart_build_source_sha=build_producer["source_sha"],
                heart_build_source_attempt=build_producer["run_attempt"],
                heart_build_reuse_receipt_sha256=installation.get("build_reuse_receipt_sha256"),
                heart_original_build_artifact_id=installation.get("original_build_artifact_id"),
                heart_original_build_artifact_sha256=installation.get("original_build_artifact_sha256"),
                heart_original_build_proof_artifact_id=installation.get("original_build_proof_artifact_id"),
                heart_original_build_proof_artifact_sha256=installation.get("original_build_proof_artifact_sha256"),
            )
    verify_binding(value)
    return value
