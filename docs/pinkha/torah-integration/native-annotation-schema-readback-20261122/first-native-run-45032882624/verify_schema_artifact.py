"""Read-only acceptance intake for the single reviewed native schema run."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import zipfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(archive, artifact_id, packet, output):
    source = "50543a6a3895fb10a03e69e6a39746847b4c7336"
    manifest_sha = "0ea7581ee2de14bbc31b7bb35f7b5650201bc60022956cfa07d1c43441b07178"
    manifest_bytes = (packet / "EXECUTION_INPUTS.json").read_bytes()
    assert sha(manifest_bytes) == manifest_sha
    manifest = json.loads(manifest_bytes)
    parent = "TestOtzariaAnnotationSchemaReadback"
    children = manifest["expected_cases"]["native"]
    expected = {parent, *(parent + "/" + child for child in children)}
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        names = zipped.namelist()
        assert len(names) == len(set(names))
        assert all(Path(name).name == name and name not in ("", ".", "..") for name in names)
        files = {name: zipped.read(name) for name in names}
    index = json.loads(files["EVIDENCE_INDEX.json"])
    assert set(files) == {entry["path"] for entry in index["files"]} | {"EVIDENCE_INDEX.json"}
    for entry in index["files"]:
        data = files[entry["path"]]
        assert len(data) == entry["bytes"] and sha(data) == entry["sha256"], entry["path"]
    result = json.loads(files["RESULT.json"])
    assert result["status"] == "PASS" and result["control_head"] == source
    assert result["heart_base"] == "d98420b1113536afd08cde6de9a5816f6d27ffff"
    assert result["execution_manifest_sha256"] == manifest_sha
    assert result["gofmt"]["source_equality"] is True
    assert result["post_execution_source_recheck"] is True
    assert result["native_library_inputs_unchanged"] is True
    assert result["owned_disposable_temp_removed"] is True
    commands = json.loads(files["COMMANDS.json"])
    assert len(commands) == 18 and len({row["label"] for row in commands}) == 18
    for row in commands:
        assert row["status"] == "TERMINAL" and row["returncode"] == row["effective_returncode"] == 0
        assert row["timed_out"] is False
        for stream in ("stdout", "stderr"):
            assert sha(files[row[stream]]) == row[stream + "_sha256"]
    run_command, = [row for row in commands if row["label"] == "run-native"]
    selection = "^" + re.escape(parent) + "$/^(" + "|".join(map(re.escape, children)) + ")$"
    assert "-test.run=" + selection in run_command["argv"]
    assert "-test.count=1" in run_command["argv"]
    events = [json.loads(line) for line in files[run_command["stdout"]].splitlines()]
    starts = [row["Test"] for row in events if row.get("Action") == "run" and row.get("Test")]
    terminals = [row for row in events if row.get("Action") in ("pass", "fail", "skip") and row.get("Test")]
    assert len(starts) == len(expected) and set(starts) == expected
    assert len(terminals) == len(expected) and {row["Test"] for row in terminals} == expected
    assert all(row["Action"] == "pass" for row in terminals)
    assert [row["Action"] for row in events if not row.get("Test") and row.get("Action") in ("pass", "fail", "skip")] == ["pass"]
    native = result["tests"]["native"]
    assert native["compiled"] and native["pass"] and native["binary_unchanged"]
    assert native["selection"] == selection and set(result["tests"]) == {"native"}
    report = json.loads(files["annotation-schema-readback.json"])
    assert report["schema"] == "otzaria-native-schema-readback/1"
    assert report["protocol"] == "pinkha.torah.annotation/1"
    assert report["disposition"] == "MATCHING_SCHEMA_OBSERVED"
    assert type(report["process_id"]) is int and report["process_id"] > 0
    entries = report["definitions"]
    keys = re.findall(r'\{"(pinkhaTorahAnnotation[^\"]+)",', (packet / "native/core/pinkha/annotationschema/definition.go").read_text())
    assert len(keys) == 17
    assert [entry["native_key"] for entry in entries] == ["ot-pinkhatorahannotationv1"] + ["rel-" + key for key in keys]
    assert len(entries) == len({entry["object_id"] for entry in entries}) == 18
    for entry in entries:
        assert entry["object_id"] and entry["space_id"] == report["space_id"]
        assert entry["account_identity"] == report["account_identity"]
        assert entry["disposition"] == 1 and entry["index"] == "ONE_MATCHING_LOCAL_INDEX_ROW"
        assert entry["persisted_heads"] and entry["acl_id"] and entry["acl_head"]
        assert entry["archive_id"] and entry["archive_heads"]
        assert base64.b64decode(entry["details_protobuf"], validate=True)
        assert all(base64.b64decode(block, validate=True) for block in entry["blocks_protobuf"])
    layout = report["type_layout"]
    assert layout["Disposition"] == "MATCHING_SCHEMA_OBSERVED"
    assert layout["Hidden"] is True and layout["DiscoveryHidden"] is True
    assert not layout["MissingRelationKeys"] and layout["ViewIDs"]
    assert {entry["object_id"] for entry in entries[1:]} <= set(layout["HiddenRelationIDs"])
    source_inputs = {entry["path"]: entry for entry in result["composed_product_and_test_inputs"]}
    assert len(source_inputs) == 13
    for entry in manifest["copyout_afterimages"] + manifest["new_product_sources"] + manifest["new_test_sources"]:
        assert source_inputs[entry["path"]]["sha256"] == entry["sha256"]
    declared = json.loads(files["DECLARED_NATIVE_INPUTS.json"])
    assert sha(files["DECLARED_NATIVE_INPUTS.json"]) == result["declared_native_inputs_sha256"]
    assert len(declared["files"]) == result["declared_native_input_count"]
    assert len(declared["required_product_test_coverage"]) == 13
    for entry in declared["required_product_test_coverage"]:
        assert source_inputs[entry["path"]]["sha256"] == entry["sha256"]
    summary = {
        "status": "VERIFIED_NINE_NEW_NATIVE_CASES_PASS",
        "run_id": 45032882624, "attempt": 1, "source_sha": source,
        "artifact_id": artifact_id, "artifact_sha256": sha(archive.read_bytes()),
        "artifact_bytes": archive.stat().st_size, "payloads_verified": len(index["files"]),
        "commands_verified": len(commands), "case_counts": {"pass": 9, "fail": 0, "skip": 0},
        "exact_child_events": [row for row in terminals if row["Test"] != parent],
        "prior_cases_replayed": 0, "native_definition_count": len(entries),
        "native_view_count": len(layout["ViewIDs"]),
        "reported_native_process_id": report["process_id"],
        "native_declared_input_count": result["declared_native_input_count"],
        "composed_product_and_test_inputs": result["composed_product_and_test_inputs"],
        "result_sha256": sha(files["RESULT.json"]), "native_log_sha256": sha(files[run_command["stdout"]]),
        "boundary": "Genuine disposable original Heart controls only. Report framing, exact source/selection and evidence hashes independently checked; original Go assertions own protobuf semantics. No production registration/recovery, Swift integration, body/mapping/COMMIT/ACK acceptance. Native binary hash and process ID remain runner observations; executable bytes are not uploaded."
    }
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--artifact-id", type=int, required=True)
    parser.add_argument("--packet", type=Path, default=Path(__file__).resolve().parent / "candidate")
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(json.dumps(verify(arguments.archive, arguments.artifact_id, arguments.packet, arguments.output)))
