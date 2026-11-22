"""Independent, read-only intake of the single Heart V7 native artifact."""
from pathlib import Path
import base64
import hashlib
import json

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "extracted"
sha = lambda value: hashlib.sha256(value).hexdigest()
archive = ROOT / "Heart_45027606300_artifact.zip"
assert sha(archive.read_bytes()) == "2145510a2b7619daae6d7d7cfd47c12351a39033af400c7ea1f94611be2c018f"
index = json.loads((EVIDENCE / "EVIDENCE_INDEX.json").read_bytes())
for item in index["files"]:
    data = (EVIDENCE / item["path"]).read_bytes()
    assert len(data) == item["bytes"] and sha(data) == item["sha256"], item["path"]
result = json.loads((EVIDENCE / "RESULT.json").read_bytes())
assert result["status"] == "PASS"
assert result["control_head"] == "7431d8fd3b3e9f4a3ef167dbb3b6c995ab972508"
assert result["execution_manifest_sha256"] == "8b4306ca235e95a5990ddf9378755ca41aef5dffeba856bc2396c88b7b89e941"
commands = json.loads((EVIDENCE / "COMMANDS.json").read_bytes())
assert len(commands) == 15 and len({row["label"] for row in commands}) == 15
for row in commands:
    assert row["status"] == "TERMINAL" and row["returncode"] == row["effective_returncode"] == 0
    assert not row["timed_out"]
    for stream in ("stdout", "stderr"):
        assert sha((EVIDENCE / row[stream]).read_bytes()) == row[stream + "_sha256"]
cases = {"ActualLocalZeroCounterAccepted", "NativeComputedRemoteCounterAccepted"}
events = [json.loads(line) for line in (EVIDENCE / "15-run-native.stdout").read_bytes().splitlines()]
parent = "TestOtzariaFixedSchemaNativeObserverV5"
starts = [row["Test"] for row in events if row.get("Action") == "run" and row.get("Test", "").startswith(parent + "/")]
terminals = [row for row in events if row.get("Action") in {"pass", "fail", "skip"} and row.get("Test", "").startswith(parent + "/")]
assert len(starts) == len(set(starts)) == 2 and {row.split("/")[-1] for row in starts} == cases
assert len(terminals) == 2 and all(row["Action"] == "pass" for row in terminals)
assert {row["Test"] for row in terminals} == set(starts)
observations = []
for path in sorted(EVIDENCE.glob("counter-*.json")):
    row = json.loads(path.read_bytes())
    assert row["Case"] in cases and row["ProcessID"] > 0 and row["MaximumAttempts"] == 3
    assert row["CounterUnchanged"] and row["ScopeUnchanged"] and not row["Failure"]
    before = base64.b64decode(row["CounterBefore"], validate=True)
    assert before == base64.b64decode(row["CounterAfter"], validate=True)
    assert len(row["Snapshots"]) == 2
    snapshots = []
    for number, snapshot in enumerate(row["Snapshots"], 1):
        assert snapshot["Index"] == number and snapshot["Committed"] and snapshot["Done"]
        assert not snapshot["CommitError"] and not snapshot["ReadErrors"] and not snapshot["TraceErrors"]
        assert len(snapshot["Rows"]) == 11
        decoded = {}
        for key, value in snapshot["Rows"].items():
            raw = base64.b64decode(value["Encoded"], validate=True)
            assert sha(raw) == value["SHA256"] and key == value["Collection"] + "\0" + value["ID"]
            decoded[key] = raw
        assert any(raw == before for raw in decoded.values())
        snapshots.append(decoded)
    differences = {key for key in snapshots[0].keys() | snapshots[1].keys() if snapshots[0].get(key) != snapshots[1].get(key)}
    assert differences == {d["Collection"] + "\0" + d["ID"] for d in row["Differences"]}
    if row["CompleteStableMatch"]:
        assert not differences and not row["Error"] and not row["RetryAdmitted"] and row["Disposition"] == 1
    else:
        assert differences and row["ExactChangedError"] and row["RetryAdmitted"] and row["Disposition"] == 5
    observations.append(row)
for case in sorted(cases):
    rows = sorted([row for row in observations if row["Case"] == case], key=lambda row: row["Attempt"])
    assert [row["Attempt"] for row in rows] == list(range(1, len(rows) + 1))
    assert rows[-1]["CompleteStableMatch"] and all(not row["CompleteStableMatch"] for row in rows[:-1])
    assert all(row["Scope"] == rows[0]["Scope"] and row["CounterBefore"] == rows[0]["CounterBefore"] for row in rows)
    assert all(row["ExpectedCounter"] == (0 if case == "ActualLocalZeroCounterAccepted" else 3) for row in rows)
assert len({row["ProcessID"] for row in observations}) == 1
declared = json.loads((EVIDENCE / "DECLARED_NATIVE_INPUTS.json").read_bytes())
assert len(declared["files"]) == result["declared_native_input_count"] == 11319
assert sha((EVIDENCE / "DECLARED_NATIVE_INPUTS.json").read_bytes()) == result["declared_native_inputs_sha256"]
summary = {
    "status": "VERIFIED_TWO_NATIVE_CASES_PASS",
    "run_id": 45027606300, "attempt": 1,
    "head": result["control_head"], "artifact_id": 14756238741,
    "artifact_sha256": sha(archive.read_bytes()), "artifact_bytes": archive.stat().st_size,
    "payloads_verified": len(index["files"]), "commands_verified": len(commands),
    "case_counts": {"pass": 2, "fail": 0, "skip": 0},
    "exact_case_events": terminals,
    "counter_observations": [{key: row[key] for key in ["Case", "Attempt", "ExpectedCounter", "ProcessID", "Started", "Finished", "Differences", "CompleteStableMatch", "RetryAdmitted"]} for row in observations],
    "prior_passed_cases_rerun": 0,
    "source_inputs": result["composed_product_and_test_inputs"],
    "native_declared_input_count": result["declared_native_input_count"],
    "raw_log_sha256": sha((EVIDENCE / "15-run-native.stdout").read_bytes()),
    "result_sha256": sha((EVIDENCE / "RESULT.json").read_bytes()),
    "boundary": "Original disposable LocalOnly Heart native observer controls only. No iOS SDK, editor, schema creation/repair, annotation body equality or COMMIT/ACK acceptance. Native binary hashes and reported process ID are runner observations; executable bytes were not uploaded."
}
(ROOT / "VERIFIED_RESULT.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary))
