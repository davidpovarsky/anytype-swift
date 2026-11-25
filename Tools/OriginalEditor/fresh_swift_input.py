"""Admit one freshly executed original Swift gate without relabeling history.

The legacy generation/Swift proof path is unchanged. This additional route binds
the real local execution, its original driver/pin, all raw indexed evidence and
all successful command groups. It grants neither native ABI nor editor UI credit.
"""
import json

from local_execution import require
from reused_abi_history import HISTORICAL_SHA256

CONTROL = "fc4a84f68d26bcf36a8662367d08475b4024824a"
CONTROL_TREE = "8b16ac0ebddd56293aa30f566cd5e642641ea818"
EXECUTION_ID = "local-580a9308-fd9a-4dc7-a2a5-aab8e73205a2"
FRESH_SHA256 = {
    "execution": "73ee9eecbf04882d4cb8803adf838ae8bd7a157dbada5bda65c4589d7e74f28e",
    "controller": "8cc9520b65a09190a93916576515feaec0c1e819afd78811650b4706d142716c",
    "evidence_index": "c51e53500db9ac57ccde6643f9f812f958f5e443616bfd1614d4212e98b9cf32",
    "source_driver": "f175c2a9b0b9bdeec45c3495d2286d832cce02574b1d1a4475590861d551bfa6",
    "source_pin": "69d95e6dfa9cc09d3162c7f110fe75df1362e7da9775c96179fed4a526388423",
}
RESULT_SHA256 = "207aaabf0840383ad19453ab68e34ebc9c892f1aa0f8cae962dae23023894e5f"
SWIFT_DRIVER_SHA256 = "84b410d8143298f90ab0b721d488dab90e2fdbf23577ae6186162832a1155cb7"
PRIMARIES = [
    "Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Annotation.Import.swift",
    "Modules/ProtobufMessages/Sources/Loc/Generated/Error+Localization.swift",
]
LABELS = [
    "actual-generation-run", "actual-generation-artifact", "download-actual-generation",
    "actual-xcode-version", "actual-swiftc-path", "actual-macos-sdk-root",
    "actual-macos-sdk-version", "actual-swift-target-context",
    "actual-swift-frontend-path", "typecheck-changed-original-swift-with-sdk",
]


