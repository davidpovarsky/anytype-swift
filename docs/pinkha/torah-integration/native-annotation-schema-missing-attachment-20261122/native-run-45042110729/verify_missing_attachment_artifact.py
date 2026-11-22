#!/usr/bin/env python3
"""Verify immutable diagnostic bytes; never execute native tests or alter a pair."""
import base64
import hashlib
import json
from pathlib import Path
import zipfile

BASE = Path(__file__).resolve().parent
DIAGNOSTIC_PACKET = BASE / "diagnostic_v1" if (BASE / "diagnostic_v1").is_dir() else BASE.parent
REGISTRATION_PACKET = BASE / "candidate" if (BASE / "candidate").is_dir() else BASE.parent.parent / "native-annotation-schema-registration-20261122"
ARCHIVE_SHA = "270b824b9c0210cd1cd584db0315215678bfa04c29c4251692527c57e403fd6e"
HEAD = "b93b7b351cfeb625607b5b7d86aef7c29fe78b0b"
MANIFEST_SHA = "0653a672d696f200e1333b163a6e6362262e46629e0d70346069607d68652744"
PARENT = "TestOtzariaAnnotationSchemaRegistration"
CHILD = PARENT + "/MissingAttachmentUsesOneNativeApply"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def rows(entries):
    result = {e["path"]: (e["sha256"], e["bytes"]) for e in entries}
    assert len(result) == len(entries)
    return result


