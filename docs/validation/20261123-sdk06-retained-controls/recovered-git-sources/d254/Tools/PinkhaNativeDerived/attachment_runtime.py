"""Compose attachment-safe Heart runtimes without replacing immutable r14/r15.

The correction is authored once by prepare_heart_integration.py. This module
ports its exact already-tested three patch sections onto each frozen revision.
It never edits an approval or treats the r14 candidate as a complete r15.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

SOURCE_SHA = "947fbde24d5657d0e1229f45bb3993648884a8a1"
HEART_SHA = "d98420b1113536afd08cde6de9a5816f6d27ffff"
HEART_TAG = "v0.51.7-nightly.20261014.1"
APPROVAL_ROOT = "docs/pinkha/torah-integration/evidence/native-derived/8494cfb347/approval"
CANDIDATE_ROOT = "docs/validation/20261119-t5-native-attachment/generated"
CANDIDATE_PATCH_SHA = "d055933d365d3f0453ad42ce4eb4463a25deceac3d0df11162d460896810a6b4"
PROOF_SOURCE_SHA = "be6cc5d8b5e65ee78f46e09b3105e3360eec894f"
PROOF_RUN_ID = "44610974453"
PROOF_ARTIFACT_ID = "14571684164"
PROOF_ARTIFACT_SHA = "c66ae9716884316f470d56a7c57cf5f82552b0111fb05dd20e2d650102213e5a"
DETAILS = "core/block/editor/basic/details.go"
BASE_DETAILS_SHA = "0ac058091f7ab161aec3d462d3cfa3e844af980cb0d5cecf2400b64360f7f033"
FIXED_FILES = {
    DETAILS: {
        "before_sha256": "581e9357b14334a9882fe4fd2907bb1d77e6109c2bdc59955d03bda4a5504b9b",
        "after_sha256": "3247b789370d21d4ff9ca8eeb0df6580be6a7d18819820e31aac2858cff9fc59",
    },
    "core/block/editor/basic/pinkha_torah_attachment_test.go": {
        "before_sha256": None,
        "after_sha256": "3e68b777e64b28d7a5d88ea5eea92cd01b67db00ae9e4fd87df2f355ff9e764f",
    },
    "core/block/detailservice/pinkha_torah_attachment_test.go": {
        "before_sha256": None,
        "after_sha256": "efb25c593e4a1eabf04ca98ff0af824d8daed449a4284ad6dd5205857a5be41d",
    },
}
VARIANTS = {
    "r14-attachment-v1": {
        "revision": 14,
        "patch_sha256": "fb96818eb57bd9e0be8da90a11831bcccc7ca8e72cc0a4e9a065500feb7cc077",
        "inventory_sha256": "952073d8dccc991f21bffe5d3ded4e1d5369bb2c30f247ae5204d47cb03aee14",
        "t5_related_lookup": 0,
        "corrected_patch_sha256": "d055933d365d3f0453ad42ce4eb4463a25deceac3d0df11162d460896810a6b4",
        "corrected_inventory_sha256": "2cc13eb6269acb3ccfb79544d6401592b03c6bb9b3a6b7094d3d2915b2d3bc9d",
    },
    "r15-attachment-v1": {
        "revision": 15,
        "patch_sha256": "5a0906158569d47642d9fc978932cdf254550a31c864a1fb34bd1f8e4e7c10f2",
        "inventory_sha256": "f0e4a4c2d1b4c1baa11347362cfd18368ad272a8902b2beaf8de52270f809ee7",
        "t5_related_lookup": 1,
        "corrected_patch_sha256": "595f8142f00035da2fff4925c8fe125fa7cf36de9ae124b528a9d2130b2a9bf6",
        "corrected_inventory_sha256": "a9c381a46a0003c34695f22232b57716096ec51b100bb8dae2a18b47148274d8",
    },
}


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def checked_digest(data: bytes, expected: str, name: str) -> bytes:
    data = normalized(data)
    if sha256(data) != expected:
        raise RuntimeError("Immutable source bytes changed: " + name)
    return data


def sections(patch: bytes) -> dict[str, bytes]:
    """Accept only one regular same-path section per tracked native file."""
    result = {}
    chunks = patch.split(b"diff --git ")
    if chunks[0]:
        raise RuntimeError("Unexpected bytes before native patch")
    for chunk in chunks[1:]:
        header = chunk.split(b"\n", 1)[0].decode("utf8")
        left, right = header.split(" ")
        path = left.removeprefix("a/")
        if left != "a/" + path or right != "b/" + path:
            raise RuntimeError("Renamed or malformed native patch path")
        if (not path or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts
                or "\\" in path or path in result):
            raise RuntimeError("Duplicate or unsafe native patch path")
        result[path] = b"diff --git " + chunk
    if not result:
        raise RuntimeError("Native patch is empty")
    return result


def file_inventory(inventory: dict) -> dict[str, dict]:
    entries = inventory.get("files", [])
    result = {entry["path"]: dict(entry) for entry in entries}
    if len(result) != len(entries) or not result:
        raise RuntimeError("Duplicate or empty native source inventory")
    return result


def runtime_version(variant: str, patch_sha: str) -> str:
    config = VARIANTS[variant]
    version = HEART_TAG + "-pinkha-native-derived-v1-" + patch_sha
    if config["t5_related_lookup"]:
        version += "-pinkha-native-t5-lookup-v1-" + patch_sha
    return version + "-pinkha-torah-attachment-v1-" + patch_sha


@dataclass(frozen=True)
class RuntimeSource:
    variant: str
    patch: bytes
    inventory: bytes

    @property
    def patch_sha256(self) -> str:
        return sha256(self.patch)

    @property
    def inventory_sha256(self) -> str:
        return sha256(self.inventory)

    @property
    def version(self) -> str:
        return runtime_version(self.variant, self.patch_sha256)

    @property
    def lookup_capability(self) -> int:
        return VARIANTS[self.variant]["t5_related_lookup"]

    def write(self, output: Path) -> tuple[Path, Path]:
        if output.exists():
            raise RuntimeError("Fresh corrected-runtime output directory required")
        output.mkdir(parents=True)
        patch = output / "native-heart-integration.patch"
        inventory = output / "native-heart-integration.json"
        patch.write_bytes(self.patch)
        inventory.write_bytes(self.inventory)
        return patch, inventory


def compose(variant: str, base_patch: bytes, base_inventory: bytes,
            candidate_patch: bytes, candidate_inventory: bytes) -> RuntimeSource:
    config = VARIANTS[variant]
    base_patch = checked_digest(base_patch, config["patch_sha256"], variant + " base patch")
    base_inventory = checked_digest(base_inventory, config["inventory_sha256"], variant + " base inventory")
    candidate_patch = checked_digest(candidate_patch, CANDIDATE_PATCH_SHA, "tested attachment patch")
    base, candidate = json.loads(base_inventory), json.loads(normalized(candidate_inventory))
    for name, inventory, expected in [
        ("base", base, config["patch_sha256"]), ("candidate", candidate, CANDIDATE_PATCH_SHA)
    ]:
        if inventory.get("heart_sha") != HEART_SHA or inventory.get("patch_sha256") != expected:
            raise RuntimeError(name + " native source identity differs")
    if base.get("features", {}).get("t5_related_lookup", 0) != config["t5_related_lookup"]:
        raise RuntimeError("The base lookup capability differs")
    original, correction = sections(base_patch), sections(candidate_patch)
    original_files, correction_files = file_inventory(base), file_inventory(candidate)
    if set(original) != set(original_files) or set(correction) != set(correction_files):
        raise RuntimeError("Native patch and source inventory disagree")
    if original_files[DETAILS]["after_sha256"] != BASE_DETAILS_SHA:
        raise RuntimeError("The tested correction does not apply to this details implementation")
    for path, expected in FIXED_FILES.items():
        if correction_files.get(path) != dict(path=path, **expected):
            raise RuntimeError("The correction source differs from the native PASS: " + path)
        if path == DETAILS:
            if original_files[path]["before_sha256"] != expected["before_sha256"]:
                raise RuntimeError("The base Heart details file changed")
        elif path in original:
            raise RuntimeError("The attachment fixture would replace existing native code")
    # Preserve every base section, including all r15 lookup additions. The only
    # replacements are the tested details implementation and its two fixtures.
    composed = dict(original)
    files = dict(original_files)
    for path in FIXED_FILES:
        composed[path] = correction[path]
        files[path] = correction_files[path]
    patch = b"".join(composed[path] for path in sorted(composed))
    patch_sha = sha256(patch)
    if config["revision"] == 14 and patch_sha != CANDIDATE_PATCH_SHA:
        raise RuntimeError("Corrected r14 must reproduce the complete tested candidate exactly")
    result = dict(base)
    result.update(
        status="SOURCE_COMPOSED_APPLE_RUNTIME_NOT_RUN",
        patch_sha256=patch_sha,
        previous_patch_sha256=config["patch_sha256"],
        runtime_variant=variant,
        expected_app_get_version=runtime_version(variant, patch_sha),
        features=dict(base.get("features", {}), ordinary_details_preserve_torah_attachment=1),
        files=[files[path] for path in sorted(files)],
        client_enablement="DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF",
        correction_provenance=dict(
            source_sha=PROOF_SOURCE_SHA, run_id=PROOF_RUN_ID,
            artifact_id=PROOF_ARTIFACT_ID, artifact_sha256=PROOF_ARTIFACT_SHA,
            tested_patch_sha256=CANDIDATE_PATCH_SHA,
            frozen_base_source_sha=SOURCE_SHA, base_patch_sha256=config["patch_sha256"],
            base_inventory_sha256=config["inventory_sha256"],
            replaced_or_added_files=sorted(FIXED_FILES),
            unchanged_base_files=[path for path in sorted(original) if path not in FIXED_FILES],
            native_package_proof_scope=("EXACT_TESTED_R14_SOURCE" if config["revision"] == 14
                                        else "CORRECTION_IDENTICAL_COMBINED_R15_NOT_RUN"),
            original_r14_r15_write_compatibility="KNOWN_ATTACHMENT_DRIFT_NOT_PROVEN",
            apple_runtime="NOT_RUN", account_pair="NOT_RUN", full_t5_acceptance=False,
        ),
    )
    runtime = RuntimeSource(variant, patch, json_bytes(result))
    if (runtime.patch_sha256 != config["corrected_patch_sha256"]
            or runtime.inventory_sha256 != config["corrected_inventory_sha256"]):
        raise RuntimeError("Composed runtime differs from its frozen profile")
    return runtime


def frozen_blob(repository: Path, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repository), "show", SOURCE_SHA + ":" + path])


def prepare(repository: Path, control: Path, variant: str) -> RuntimeSource:
    config = VARIANTS[variant]
    approval = APPROVAL_ROOT + "/revision-" + str(config["revision"])
    # Read approvals from the immutable Git object, never a mutable copied
    # approval. Working candidate bytes must still equal the exact native PASS.
    return compose(
        variant,
        frozen_blob(repository, approval + "/native-heart-integration.patch"),
        frozen_blob(repository, approval + "/native-heart-integration.json"),
        (control / CANDIDATE_ROOT / "native-heart-integration.patch").read_bytes(),
        (control / CANDIDATE_ROOT / "native-heart-integration.json").read_bytes(),
    )


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--source-repository", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--variant", choices=VARIANTS, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runtime = prepare(args.source_repository.resolve(), args.control.resolve(), args.variant)
    patch, inventory = runtime.write(args.output.resolve())
    print(json.dumps(dict(status="SOURCE_COMPOSED_RUNTIME_NOT_RUN", variant=runtime.variant,
                          patch=str(patch), patch_sha256=runtime.patch_sha256,
                          inventory=str(inventory), inventory_sha256=runtime.inventory_sha256,
                          expected_app_get_version=runtime.version)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
