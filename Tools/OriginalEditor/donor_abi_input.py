"""Reuse an unchanged native ABI with its original, independently verified owner.

The consumer receives a new source/execution identity. The original native,
generator, wrapper, ABI and Debug receipts keep their real source/run identities.
No prior runtime acceptance is attributed to the new facade.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from local_execution import require, sha, git

SCHEMA = "otzaria.original-import-donor-sdk-input/1"
POLICY = "Tools/OriginalEditor/AnnotationExchange/abi_donor_policy.json"
DONOR = "34b8a7c5ddb34e9287acdb5c189849eeac8cff86"
FRESH_DONOR = "1f90175b006be0a19a4e1804f858caaf59d6c174"
FRESH_POLICY = "Tools/OriginalEditor/MiniApps/abi_donor_1f90175b.json"
WAVE1_DONOR = "75a98ba98d6455eefc2c98113fa744b0f3c2e7bf"
WAVE1_POLICY = "Tools/OriginalEditor/Wave1/abi_donor_75a98ba.json"
WAVE1_SWIFT_TREES = ("Anytype/Sources", "Modules")
CLOSURE = ("Anytype/Sources", "Anytype/Resources", "Modules", "Dependencies/Middleware",
           "Tools/OriginalEditor/ABIPinnedWrapper", "Tools/OriginalEditor/GeneratedImport",
           "Tools/PinkhaNativeDerived",
           "Tools/OriginalEditor/build_local_import_abi.py")

FRESH_CLOSURE = CLOSURE + (
    "OriginalEditorFramework", "Tools/OriginalEditor/ImportRPC",
    "Tools/OriginalEditor/NativeRegeneration", "Tools/OriginalEditor/fresh_swift_input.py",
    "Tools/OriginalEditor/reused_abi_history.py", "Tools/OriginalEditor/import_abi_input.py",
)

# The Wave 1 facade changes application Swift only. Preserve exact original
# native/generated/wrapper inputs and require a new complete SDK compilation.
WAVE1_CLOSURE = CLOSURE + (
    "Tools/OriginalEditor/ImportRPC", "Tools/OriginalEditor/NativeRegeneration",
    "Tools/OriginalEditor/fresh_swift_input.py", "Tools/OriginalEditor/reused_abi_history.py",
    "Tools/OriginalEditor/import_abi_input.py",
)

# A fresh interpreter imports only the original owner's unchanged verifiers.
# This reads the original retained evidence; it neither reruns a generator/test
# nor substitutes a new identity for the original producer.
ORIGINAL_VERIFY = """
import json,sys,os
from pathlib import Path
root=Path(sys.argv[1]); policy=json.loads(Path(sys.argv[2]).read_text())
sys.path.insert(0,str(root/'Tools/OriginalEditor'))
from framework_profile import source_observation
from import_abi_input import verify
paths=policy['receipts']
env={'OTZARIA_LOCAL_EXECUTION':str(root/paths['execution']['path']),
     'OTZARIA_LOCAL_EXECUTION_SHA256':paths['execution']['sha256']}
