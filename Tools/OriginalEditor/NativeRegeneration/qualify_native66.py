"""Qualify freshly executed original native controls, retaining every raw receipt."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess

CONTROL = "c7e9935eb36a47f73d04cf72ea45472d3f2a8a70"
MANIFEST = "42ce77f47c67d5495b19355fe1ab8c263d6c5d1c57546f7e415c3c21698e788c"
NATIVE_TREE = "4b1ce2b7629974eb2bff91155f66b03122548aa6"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(root, name):
    path = root / name
    require(path.is_file() and not path.is_symlink() and path.resolve() == path,
            "Missing or aliased original evidence: " + name)
    return json.loads(path.read_bytes())


def passed(count):
    return {"passes": count, "failures": 0, "skipped": 0, "not_run": 0}


def leaves(value, expected):
    require(value["leaf_pass"] == expected and value["leaf_fail"] == 0
            and value["leaf_skip"] == 0 and value["leaf_not_run"] == 0,
            "The actual native leaf counts are incomplete")
    return passed(expected)


def qualify(evidence, heart):
    evidence, heart = Path(evidence), Path(heart)
    require(evidence.is_absolute() and evidence.resolve() == evidence
            and heart.is_absolute() and heart.resolve() == heart,
            "Native qualification roots are aliased")
    original = read(evidence, "RESULT.json")
    require(original["status"] == "PASS_ORIGINAL_NATIVE_CLOSED_ANNOTATION_QUALIFICATION_ONLY"
            and original["control_head"] == CONTROL
            and original["execution_manifest_sha256"] == MANIFEST
            and original["native_all_new_cases_passed"] is True
            and original["owned_command_groups_drained"] is True
            and original["owned_native_temporary_removed"] is True,
            "A complete fresh original native execution is required")
    require(all(original[name] is False for name in
                ("diagnostic_only", "historical_selectors_replayed",
                 "production_import_activated", "swift_invocation_qualified",
                 "cold_reopen_qualified", "body_ack_authority")),
            "Original native scope cannot grant SDK or application acceptance")
    index = read(evidence, "EVIDENCE_INDEX.json")
    inventory = {}
    for row in index["files"]:
        relative = PurePosixPath(row["path"])
        require(not relative.is_absolute() and ".." not in relative.parts
                and str(relative) == row["path"] and row["path"] not in inventory,
                "Invalid or repeated evidence member")
        path = evidence / row["path"]
        require(path.resolve() == path and path.is_file() and not path.is_symlink()
                and path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                "Original evidence bytes changed: " + row["path"])
        inventory[row["path"]] = row
    actual = {p.relative_to(evidence).as_posix() for p in evidence.rglob("*") if p.is_file()}
    require(actual == set(inventory) | {"EVIDENCE_INDEX.json"},
            "Unrecorded or missing native evidence")
    commands = read(evidence, "COMMANDS.json")
    require(original["commands"] == len(commands) == 37, "Original command closure differs")
    for item in commands:
        require(item["status"] == "TERMINAL" and item["returncode"] == 0
                and item["effective_returncode"] == 0 and item["timed_out"] is False
                and any(c.get("drained") is True for c in item["cleanup"]),
                "An original owned command did not pass and drain")
        for stream in ("stdout", "stderr"):
            require(item[stream] in inventory
                    and inventory[item[stream]]["sha256"] == item[stream + "_sha256"],
                    "An original compiler/test stream lost its hash binding")
    tree = read(evidence, "QUALIFIED_NATIVE_TREE.json")
    require(tree["canonical_union_tree"] == NATIVE_TREE
            and tree["approved_file_count"] == 112
            and subprocess.check_output(["git", "-C", str(heart), "write-tree"],
                                        text=True).strip() == NATIVE_TREE
            and not subprocess.check_output(["git", "-C", str(heart), "diff", "--name-only"]),
            "The fresh qualified original source tree changed")
    stability = original["post_execution_source_module_link_stability"]
    require(stability["status"] == "PASS" and stability["composed_native_files_checked"] == 112
            and stability["actual_link_inputs_checked"] is True
            and stability["actual_native_binary_checked"] is True
            and stability["actual_core_compile_only_binary_checked"] is True
            and stability["control_source_rechecked"] is True,
            "Native source/module/link stability is incomplete")
    counts = {"native9": leaves(original["native_cases"], 9)}
    for key, field, count in (
            ("schema_closure", "schema_closure_controls", 11),
            ("relation_target_closure", "relation_target_closure_controls", 12),
            ("imported_creation_date", "imported_creation_date_controls", 6),
            ("bounded_native_metadata", "bounded_native_metadata_controls", 12)):
        value = original[field]
        require(value["status"] == "PASS", "Native control group did not pass")
        counts[key] = leaves(value, count)
    semantic = original["bundled_persistence_semantic_control"]
    require(semantic["status"] == "PASS" and semantic["executed_this_run"] is True
            and semantic["previous_six_passes_reused"] is False and semantic["leaf_count"] == 6
            and len(semantic["cases"]) == 7
            and all(row["run_count"] == 1 and row["terminal_actions"] == ["pass"]
                    for row in semantic["cases"].values()),
            "The six original semantic cases were not freshly executed")
    counts["bundled_semantic"] = passed(6)
    rpc = original["rpc_union_controls"]
    require(rpc["status"] == "PASS" and rpc["shared_command_groups_drained"] is True
            and rpc["post_input_and_binary_stability"] == "PASS",
            "Fresh original RPC source/binary/drain proof is incomplete")
    for name, count in (("rpc9", 9), ("cancel_panic", 1)):
        require(rpc[name]["counts"] == passed(count)
                and len(rpc[name]["cases"]) == count
                and all(value == "PASS" for value in rpc[name]["cases"].values()),
                "Fresh original RPC cases are incomplete")
        counts[name] = passed(count)
    return {
        "schema": "otzaria.fresh-native-rpc-union-qualification/1", "status": "PASS",
        "counts": counts, "source_sha": CONTROL, "native_source_tree": NATIVE_TREE,
        "source_module_link_stability": "PASS", "owned_command_groups_drained": True,
        "execution_origin": "local-mac", "github_run_id": None,
        "original_control_source": CONTROL, "execution_manifest_sha256": MANIFEST,
        "raw_evidence_root": str(evidence), "raw_result_sha256": sha(evidence / "RESULT.json"),
        "raw_evidence_index_sha256": sha(evidence / "EVIDENCE_INDEX.json"),
        "verified_evidence_members": len(inventory), "verified_original_commands": len(commands),
        "full_sdk_accepted": False, "editor_ui_accepted": False,
        "historical_missing_receipts_replaced": False,
    }


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--heart", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "Preserve the existing qualification receipt")
    result = qualify(args.evidence, args.heart)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
