#!/usr/bin/env python3
"""Verify the retained first registration artifact without running native code."""
import collections
import hashlib
import json
from pathlib import Path
import sys
import zipfile

BASE = Path(__file__).resolve().parent
ARCHIVE_SHA = "50ac79ce2728afa86feeff3c86ead0bdf21f9fec7ace16a743f6a451370c74ee"
HEAD = "60b8300c3506e53638c8ca883f82484de073fae8"
MANIFEST_SHA = "f3d2fd65b109fc67602318ff8e0e51c79b4295eae535a2d7ed3153e19ef0c36f"
PARENT = "TestOtzariaAnnotationSchemaRegistration"
FAILED = PARENT + "/MissingAttachmentUsesOneNativeApply"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify(archive, manifest_path):
    raw = archive.read_bytes()
    assert len(raw) == 3860363 and sha(raw) == ARCHIVE_SHA
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        assert all("/" not in n and "\\" not in n and n not in (".", "..") for n in z.namelist())
        files = {name: z.read(name) for name in z.namelist()}
    index = json.loads(files["EVIDENCE_INDEX.json"])
    assert len(index["files"]) == 44
    assert set(files) == {e["path"] for e in index["files"]} | {"EVIDENCE_INDEX.json"}
    for entry in index["files"]:
        data = files[entry["path"]]
        assert len(data) == entry["bytes"] and sha(data) == entry["sha256"]
    manifest_data = manifest_path.read_bytes()
    assert sha(manifest_data) == MANIFEST_SHA
    manifest = json.loads(manifest_data)
    result = json.loads(files["RESULT.json"])
    assert result["control_head"] == HEAD and result["execution_manifest_sha256"] == MANIFEST_SHA
    assert result["status"] == "FAIL" and result["owned_disposable_temp_removed"] is True
    assert result["post_execution_source_recheck"] is True and result["native_library_inputs_unchanged"] is True
    assert result["gofmt"]["source_equality"] is True
    expected_inputs = manifest["unchanged_composed_baseline_inputs"] + manifest["new_product_sources"] + manifest["new_test_sources"]
    expected = {e["path"]: (e["sha256"], e["bytes"]) for e in expected_inputs}
    actual = {e["path"]: (e["sha256"], e["bytes"]) for e in result["composed_product_and_test_inputs"]}
    assert len(expected) == len(actual) == 19 and actual == expected
    assert result["baseline_inputs_unchanged"] == manifest["unchanged_composed_baseline_inputs"]
    closure = json.loads(files["DECLARED_NATIVE_INPUTS.json"])
    assert len(closure["required_product_test_coverage"]) == 19
    assert {e["path"]: e["sha256"] for e in closure["required_product_test_coverage"]} == {p: v[0] for p, v in expected.items()}
    assert sha(files["DECLARED_NATIVE_INPUTS.json"]) == result["declared_native_inputs_sha256"]
    commands = json.loads(files["COMMANDS.json"])
    assert len(commands) == 18
    assert all(c["timed_out"] is False for c in commands)
    assert all(c["returncode"] == c["effective_returncode"] == 0 for c in commands[:-1])
    assert commands[-1]["label"] == "run-native" and commands[-1]["returncode"] == commands[-1]["effective_returncode"] == 1
    for c in commands:
        for stream in ("stdout", "stderr"):
            assert sha(files[c[stream]]) == c[stream + "_sha256"]
    native = result["tests"]["native"]
    assert native["compiled"] is True and native["execution_started"] is True and native["binary_unchanged"] is True
    assert native["binary_sha256_before"] == native["binary_sha256_after"]
    wanted = [PARENT] + [PARENT + "/" + case for case in manifest["expected_cases"]["native"]]
    starts, terminal, package_terminal = [], {}, []
    failures = []
    for line in files[commands[-1]["stdout"]].decode().splitlines():
        e = json.loads(line)
        name, action = e.get("Test"), e.get("Action")
        if not name:
            if action in ("pass", "fail", "skip"):
                package_terminal.append(action)
            continue
        assert name in wanted
        if action == "run":
            starts.append(name)
        if action in ("pass", "fail", "skip"):
            assert name not in terminal
            terminal[name] = action
        if name == FAILED and "loaded type differs from complete persisted native state" in e.get("Output", ""):
            failures.append(e)
    assert sorted(starts) == sorted(wanted) and len(starts) == 14
    expected_terminal = {name: ("fail" if name in (PARENT, FAILED) else "pass") for name in wanted}
    assert terminal == expected_terminal == native["terminal"] and package_terminal == ["fail"]
    assert len(failures) == 2
    report = json.loads(files["annotation-schema-readback.json"])
    phases = json.loads(files["annotation-schema-registration-phases.json"])
    assert report["process_id"] == phases["process_id"] == result["schema_readback"]["reported_native_process_id"]
    assert report["disposition"] == "MATCHING_SCHEMA_OBSERVED" and len(report["definitions"]) == 18
    ids = {e["object_id"] for e in report["definitions"]}
    assert len(ids) == 18 and all(e["space_id"] == report["space_id"] and e["account_identity"] == report["account_identity"] for e in report["definitions"])
    invoked = [c for p in phases["calls"] for c in (p.get("creations") or []) if c["invoked"]]
    assert len(phases["calls"]) == 4 and len(invoked) == 18
    assert {c["fixed_id"] for c in invoked} == ids and all(c["returned_id"] == c["fixed_id"] for c in invoked)
    assert sum(p["type_apply_invoked"] for p in phases["calls"]) == 1
    assert sum(p["type_apply_returned"] for p in phases["calls"]) == 1
    return {
        "status": "VERIFIED_ACTUAL_12_PASS_1_FAIL",
        "source": HEAD, "run_id": 45038140322, "attempt": 1,
        "artifact_id": 14760254250, "artifact_bytes": len(raw), "artifact_sha256": ARCHIVE_SHA,
        "payloads_verified": len(index["files"]), "native_compile": "PASS",
        "native_cases": dict(collections.Counter(v for k, v in terminal.items() if k != PARENT)),
        "case_results": {k.split("/", 1)[1]: v for k, v in terminal.items() if k != PARENT},
        "first_failure": "MissingAttachmentUsesOneNativeApply refused before repair Apply because complete loaded type differed from strict persisted native state. The original artifact has no complete paired loaded/persisted snapshot for that point; cause is not yet established.",
        "failed_case_events": failures,
        "positive_registration": {"actual_native_definitions": 18, "unique_original_creates": 18, "type_applies": 1, "explicit_phases": 4, "reported_native_pid": report["process_id"]},
        "composed_inputs_verified": 19, "old_composed_inputs_preserved": 13,
        "declared_input_count": len(closure["files"]),
        "source_format_equality": True, "post_execution_source_recheck": True,
        "owned_disposable_temp_removed": True, "native_command_seconds": commands[-1]["duration_seconds"],
        "binary_scope": "Runner-observed executable hashes/PID; executable bytes are absent from the artifact and were not independently rehashed.",
        "scope": "Exact original native registration controls. Twelve passing children are preserved; the remaining repair failure is unresolved. No Swift/RPC, ordinary annotation create, body/map authority or ACK acceptance.",
    }


if __name__ == "__main__":
    archive = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE / "Heart_Annotation_Registration_45038140322.zip"
    manifest = Path(sys.argv[2]) if len(sys.argv) > 2 else BASE / "candidate/EXECUTION_INPUTS.json"
    receipt = verify(archive, manifest)
    target = BASE / "VERIFIED_FIRST_RESULT.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("status", "artifact_sha256", "payloads_verified", "native_compile", "native_cases", "composed_inputs_verified", "old_composed_inputs_preserved")}))
