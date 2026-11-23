#!/usr/bin/env python3
"""Read original recovery evidence; never launch a product process."""
import base64
import hashlib
import json
from pathlib import Path
import re
import sys

root = Path(sys.argv[1]).resolve()
output = Path(sys.argv[2]).absolute()
plan = json.loads(Path(sys.argv[3]).read_text())
sha = lambda raw: hashlib.sha256(raw).hexdigest()
load = lambda path: json.loads(path.read_text())
status = load(root / "execution-status.json")
assert status["status"] == "PASS_NEW_SCOPES"
assert status["selectors"] == plan["selectors"]
assert status["namedStarts"] == status["namedPasses"] == plan["selectors"]
assert status["failureOrSkipEvents"] == []
assert status["sourceUnchanged"] and status["binaryUnchanged"]
before = load(root / "source-before.json")
assert len(before["any"]) == 852 and len(before["sdk"]) == 683
for name in ("source-after-build.json", "source-after-execution.json"):
    assert load(root / name) == before
build = load(root / "build-qualified.json")
binary = root / "qualified-products/inline-recovery.test"
assert sha(binary.read_bytes()) == build["binarySHA256"]
events = load(root / "named-events.json")
assert [e["Test"] for e in events if e.get("Action") == "run" and "Test" in e] == plan["selectors"]
assert [e["Test"] for e in events if e.get("Action") == "pass" and "Test" in e] == plan["selectors"]
for row in events:
    assert row["Action"] not in ("skip", "fail")

