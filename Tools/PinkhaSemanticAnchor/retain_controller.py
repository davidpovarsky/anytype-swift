#!/usr/bin/env python3
"""Read the four original Python control results; never rerun them in native CI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re

import contract

PROOF = contract.ROOT / "docs/validation/20261122-semantic-anchor-native-candidate"
RECEIPT_SHA = "efc626987495241f6c923fe1044e5252ca88900bde99f8996f556c6a10feacd9"
LOG_SHA = "d745d364f0404d0103b9afe4448fcc7d7f217fbf274715feac464989ae4e1413"
METHODS = {
    "test_candidate_inventory_rejects_changed_source_extra_files_and_old_source_claims",
    "test_named_output_rejects_missing_repeated_skipped_and_unselected_cases",
    "test_original_five_are_source_bound_and_retained_without_execution",
    "test_selected_methods_are_exactly_the_new_native_declarations",
}


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
                     and current == receipt["source_before_sha256"] == receipt.get("source_after_sha256")
                     and receipt.get("source_stable") is True,
                     "Original controller source/input closure changed")
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
    return dict(status="PASS_RETAINED_CONTROLLER_AND_PURE_CONTRACT_CONTROLS",
                github_run_id=os.environ.get("GITHUB_RUN_ID"), github_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                original_controller_receipt_sha256=contract.digest(PROOF / "controller-controls.json"),
                original_controller_log_sha256=LOG_SHA, retained_controller_methods=sorted(METHODS),
                retained_pure_contract=retained_five, source_and_input_sha256=current,
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
