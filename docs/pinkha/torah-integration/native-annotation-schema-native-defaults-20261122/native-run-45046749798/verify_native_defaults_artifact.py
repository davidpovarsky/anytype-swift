#!/usr/bin/env python3
"""Check immutable native evidence only; never execute or normalize a native input."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import zipfile

BASE = Path(__file__).resolve().parent
PACKET = BASE / "semantic_fix_v1" if (BASE / "semantic_fix_v1").is_dir() else BASE.parent
DIAGNOSTIC = BASE / "diagnostic_v1" if (BASE / "diagnostic_v1").is_dir() else BASE.parent.parent / "native-annotation-schema-missing-attachment-20261122"
REGISTRATION = BASE / "candidate" if (BASE / "candidate").is_dir() else BASE.parent.parent / "native-annotation-schema-registration-20261122"
HEAD = "0896ae82864142e0b633278a8c5cb718ddf66e1e"
ARCHIVE_SHA = "3ac1d224746d3a466cf978798fc238eaec0c556ffd5ed4ae2f3fcb894a07210a"
MANIFEST_SHA = "af5e099142aa6f28b43ecf64e1fdbfb3c60a6293755074ba9f440cfd55417285"
PARENTS = {"semantics": "TestOtzariaAnnotationSchemaNativeBlockSemantics", "native": "TestOtzariaAnnotationSchemaRegistration"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rows(entries):
    values = {e["path"]: (e["sha256"], e["bytes"]) for e in entries}
    assert len(values) == len(entries)
    return values


def verify():
    data = (BASE / "Heart_Schema_Native_Defaults_45046749798.zip").read_bytes()
    assert len(data) == 3191815 and sha(data) == ARCHIVE_SHA
    with zipfile.ZipFile(BASE / "Heart_Schema_Native_Defaults_45046749798.zip") as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        assert all("/" not in n and "\\" not in n and n not in (".", "..") for n in z.namelist())
        files = {name: z.read(name) for name in z.namelist()}
    index = json.loads(files["EVIDENCE_INDEX.json"])
    assert len(index["files"]) == 54
    assert set(files) == {e["path"] for e in index["files"]} | {"EVIDENCE_INDEX.json"}
    for entry in index["files"]:
        raw = files[entry["path"]]
        assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
    manifest_bytes = (PACKET / "EXECUTION_INPUTS.json").read_bytes()
    assert sha(manifest_bytes) == MANIFEST_SHA
    manifest = json.loads(manifest_bytes)
    result = json.loads(files["RESULT.json"])
    assert result["control_head"] == HEAD and result["status"] == "PASS"
    assert result["repair_execution_manifest_sha256"] == MANIFEST_SHA
    assert result["diagnostic_execution_manifest_sha256"] == manifest["diagnostic_execution_manifest_sha256"]
    assert result["execution_manifest_sha256"] == manifest["registration_execution_manifest_sha256"]
    assert result["semantic_product_changes"] == 1 and result["diagnostic_only"] is False and result["ios_build"] is False
    for key in ("post_execution_source_recheck", "native_library_inputs_unchanged", "owned_disposable_temp_removed", "passed_registration_case_bodies_unchanged", "diagnostic_helper_and_case_unchanged"):
        assert result[key] is True
    assert result["gofmt"]["source_equality"] is True
    assert result["go"]["version"] == "go version go1.26.5 darwin/arm64"
    before = rows(manifest["diagnostic_composed_inputs"])
    assert len(before) == 20 and rows(result["diagnostic_inputs_verified_before_semantic_fix"]) == before
    expected = dict(before)
    expected.update(rows(manifest["product_afterimages"] + manifest["new_test_sources"]))
    assert len(expected) == 21 and rows(result["composed_product_and_test_inputs"]) == expected
    replaced = {e["path"] for e in manifest["product_afterimages"]}
    unchanged = {p: v for p, v in before.items() if p not in replaced}
    assert len(unchanged) == 19 and rows(result["diagnostic_inputs_unchanged"]) == unchanged
    for entry in manifest["control_inputs"]:
        raw = (PACKET / entry.get("retained_path", entry["path"])).read_bytes()
        assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
    diagnostic_bytes = (DIAGNOSTIC / "EXECUTION_INPUTS.json").read_bytes()
    assert sha(diagnostic_bytes) == manifest["diagnostic_execution_manifest_sha256"]
    diagnostic = json.loads(diagnostic_bytes)
    assert rows(result["registration_run_inputs_before_diagnostic"]) == rows(diagnostic["original_registration_run_inputs"])
    registration_bytes = (REGISTRATION / "EXECUTION_INPUTS.json").read_bytes()
    assert sha(registration_bytes) == manifest["registration_execution_manifest_sha256"]
    registration = json.loads(registration_bytes)
    assert result["baseline_inputs_unchanged"] == registration["unchanged_composed_baseline_inputs"]
    assert len(result["baseline_inputs_unchanged"]) == 13
    original_unchanged = {p: v for p, v in rows(diagnostic["original_registration_run_inputs"]).items() if p not in replaced and p not in {e["path"] for e in diagnostic["test_afterimages"]}}
    assert len(original_unchanged) == 17 and rows(result["registration_inputs_unchanged"]) == original_unchanged
    closure = json.loads(files["DECLARED_NATIVE_INPUTS.json"])
    assert len(closure["required_product_test_coverage"]) == 21
    assert {e["path"]: e["sha256"] for e in closure["required_product_test_coverage"]} == {p: v[0] for p, v in expected.items()}
    assert sha(files["DECLARED_NATIVE_INPUTS.json"]) == result["declared_native_inputs_sha256"]
    assert len(closure["files"]) == result["declared_native_input_count"] == 11332
    commands = json.loads(files["COMMANDS.json"])
    assert len(commands) == result["commands"] == 21
    assert len({c["label"] for c in commands}) == 21
    for command in commands:
        assert command["status"] == "TERMINAL" and not command["timed_out"]
        assert command["returncode"] == command["effective_returncode"] == 0
        assert command["start_new_session"] is True
        assert command["cleanup"][-1]["drained"] is True
        for stream in ("stdout", "stderr"):
            assert sha(files[command[stream]]) == command[stream + "_sha256"]
    by_label = {c["label"]: c for c in commands}
    outcomes, native_phases = {}, []
    for lane, parent in PARENTS.items():
        native = result["tests"][lane]
        assert native["compiled"] and native["execution_started"] and native["binary_unchanged"] and native["pass"]
        assert native["binary_sha256_before"] == native["binary_sha256_after"]
        assert native["process_returncode"] == native["effective_returncode"] == 0 and not native["timed_out"]
        expected_names = [parent] + [parent + "/" + n for n in manifest["expected_cases"][lane]]
        started, terminal, package_terminal = [], {}, []
        events = [json.loads(line) for line in files[by_label["run-" + lane]["stdout"]].decode().splitlines()]
        for event in events:
            name, action = event.get("Test"), event.get("Action")
            if name:
                assert name in expected_names
                if action == "run": started.append(name)
                if action in ("pass", "fail", "skip"):
                    assert name not in terminal
                    terminal[name] = action
                if lane == "native" and "native registration phase=" in event.get("Output", ""):
                    native_phases.append(event)
            elif action in ("pass", "fail", "skip"):
                package_terminal.append(action)
        assert started == native["started"] == expected_names
        assert terminal == native["terminal"] == {n: "pass" for n in expected_names}
        assert package_terminal == native["package_terminal"] == ["pass"]
        assert native["unexpected"] == []
        outcomes[lane] = {"pass": len(expected_names) - 1, "fail": 0, "skip": 0, "compile_seconds": by_label["compile-" + lane]["duration_seconds"], "execution_seconds": by_label["run-" + lane]["duration_seconds"], "cases": expected_names[1:]}
    repair = [e for e in native_phases if "native_test.go:110:" in e["Output"]]
    assert len(repair) == 1 and "creates=0 apply=true returned=true disposition=MATCHING_SCHEMA_OBSERVED error=<nil>" in repair[0]["Output"]
    capture_rows, identity = [], None
    pairs = {}
    for stage in diagnostic["capture_stages"]:
        name = "missing-attachment-" + stage + ".json"
        pair = json.loads(files[name]); pairs[stage] = pair
        assert pair["stage"] == stage and pair["diagnostic_only"] is True
        scope = tuple(pair[k] for k in ("process_id", "account_identity", "space_id", "object_id", "acl_id", "acl_head", "archive_id"))
        identity = scope if identity is None else identity
        assert scope == identity and pair["process_id"] == 19085
        assert pair["object_id"] == pair["loaded_object_id"] == pair["native_object_id"]
        assert pair["space_id"] == pair["loaded_space_id"] == pair["native_space_id"]
        assert pair["expected_native_key"] == pair["loaded_native_key"] == "ot-pinkhatorahannotationv1"
        assert pair["native_disposition"] == 1 and pair["live"]["heads"] == pair["persisted"]["heads"]
        assert pair["details_equal"] is True and pair["blocks_equal"] is False
        assert pair["different_detail_keys"] in (None, []) and pair["different_block_ids"] == ["dataview"]
        for side in ("live", "persisted"):
            state = pair[side]
            assert sha(base64.b64decode(state["details_protobuf"], validate=True)) == state["details_sha256"]
            for block in state["blocks"]:
                assert sha(base64.b64decode(block["protobuf"], validate=True)) == block["sha256"]
        assert pair["live"]["details_json"] == pair["persisted"]["details_json"]
        live = {b["id"]: b for b in pair["live"]["blocks"]}
        persisted = {b["id"]: b for b in pair["persisted"]["blocks"]}
        assert len(live) == len(pair["live"]["blocks"]) == len(persisted) == len(pair["persisted"]["blocks"])
        assert live.keys() == persisted.keys()
        for block_id, block in live.items():
            actual = base64.b64decode(block["protobuf"], validate=True)
            saved = base64.b64decode(persisted[block_id]["protobuf"], validate=True)
            if block_id == "dataview":
                assert actual[:10] == saved[:10] == b"\x0a\x08dataview" and actual[10:12] == b"\x1a\x00"
                assert actual[:10] + actual[12:] == saved
                assert block["json"]["restrictions"] == {} and "restrictions" not in persisted[block_id]["json"]
                assert {k: v for k, v in block["json"].items() if k != "restrictions"} == persisted[block_id]["json"]
            else:
                assert actual == saved and block["json"] == persisted[block_id]["json"]
        capture_rows.append({"stage": stage, "path": name, "sha256": sha(files[name]), "heads_equal": True, "details_equal_native": True, "blocks_equal_native": False, "sole_wire_difference": "dataview top-level Restrictions empty message 1a00 present only in loaded state", "all_remaining_block_bytes_identical": True})
    before_pair, after_pair = pairs["04-before-registration-attempt"], pairs["05-after-registration-attempt"]
    assert before_pair["persisted"]["heads"] != after_pair["persisted"]["heads"]
    # Cross-check the actual declared repair delta on copies of decoded evidence;
    # native acceptance remains the unchanged original full-protobuf assertions.
    before_details = copy.deepcopy(before_pair["persisted"]["details_json"])
    after_details = copy.deepcopy(after_pair["persisted"]["details_json"])
    hidden_before = before_details["fields"]["recommendedHiddenRelations"]["Kind"]["list_value"]["values"]
    hidden_after = after_details["fields"]["recommendedHiddenRelations"]["Kind"]["list_value"]["values"]
    assert hidden_after[:-1] == hidden_before and len(hidden_after) == len(hidden_before) + 1
    added_property_id = hidden_after.pop()["Kind"]["string_value"]
    assert before_details == after_details
    before_blocks = {b["id"]: copy.deepcopy(b["json"]) for b in before_pair["persisted"]["blocks"]}
    after_blocks = {b["id"]: copy.deepcopy(b["json"]) for b in after_pair["persisted"]["blocks"]}
    key = "pinkhaTorahAnnotationProtocol"
    dv = after_blocks["dataview"]["Content"]["dataview"]
    assert dv["relationLinks"].pop() == {"key": key}
    assert len(dv["views"]) == 2
    for view in dv["views"]:
        assert view["relations"].pop() == {"key": key, "width": 200}
    assert before_blocks == after_blocks
    assert result["diagnostic_capture"]["complete"] is True
    return {"status": "VERIFIED_ACTUAL_FIVE_PASS", "source": HEAD, "run_id": 45046749798, "attempt": 1, "artifact_id": 14764570821, "artifact_bytes": len(data), "artifact_sha256": ARCHIVE_SHA, "payloads_verified": 54, "commands_verified": 21, "all_owned_command_groups_drained": True, "composed_inputs_verified": 21, "unchanged_diagnostic_inputs": 19, "unchanged_registration_inputs": 17, "old_baseline_inputs_unchanged": 13, "native_registration_passes_preserved_not_replayed": 12, "outcomes": outcomes, "repair_phase": repair[0], "repair_added_property_id": added_property_id, "repair_delta": "One hidden property ID, one relation link and one hidden column in each of two preserved views; all remaining decoded persisted state identical, plus unchanged original full native protobuf preservation assertions PASS.", "captures": capture_rows, "semantic_scope": result["semantic_comparison_scope"], "decoder_limit": "Original generated Block and BlockRestrictions decoders discard unknown wire fields; all represented native state remains compared. No wire-equality or unknown-wire-retention claim.", "binary_scope": "Two compiled binary hashes are runner-observed before/after; executable bytes are excluded from uploaded evidence and have not been independently rehashed.", "owned_disposable_temp_removed": True, "open_scope": "Swift/RPC generation, generated compilation, native response/cancellation integration and production destination wiring remain separate gates. No body, lease or ACK acceptance."}


if __name__ == "__main__":
    result = verify()
    (BASE / "VERIFIED_SEMANTIC_RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "artifact_sha256", "payloads_verified", "commands_verified", "composed_inputs_verified", "outcomes")}))