def verify():
    archive = BASE / "Heart_Schema_Missing_Attachment_45042110729.zip"
    data = archive.read_bytes()
    assert len(data) == 2634204 and sha(data) == ARCHIVE_SHA
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        assert all("/" not in n and "\\" not in n and n not in (".", "..") for n in z.namelist())
        files = {name: z.read(name) for name in z.namelist()}
    index = json.loads(files["EVIDENCE_INDEX.json"])
    assert len(index["files"]) == 48
    assert set(files) == {e["path"] for e in index["files"]} | {"EVIDENCE_INDEX.json"}
    for entry in index["files"]:
        raw = files[entry["path"]]
        assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
    manifest_bytes = (DIAGNOSTIC_PACKET / "EXECUTION_INPUTS.json").read_bytes()
    assert sha(manifest_bytes) == MANIFEST_SHA
    manifest = json.loads(manifest_bytes)
    result = json.loads(files["RESULT.json"])
    assert result["control_head"] == HEAD
    assert result["diagnostic_execution_manifest_sha256"] == MANIFEST_SHA
    assert result["execution_manifest_sha256"] == manifest["registration_execution_manifest_sha256"]
    assert result["status"] == "FAIL" and result["diagnostic_only"] is True
    assert result["diagnostic_product_changes"] == 0
    for key in ("post_execution_source_recheck", "native_library_inputs_unchanged", "owned_disposable_temp_removed", "passed_registration_case_bodies_unchanged"):
        assert result[key] is True
    assert result["gofmt"]["source_equality"] is True
    before = rows(manifest["original_registration_run_inputs"])
    assert len(before) == 19 and rows(result["registration_run_inputs_before_diagnostic"]) == before
    expected = dict(before)
    expected.update(rows(manifest["test_afterimages"] + manifest["new_test_sources"]))
    assert len(expected) == 20 and rows(result["composed_product_and_test_inputs"]) == expected
    afterimage_paths = {e["path"] for e in manifest["test_afterimages"]}
    unchanged = {p: value for p, value in before.items() if p not in afterimage_paths}
    assert len(unchanged) == 18 and rows(result["registration_inputs_unchanged"]) == unchanged
    for entry in manifest["control_inputs"]:
        raw = (DIAGNOSTIC_PACKET / entry.get("retained_path", entry["path"])).read_bytes()
        assert len(raw) == entry["bytes"] and sha(raw) == entry["sha256"]
    baseline_manifest = json.loads((REGISTRATION_PACKET / "EXECUTION_INPUTS.json").read_bytes())
    assert result["baseline_inputs_unchanged"] == baseline_manifest["unchanged_composed_baseline_inputs"]
    closure = json.loads(files["DECLARED_NATIVE_INPUTS.json"])
    assert len(closure["required_product_test_coverage"]) == 20
    assert {e["path"]: e["sha256"] for e in closure["required_product_test_coverage"]} == {p: value[0] for p, value in expected.items()}
    assert sha(files["DECLARED_NATIVE_INPUTS.json"]) == result["declared_native_inputs_sha256"]
    commands = json.loads(files["COMMANDS.json"])
    assert len(commands) == 18
    assert all(not c["timed_out"] for c in commands)
    assert all(c["returncode"] == c["effective_returncode"] == 0 for c in commands[:-1])
    assert commands[-1]["label"] == "run-native" and commands[-1]["returncode"] == commands[-1]["effective_returncode"] == 1
    for command in commands:
        for stream in ("stdout", "stderr"):
            assert sha(files[command[stream]]) == command[stream + "_sha256"]
    native = result["tests"]["native"]
    assert native["compiled"] and native["execution_started"] and native["binary_unchanged"]
    assert native["binary_sha256_before"] == native["binary_sha256_after"]
    assert native["selection"] == "^TestOtzariaAnnotationSchemaRegistration$/^(MissingAttachmentUsesOneNativeApply)$"
    started, terminal, package_terminal, failures = [], {}, [], []
    for line in files[commands[-1]["stdout"]].decode().splitlines():
        event = json.loads(line)
        name, action = event.get("Test"), event.get("Action")
        if name:
            assert name in (PARENT, CHILD)
            if action == "run":
                started.append(name)
            if action in ("pass", "fail", "skip"):
                assert name not in terminal
                terminal[name] = action
            if name == CHILD and "loaded type differs from complete persisted native state" in event.get("Output", ""):
                failures.append(event)
        elif action in ("pass", "fail", "skip"):
            package_terminal.append(action)
    assert started == [PARENT, CHILD] and terminal == native["terminal"] == {PARENT: "fail", CHILD: "fail"}
    assert package_terminal == ["fail"] and len(failures) == 2
    assert "creates=0 apply=false returned=false" in failures[0]["Output"]
    capture_rows, scope = [], None
    for stage in manifest["capture_stages"]:
        name = "missing-attachment-" + stage + ".json"
        pair = json.loads(files[name])
        assert pair["stage"] == stage and pair["diagnostic_only"] is True
        identity = (pair["process_id"], pair["account_identity"], pair["space_id"], pair["object_id"], pair["acl_id"], pair["acl_head"], pair["archive_id"])
        scope = identity if scope is None else scope
        assert identity == scope and pair["process_id"] == 24081
        assert pair["object_id"] == pair["loaded_object_id"] == pair["native_object_id"]
        assert pair["space_id"] == pair["loaded_space_id"] == pair["native_space_id"]
        assert pair["expected_native_key"] == pair["loaded_native_key"] == "ot-pinkhatorahannotationv1"
        assert pair["native_disposition"] == 1
        assert pair["live"]["heads"] == pair["persisted"]["heads"]
        assert pair["details_equal"] is True and pair["blocks_equal"] is False
        assert not pair["different_detail_keys"] and pair["different_block_ids"] == ["dataview"]
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
                # Diagnostic byte localization only. Neither input nor the
                # native equality outcome is rewritten/normalized here.
                assert actual[:10] == saved[:10] == b"\x0a\x08dataview"
                assert actual[10:12] == b"\x1a\x00"
                assert actual[:10] + actual[12:] == saved
                assert block["json"]["restrictions"] == {} and "restrictions" not in persisted[block_id]["json"]
                assert {k: v for k, v in block["json"].items() if k != "restrictions"} == persisted[block_id]["json"]
            else:
                assert actual == saved and block["json"] == persisted[block_id]["json"]
        capture_rows.append({"stage": stage, "path": name, "sha256": sha(files[name]), "heads_equal": True, "details_equal_native": True, "blocks_equal_native": False, "sole_wire_difference": "dataview field 3 empty message (1a00) present only in loaded state", "all_remaining_block_bytes_identical": True})
    before_pair = json.loads(files["missing-attachment-04-before-registration-attempt.json"])
    after_pair = json.loads(files["missing-attachment-05-after-registration-attempt.json"])
    for side in ("live", "persisted"):
        assert before_pair[side]["heads"] == after_pair[side]["heads"]
        assert before_pair[side]["details_json"] == after_pair[side]["details_json"]
        assert before_pair[side]["blocks"] == after_pair[side]["blocks"]
    return {"status": "VERIFIED_ACTUAL_ONE_FAIL_WITH_SIX_COMPLETE_PAIRS", "source": HEAD, "run_id": 45042110729, "attempt": 1, "artifact_id": 14762199006, "artifact_bytes": len(data), "artifact_sha256": ARCHIVE_SHA, "payloads_verified": 48, "commands_verified": 18, "native_compile": "PASS", "compile_seconds": commands[-3]["duration_seconds"], "native_seconds": commands[-1]["duration_seconds"], "native_cases": {"fail": 1, "pass": 0, "skip": 0}, "composed_inputs_verified": 20, "unchanged_previous_inputs": 18, "old_baseline_inputs_unchanged": len(result["baseline_inputs_unchanged"]), "native_registration_passes_preserved_not_replayed": 12, "captures": capture_rows, "failed_case_events": failures, "diagnosis": "All six pairs have exactly one additional empty dataview Restrictions message in loaded state. This includes the initial post-registration pair. All other complete block wire bytes match, details compare equal under original native proto.Equal, and heads match. The repair is correctly refused under the frozen exact guard before any create or Apply.", "root_cause_scope": "Original live initialization/persistence semantics require source review before a bounded fix; no guard change or native acceptance follows from this diagnostic.", "binary_scope": native["binary_evidence_scope"], "owned_disposable_temp_removed": True}


if __name__ == "__main__":
    result = verify()
    (BASE / "VERIFIED_DIAGNOSTIC_RESULT.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "artifact_sha256", "payloads_verified", "commands_verified", "native_compile", "native_cases", "composed_inputs_verified", "unchanged_previous_inputs")}))
