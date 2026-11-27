#!/usr/bin/env python3
"""Qualify the already executed five native RPC tests without rerunning them."""
import argparse,hashlib,json,os,time
from pathlib import Path
import qualify_current8ac_core as base
import continue_current8ac_core as retained
from qualify_cutover_rpc import METHODS
FRAMES=["source-read-response.pb","begin-request.pb","begin-response.pb","frozen-import-request.pb",
 "frozen-import-response.pb","association-append-request.pb","association-append-response.pb","sealed-unlinked-read-response.pb"]
OLD_MANIFEST="75f44277c8c5b3f89c5f9e1ed28e443658dd38a72bd573edc18a95f61e42dd48"
OLD_RECEIPT="8dca23e931f9ae6d786008bf5ae7c0072331ffc7c17c500fd0ee86b2d3bf3a59"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",required=True,type=Path);a=ap.parse_args()
 root=a.root;assert root.parent==retained.BASE.parent and root.is_absolute() and not root.exists()
 os.umask(0o077);root.mkdir(mode=0o700)
 prior=retained.BASE.parent/"rpc-core-attempt4"
 original=json.loads(base.pinned(prior/"receipt.json",OLD_RECEIPT).read_text())
 assert original["status"]=="FAIL" and original["error"]=="AssertionError: crash-prepare did not reach the actual crash boundary"
 assert original["manifestSHA256"]==OLD_MANIFEST and original["retainedSourceUnchanged"] is True
 manifest_path=retained.BASE.parent/"rpc-crash-expectation-revision1/rpc-source-candidate.json"
 manifest=json.loads(base.pinned(manifest_path,OLD_MANIFEST).read_text())
 commands={p.name:json.loads((p/"result.json").read_text()) for p in (prior/"commands").iterdir()}
 for label in ["compile","core"]:
  command=commands[label]
  assert command["exitCode"]==0 and command["processGroupAbsent"] and command["stopReason"] is None
  assert base.sha(prior/"commands"/label/"original.log")==command["logSHA256"]
 assert "-vet=off" not in commands["compile"]["argv"]
 events=[json.loads(s) for s in (prior/"commands/core/original.log").read_text().splitlines()]
 top=lambda action:sorted(x["Test"] for x in events if x.get("Action")==action and x.get("Test") and "/" not in x["Test"])
 assert top("run")==top("pass")==sorted(METHODS["core"])
 assert not any(x.get("Action") in ("skip","fail") for x in events)
 assert any(x.get("Action")=="pass" and not x.get("Test") for x in events)
 assert original["methods"]==METHODS["core"]
 source_before=json.loads((prior/"source-before.json").read_text())
 source_after=json.loads((prior/"source-after.json").read_text())
 assert source_before==source_after
 inputs=json.loads((prior/"source-inputs.json").read_text())
 for rel,row in inputs.items():assert base.row(prior/"inputs"/rel)==row["after"],rel
 for rel,row in manifest["files"].items():assert inputs[rel]==row,rel
 binary=base.pinned(Path(original["binaryPath"]),original["binarySHA256"])
 assert base.row(binary)==json.loads((prior/"binary.json").read_text())
 proof_path=prior/"private/TestPinkhaTorahCutoverActualGeneratedRPCAndReopen/generated-rpc-proof.json"
 proof=json.loads(base.pinned(proof_path,original["generatedRPCProofSHA256"]).read_text())
 assert proof==original["generatedRPCProof"]
 for key,value in {"realAccounts":1,"realLegacyFacts":2,"signedMetadataRecords":4,"signedV1ImportClaims":2,"signedV1RemovalClaims":1}.items():assert proof[key]==value
 for key in ["generatedGRPC","allFiveGeneratedMethodsExecuted","sourceBytesRetained","nativeSignersVerified","sealedImportRetryIdempotent","accountStopAndReopen"]:assert proof[key] is True
 for key in ["newProcessReopen","peerTransport","appleUI"]:assert proof[key] is False
 frames={name:base.row(proof_path.parent/name) for name in FRAMES}
 assert all(0<r["bytes"]<=4*1024**2 for r in frames.values())
 public_events=[{k:v for k,v in x.items() if k!="Output"} for x in events if x.get("Action") in ["run","pass"]]
 base.save(root/"method-events.json",public_events)
 receipt={"status":"PASS_ACTUAL_GENERATED_GRPC_FIVE_METHODS_CRASH_PENDING",
  "controllerSHA256":base.sha(Path(__file__)),"executedAgain":False,"methods":METHODS["core"],"skips":0,
  "nativeGeneratedGRPC":True,"sameProcessAccountReopen":True,"processCrashAcceptance":False,"peerTransport":False,"appleUI":False,
  "originalOverallStatus":"FAIL","originalOverallReceipt":str(prior/"receipt.json"),"originalOverallReceiptSHA256":OLD_RECEIPT,
  "manifest":str(manifest_path),"manifestSHA256":OLD_MANIFEST,"nativeCoreManifestSHA256":manifest["coreManifestSHA256"],
  "binary":str(binary),"binaryRow":base.row(binary),"commands":{"compile":commands["compile"],"core":commands["core"]},
  "sourceInputs":inputs,"sourceBeforeManifestSHA256":base.sha(prior/"source-before.json"),
  "originalSourcesAndFrozenInputsVerified":True,"generatedRPCProof":proof,"generatedRPCProofSHA256":base.sha(proof_path),
  "nativeFramesRoot":str(proof_path.parent),"nativeFrames":frames,"methodEventsSHA256":base.sha(root/"method-events.json"),
  "completedUTC":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
 base.save(root/"receipt.json",receipt)
 print(json.dumps({"status":receipt["status"],"receipt":str(root/"receipt.json"),"sha256":base.sha(root/"receipt.json")}))
if __name__=="__main__":main()
