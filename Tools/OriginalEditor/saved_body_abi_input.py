"""Admit the exact existing binary ABI for the source-verifier-only continuation."""
import json
from pathlib import Path

from local_execution import current_identity, git, require, sha

DONOR_SOURCE = "e973cc7432419778f0342624a3b7052055fd270d"
CONTINUATION = {
    "Tools/OriginalEditor/MiniApps/saved_body_focus_source_adoption.json",
    "Tools/OriginalEditor/framework_profile.json",
    "Tools/OriginalEditor/import_abi_input.py",
    "Tools/OriginalEditor/native_files_source.py",
    "Tools/OriginalEditor/saved_body_abi_input.py",
}
ABI_PATH = "build/ABI-Candidate-Evidence/ABI_INPUT.json"
DONOR_ABI_SHA256 = "f8c7cf6013d25adade460a2084ae2c7460d3dc968b1327ccebd17204856c1e67"
EXECUTION_PATH = "build/SDK-Page-Lifetime-Debug-Evidence/local-execution.json"


def verify(root, path, digest, source, value):
    from import_abi_input import exact_file, verify as verify_original_abi

    require(value.get("consumer_source_sha") == source["head_sha"] == git(root, "rev-parse", "HEAD")
            and value.get("consumer_execution_sha256") == source["execution_identity"]["local_execution_sha256"]
            and value.get("donor_source_sha") == DONOR_SOURCE
            and value.get("donor_abi_sha256") == DONOR_ABI_SHA256,
            "Retained ABI does not belong to this original source and execution")
    changed = set(git(root, "diff", "--name-only", DONOR_SOURCE, "HEAD").splitlines())
    require(changed == CONTINUATION and not git(root, "diff", "--name-only", "HEAD"),
            "Source-verifier continuation changed a binary compiler input")
    focus = source["generated_import_source"]["annotation_exchange"]["miniapps"]["lifecycle_batch"][
        "native_files"]["current_annotation_runtime"]["saved_body_focus"]
    require(focus["reviewed_source"] == DONOR_SOURCE and not focus["native_acceptance_reused_by_this_document"],
            "The current original saved-body focus source was not observed")

    donor = Path(value["donor_root"])
    require(donor.is_absolute() and donor == donor.resolve() and donor != root
            and git(donor, "rev-parse", "HEAD") == DONOR_SOURCE
            and not git(donor, "diff", "--name-only", "HEAD"),
            "Retained ABI producer original checkout differs")
    donor_receipt = donor / ABI_PATH
    execution = donor / EXECUTION_PATH
    identity = current_identity({
        "OTZARIA_LOCAL_EXECUTION": str(execution),
        "OTZARIA_LOCAL_EXECUTION_SHA256": sha(execution),
    })
    require(identity["source_sha"] == DONOR_SOURCE and identity["local_execution"]["root"] == str(donor)
            and not donor_receipt.is_symlink() and sha(donor_receipt) == DONOR_ABI_SHA256
            and json.loads(donor_receipt.read_bytes()).get("schema") == "otzaria.original-import-local-sdk-input/3",
            "Retained ABI raw source, execution or schema differs")
    verified = verify_original_abi(
        donor, donor_receipt, DONOR_ABI_SHA256,
        {"head_sha": DONOR_SOURCE, "execution_identity": identity},
    )
    for row in verified["lib_files"]:
        exact_file(root, row)
    return {**verified, "receipt_sha256": digest, "app_source_sha": source["head_sha"],
            "retained_abi_source_sha": DONOR_SOURCE, "retained_abi_receipt_sha256": DONOR_ABI_SHA256,
            "retained_abi_original_schema": verified["schema"],
            "schema": "otzaria.original-saved-body-retained-abi/1"}
