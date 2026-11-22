#!/usr/bin/env python3
"""Read one frozen generation artifact without executing generated code."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

MANIFEST = "800c0745ddc36537c443e17f9d984c98a11fd22c4d825c4a935ffa4f8d264ee3"
PASS = "GENERATED_AND_MESSAGE_COMPILE_VERIFIED"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def delta(before, after):
    left = {row["path"]: row for row in before}
    right = {row["path"]: row for row in after}
    assert len(left) == len(before) and len(right) == len(after)
    return [{"path": path, "before": left.get(path), "after": right.get(path)}
            for path in sorted(left.keys() | right.keys()) if left.get(path) != right.get(path)]


def verify(archive, expected_size, expected_sha256, head, packet):
    raw_archive = archive.read_bytes()
    assert len(raw_archive) == expected_size and sha256(raw_archive) == expected_sha256
    manifest_raw = (packet / "EXECUTION_INPUTS.json").read_bytes()
    assert sha256(manifest_raw) == MANIFEST
    manifest = json.loads(manifest_raw)
    for row in manifest["control_inputs"]:
        raw = (packet / row["path"]).read_bytes()
        assert len(raw) == row["bytes"] and sha256(raw) == row["sha256"]
    with zipfile.ZipFile(archive) as source:
        infos = source.infolist()
        assert len(infos) == len({info.filename for info in infos})
        assert sum(info.file_size for info in infos) <= 512 * 1024 * 1024
        for info in infos:
            path = PurePosixPath(info.filename)
            assert not path.is_absolute() and ".." not in path.parts
            assert not any(":" in part or "\\" in part for part in path.parts)
            assert not stat.S_ISLNK(info.external_attr >> 16)
        assert source.testzip() is None
        files = {info.filename for info in infos if not info.is_dir()}
        index = json.loads(source.read("EVIDENCE_INDEX.json"))
        rows = {row["path"]: row for row in index["files"]}
        assert len(rows) == len(index["files"]) and files == rows.keys() | {"EVIDENCE_INDEX.json"}
        for path, row in rows.items():
            raw = source.read(path)
            assert len(raw) == row["bytes"] and sha256(raw) == row["sha256"]
            assert blob(raw) == row["git_blob"]

        def read_json(path):
            return json.loads(source.read(path))

        def check_copied_rows(items, prefix):
            assert len(items) == len({row["path"] for row in items})
            for row in items:
                payload = source.read(prefix + "/" + row["path"])
                assert len(payload) == row["bytes"] and sha256(payload) == row["sha256"]
                assert blob(payload) == row["git_blob"]

        result = read_json("RESULT.json")
        assert result["control_head"] == head and result["manifest_sha256"] == MANIFEST
        assert result["native_tests_executed"] == 0
        assert result["ios_build"] is False and result["full_sdk_typecheck"] is False
        assert result["integration_authority"] is False
        commands = read_json("COMMANDS.json") if "COMMANDS.json" in files else []
        assert result["commands"] == len(commands)
        assert len(commands) == len({row["label"] for row in commands})
        command_rows = []
        for command in commands:
            for stream in ("stdout", "stderr"):
                if stream + "_sha256" in command:
                    assert sha256(source.read(command[stream])) == command[stream + "_sha256"]
            started = command["pid"] is not None
            drained = any(row.get("drained") is True and row["event"] in
                          ("OWNED_GROUP_ABSENT_AFTER_WAIT", "OWNED_GROUP_DRAIN_RESULT")
                          for row in command["cleanup"])
            if started:
                assert command["start_new_session"] is True
                assert command["pid"] == command["process_group_id"]
            command_rows.append({"label": command["label"], "status": command["status"],
                                 "returncode": command["returncode"],
                                 "effective_returncode": command["effective_returncode"],
                                 "timed_out": command["timed_out"], "started": started,
                                 "owned_group_drain_recorded": drained})
        generated = read_json("GENERATED_OUTPUT_INDEX.json") if "GENERATED_OUTPUT_INDEX.json" in files else {}
        generated_counts = {}
        for lane, kinds in generated.items():
            generated_counts[lane] = {}
            for kind, items in kinds.items():
                check_copied_rows(items, "generated/" + lane + "/" + ("native" if kind == "native" else "swift"))
                generated_counts[lane][kind] = len(items)
        failure_counts = {}
        if "FAILURE_OUTPUT_INDEX.json" in files:
            failure = read_json("FAILURE_OUTPUT_INDEX.json")
            for lane, kinds in failure["lanes"].items():
                failure_counts[lane] = {}
                for kind, items in kinds.items():
                    if isinstance(items, list):
                        check_copied_rows(items, "failure-time/" + lane + "/" + kind)
                        failure_counts[lane][kind] = len(items)
                    else:
                        assert "capture_error" in items
                        failure_counts[lane][kind] = items
        verified_deltas = None
        if result["status"] == PASS:
            assert len(commands) == 41
            assert all(row["status"] == "TERMINAL" and row["returncode"] == 0 and
                       row["effective_returncode"] == 0 and not row["timed_out"] and
                       row["owned_group_drain_recorded"] for row in command_rows)
            labels = {row["label"]: row for row in commands}
            for lane in ("baseline", "candidate"):
                assert labels[lane + "-compile-generated-go"]["argv"] == ["go", "build", "./pb", "./pb/service"]
                assert labels[lane + "-typecheck-generated-swift"]["argv"][:3] == ["xcrun", "swiftc", "-typecheck"]
                for family in ("native", "swift"):
                    assert labels[lane + "-original-" + family + "-generation"]["argv"][:3] == ["make", "SHELL=/bin/bash", ".SHELLFLAGS=-e -o pipefail -c"]
            assert result["owned_command_groups_drained"] is True and result["owned_work_removed"] is True
            assert result["endpoint_invocation_and_sdk_compiled"] is False
            assert result["generated_outputs_require_review_before_integration"] is True
            original_inputs = read_json("ORIGINAL_GENERATOR_INPUTS.json")
            baseline_inputs = read_json("BASELINE_GENERATED_INPUTS.json")
            candidate_inputs = read_json("CANDIDATE_GENERATED_INPUTS.json")
            assert original_inputs == baseline_inputs
            assert original_inputs["swift"] == candidate_inputs["swift"]
            changes = delta(original_inputs["heart"], candidate_inputs["heart"])
            assert {row["path"]: (row["after"]["bytes"], row["after"]["sha256"]) for row in changes} == {
                row["path"]: (row["bytes"], row["sha256"]) for row in manifest["proto_afterimages"]}
            actual_delta = {kind: delta(generated["baseline"][kind], generated["candidate"][kind]) for kind in ("native", "swift", "middleware")}
            baseline_drift = {kind: delta(generated["tracked"][kind], generated["baseline"][kind]) for kind in ("native", "swift")}
            declared = read_json("GENERATED_DELTA.json")
            assert declared["candidate_vs_same_toolchain_baseline"] == actual_delta
            assert declared["baseline_vs_original_tracked"] == baseline_drift
            assert result["generated_delta_counts"] == {kind: len(items) for kind, items in actual_delta.items()}
            assert result["baseline_drift_counts"] == {kind: len(items) for kind, items in baseline_drift.items()}
            pins = json.loads((packet / "TOOL_PINS.json").read_bytes())
            actual_tools = read_json("ACTUAL_TOOL_EXECUTABLES.json")
            assert actual_tools["go_version"] == "go version go1.26.5 darwin/arm64"
            assert actual_tools["archive_pins"] == pins["archives"]
            tools = {row["path"]: row for row in actual_tools["tools"]}
            for pin in pins["archives"]:
                assert tools[pin["name"]]["sha256"] == pin["binary_sha256"]
            verified_deltas = {"candidate": {kind: [row["path"] for row in items] for kind, items in actual_delta.items()},
                               "baseline_drift": {kind: [row["path"] for row in items] for kind, items in baseline_drift.items()}}
        else:
            assert result["status"] == "FAIL" and (result.get("error") or result.get("cleanup_error"))
        return {"schema": "otzaria.independent-schema-rpc-generation-artifact-verification/1",
                "artifact": {"bytes": expected_size, "sha256": expected_sha256}, "head": head,
                "payloads_verified": len(rows), "control_inputs_locally_bound": len(manifest["control_inputs"]),
                "actual_result": result, "commands": command_rows, "generated_counts": generated_counts,
                "failure_time_counts": failure_counts, "verified_generated_deltas": verified_deltas,
                "scope": "Archive bytes, all indexed source/log payloads, source bindings, declared deltas and actual command outcomes only. Generated output semantics require separate review; full endpoint/Invocation/SDK/native acceptance remains open.",
                "tool_limit": "CI records actual generator executable hashes before/after use. Executable binaries and the complete OS/SDK closure are not part of this artifact and cannot be independently rehashed here.",
                "native_or_app_reexecutions": 0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--bytes", required=True, type=int)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--packet", type=Path, default=Path(__file__).parent / "schema_rpc_generation_candidate")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.archive, args.bytes, args.sha256, args.head, args.packet)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"payloads_verified": result["payloads_verified"],
                      "actual_generation_status": result["actual_result"]["status"],
                      "commands": len(result["commands"]), "native_or_app_reexecutions": 0}))


if __name__ == "__main__":
    main()
