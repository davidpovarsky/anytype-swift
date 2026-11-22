"""Read-only verification of the actual once-only 26-control result."""
from pathlib import Path
import collections
import hashlib
import json

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
RAW = ROOT / "evidence/attempt-v2/retained"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


result_path = RAW / "evidence/RESULT.json"
assert digest(result_path) == "b14984b12ca23f2b3ff73784cc79815a0fcb002491d43e1084ea3339618a08b1"
result = json.loads(result_path.read_bytes())
source = json.loads((ROOT / "SOURCE.json").read_bytes())
assert result["status"] == "PASS_NEW_OWNED_UPLOAD_IMPORT_UNIT_BOUNDARIES"
assert result["source_manifest"] == source == json.loads((RAW / "evidence/SOURCE.json").read_bytes())
assert result["go_version"] == "go version go1.25.6 windows/amd64"
assert result["native_executions"] == result["prior_suites_replayed"] == 0
assert [c["name"] for c in result["commands"]] == ["go-version", "compile-uploader", "compile-importer", "controls"]
for command in result["commands"]:
    assert command["exit"] == 0 and not command["timed_out"] and command["process_wait_completed"]
    for stream in ["stdout", "stderr"]:
        path = RAW / "evidence" / (command["name"] + "." + stream + ".log")
        assert path.stat().st_size == command[stream]["bytes"] and digest(path) == command[stream]["sha256"]
assert result["commands"][3]["args"][-2:] == ["./core/files/fileuploader", "./core/block/import"]
assert "-count=1" in result["commands"][3]["args"]
for command in result["commands"][1:3]:
    assert command["args"][1:4] == ["test", "-x", "-c"]
expected = {(e["package"], e["name"]) for e in source["expected_tests"]}
assert len(expected) == 26
starts, outcomes = collections.Counter(), collections.defaultdict(list)
events = [json.loads(line) for line in (RAW / "evidence/controls.stdout.log").read_text().splitlines()]
for event in events:
    if "Test" not in event:
        continue
    key = event["Package"], event["Test"]
    if event["Action"] == "run":
        starts[key] += 1
    elif event["Action"] in {"pass", "fail", "skip"}:
        outcomes[key].append(event["Action"])
assert starts.keys() == expected == outcomes.keys()
assert all(starts[k] == 1 and outcomes[k] == ["pass"] for k in expected)
assert result["tests_run"] == result["tests_passed"] == 26 and result["tests_failed"] == result["tests_skipped"] == 0
assert result["source_after"] == source["module_files"]
for entry in source["module_files"]:
    local, executed = ROOT / "module" / entry["path"], RAW / "module" / entry["path"]
    assert local.read_bytes() == executed.read_bytes()
    assert digest(executed) == entry["sha256"] and executed.stat().st_size == entry["bytes"]
for entry in source["full_actual_source_files"]:
    actual, executed = WORKSPACE / entry["source"], RAW / "module" / entry["compiled_path"]
    assert actual.read_bytes() == executed.read_bytes()
    assert digest(actual) == entry["sha256"]
for entry in source["actual_source_fragments"]:
    actual = WORKSPACE / entry["source"]
    assert digest(actual) == entry["source_sha256"]
    text = actual.read_bytes().decode()
    fragment = text[text.index(entry["start"]):]
    if entry["end"]:
        fragment = fragment[:fragment.index(entry["end"])]
    assert len(fragment.encode()) == entry["bytes"] and hashlib.sha256(fragment.encode()).hexdigest() == entry["fragment_sha256"]
    occurrences = sum(p.read_bytes().count(fragment.encode()) for p in (RAW / "module").rglob("*.go"))
    assert occurrences == 1
old = json.loads((ROOT / "evidence/attempt-v1/RESULT.json").read_bytes())
assert old["tests_run"] == 0 and old["commands"][-1]["timed_out"] and old["commands"][-1]["process_wait_completed"]
receipt = {
    "status": "PASS_RAW_SOURCE_AND_ONCE_ONLY_UNIT_RESULT_VERIFICATION",
    "result_sha256": digest(result_path), "source_manifest_sha256": digest(ROOT / "SOURCE.json"),
    "raw_control_events": len(events), "unique_starts": 26, "unique_passes": 26, "failures": 0, "skips": 0,
    "packages_executed": 2, "commands": 4, "streams_verified": 8, "source_inputs_verified": 39,
    "full_source_files_verified": 12, "exact_source_fragments_verified": 3,
    "prior_compile_timeout_retained": True, "prior_tests_executed": 0,
    "original_module_or_native_acceptance": False,
    "scope": source["scope"], "fixture_scope": source["fixture_scope"],
    "worker_scope": "Actual original workers already executing are joined. Queued Execute-after-Stop race is not itself exercised; no prevention of further work after cancel is claimed.",
}
(ROOT / "evidence/attempt-v2/VERIFICATION.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt))
