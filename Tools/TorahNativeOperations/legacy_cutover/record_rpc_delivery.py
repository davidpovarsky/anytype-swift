#!/usr/bin/env python3
"""Package reviewed native RPC/crash source and original receipts for integration."""
import argparse,difflib,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
import qualify_current8ac_core as base
import continue_current8ac_core as retained

EXPECTED="b98c93ff11e492e173ca2a0b93548ed4cdfb275bb4b345bd82468e55c6e481ac"
RPC_RECEIPT="b02f58b6a9c341bcc2c0820c599e0f6ed1cb699d457e936375aea8495865ee62"
CRASH_RECEIPT="73478d7b445484746b2504cd0e0136735a3893143e83230ced242394fdbc7bfb"
REPO=base.HERE.parents[2]
DEST=REPO/"docs/architecture/20261127-heart-cutover-native-rpc"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--host-root",type=Path);ap.add_argument("--byte-root",type=Path);a=ap.parse_args()
 assert not DEST.exists();DEST.mkdir(parents=True)
 work=retained.BASE.parent/"rpc-patch-qualification1";assert not work.exists();work.mkdir(mode=0o700)
 source=retained.BASE/"source/heart"
 manifest=json.loads(base.pinned(base.HERE/"rpc-source-candidate.json",EXPECTED).read_text())
 rpc=retained.BASE.parent/"rpc-generated-qualification1"
 native=retained.BASE.parent/"rpc-core-attempt5"
 r=json.loads(base.pinned(rpc/"receipt.json",RPC_RECEIPT).read_text())
 c=json.loads(base.pinned(native/"receipt.json",CRASH_RECEIPT).read_text())
 assert r["status"]=="PASS_ACTUAL_GENERATED_GRPC_FIVE_METHODS_CRASH_PENDING"
 assert c["status"]=="PASS_GENERATED_GRPC_AND_OFFLINE_PROCESS_CRASH_NOT_PEER_OR_APPLE"
 assert c["manifestSHA256"]==EXPECTED and c["retainedSourceUnchanged"] and c["secretLogScanPassed"]
 assert c["reusedRPCQualification"]["sha256"]==RPC_RECEIPT
 assert c["reusedRPCQualification"]["allProductAndFiveRPCMethodSourcesUnchanged"]
 assert c["reusedRPCQualification"]["methodsExecutedAgain"] is False
 assert c["osNetworkIsolated"] and c["newProcessReopen"] and len(set(c["crashProof"]["actualTestPIDs"]))==3
 fixture=work/"source";fixture.mkdir()
 parts=[]
 for rel,entry in manifest["files"].items():
  incoming=base.HERE/"overlay"/rel;original=source/rel
  assert base.row(incoming)==entry["after"]
  assert (base.row(original) if original.exists() else None)==entry["before"]
  before=original.read_text() if original.exists() else ""
  after=incoming.read_text();assert after.endswith("\n")
  target=fixture/rel;target.parent.mkdir(parents=True,exist_ok=True)
  if original.exists():shutil.copyfile(original,target)
  header="diff --git a/"+rel+" b/"+rel+"\n"
  if not original.exists():header+="new file mode 100644\n"
  parts.append(header+"".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
   fromfile="a/"+rel if original.exists() else "/dev/null",tofile="b/"+rel)))
 patch=DEST/"current8ac-plus-core-native-rpc.patch";patch.write_text("".join(parts))
 checks=[]
 for args in [["git","apply","--check",str(patch)],["git","apply",str(patch)]]:
  run=subprocess.run(args,cwd=fixture,capture_output=True,text=True)
  checks.append({"argv":args,"exitCode":run.returncode,"stdout":run.stdout,"stderr":run.stderr})
  assert run.returncode==0,run.stderr
 for rel,entry in manifest["files"].items():assert base.row(fixture/rel)==entry["after"],rel
 base.save(work/"patch-apply.json",checks)
 files={
  "source-candidate.json":base.HERE/"rpc-source-candidate.json",
  "generated-rpc-five-methods-receipt.json":rpc/"receipt.json",
  "generated-rpc-method-events.json":rpc/"method-events.json",
  "rpc-crash-receipt.json":native/"receipt.json",
  "original-rpc-attempt4-failure.json":retained.BASE.parent/"rpc-core-attempt4/receipt.json",
  "original-host-attempt1-fixture-environment-failure.json":retained.BASE.parent/"rpc-host-attempt1/receipt.json",
  "original-rpc-attempt2-reserve-stop.json":retained.BASE.parent/"rpc-core-attempt2/receipt.json",
  "original-rpc-attempt3-vet-topology-failure.json":retained.BASE.parent/"rpc-core-attempt3/receipt.json",
  "canonical-go-generator-receipt.json":retained.BASE.parent/"rpc-generation2-isolated/receipt.json",
  "empty-overlay-topology-receipt.json":retained.BASE.parent/"rpc-overlay-topology2/receipt.json",
  "crash-fixture-revision.json":retained.BASE.parent/"rpc-crash-expectation-revision1/revision.json",
  "crash-fixture-correction.diff":retained.BASE.parent/"rpc-crash-expectation-revision1/stronger-crash-boundary.diff",
  "original-crash-test.go":retained.BASE.parent/"rpc-crash-expectation-revision1/original-crash-test.go",
  "original-rpc-source-candidate.json":retained.BASE.parent/"rpc-crash-expectation-revision1/rpc-source-candidate.json",
  "RPC_CONTRACT.md":base.HERE/"RPC_CONTRACT.md",
 }
 extra={}
 for label,p,status in [("host",a.host_root,"PASS_AFFECTED_NATIVE_SIGNED_HOST_REGRESSIONS"),("byte",a.byte_root,"PASS_GENERATED_GOMOBILE_BYTE_BOUNDARY")]:
  if p is None:continue
  proof=json.loads((p/"receipt.json").read_text())
  assert proof["status"]==status and proof["manifestSHA256"]==EXPECTED and proof["retainedSourceUnchanged"]
  files[label+"-receipt.json"]=p/"receipt.json"
  extra[label]={"receipt":base.row(p/"receipt.json"),"methods":proof["methods"],"status":proof["status"]}
  qualification_events=[]
  for line in (p/"commands"/label/"original.log").read_text().splitlines():
   event=json.loads(line)
   if event.get("Action") in ["run","pass","fail","skip"]:qualification_events.append({k:v for k,v in event.items() if k!="Output"})
  assert not any(x.get("Action") in ["fail","skip"] for x in qualification_events)
  base.save(DEST/(label+"-method-events.json"),qualification_events)

 for name,p in files.items():
  target=DEST/name;shutil.copyfile(p,target);assert base.row(target)==base.row(p)
 for phase in ["prepare","resume","verify"]:
  name=phase+"-network-namespace.json";p=native/"private/crash"/(phase+"-namespace.json")
  observed=json.loads(p.read_text())
  assert observed["interfaces"]==["lo"] and observed["externalRoutes"]==0 and observed["namespace"]!=observed["parentNamespace"]
  shutil.copyfile(p,DEST/name)
 events=[]
 for phase in ["resume","verify"]:
  log=native/"commands"/("crash-"+phase)/"original.log"
  for line in log.read_text().splitlines():
   event=json.loads(line)
   if event.get("Action") in ["run","pass"]:events.append({k:v for k,v in event.items() if k!="Output"})
 base.save(DEST/"crash-method-events.json",events)
 base.save(DEST/"patch-application-receipt.json",{
  "status":"PASS_EXACT_PATCH_APPLY_ALL_ELEVEN_FILES","files":len(manifest["files"]),
  "patchSHA256":base.sha(patch),"commands":checks,"resultingFiles":{rel:base.row(fixture/rel) for rel in manifest["files"]}})
 (DEST/"README.md").write_text("# Heart cutover: qualified native RPC and real process recovery\n\nThis delivery extends the qualified native core commit `05c2f6d4f391a5b9d3dab7efa2987afd887a5f65` with five generated RPC methods, a lossless error/result boundary, and actual process recovery evidence. Apply the core overlay first, then `current8ac-plus-core-native-rpc.patch`, to the exact retained native manifest `8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b`.\n\n## Source and integration contract\n\nThe eleven-file RPC source manifest is `b98c93ff11e492e173ca2a0b93548ed4cdfb275bb4b345bd82468e55c6e481ac`. The additional protobuf types live in `pb/cutoverpb`; original top-level protobuf files remain byte-identical. The canonical generator preserves protobuf full names and wire numbers, and changes only the additive Go package metadata. Existing 1,055 gRPC function bodies and 702 gomobile function bodies remain exact. Generated registration/dispatch adds the five new methods. No existing Anytype UI or app association repository is replaced.\n\nThe methods read the legacy source, read the cutover projection, append signed cutover metadata, import a frozen association, and append an association operation. The native core owns authority and signing. Request ownership, source version/digest, deterministic claim identity, signed receipt identity, ACL and loaded account lifetime remain admission checks. `RPC_CONTRACT.md` gives precise messages, error codes and limits.\n\nA durable write can return both a committed native receipt and a post-commit authority error. Callers must retain the disposition, claim ID, native ChangeID and complete joined issue list. They must neither return a zero result nor automatically retry. Private projection data is withheld when authority has retired. A valid frozen retry remains idempotent after sealing; a changed source/conflicting plan is refused before the idempotency lookup.\n\n## Executed evidence\n\n| Boundary | Actual evidence | Reuse and scope |\n| --- | --- | --- |\n| Generated gRPC | Five selected methods passed, zero skips; real account, all five generated methods, two original legacy facts, four signed metadata records, two signed imports, one signed unlink, AccountStop/Select reopen | Original aggregate attempt4 remains FAIL because its later crash preparation assertion modeled physical imports incorrectly. The five RPC methods are independently qualified by receipt `b02f58b6a9c341bcc2c0820c599e0f6ed1cb699d457e936375aea8495865ee62`. |\n| Crash recovery | Actual SIGKILL after one durable signed import and Begin but before its metadata witness/Seal; two subsequent native processes reopen the same account under OS network isolation | Receipt `73478d7b445484746b2504cd0e0136735a3893143e83230ced242394fdbc7bfb`; actual native PIDs 3002933, 3003402 and 3003773. Each namespace contains only loopback, with zero external routes. |\n| Signed host regressions | Four affected signed native host methods; exact signed phases/unlink/reopen, two native authors and older writer divergence, ACL/retired lease refusal, durable write with lost acknowledgement | The compiled binary is unchanged. Initial controller FAIL omitted `PINKHA_CUTOVER_NATIVE_WORK`; the corrected run uses a fresh private fixture directory after exact source/overlay/compiler-input comparison. It does not rerun the accepted RPC or crash methods. |\n| Generated gomobile bytes | The byte-boundary receipt and selected method events are included when supplied to the packaging controller | Exercises all five generated byte dispatchers with explicit unsupported/absent protocol and malformed input controls. Native positive execution is covered by the generated gRPC fixture. This is not an Apple Lib bridge acceptance. |\n\nThe crash fixture correction changes only one test file. It now requires the physically committed import, exact original author/claim/payload/receipt, zero metadata witnesses, the precise two pending reasons, no seal or conflict, and a nonmutating INCOMPLETE refusal for an empty seal both before the crash and after reopening. The original assertion, original failure, focused diff and revision custody are retained. The five RPC method and production source closure is unchanged; those methods were reused without rerunning.\n\nEvery original native account and complete command log remains in the private Oracle qualification directories under `/var/tmp/pinkha-e-cutover-current8ac-20261127`. Published receipts retain their hashes and paths. Private logs, wallet material and native account data are not part of this Git delivery. Package application is independently checked and each resulting file is compared with the reviewed manifest.\n\n## Remaining integration boundaries\n\nThe delivery qualifies native local signing, generated gRPC, crash recovery, signed host regressions and the supplied byte boundary. It does not establish real peer transport for cutover, an Apple framework/App build, Swift client acceptance, full-space index completeness, or UI acceptance. Swift canonical generation and the ownership adapter are a separate delivery; Wave3 must build the coherent native bridge/framework and App together before enabling the new native feature. Existing App15 binaries do not contain these new methods.\n\nThe retained earlier core and migration proofs keep their original source scope. This delivery does not relabel the original failed attempts, infer peer convergence from local completion, or rerun unchanged accepted migration evidence.\n")
 delivery={"status":"QUALIFIED_NATIVE_RPC_AND_REAL_PROCESS_CRASH","sourceManifestSHA256":EXPECTED,
  "requiredCoreCommit":"05c2f6d4f391a5b9d3dab7efa2987afd887a5f65","requiredCoreManifestSHA256":manifest["coreManifestSHA256"],
  "baseNativeManifestSHA256":"8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b",
  "nativePatch":base.row(patch),"nativeGeneratedRPC":True,"fiveRPCTestsReusedWithoutRerun":True,
  "realSIGKILLAndTwoNewProcesses":True,"osNetworkIsolated":True,"originalFailureReceiptsPreserved":True,
  "peerTransport":False,"appleBridge":False,"swiftClientAcceptance":False,"uiAcceptance":False,"extraQualifications":extra,
  "originalPrivateAccountsAndLogsRetained":True,"privateLogsPublished":False,
  "artifacts":{str(p.relative_to(DEST)):base.row(p) for p in sorted(DEST.rglob("*")) if p.is_file()},
  "completedUTC":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
 base.save(DEST/"delivery.json",delivery)
 print(json.dumps({"directory":str(DEST),"deliverySHA256":base.sha(DEST/"delivery.json"),"patchSHA256":base.sha(patch),"extraQualifications":list(extra)}))
if __name__=="__main__":main()