cases, all_pids, all_nonces, private_log_proofs = [], set(), set(), []
total_crashes, normal_closes = 0, 0
for method, expected_children, expected_crashes in zip(plan["selectors"], (3, 2), (2, 1)):
    safe = root / "safe" / method
    private = root / "private" / method
    files = sorted(safe.glob("*.json"))
    rows = []
    for index, path in enumerate(files, 1):
        assert path.name.startswith(f"{index:03d}-")
        kind = path.name[4:-5]
        record = load(path)
        assert record["protocol"] == plan["protocol"] and record["test"] == method
        rows.append((kind, record))
    nonce = rows[0][1]["nonce"]
    assert nonce not in all_nonces and re.fullmatch(r"[0-9a-f]{32}", nonce)
    all_nonces.add(nonce)
    assert all(row["nonce"] == nonce for _, row in rows)
    assert len({row["parentPID"] for _, row in rows}) == 1
    pick = lambda kind: [row["value"] for k, row in rows if k == kind]
    starts, ready = pick("process-start"), pick("ready")
    assert len(starts) == len(ready) == expected_children
    pids = [row["pid"] for row in starts]
    assert len(set(pids)) == expected_children and not (set(pids) & all_pids)
    assert all(row["pgid"] == row["pid"] and row["separateProcessGroup"] for row in starts)
    all_pids.update(pids)
    baseline = ready[0]["ready"]
    for index, frame in enumerate(ready):
        assert frame["pid"] == frame["pgid"] == pids[index]
        assert frame["nonce"] == nonce and frame["kind"] == "ready" and frame["sequence"] == 0
        assert frame["ready"]["capability"] == baseline["capability"]
        assert frame["ready"]["owner"] == baseline["owner"]
        assert frame["ready"]["walletCreated"] == (index == 0)
    capability = baseline["capability"]
    assert capability["file"] == 0 and capability["networkVerified"] is False
    assert capability["inlineFile"] == 1 and capability["maximumInlineBytes"] == 4095
    original = pick("original-input")
    assert len(original) == 1
    original = original[0]
    receipt = original["originalReceipt"]
    spec = original["sourceSpecification"]
    raw = json.dumps(spec, ensure_ascii=False, separators=(",", ":")).encode()
    assert sha(raw) == original["specSHA256"] == receipt["specSHA256"]
    content = base64.b64decode(spec["content"], validate=True)
    assert content == bytes(i % 256 for i in range(4095))
    assert sha(content) == spec["contentSHA256"] == receipt["contentSHA256"]
    assert receipt["size"] == 4095 and receipt["ownerObjectId"] == baseline["owner"]
    assert receipt["recordIds"] == [receipt["fileId"]]
    assert receipt["storeId"] == capability["storeId"] and receipt["accountId"] == capability["accountId"]
    assert receipt["spaceId"] == capability["spaceId"]
    identity = {key: value for key, value in receipt.items() if key not in ("stage", "outcome")}
    expected_name = "\u05e7\u05d5\u05d1\u05e5 \U0001f9ea.bin"
    assert spec["name"] == expected_name and spec["mime"] == "application/octet-stream"

    observations = []
    for kind, row in rows:
        value = row["value"]
        if kind == "http":
            current = value["receipt"]
            assert {key: val for key, val in current.items() if key not in ("stage", "outcome")} == identity
            if value["method"] == "PUT":
                assert value["requestSHA256"] == original["prepareJSONSHA256"]
        if kind == "observe":
            assert value["pid"] in pids and value["pgid"] == value["pid"] and value["nonce"] == nonce
            observations.append(value["observation"])
    for observed in observations:
        current = observed["receipt"]
        assert {key: val for key, val in current.items() if key not in ("stage", "outcome")} == identity
        count = 1 if current["stage"] == "complete" else 0
        assert observed["stats"] == {"Total": count, "Durable": count, "InFlight": 0, "Limited": 0}
        assert len(observed["files"] or []) == count
        if count:
            assert current["outcome"] == "committed"
            assert base64.b64decode(observed["content"], validate=True) == content
            assert observed["contentSHA256"] == sha(content)
            info = observed["info"]
            assert info == observed["files"][0]
            assert info["FileId"] == receipt["fileId"] and info["ObjectId"] == receipt["ownerObjectId"]
            assert info["Size"] == 4095 and info["Name"] == expected_name and info["Mime"] == spec["mime"]
            assert info["Inline"] and info["Cached"] and info["Durable"] and info["RootCid"] == ""
        else:
            assert "info" not in observed

    crashes, cleanups = pick("sigkill"), pick("normal-cleanup")
    assert len(crashes) == expected_crashes and len(cleanups) == 1
    assert not pick("failed-child-already-exited")
    assert [row["pid"] for row in crashes] == pids[:-1]
    assert cleanups[0]["pid"] == pids[-1] and cleanups[0]["exitCode"] == 0
    assert cleanups[0]["usedAsCrashProof"] is False
    for termination in crashes + cleanups:
        child = termination["child"]
        log = private / f"child-{child}-original.log"
        raw_log = log.read_bytes()
        assert sha(raw_log) == termination["privateOriginalLogSHA256"]
        text = raw_log.decode(errors="replace")
        starts_count = len(re.findall(r"(?m)^=== RUN\s+TestPreparedInlineFileRecoveryChild\s*$", text))
        passes_count = len(re.findall(r"(?m)^--- PASS: TestPreparedInlineFileRecoveryChild ", text))
        assert starts_count == 1
        if termination in crashes:
            assert termination["deliberate"] and termination["signal"] == termination["waitStatus"] == 9
            assert termination["signaled"] and termination["exitCode"] == -1
            assert termination["waitCompleted"] and termination["exactPIDAbsent"]
            assert not termination["orderlyCloseStarted"] and not termination["orderlyCloseCompleted"]
            assert not (private / f"child-{child}-close-start.json").exists()
            assert not (private / f"child-{child}-close-complete.json").exists()
            assert passes_count == 0
        else:
            assert passes_count == 1
            for suffix in ("close-start", "close-complete"):
                marker = load(private / f"child-{child}-{suffix}.json")
                assert marker["pid"] == termination["pid"] and marker["nonce"] == nonce
        private_log_proofs.append({"method": method, "child": child, "pid": termination["pid"],
            "originalLogSHA256": sha(raw_log), "bytes": len(raw_log),
            "namedHelperStarts": starts_count, "namedHelperPasses": passes_count,
            "includedInProductMethodCount": False})
    if expected_crashes == 2:
        assert [row["boundary"] for row in crashes] == [
            "native-reservation-returned-file-prepared", "native-root-commit-returned-file-root-committed"]
        assert not pick("actual-ack-loss")
    else:
        clients, losses = pick("client-transport"), pick("actual-ack-loss")
        assert len(clients) == len(losses) == 1
        client = clients[0]
        assert client["connected"] and client["requestWritten"]
        assert not client["responsePresent"] and not client["firstResponseByte"]
        assert "EOF" in client["error"] or "connection reset" in client["error"]
        frame = losses[0]
        assert frame["pid"] == frame["pgid"] == pids[0] and frame["nonce"] == nonce
        drop = frame["drop"]
        assert drop["requestSHA256"] == client["requestSHA256"]
        assert drop["responseStatus"] == 200 and drop["responseBytes"] > 0
        assert drop["forwardedBytes"] == drop["networkBufferedBytes"] == 0
        assert drop["targetRequests"] == 1 and drop["hijacked"] and drop["connectionClosed"]
        assert drop["observation"]["receipt"]["stage"] == "complete"
        assert drop["observation"]["receipt"]["outcome"] == "committed"
        assert base64.b64decode(drop["observation"]["content"], validate=True) == content
        assert crashes[0]["boundary"] == "native-complete-after-actual-client-EOF-before-retry"
    accepted, terminal = pick("accepted"), pick("terminal")
    assert len(accepted) == len(terminal) == 1 and terminal[0]["failed"] is False
    assert accepted[0]["deliberateSIGKILLs"] == expected_crashes
    assert accepted[0]["distinctOwnedProcesses"] == expected_children
    assert accepted[0]["independentNativeRows"] == 1
    total_crashes += expected_crashes
    normal_closes += 1
    cases.append({"method": method, "ownedPIDs": pids, "deliberateSIGKILLs": expected_crashes,
                  "independentNativeObservations": len(observations), "finalNativeRows": 1,
                  "originalSpecSHA256": original["specSHA256"], "originalContentSHA256": sha(content)})

