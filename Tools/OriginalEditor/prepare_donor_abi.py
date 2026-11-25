#!/usr/bin/env python3
"""Stage exact retained native bytes and verify the new SDK's donor reference."""
import argparse
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
from donor_abi_input import SCHEMA, read_policy, verify
from framework_profile import source_observation
from import_abi_input import LIB, exact_file
from local_execution import require, sha


def prepare(root, donor, evidence):
    root, donor, evidence = root.resolve(), donor.resolve(), evidence.resolve()
    require(root != donor and evidence.is_relative_to(root / "build")
            and not evidence.exists(), "Fresh owned donor staging evidence is required")
    policy, policy_path = read_policy(root)
    original_abi = donor / policy["receipts"]["abi"]["path"]
    require(sha(original_abi) == policy["receipts"]["abi"]["sha256"],
            "Original native ABI receipt bytes differ before staging")
    original = json.loads(original_abi.read_bytes())
    evidence.mkdir(parents=True)
    copied = []
    for row in original["lib_files"]:
        require(row["path"].startswith(LIB + "/"), "Unreviewed donor library member")
        source = exact_file(donor, row)
        destination = root / row["path"]
        require(destination.resolve() == destination and destination.is_relative_to(root) and not destination.is_symlink(),
                "Aliased native library destination")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            exact_file(root, row)
        else:
            shutil.copy2(source, destination)
            exact_file(root, row)
            copied.append(row["path"])
    before = source_observation(root)
    value = {"schema": SCHEMA, "status": "EVIDENCE_REFERENCE_ONLY_REQUIRES_VERIFICATION",
             "consumer_source_sha": before["head_sha"],
             "consumer_local_execution_sha256": before["execution_identity"]["local_execution_sha256"],
             "policy_sha256": sha(policy_path), "donor_root": str(donor),
             "new_sdk_acceptance_granted": False}
    receipt = evidence / "ABI_DONOR_INPUT.json"
    receipt.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    result = verify(root, receipt, sha(receipt), before)
    require(source_observation(root) == before, "Current SDK source changed during donor verification")
    (evidence / "consumer-source-before.json").write_text(json.dumps(before, sort_keys=True, indent=2) + "\n")
    (evidence / "VERIFIED_DONOR.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    summary = {"status": "PASS_EXACT_NATIVE_ABI_REUSE_ONLY_NEW_SDK_NOT_YET_ACCEPTED",
               "source_sha": before["head_sha"], "reference": str(receipt),
               "reference_sha256": sha(receipt), "original_source_sha": policy["source_sha"],
               "copied_member_count": len(copied), "verified_lib_members": len(original["lib_files"]),
               "native_tests_rerun": False, "new_sdk_acceptance_granted": False}
    (evidence / "RESULT.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary))
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(__doc__)
    for name in ("root", "donor", "evidence"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    prepare(a.root, a.donor, a.evidence)
