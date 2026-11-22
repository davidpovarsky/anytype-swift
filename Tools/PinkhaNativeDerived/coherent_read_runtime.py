"""Exact composition of qualified T2 and current-read sources plus one fence.

Original proofs remain original. Generation starts from clean d984 through the
unchanged T2 generator; only then may this module apply the disjoint 52 paths and
the explicitly inventoried prepare/finalize delta. It does not build a runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

import attachment_runtime as base
import current_read_runtime as current

VARIANT = "r15-attachment-authorized-current-read-v1"
CURRENT_PATCH = "977f485e13892d259da5f47b9c96bdcf3b34b23defff25271b22af43ac91b9f9"
CURRENT_INVENTORY = "d7ff255272a947c008b2bbbf951fff863b4b2469a37954c60a7cc22b0fa8301f"
CURRENT_PROOF = "docs/validation/20261122-current-read-native-proof"
CURRENT_RUN = "44966862922"
CURRENT_SOURCE = "3daed522cbc7532f51a75c77d11790dd8775bb11"
T2_CANDIDATE = "69b6b3fc8616b11230cbc45ced0635f60098950a1e611a089ab73baf70550b67"
OVERLAY = "Tools/PinkhaNativeDerived/coherent_read/overlay"
REPLACED = frozenset({"core/pinkha_torah_operation_read.go", "core/pinkha_authorized_operation_read_rpc.go"})
ADDED = frozenset({"core/pinkha_coherent_operation_read.go", "core/pinkha_coherent_operation_read_test.go"})
PRODUCTION_DELTA = tuple(sorted(REPLACED | {"core/pinkha_coherent_operation_read.go"}))
AFFECTED_PRIOR_METHODS = (
    "TestPinkhaAuthorizedOperationReadRejectsVersionBeforeAccount",
    "TestPinkhaAuthorizedOperationReadShapeAndCancellationBeforeAccount",
    "TestPinkhaAuthorizedOperationReadRequiresRunningAccount",
    "TestPinkhaAuthorizedOperationRPCRejectsBeforeAccount",
)


def require(value, message):
    if not value:
        raise ValueError(message)


def digest(path):
    require(path.is_file() and not path.is_symlink(), "Expected regular source/evidence: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(name):
    value = PurePosixPath(name)
    require(value.parts and not value.is_absolute() and ".." not in value.parts and "\\" not in name and ":" not in name,
            "Unsafe source path")
    return Path(*value.parts)


def version(patch_sha):
    return current.version(patch_sha) + "-pinkha-authorized-read-v1-" + patch_sha


@dataclass(frozen=True)
class RuntimeSource(base.RuntimeSource):
    @property
    def version(self):
        return version(self.patch_sha256)

    @property
    def lookup_capability(self):
        return 1


def qualified_current_read(control, runtime):
    require(runtime.variant == current.VARIANT and runtime.patch_sha256 == CURRENT_PATCH
            and runtime.inventory_sha256 == CURRENT_INVENTORY, "Current-read source differs from its qualified candidate")
    directory = control / CURRENT_PROOF
    manifest = json.loads((directory / "MANIFEST.json").read_bytes())
    require(manifest["sourceCommit"] == CURRENT_SOURCE and manifest["artifactID"] == 14732375776
            and manifest["artifactZIP_SHA256"] == "5b1e99411759c81ba10103ffac5d3d08724e4d62cd713002b3d55364b9ca2d07"
            and manifest["runURL"].endswith("/actions/runs/" + CURRENT_RUN), "Wrong original current-read proof")
    files = manifest["originalFilesSHA256"]
    require(len(files) == 35, "Original current-read artifact inventory changed")
    for name, expected in files.items():
        require(digest(directory / "original" / relative(name)) == expected, "Original current-read evidence changed: " + name)
    receipt = json.loads((directory / "original/receipt.json").read_bytes())
    require(receipt["status"] == "PASS_LOCAL_SIGNED_REVOCATION" and receipt["run_id"] == CURRENT_RUN
            and receipt["app_sha"] == CURRENT_SOURCE and receipt["actual"]["tests_passed"] == 1
            and receipt["actual"]["tests_failed"] == receipt["actual"]["tests_skipped"] == 0
            and receipt["actual"]["exit_code"] == 0, "Original signed account proof is incomplete")
    components = receipt["publication_components"]
    require([value["method"] for value in components] == ["TestCurrentAppReadPublicationLease", "TestCurrentSpaceReadPublicationLease"]
            and all(value["passed"] == 1 and value["failed"] == value["skipped"] == 0 for value in components),
            "Original publication components did not pass")
    native = json.loads((directory / "original/native-source-before.json").read_bytes())
    require(native == json.loads((directory / "original/native-source-after.json").read_bytes())
            and native == {name: row["after_sha256"] for name, row in base.file_inventory(json.loads(runtime.inventory)).items()}
            and len(native) == 52, "Qualified 52 native sources differ")
    return {"run_id": CURRENT_RUN, "app_sha": CURRENT_SOURCE, "patch_sha256": CURRENT_PATCH,
            "inventory_sha256": CURRENT_INVENTORY, "original_manifest_sha256": digest(directory / "MANIFEST.json"),
            "original_receipt_sha256": files["receipt.json"], "original_native_source_sha256": native,
            "original_components_retained": 2, "original_account_proof_retained": 1, "old_tests_executed": 0}


def validate_t2_generation(actual, qualified):
    require(actual.get("status") == qualified.get("status") == "PASS_PINNED_RPC_GENERATION", "T2 generation did not complete")
    for key in ("heart_sha", "source_sha256", "generated_sha256", "module_sha256", "protobuf_inputs_sha256",
                "native_read_inventory_sha256", "authorized_read_manifest_sha256", "rpc_manifest_sha256"):
        require(actual[key] == qualified[key], "Regenerated T2 source differs: " + key)
    require(actual["heart_sha"] == base.HEART_SHA and len(actual["source_sha256"]) == 85
            and len(actual["generated_sha256"]) == 4 and set(actual["module_sha256"]) == {"go.mod", "go.sum"},
            "Unexpected original T2 source closure")


def validate_union(t2, authority):
    require(len(t2) == 85 and len(authority) == 52 and not set(t2).intersection(authority),
            "Reviewed native source sets must be exactly disjoint 85+52")
    require(REPLACED <= set(t2) and not ADDED.intersection(set(t2) | set(authority)), "Coherent delta would overwrite unreviewed source")
    return dict(t2, **authority)


def verify_source(heart, inventory, module_sha256):
    require(subprocess.check_output(["git", "-C", str(heart), "rev-parse", "HEAD"], text=True).strip() == base.HEART_SHA,
            "Native base changed")
    rows = base.file_inventory(inventory)
    actual = {name: digest(heart / relative(name)) for name in rows}
    require(actual == {name: row["after_sha256"] for name, row in rows.items()}, "Composed native source changed")
    tracked = {name for name, row in rows.items() if row["before_sha256"] is not None}
    require(set(subprocess.check_output(["git", "-C", str(heart), "diff", "--name-only", "HEAD"], text=True).splitlines()) == tracked,
            "Unexpected tracked native mutation")
    untracked = set(subprocess.check_output(["git", "-C", str(heart), "ls-files", "--others", "--exclude-standard"], text=True).splitlines())
    require(untracked <= set(rows) - tracked, "Unexpected native source addition")
    require({name: digest(heart / name) for name in module_sha256} == module_sha256, "Original native Go module declarations changed")
    return actual


def compose(source, control, heart, work, generation, qualified_generation, run):
    validate_t2_generation(generation, qualified_generation)
    import run_native_rpc as rpc
    rpc.verify_composed_source(heart, generation["source_sha256"], set(generation["tracked_paths"]), generation["module_sha256"])
    retained = current.prepare(source, control, heart)
    retained_proof = qualified_current_read(control, retained)
    current_files = base.file_inventory(json.loads(retained.inventory))
    baseline = validate_union(generation["source_sha256"], {name: row["after_sha256"] for name, row in current_files.items()})
    overlay_root = control / OVERLAY
    overlay = {path.relative_to(overlay_root).as_posix(): path for path in overlay_root.rglob("*") if path.is_file()}
    require(set(overlay) == REPLACED | ADDED, "Coherent overlay gained an unreviewed path")
    patch, _ = retained.write(work / "current-read-source")
    run(["git", "apply", "--check", str(patch)], "current-read-apply-check", heart, os.environ.copy())
    run(["git", "apply", str(patch)], "current-read-apply", heart, os.environ.copy())
    require({name: digest(heart / relative(name)) for name in baseline} == baseline, "85+52 composition changed a qualified byte")
    replacements = {}
    for name, path in overlay.items():
        target = heart / relative(name)
        if name in REPLACED:
            before = digest(target)
            require(before == generation["source_sha256"][name], "Replacement input differs from original T2")
        else:
            require(not target.exists(), "New coherent helper would replace a native file")
            before = None
        raw = base.normalized(path.read_bytes())
        require(raw.startswith(b"package core\n") and raw.endswith(b"\n"), "Invalid coherent native overlay")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        replacements[name] = {"before_sha256": before, "after_sha256": digest(target)}
        require(before != replacements[name]["after_sha256"], "Coherent overlay did not change source")
    names = set(baseline) | ADDED
    require(len(names) == 139, "Unexpected complete coherent native closure")
    native_tracked = set(subprocess.check_output(["git", "-C", str(heart), "ls-tree", "-r", "--name-only", "HEAD"], text=True).splitlines())
    parts, rows = {}, {}
    for name in sorted(names):
        before = subprocess.check_output(["git", "-C", str(heart), "show", "HEAD:" + name]) if name in native_tracked else None
        after = (heart / relative(name)).read_bytes()
        parts[name] = current.patch_section(name, before, after)
        rows[name] = {"path": name, "before_sha256": None if before is None else hashlib.sha256(before).hexdigest(),
                      "after_sha256": hashlib.sha256(after).hexdigest()}
    for name in current_files:
        require(rows[name] == current_files[name], "Coherent delta changed current-read/r15 source")
    for name in set(generation["source_sha256"]) - REPLACED:
        require(rows[name]["after_sha256"] == generation["source_sha256"][name], "Coherent delta changed unreviewed T2 source")
    full_patch = b"".join(parts[name] for name in sorted(parts))
    full_sha = hashlib.sha256(full_patch).hexdigest()
    inventory = json.loads(retained.inventory)
    inventory.update(status="SOURCE_COMPOSED_COHERENT_NATIVE_NOT_RUN", runtime_variant=VARIANT, patch_sha256=full_sha,
        previous_patch_sha256=CURRENT_PATCH, expected_app_get_version=version(full_sha), files=[rows[name] for name in sorted(rows)],
        features=dict(inventory["features"], authorized_operation_read=1, coherent_read_publication=1),
        product_source_changes=len([name for name in names if not name.endswith("_test.go")]),
        client_enablement="DISABLED_PENDING_COHERENT_NATIVE_AND_RUNTIME_PROOF",
        coherent_read_provenance={"t2_candidate_sha256": T2_CANDIDATE, "t2_original_native_paths": 85,
            "current_read_original_native_paths": 52, "baseline_union_paths": 137, "native_source_paths": 139,
            "current_read_proof": retained_proof, "t2_generated_sha256": generation["generated_sha256"],
            "original_module_sha256": generation["module_sha256"], "integration_delta": replacements,
            "production_delta_paths": list(PRODUCTION_DELTA), "unchanged_current_read_paths": sorted(current_files),
            "unchanged_t2_paths": sorted(set(generation["source_sha256"]) - REPLACED),
            "affected_prior_methods_selected": list(AFFECTED_PRIOR_METHODS), "unaffected_prior_t2_terminals_retained": 67,
            "new_component_methods": 5, "new_component_terminals": 14,
            "automatic_t2_to_t5_projection": "NOT_PROVEN", "default_runtime_unchanged": True,
            "network_acl_transport": "NOT_RUN", "ios_acceptance": "NOT_RUN"})
    runtime = RuntimeSource(VARIANT, full_patch, base.json_bytes(inventory))
    verify_source(heart, inventory, generation["module_sha256"])
    return runtime