assert len(all_pids) == 5 and total_crashes == 3 and normal_closes == 2
artifacts = []
for path in sorted(root.rglob("*")):
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    if relative.parts[0] in ("private", "tmp", "go-tmp", "qualified-products"):
        continue
    raw = path.read_bytes()
    artifacts.append({"path": str(relative), "bytes": len(raw), "sha256": sha(raw)})
result = {"status": "PASS_ORIGINAL_TWO_NEW_RECOVERY_SCOPES", "protocol": plan["protocol"],
          "sourceAnyCommit": plan["any"]["fixtureCommit"], "sourceSDKCommit": plan["sdk"]["candidateCommit"],
          "sourceInputs": 1535, "sourceUnchanged": True, "binarySHA256": build["binarySHA256"],
          "actualParentMethods": 2, "distinctOwnedChildProcesses": 5, "actualSIGKILLs": 3,
          "normalFinalCleanupProcesses": 2, "actualLostHTTPAcknowledgements": 1,
          "cases": cases, "privateOriginalLogProofs": private_log_proofs, "originalArtifacts": artifacts,
          "auditScriptSHA256": sha(Path(__file__).read_bytes()), "powerLossDurability": False,
          "swiftClientAcceptance": False, "AppleAcceptance": False, "networkAcceptance": False,
          "notificationOutboxDelivery": False, "fullMigrationComplete": False}
with output.open("x", encoding="utf-8") as stream:
    json.dump(result, stream, indent=2, sort_keys=True)
    stream.write("\n")
print(json.dumps({key: value for key, value in result.items() if key not in ("cases", "privateOriginalLogProofs", "originalArtifacts")}))
