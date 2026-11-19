#!/usr/bin/env python3
"""Real object-scoped Swift client against an explicitly disposable native Any fixture."""
import argparse, base64, hashlib, json, queue, subprocess, sys, threading, urllib.request, uuid
from datetime import datetime, timezone
from pathlib import Path

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def require(value, message):
    if not value: raise RuntimeError(message)

def main():
    parser = argparse.ArgumentParser()
    for key in ("probe", "endpoint", "account", "space", "object", "block", "native-binary-sha256", "output"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--allow-disposable-writes", action="store_true", required=True)
    args = parser.parse_args()
    module = Path(__file__).resolve().parents[1]
    build_path = module / "Evidence/native-object-components-v1.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    def stable():
        return all((module / path).is_file() and sha(module / path) == digest
                   for path, digest in build["sourceManifest"].items())
    require(build["status"] == "PASS" and build["sourceStable"], "tested build receipt")
    require(stable(), "source differs from compiled object client")
    require(sha(args.probe) == build["probe"]["sha256"], "probe binary differs from tested build")
    prefix = [args.probe, "--endpoint", args.endpoint, "--account-id", args.account,
              "--space-id", args.space, "--lane", "native"]
    receipt = {"startedAt": now(),
        "scope": "real native object closure/append/watch through compiled Swift client; synthetic data, no UIKit claim",
        "buildReceiptSHA256": sha(build_path), "probeSHA256": sha(args.probe),
        "nativeBinarySHA256": args.native_binary_sha256, "checks": []}
    watcher = None
    def request(path, body=None):
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
        req = urllib.request.Request(args.endpoint + path, data=data,
            headers={"Content-Type": "application/json"} if data else {})
        with urllib.request.urlopen(req, timeout=20) as response: return json.load(response)
    def command(mode, extra=()):
        result = subprocess.run(prefix + ["--mode", mode] + list(extra), capture_output=True,
                                text=True, encoding="utf-8", timeout=40)
        require(result.returncode == 0, mode + " client failed: " + result.stderr[:400])
        return json.loads(result.stdout)
    def snapshot(target=args.object):
        return command("object-snapshot", ["--target-id", target])
    def payload(operation, target, block="", reference="Genesis 1:1"):
        record = {"spaceId": args.space, "objectId": target,
                  "item": {"id": "object-client-" + operation, "kind": "ref", "role": "context",
                           "providerID": "sefaria", "canonicalKey": reference, "externalID": reference,
                           "labelHe": "מקור", "futureItem": {"preserved": True}}}
        if block: record["blockId"] = block
        return json.dumps({"version": 2, "records": [record], "futureEnvelope": "preserved"},
                          ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    def append(operation, target=args.object, block="", observed=None):
        extra = ["--allow-disposable-writes", "--operation-id", operation, "--target-id", target]
        if block: extra += ["--target-block-id", block]
        if observed: extra += ["--kind", "remove", "--observed", observed]
        else: extra += ["--kind", "add", "--provider-id", "sefaria", "--source-ref", "Genesis 1:1",
                        "--payload-base64", base64.b64encode(payload(operation, target, block)).decode()]
        return command("append", extra)
    try:
        auth = request("/v1/auth")
        require(auth.get("authorized") is True and auth.get("accountId") == args.account, "fixture account")
        caps = request("/v1/pinkha/capabilities")
        require(caps.get("nativeObjectClaimsSnapshot") == 1 and caps.get("nativeObjectClaimsWatch") == 1,
                "object read/watch capabilities")
        receipt["checks"].append("explicit_native_object_snapshot_and_watch_capabilities")
        before = snapshot()
        require(before["status"] == "PASS_REAL_NATIVE_ANY_OBJECT_SNAPSHOT"
                and before["targetObjectId"] == args.object, "exact object scope")
        baseline_all, baseline_live = set(before["allClaimIds"]), set(before["liveClaimIds"])
        baseline_conflicts, baseline_blocks = set(before["conflictKeys"]), set(before["reachableClaimBlockIds"])
        receipt["checks"].append("complete_native_object_snapshot_and_readiness")
        foreign = request("/v1/spaces/" + args.space + "/objects", {
            "type": "page", "initialProperties": {"any": {"name": "Synthetic object closure exclusion"}}})["objectId"]
        foreign_claim = append(uuid.uuid4().hex, target=foreign)
        after_foreign = snapshot()
        require(set(after_foreign["allClaimIds"]) == baseline_all
                and foreign_claim["claimId"] not in after_foreign["allClaimIds"], "unrelated object excluded")
        receipt["checks"].append("unrelated_global_claim_excluded_without_whole_workspace_read")
        doc_op, block_op, later_op, remove_op = [uuid.uuid4().hex for _ in range(4)]
        document = append(doc_op)
        block = append(block_op, block=args.block)
        after_block = snapshot()
        require(set(after_block["allClaimIds"]) == baseline_all | {document["claimId"], block["claimId"]}
                and set(after_block["reachableClaimBlockIds"]) == baseline_blocks | {args.block},
                "block reachability native proof")
        receipt["checks"].append("native_scoped_append_with_real_reachable_block_metadata")
        retry = append(block_op, block=args.block)
        require(retry["claimId"] == block["claimId"] and not retry["created"]
                and retry["acknowledgment"] == "preexisting", "native exact retry")
        receipt["checks"].append("exact_retry_still_enters_native_authority_without_new_claim")
        watcher = subprocess.Popen(prefix + ["--mode", "object-watch", "--target-id", args.object,
            "--updates", "2", "--timeout-seconds", "30"], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8")
        lines = queue.Queue()
        def collect():
            for line in watcher.stdout: lines.put(line)
            lines.put(None)
        threading.Thread(target=collect, daemon=True).start()
        ready = json.loads(lines.get(timeout=20))
        require(ready["status"] == "READY_REAL_NATIVE_ANY_OBJECT_SNAPSHOT", "actual object initial snapshot")
        later = append(later_op)
        event = json.loads(lines.get(timeout=20))
        watcher.wait(timeout=10)
        require(watcher.returncode == 0 and event["status"] == "PASS_REAL_NATIVE_ANY_OBJECT_WATCH"
                and event["initialSnapshotCount"] == 1 and event["updateCount"] == 2
                and set(event["allClaimIds"]) == baseline_all | {document["claimId"], block["claimId"], later["claimId"]}
                and foreign_claim["claimId"] not in event["allClaimIds"], "native object watch exact state")
        receipt["checks"].append("actual_object_SSE_atomic_initial_and_complete_live_scope")
        removed = append(remove_op, block=args.block, observed=block["claimId"])
        final = snapshot()
        require(set(final["allClaimIds"]) == baseline_all | {document["claimId"], block["claimId"], later["claimId"], removed["claimId"]}
                and set(final["liveClaimIds"]) == baseline_live | {document["claimId"], later["claimId"]}
                and set(final["reachableClaimBlockIds"]) == baseline_blocks | {args.block}
                and set(final["conflictKeys"]) == baseline_conflicts, "observed remove retains full object history")
        receipt["checks"].append("observed_remove_keeps_immutable_history_and_native_reachability")
        whole = command("verify", ["--expected-claims", ",".join(final["allClaimIds"] + [foreign_claim["claimId"]])])
        require(foreign_claim["claimId"] in whole["allClaimIds"], "full workspace diagnostic remains complete")
        receipt["checks"].append("whole_workspace_diagnostic_contract_remains_distinct")
        receipt["final"] = {"all": len(final["allClaimIds"]), "live": len(final["liveClaimIds"]),
                            "conflicts": len(final["conflictKeys"]), "addedTargetClaims": 4,
                            "unrelatedClaimExcluded": True}
        receipt["status"] = "PASS"
    except Exception as error:
        receipt["status"] = "FAIL"
        receipt["error"] = type(error).__name__ + ": " + str(error)[:900]
    finally:
        if watcher is not None and watcher.poll() is None:
            watcher.kill(); watcher.wait(timeout=10)
        receipt["sourceStableSinceBuild"] = stable()
        receipt["probeUnchanged"] = sha(args.probe) == receipt["probeSHA256"]
        if not receipt["sourceStableSinceBuild"] or not receipt["probeUnchanged"]:
            receipt["status"] = "FAIL"
        receipt["finishedAt"] = now(); receipt["harnessSHA256"] = sha(__file__)
        Path(args.output).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(receipt, ensure_ascii=False), flush=True)
    return 0 if receipt["status"] == "PASS" else 1

if __name__ == "__main__": sys.exit(main())
