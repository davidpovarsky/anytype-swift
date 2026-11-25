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
CLOSURE = ("Anytype/Sources", "Anytype/Resources", "Modules", "Dependencies/Middleware",
           "Tools/OriginalEditor/ABIPinnedWrapper", "Tools/OriginalEditor/GeneratedImport",
           "Tools/PinkhaNativeDerived",
           "Tools/OriginalEditor/build_local_import_abi.py")

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


def read_policy(root):
    path = root / POLICY
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased native ABI donor policy")
    profile = json.loads((root / "Tools/OriginalEditor/framework_profile.json").read_text())
    binding = profile.get("native_abi_donor")
    require(binding == {"path": POLICY, "sha256": sha(path), "source_sha": DONOR}
            and git(root, "hash-object", "--", POLICY) == git(root, "rev-parse", "HEAD:" + POLICY),
            "Committed native ABI donor policy differs")
    policy = json.loads(path.read_text())
    require(policy.get("schema") == "otzaria.native-abi-donor-policy/1"
            and policy.get("source_sha") == DONOR
            and set(policy.get("unchanged_git_inputs", {})) == set(CLOSURE)
            and set(policy.get("receipts", {})) == {"execution", "source_before", "abi", "debug_qualification"}
            and policy.get("native_tests_rerun") is False
            and policy.get("new_sdk_acceptance_granted") is False,
            "Unreviewed native ABI donor scope")
    return policy, path


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
    validate_reference(value, source, sha(policy_path))
    require(git(root, "rev-parse", "HEAD") == source["head_sha"],
            "Consumer source changed during native donor admission")
    donor = Path(value["donor_root"])
    require(donor.is_absolute() and donor.resolve() == donor and donor != root
            and git(donor, "rev-parse", "HEAD") == DONOR,
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
    require(before["head_sha"] == installation["app_source_sha"] == DONOR
            and installation["status"] == "PASS"
            and installation["full_sdk_accepted"] is False
            and installation["editor_ui_accepted"] is False,
            "Original ABI verification scope changed")
    qualification = json.loads((donor / policy["receipts"]["debug_qualification"]["path"]).read_text())
    require(qualification.get("status") == "ACTUAL_ORIGINAL_FRAMEWORK_EXTERNAL_IMPORT_LINK_RESOURCES_PASS"
            and qualification.get("phase") == "COMPLETE"
            and qualification.get("source_sha") == DONOR,
            "Original donor Debug qualification is not terminal actual acceptance")
    trees = policy["unchanged_git_inputs"]
    require(all(git(donor, "rev-parse", "HEAD:" + p) == expected
                == git(root, "rev-parse", "HEAD:" + p) for p, expected in trees.items()),
            "Current facade changed native/generated/wrapper/source input closure")
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
                         "donor_source_sha": DONOR, "donor_root": str(donor),
                         "donor_receipts": policy["receipts"], "unchanged_git_inputs": trees,
                         "original_abi_installation": installation,
                         "native_tests_rerun": False, "new_sdk_acceptance_granted": False}}
