#!/usr/bin/env python3
"""Read the four original Python control results; never rerun them in native CI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re

import contract
import resume_native

PROOF = contract.ROOT / "docs/validation/20261122-semantic-anchor-native-candidate"
RECEIPT_SHA = "efc626987495241f6c923fe1044e5252ca88900bde99f8996f556c6a10feacd9"
LOG_SHA = "d745d364f0404d0103b9afe4448fcc7d7f217fbf274715feac464989ae4e1413"
METHODS = {
    "test_candidate_inventory_rejects_changed_source_extra_files_and_old_source_claims",
    "test_named_output_rejects_missing_repeated_skipped_and_unselected_cases",
    "test_original_five_are_source_bound_and_retained_without_execution",
    "test_selected_methods_are_exactly_the_new_native_declarations",
}
CONTINUATION_RECEIPT_SHA = "f295274c6b2903955e5f7712db49aab9af93da3424ad3dd6a4d2aea5959b97f5"
CONTINUATION_LOG_SHA = "c1c89c7b82df43c7e7f282020b4b7e605aec9a8d980daa6b1a1f6ce0e11941e4"
CONTINUATION_METHODS = {
    "test_exact_review_rejects_unreviewed_source_input_and_original_archive_bytes",
    "test_original_failure_retains_exact_seven_and_selects_only_missing_two",
    "test_partial_failure_and_original_run_cannot_be_relabelled_or_omit_cases",
}


def retained_continuation_controls():
    proof = contract.ROOT / resume_native.PROOF_REL
    path, log = proof / "continuation-controls.json", proof / "continuation-controls.log"
    contract.require(contract.digest(path) == CONTINUATION_RECEIPT_SHA and contract.digest(log) == CONTINUATION_LOG_SHA,
                     "Original three continuation-control records changed")
    value = contract.load(path)
    source = value.get("source_before_sha256", {})
    contract.require(value.get("status") == "PASS_NEW_CONTINUATION_CONTROLS_ONLY" and value.get("exit_code") == 0
                     and value.get("expected_methods") == 3 and value.get("source_stable") is True
                     and value.get("source_after_sha256") == source
                     and {name: contract.digest(contract.ROOT / name) for name in source} == source
                     and value.get("log_sha256") == CONTINUATION_LOG_SHA
                     and value.get("native_methods_executed") == value.get("prior_python_methods_rerun") == value.get("prior_portable_methods_rerun") == 0,
                     "Executed continuation source/input closure or scope changed")
    output = log.read_text(encoding="utf8")
    passed = re.findall(r"^(test_\w+) \(test_resume_native\.NativeWitnessContinuationTests\.\1\) \.\.\. ok$",
                        output, re.MULTILINE)
    contract.require(len(passed) == 3 and set(passed) == CONTINUATION_METHODS
                     and re.search(r"^Ran 3 tests in [\d.]+s\n\nOK\n$", output, re.MULTILINE),
                     "Exact three original continuation controls did not pass")
    return dict(status="RETAINED_THREE_NEW_CONTINUATION_CONTROLS", methods=sorted(passed), methods_executed_again=0,
                original_receipt_sha256=CONTINUATION_RECEIPT_SHA, original_log_sha256=CONTINUATION_LOG_SHA,
                source_and_input_sha256=source)


def verify():
    contract.require(contract.digest(PROOF / "controller-controls.json") == RECEIPT_SHA,
                     "Original controller receipt changed")
    receipt = contract.load(PROOF / "controller-controls.json")
    log = PROOF / "controller-controls.log"
    contract.require(contract.digest(log) == receipt.get("log_sha256") == LOG_SHA,
                     "Original controller log changed")
    expected_paths = {"contract.py", "test_contract.py", "native-source.json"} | {
        "native/" + name for name in contract.SOURCE_PATHS} | {
        "retained-contract/semantic-contract-receipt.json", "retained-contract/semantic-contract-controls.jsonl"}
    current = {name: contract.digest(contract.HERE / name) for name in expected_paths}
    contract.require(set(receipt.get("source_before_sha256", {})) == expected_paths
                     and receipt["source_before_sha256"] == receipt.get("source_after_sha256")
                     and receipt.get("source_stable") is True,
                     "Original controller source/input closure changed")
    input_review = None
    if current != receipt["source_before_sha256"]:
        input_review = resume_native.reviewed_controller_inputs(receipt["source_before_sha256"], current)
    contract.require(receipt.get("status") == "PASS_CONTROLLER_CONTROLS_ONLY" and receipt.get("exit_code") == 0
                     and receipt.get("expected_test_methods") == 4 and receipt.get("native_methods_executed") == 0
                     and receipt.get("original_five_methods_rerun") == 0 and receipt.get("portable_swift_methods_rerun") == 0,
                     "Original controller result differs or overstates its scope")
    output = log.read_text(encoding="utf8")
    passed = re.findall(r"^(test_\w+) \(test_contract\.NativeSemanticControllerTests\.\1\) \.\.\. ok$",
                        output, re.MULTILINE)
    contract.require(len(passed) == 4 and set(passed) == METHODS
                     and re.search(r"^Ran 4 tests in [\d.]+s\n\nOK\n$", output, re.MULTILINE),
                     "Exact four original controller methods did not pass")
    contract.source_manifest()
    retained_five = contract.retained_contract()
    retained_three = retained_continuation_controls() if input_review is not None else None
    return dict(status="PASS_RETAINED_CONTROLLER_AND_PURE_CONTRACT_CONTROLS",
                github_run_id=os.environ.get("GITHUB_RUN_ID"), github_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                original_controller_receipt_sha256=contract.digest(PROOF / "controller-controls.json"),
                original_controller_log_sha256=LOG_SHA, retained_controller_methods=sorted(METHODS),
                retained_pure_contract=retained_five, source_and_input_sha256=current,
                original_source_and_input_sha256=receipt["source_before_sha256"], reviewed_input_changes=input_review,
                retained_continuation_controls=retained_three,
                controller_methods_rerun=0, pure_contract_methods_rerun=0,
                native_component_storage_methods_executed=0, verifier_sha256=contract.digest(Path(__file__)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    value = verify()
    contract.save(args.output, value)
    print(value["status"])


if __name__ == "__main__":
    main()