def qualify(base, history_rows, fresh_row, exact_file):
    require(set(history_rows) == {"generation", "generation_tools", "generated_index"},
            "Fresh Swift admission must retain the three original generation receipts")
    history = {}
    for name, row in history_rows.items():
        require(row["sha256"] == HISTORICAL_SHA256[name],
                "Original generation receipt identity differs: " + name)
        history[name] = json.loads(exact_file(base, row).read_bytes())
    manifest_path = exact_file(base, fresh_row)
    manifest = json.loads(manifest_path.read_bytes())
    require(manifest.get("schema") == "otzaria.local-changed-swift-original-execution/1"
            and set(manifest.get("files", {})) == set(FRESH_SHA256),
            "A separately identified complete original Swift execution is required")
    paths = {}
    for name, digest in FRESH_SHA256.items():
        row = manifest["files"][name]
        require(row["sha256"] == digest, "Fresh original Swift input identity differs: " + name)
        paths[name] = exact_file(manifest_path.parent, row)
    execution = json.loads(paths["execution"].read_bytes())
    controller = json.loads(paths["controller"].read_bytes())
    require(execution.get("schema") == "otzaria.changed-swift-local-execution/1"
            and execution.get("execution_origin") == "local-mac"
            and execution.get("github_run_id") is None
            and execution.get("execution_id") == EXECUTION_ID
            and execution.get("control_head") == CONTROL
            and execution.get("control_tree") == CONTROL_TREE,
            "Fresh Swift execution/source identity differs")
    require(controller.get("status") == "PASS" and controller.get("returncode") == 0
            and controller.get("execution_id") == EXECUTION_ID
            and controller.get("original_source_unchanged") is True
            and controller.get("raw_result_sha256") == RESULT_SHA256,
            "The actual original Swift controller did not close successfully")
    evidence = paths["evidence_index"].parent
    index = json.loads(paths["evidence_index"].read_bytes())
    inventory = {}
    for row in index["files"]:
        require(row["path"] not in inventory, "Repeated original Swift evidence")
        exact_file(evidence, row)
        inventory[row["path"]] = row
    actual = {p.relative_to(evidence).as_posix() for p in evidence.rglob("*") if p.is_file()}
    require(actual == set(inventory) | {paths["evidence_index"].name},
            "Original Swift evidence has missing or unrecorded members")
    require(inventory["RESULT.json"]["sha256"] == RESULT_SHA256
            and inventory["AUTHENTICATED_GENERATION.json"]["sha256"] == HISTORICAL_SHA256["generation"],
            "Fresh Swift result/generation binding differs")
    swift = json.loads((evidence / "RESULT.json").read_bytes())
    require(swift.get("schema") == "otzaria.original-import-rpc-changed-swift-sdk-typecheck/1"
            and swift.get("status") == "PASS" and swift.get("changed_swift_primary_typecheck") == "PASS"
            and swift.get("control_head") == CONTROL
            and swift.get("pin_sha256") == FRESH_SHA256["source_pin"]
            and swift.get("actual_input_files") == 689 and swift.get("primary_paths") == PRIMARIES
            and swift.get("swift_typecheck_invocations") == 1
            and swift.get("generator_invocations") == 0 and swift.get("dependency_builds") == 0
            and swift.get("native_tests") == 0 and swift.get("mobile_abi_built") is False
            and swift.get("full_sdk_typechecked") is False
            and swift.get("post_input_stability") == "PASS"
            and swift.get("owned_command_groups_drained") is True
            and swift.get("owned_work_removed") is True,
            "Fresh original Swift qualification scope/result differs")
    commands = json.loads((evidence / "COMMANDS.json").read_bytes())
    require([item["label"] for item in commands] == LABELS
            and swift.get("commands") == len(commands), "Original Swift command closure differs")
    for item in commands:
        require(item["returncode"] == 0 and item["effective_returncode"] == 0
                and item["status"] == "TERMINAL" and item["timed_out"] is False
                and item["start_new_session"] is True
                and any(part.get("drained") is True for part in item["cleanup"]),
                "An original Swift command did not pass and drain")
        for stream in ("stdout", "stderr"):
            require(item[stream] in inventory
                    and inventory[item[stream]]["sha256"] == item[stream + "_sha256"],
                    "An original Swift command stream lost its identity")
    actual_inputs = json.loads((evidence / "ACTUAL_SWIFT_TYPECHECK_INPUTS.json").read_bytes())
    require(len(actual_inputs["files"]) == 689 and actual_inputs["primary_paths"] == PRIMARIES
            and len(actual_inputs["module_files"]) == 3
            and actual_inputs["generated_index_sha256"] == HISTORICAL_SHA256["generated_index"],
            "Actual original Swift input/module closure differs")
    context = json.loads((evidence / "ACTUAL_SWIFT_COMPILER_CONTEXT.json").read_bytes())
    require(context == swift["actual_compiler_context"]
            and context["compiler_driver"]["sha256"] == SWIFT_DRIVER_SHA256
            and context["frontend"]["sha256"] == SWIFT_DRIVER_SHA256
            and context["sdk_version"] == "27.0"
            and (evidence / "04-actual-xcode-version.stdout").read_text().strip()
                == "Xcode 27.0\nBuild version 27A266a",
            "Fresh original Apple compiler/SDK context differs")
    generation = history["generation"]
    require(generation["aggregate_outcome_preserved"] == "FAIL at missing-SDK Swift invocation"
            and generation["result"]["status"] == "FAIL"
            and generation["all_744_outputs_stable"] is True
            and generation["result"]["native_source_tree"] == swift["generated_native_tree"]
            and swift["generated_index_sha256"] == HISTORICAL_SHA256["generated_index"]
            and swift["generation_run"] == 45261979047
            and swift["generation_source"] == "af96f761efe2cb4d92f5296fec85a152fd3aef17"
            and swift["generation_artifact_sha256"]
                == "1b8b5beda8e28322bc10ecebb37007b400aff2f17fa27c1e1dfc854f4c5eab2c",
            "Historical generator failure/output identity must remain unchanged")
    counts = {name: len(rows) for name, rows in history["generated_index"].items()}
    require(counts == {"native": 11, "swift": 696, "middleware": 37},
            "Original generated output counts differ")
    go = [item for item in history["generation_tools"]["tools"] if item["path"] == "go"]
    require(len(go) == 1, "Qualified original Go compiler identity is ambiguous")
    return {
        "generation_qualification": {
            "status": "PASS", "output_counts": counts, "aggregate_producer_outcome": "FAIL",
            "generators_replayed_by_abi": 0,
            "generated_index_sha256": HISTORICAL_SHA256["generated_index"],
            "native_generated_tree": swift["generated_native_tree"], "go_compiler_driver": go[0],
            "source_receipt_sha256": HISTORICAL_SHA256["generation"],
            "artifact_sha256": swift["generation_artifact_sha256"],
            "source_sha": swift["generation_source"], "run_id": swift["generation_run"],
        },
        "changed_swift_qualification": {
            "status": "PASS", "primary_count": 2, "input_files": 689, "typecheck_invocations": 1,
            "generated_index_sha256": HISTORICAL_SHA256["generated_index"],
            "generation_replayed": False, "full_sdk_typechecked": False,
            "actual_compiler_context": context, "source_receipt_sha256": RESULT_SHA256,
            "execution_origin": "local-mac", "github_run_id": None,
            "local_execution": execution, "local_execution_sha256": FRESH_SHA256["execution"],
            "original_control_source": CONTROL, "raw_evidence_index_sha256": FRESH_SHA256["evidence_index"],
            "owned_command_groups_drained": True, "historical_missing_receipts_replaced": False,
        },
    }


def copy_evidence(base, fresh_row, target, exact_file, reference):
    """Copy verified fresh raw evidence for independently portable ABI admission."""
    import shutil
    manifest_path = exact_file(base, fresh_row)
    source = manifest_path.parent
    manifest = json.loads(manifest_path.read_bytes())
    target.mkdir(parents=True, exist_ok=False)
    for name, row in manifest["files"].items():
        original = exact_file(source, row)
        destination = target / row["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        if name == "evidence_index":
            index = json.loads(original.read_bytes())
            for item in index["files"]:
                raw = exact_file(original.parent, item)
                copy = destination.parent / item["path"]
                copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(raw, copy)
    copied = target / manifest_path.name
    shutil.copyfile(manifest_path, copied)
    return reference(copied, target.parent)