before=json.loads((root/paths['source_before']['path']).read_text())
assert source_observation(root,env)==before,'Original source no longer matches actual producer'
result=verify(root,root/paths['abi']['path'],paths['abi']['sha256'],before)
print(json.dumps({'source':before,'installation':result}))
"""


def validate_policy(policy, binding):
    expected = {
        (POLICY, DONOR): ("otzaria.native-abi-donor-policy/1", CLOSURE),
        (FRESH_POLICY, FRESH_DONOR): ("otzaria.native-abi-donor-policy/2", FRESH_CLOSURE),
        (WAVE1_POLICY, WAVE1_DONOR): ("otzaria.native-abi-donor-policy/4",
            tuple(p for p in WAVE1_CLOSURE if p not in WAVE1_SWIFT_TREES)),
    }
    key = (binding.get("path"), binding.get("source_sha"))
    require(key in expected, "Unreviewed exact native donor policy identity")
    schema, closure = expected[key]
    receipt_roles = {"execution", "source_before", "abi", "debug_qualification"}
    if key == (WAVE1_POLICY, WAVE1_DONOR):
        receipt_roles.add("shared_runtime_ownership")
        require(set(policy) == {"schema", "source_sha", "unchanged_git_inputs",
                                "reviewed_swift_inputs", "receipts", "native_tests_rerun",
                                "new_sdk_acceptance_granted"}
                and set(policy.get("reviewed_swift_inputs", {})) == set(WAVE1_SWIFT_TREES),
                "Wave 1 permits only exact separately reviewed application/PinkhaKit Swift trees")
    require(policy.get("schema") == schema
            and policy.get("source_sha") == key[1]
            and set(policy.get("unchanged_git_inputs", {})) == set(closure)
            and set(policy.get("receipts", {})) == receipt_roles
            and policy.get("native_tests_rerun") is False
            and policy.get("new_sdk_acceptance_granted") is False,
            "Unreviewed native ABI donor scope")
    return policy


def read_policy(root):
    profile = json.loads((root / "Tools/OriginalEditor/framework_profile.json").read_text())
    binding = profile.get("native_abi_donor", {})
    require(isinstance(binding, dict) and
            (binding.get("path"), binding.get("source_sha")) in {
                (POLICY, DONOR), (FRESH_POLICY, FRESH_DONOR), (WAVE1_POLICY, WAVE1_DONOR)},
            "Unreviewed exact native donor policy binding")
    relative = binding["path"]
    path = root / relative
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased native ABI donor policy")
    require(binding == {"path": relative, "sha256": sha(path), "source_sha": binding["source_sha"]}
            and git(root, "hash-object", "--", relative) == git(root, "rev-parse", "HEAD:" + relative),
            "Committed native ABI donor policy differs")
    return validate_policy(json.loads(path.read_text()), binding), path


def validate_reference(value, source, policy_sha):
    require(set(value) == {"schema", "status", "consumer_source_sha", "consumer_local_execution_sha256",
                           "policy_sha256", "donor_root", "new_sdk_acceptance_granted"}
            and value.get("schema") == SCHEMA
            and value.get("status") == "EVIDENCE_REFERENCE_ONLY_REQUIRES_VERIFICATION"
            and value.get("consumer_source_sha") == source["head_sha"]
            and value.get("consumer_local_execution_sha256")
                == source["execution_identity"]["local_execution_sha256"]
            and value.get("policy_sha256") == policy_sha
            and source["execution_identity"]["producer_kind"] == "local-mac"
            and value.get("new_sdk_acceptance_granted") is False,
            "Native donor reference is not owned by this exact current SDK execution")


def verify(root, path, digest, source, value=None):
    root, path = Path(root).resolve(), Path(path)
    require(path.is_file() and not path.is_symlink() and path.resolve() == path
            and path.is_relative_to(root / "build") and sha(path) == digest,
            "Exact owned native donor reference is required")
    value = json.loads(path.read_text()) if value is None else value
    policy, policy_path = read_policy(root)
    donor_sha = policy["source_sha"]
    validate_reference(value, source, sha(policy_path))
    require(git(root, "rev-parse", "HEAD") == source["head_sha"],
            "Consumer source changed during native donor admission")
    donor = Path(value["donor_root"])
    require(donor.is_absolute() and donor.resolve() == donor and donor != root
            and git(donor, "rev-parse", "HEAD") == donor_sha,
            "Native ABI donor is not its actual original checkout")
    for role, row in policy["receipts"].items():
        p = donor / row["path"]
        require(p.is_relative_to(donor / "build") and p.resolve() == p
                and p.is_file() and not p.is_symlink() and sha(p) == row["sha256"],
                "Historical donor receipt differs: " + role)
    observed = json.loads(subprocess.check_output(
        [sys.executable, "-I", "-B", "-c", ORIGINAL_VERIFY, str(donor), str(policy_path)],
        text=True, timeout=600))
    before, installation = observed["source"], observed["installation"]
    require(before["head_sha"] == installation["app_source_sha"] == donor_sha
            and installation["status"] == "PASS"
            and installation["full_sdk_accepted"] is False
            and installation["editor_ui_accepted"] is False,
            "Original ABI verification scope changed")
    qualification = json.loads((donor / policy["receipts"]["debug_qualification"]["path"]).read_text())
    require(qualification.get("status") == "ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS"
            and qualification.get("phase") == "COMPLETE"
            and qualification.get("source_sha") == donor_sha,
            "Original donor Debug qualification is not terminal actual acceptance")
    if donor_sha == FRESH_DONOR:
        require(installation.get("schema") == "otzaria.original-import-local-sdk-input/3"
                and qualification.get("execution_identity") == before["execution_identity"]
                and qualification.get("heart") == installation
                and qualification.get("shared_runtime_ownership", {}).get("status")
                    == "PASS_OBSERVED_SINGLE_SHARED_IMPLEMENTATIONS"
                and {row.get("language") for row in qualification.get("verified_runtime_observations", [])}
                    == {"en", "he"}
                and len(qualification.get("verified_runtime_observations", [])) == 2,
                "The fresh native ABI donor lost its exact schema3/compiler/runtime owner")
    if donor_sha == WAVE1_DONOR:
        ownership = json.loads((donor / policy["receipts"]["shared_runtime_ownership"]["path"]).read_bytes())
        require(installation.get("schema") == "otzaria.original-saved-body-retained-abi/1"
                and qualification.get("execution_identity") == before["execution_identity"]
                and qualification.get("heart") == installation
                and {row.get("language") for row in qualification.get("verified_runtime_observations", [])}
                    == {"en", "he"}
                and len(qualification.get("verified_runtime_observations", [])) == 2
                and ownership.get("status") == "PASS_OBSERVED_SINGLE_SHARED_IMPLEMENTATIONS"
                and ownership.get("original_qualification_sha256")
                    == policy["receipts"]["debug_qualification"]["sha256"],
                "Wave 1 ABI donor lost its original source, runtime or shared ownership proof")
    trees = policy["unchanged_git_inputs"]
    reviewed_swift = policy.get("reviewed_swift_inputs", {})
    require(all(git(donor, "rev-parse", "HEAD:" + p) == expected
                for p, expected in {**trees, **reviewed_swift}.items()),
            "Original native donor source input closure changed")
    # The original Go mobile ABI does not compile application Swift. Permit
    # only the separately committed/reviewed Swift continuation, never changes
    # to generated messages, native middleware, wrappers or resources. Exact
    # application/PinkhaKit Swift deltas are admitted separately, never as ABI tests.
    from framework_profile import read_manifest
    from generated_import_source import verify_generated_source
    current_source = verify_generated_source(root, read_manifest())
    require(current_source == source["generated_import_source"],
            "Current source observation differs during native donor admission")
    if donor_sha == WAVE1_DONOR:
        wave1 = current_source["annotation_exchange"]["miniapps"]["lifecycle_batch"]["native_files"].get("wave1_product")
        require(wave1 is not None and wave1.get("base_source") == WAVE1_DONOR
                and wave1.get("native_acceptance_reused_by_this_document") is False
                and wave1.get("sdk_compiler_and_runtime_acceptance")
                    == "NOT_GRANTED_BY_SOURCE_OBSERVATION",
                "Wave 1 native reuse requires exact separately admitted current product source")
        for relative, expected in reviewed_swift.items():
            changed = [name for name in wave1["all_changed_paths"] if name.startswith(relative + "/")]
            require(wave1["base_product_trees"].get(relative) == expected
                    and git(root, "rev-parse", "HEAD:" + relative)
                        == wave1["reviewed_product_trees"].get(relative)
                    and changed and all(name.endswith(".swift") for name in changed),
                    "Native reuse has an unreviewed application/PinkhaKit Swift delta: " + relative)
    for relative, expected in trees.items():
        actual = git(root, "rev-parse", "HEAD:" + relative)
        if relative == "Anytype/Sources" and actual != expected:
            continuation = current_source.get("annotation_exchange", {})
            require(donor_sha == DONOR and continuation.get("base_source") == DONOR
                    and continuation.get("native_acceptance_reused_by_this_document") is False
                    and continuation.get("sdk_compiler_and_runtime_acceptance")
                        == "NOT_GRANTED_BY_SOURCE_OBSERVATION"
                    and actual == continuation.get("reviewed_product_trees", {}).get(relative),
                    "Application Swift differs from its exact reviewed continuation")
        else:
            require(actual == expected,
                    "Current facade changed a native/generated/wrapper/resource input: " + relative)
    current_generated, old_generated = source["generated_import_source"], before["generated_import_source"]
    for key in ("generated_index_sha256", "source_adoption_sha256", "working_generated_files",
                "committed_generated_blobs", "postimage_source", "preimage_source"):
        require(current_generated[key] == old_generated[key],
                "Generated native ABI provenance differs: " + key)
    from import_abi_input import LIB, exact_file
    rows = installation["lib_files"]
    actual = sorted(p.relative_to(root).as_posix() for p in (root / LIB).rglob("*") if p.is_file())
    require(actual == sorted(row["path"] for row in rows)
            and not any(p.is_symlink() for p in (root / LIB).rglob("*")),
            "Current SDK installed native library membership differs")
    for row in rows:
        exact_file(root, row)
    return {"schema": SCHEMA, "status": "PASS", "receipt_sha256": digest,
            "app_source_sha": source["head_sha"], "producer_kind": "local-mac",
            "native_qualification": installation["native_qualification"], "lib_files": rows,
            "generated_files_verified": 733, "generated_files_written": 0,
            "full_sdk_accepted": False, "editor_ui_accepted": False,
            "pinned_wrapper": installation.get("pinned_wrapper"),
            "original_abi_producer_identity": before["execution_identity"],
            "abi_reuse": {"status": "EXACT_NATIVE_INPUT_AND_ARTIFACT_EQUIVALENCE",
                         "donor_source_sha": donor_sha, "donor_root": str(donor),
                         "donor_receipts": policy["receipts"], "unchanged_git_inputs": trees,
                         "separately_reviewed_swift_inputs": reviewed_swift,
                         "original_abi_installation": installation,
                         "native_tests_rerun": False, "new_sdk_acceptance_granted": False}}
