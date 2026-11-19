#!/usr/bin/env python3
"""Actual guarded Any Swift client, explicit synthetic fixture only."""
import argparse, base64, hashlib, json, os, queue, subprocess, sys, threading, time, urllib.request, uuid
from pathlib import Path
from datetime import datetime, timezone

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def require(value, name):
    if not value: raise RuntimeError(name)

def main():
    ap = argparse.ArgumentParser()
    for name in ("probe", "endpoint", "account", "space", "object", "output"):
        ap.add_argument("--" + name, required=True)
    ap.add_argument("--allow-disposable-writes", action="store_true", required=True)
    args = ap.parse_args()
    module = Path(__file__).resolve().parents[1]
    build = json.loads((module / "Evidence/native-contract-components-v1.json").read_text(encoding="utf-8"))
    def stable():
        return all((module / p).is_file() and sha(module / p) == v for p, v in build["sourceManifest"].items())
    require(stable(), "source differs from tested native client")
    require(sha(args.probe) == build["probe"]["sha256"], "probe binary differs from tested build")
    prefix = [args.probe, "--endpoint", args.endpoint, "--account-id", args.account,
              "--space-id", args.space, "--lane", "native"]
    receipt = {"startedAt": now(), "scope": "actual guarded native Any HTTP and Swift client; synthetic fixture, not native iOS UI",
        "probeSHA256": sha(args.probe), "buildReceiptSHA256": sha(module / "Evidence/native-contract-components-v1.json"),
        "nativeBinarySHA256": "ba069c3e1db36fb66a53bdc66e5d1a2a07d8263ed4fc8b26e54b57609d79dafa",
        "checks": []}
    watcher = None
    def command(mode, extra=()):
        completed = subprocess.run(prefix + ["--mode", mode] + list(extra), capture_output=True,
            text=True, encoding="utf-8", timeout=40)
        require(completed.returncode == 0, mode + " Swift probe failed: " + completed.stderr[:500])
        return json.loads(completed.stdout)
    def get(path):
        with urllib.request.urlopen(args.endpoint + path, timeout=20) as response:
            return json.load(response)
    def payload(item, reference):
        return json.dumps({"version": 2, "futureEnvelopeField": "preserved",
            "records": [{"spaceId": args.space, "objectId": args.object, "futureRecordField": 17,
            "item": {"id": item, "kind": "ref", "role": "context", "providerID": "sefaria",
                     "canonicalKey": reference, "externalID": reference, "labelHe": "מקור",
                     "futureItemField": {"kept": True}}}]}, ensure_ascii=False, sort_keys=True,
            separators=(",", ":")).encode()
    def append(operation, reference, data, observed=None, expect_collision=False):
        extra = ["--allow-disposable-writes", "--operation-id", operation, "--target-id", args.object]
        if observed:
            extra += ["--kind", "remove", "--observed", observed]
        else:
            extra += ["--kind", "add", "--provider-id", "sefaria", "--source-ref", reference,
                      "--payload-base64", base64.b64encode(data).decode()]
        if expect_collision: extra += ["--expect-collision"]
        return command("append", extra)
    try:
        auth = get("/v1/auth")
        require(auth.get("authorized") is True and auth.get("accountId") == args.account, "fixture account")
        baseline = command("verify", ["--expected-claims", ""])
        require(baseline["status"] == "PASS_REAL_NATIVE_ANY_HTTP_READ", "native lane status")
        base_all = set(baseline["allClaimIds"])
        base_live = set(baseline["liveClaimIds"])
        base_conflicts = set(baseline["conflictKeys"])
        receipt["checks"].append("gated_complete_native_snapshot")
        op1, op2, remove_id = (uuid.uuid4().hex for _ in range(3))
        data1 = payload("swift-native-" + op1, "Genesis 1:1")
        first = append(op1, "Genesis 1:1", data1)
        require(first["status"] == "PASS_REAL_NATIVE_ANY_APPEND" and first["created"], "native append")
        receipt["checks"].append("native_modify_append_and_provenance")
        retry = append(op1, "Genesis 1:1", data1)
        require(not retry["created"] and retry["acknowledgment"] == "preexisting"
                and retry["claimId"] == first["claimId"], "exact retry")
        receipt["checks"].append("exact_retry_through_native_fence_no_new_claim")
        snapshot = get("/v1/spaces/" + args.space + "/pinkha/claims?limit=10000")
        row = next(row for row in snapshot["records"] if row["operationId"] == op1)
        require(base64.b64decode(row["payload"]) == data1 and row["creator"] == args.account
                and row["nativeChangeId"] and row["nativeACLHeadId"], "native payload and derived receipt")
        receipt["checks"].append("opaque_canonical_unknown_fields_preserved_with_native_receipt")
        watcher = subprocess.Popen(prefix + ["--mode", "watch", "--updates", "2", "--timeout-seconds", "30"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
        lines = queue.Queue()
        def collect():
            for line in watcher.stdout: lines.put(line)
            lines.put(None)
        threading.Thread(target=collect, daemon=True).start()
        ready = json.loads(lines.get(timeout=20))
        require(ready.get("status") == "READY_REAL_NATIVE_ANY_SSE_SNAPSHOT", "native full snapshot readiness")
        data2 = payload("swift-native-" + op2, "Genesis 1:2")
        second = append(op2, "Genesis 1:2", data2)
        live = json.loads(lines.get(timeout=20))
        watcher.wait(timeout=10)
        require(watcher.returncode == 0 and live["status"] == "PASS_REAL_NATIVE_ANY_SSE_CLIENT"
                and live["initialSnapshotCount"] == 1 and live["updateCount"] == 2
                and set(live["allClaimIds"]) == base_all | {first["claimId"], second["claimId"]}
                and set(live["liveClaimIds"]) == base_live | {first["claimId"], second["claimId"]}, "native SSE exact state")
        receipt["checks"].append("actual_get_SSE_atomic_initial_and_live_full_state")
        removed = append(remove_id, "", b"", observed=first["claimId"])
        final = command("verify", ["--expected-claims", ",".join([first["claimId"], second["claimId"], removed["claimId"]])])
        require(set(final["allClaimIds"]) == base_all | {first["claimId"], second["claimId"], removed["claimId"]}
                and set(final["liveClaimIds"]) == base_live | {second["claimId"]}
                and set(final["conflictKeys"]) == base_conflicts, "observed remove exact fold")
        receipt["checks"].append("native_observed_remove_preserves_unseen_add")
        collision = append(op2, "Genesis 1:3", payload("collision", "Genesis 1:3"), expect_collision=True)
        require(collision["status"] == "PASS_ORDERED_COLLISION_REFUSED", "ordered collision refusal")
        unchanged = command("verify", ["--expected-claims", ",".join(final["allClaimIds"])])
        require(unchanged == final, "refusal changed native claim state")
        receipt["checks"].append("client_collision_refusal_no_native_change")
        receipt["final"] = {"all": len(final["allClaimIds"]), "live": len(final["liveClaimIds"]),
                            "conflicts": len(final["conflictKeys"]), "addedClaims": 3}
        receipt["status"] = "PASS"
    except Exception as error:
        receipt["status"] = "FAIL"
        receipt["error"] = type(error).__name__ + ": " + str(error)[:1200]
    finally:
        if watcher and watcher.poll() is None:
            watcher.kill()
            watcher.wait(timeout=10)
        receipt["sourceStableSinceBuild"] = stable()
        receipt["probeUnchanged"] = sha(args.probe) == receipt["probeSHA256"]
        if not receipt["sourceStableSinceBuild"] or not receipt["probeUnchanged"]: receipt["status"] = "FAIL"
        receipt["finishedAt"] = now()
        receipt["harnessSHA256"] = sha(__file__)
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False), flush=True)
    return 0 if receipt["status"] == "PASS" else 1

if __name__ == "__main__": sys.exit(main())
