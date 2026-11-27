#!/usr/bin/env python3
"""Qualify exact Swift owner/client files against canonical types and real native frames.

The focused Linux package omits Apple Lib and UI. Existing production sources are
copied byte-for-byte; response conformances are exact excerpts of the original
Sourcery output. This is not an Apple or native-authority acceptance substitute.
"""
import argparse,hashlib,json,os,re,shutil,signal,subprocess,time
from pathlib import Path
import qualify_current8ac_core as base
import cutover_retained_location as retained
import owned_swift_commands as owned
import qualify_cutover_swift_reuse_physical as reuse

CLIENT_GROWTH_CAP=192*1024**2
EVIDENCE_GROWTH_CAP=64*1024**2

REPO=base.HERE.parents[2]
BASE_COMMIT="4488a43443cbb09e25f02ae593d8cc8cb3d2b470"
MODULE="Modules/ProtobufMessages/"
GENERATED=[
 MODULE+"Sources/Protocol/Commands/Anytype_Rpc.Pinkha.swift",
 MODULE+"Sources/Protocol/Commands/Anytype_Rpc.Pinkha.TorahOperations.swift",
 MODULE+"Sources/Protocol/pinkha_torah_cutover.pb.swift"]
NAMES=[
 "testAllFiveMethodsDispatchWithTheOwnedFrozenScope",
 "testBothReadsRefuseOwnerRetirementWithoutReleasingPrivateResponse",
 "testThreeWritesRetainCommitAndAllNativeIssuesAfterOwnerRetirement",
 "testThreeWritesPreserveNativeFailureReceiptsWithoutRetry",
 "testCancellationAfterDispatchRetainsEachNativeAcknowledgement",
 "testCancellationBeforeValidatedHandoffNeverDispatches",
 "testRuntimeChangeAndRetiredLeaseRefuseBeforeNativeDispatch",
 "testTransportFailureIsUncertainAndNeverAutomaticallyRetried",
 "testMalformedOversizedAndVersionlessRepliesNeverInventCommitReceipts",
 "testForeignOrMismatchedAcknowledgementsNeverBecomeDurableReceipts",
 "testPrivateOrMalformedChangeIDsCannotCrossRetirementOrCancellation",
 "testNativeChangeIDGrammarRefusesNoncanonicalRepresentations",
 "testBareAcknowledgementsBindFullFrozenAuthorAndPayloadDigest",
 "testForeignSpaceAndReplacementCannotReuseOldOwner",
 "testOwnedTaskKeepsOriginalRequestBytesWhileCallerValueChanges"]
EXPECTED={"PinkhaHeartCutoverClientTests."+x for x in NAMES}|{
 "PinkhaHeartCutoverInteropTests.testAllFiveSwiftMethodsDecodeExactCapturedNativeFrames",
 "PinkhaHeartCutoverInteropTests.testCanonicalIdentityMatchesEveryCapturedSignedClaim"}
FRAMES=["source-read-response.pb","begin-request.pb","begin-response.pb","frozen-import-request.pb",
 "frozen-import-response.pb","association-append-request.pb","association-append-response.pb",
 "sealed-unlinked-read-response.pb"]
def git(rel):return subprocess.check_output(["git","-C",str(REPO),"show",BASE_COMMIT+":"+rel])
def main():
 owned.install_interrupt_handlers()
 ap=argparse.ArgumentParser()
 ap.add_argument("--root",required=True,type=Path)
 ap.add_argument("--generated-root",required=True,type=Path)
 ap.add_argument("--native-root",required=True,type=Path)
 ap.add_argument("--rpc-manifest-sha",required=True)
 ap.add_argument("--build-root",required=True,type=Path)
 ap.add_argument("--custody-receipt",required=True,type=Path)
 ap.add_argument("--custody-sha",required=True)
 a=ap.parse_args();os.umask(0o077)
 assert a.root==retained.SUCCESSOR_PARENT/"swift-client-physical4", "this allocation admits one fresh attempt only"
 root=retained.reserve_successor_output(a.root,"swift-client")
 build_root=a.build_root
 assert build_root!=root
 if build_root!=root:
  assert build_root.parent==Path("/mnt/development/projects/caches") and build_root.parent.resolve()==build_root.parent
  assert build_root.name=="pinkha-e-cutover-"+root.name+"-20261127" and not build_root.exists()
  build_root.mkdir(mode=0o700)
 result={"status":"FAIL","nativeAcceptance":False,"appleAcceptance":False,
  "scope":"Exact production Swift owner/client + canonical generated protocol + captured actual native frames",
  "controllerSHA256":base.sha(Path(__file__)),"commands":[],"buildRoot":str(build_root),
  "ownedBuildGrowthCapBytes":CLIENT_GROWTH_CAP,"ownedEvidenceGrowthCapBytes":EVIDENCE_GROWTH_CAP}
 original_live={}
 def owned_bytes():
  total=0;count=0
  for directory,dirs,files in os.walk(build_root,followlinks=False):
   dirs[:]=[name for name in dirs if not (Path(directory)/name).is_symlink()]
   for name in files:
    p=Path(directory)/name
    try:
     info=p.lstat()
     if p.is_symlink():continue
    except FileNotFoundError:continue
    count+=1;assert count<=15000,"unexpected focused client output topology"
    total+=max(info.st_size,info.st_blocks*512)
  return total
 def evidence_bytes():
  total=0;count=0
  for directory,dirs,files in os.walk(root,followlinks=False):
   assert not any((Path(directory)/name).is_symlink() for name in dirs),"unexpected evidence alias"
   for name in files:
    p=Path(directory)/name
    try:info=p.lstat()
    except FileNotFoundError:continue
    assert not p.is_symlink(),"unexpected evidence alias"
    count+=1;assert count<=20000,"bounded successor evidence topology"
    total+=max(info.st_size,info.st_blocks*512)
  return total
 def put(rel,data):
  p=root/"package"/rel;p.parent.mkdir(parents=True,exist_ok=True);assert not p.exists();p.write_bytes(data);return p
 def run(label,argv,env,timeout):
  cwd=root/"package"
  statistics={"sampledOwnedBytesPeak":owned_bytes(),"resourceSamples":0}
  def observe():
   used=owned_bytes();statistics["sampledOwnedBytesPeak"]=max(statistics["sampledOwnedBytesPeak"],used);statistics["resourceSamples"]+=1
   if used>=CLIENT_GROWTH_CAP:return "owned client output growth cap"
   if evidence_bytes()>=EVIDENCE_GROWTH_CAP:return "owned successor evidence growth cap"
   if shutil.disk_usage("/").free<2*1024**3:return "root reserve"
   if shutil.disk_usage(base.CACHE).free<512*1024**2:return "development reserve"
   return None
  log,row=owned.run(root/"commands"/label,argv,cwd,env,timeout,observe,base.save,base.sha,result["commands"],statistics)
  return log

 try:
  # The original 128 MiB allocation stopped at 43/60 compile tasks.
  # A separately reviewed 192 MiB allocation admits a fresh package only; no
  # failed partial product is reused and no functional/identity gate changes.
  prior_path=retained.SUCCESSOR_PARENT/"swift-client-physical3/receipt.json"
  prior_pin="de50efc7cfb94ace6bc6b502fb1653ea1beeabc36043f5e7191e0c8a355a7047"
  prior=json.loads(base.pinned(prior_path,prior_pin).read_text())
  assert prior["status"]=="FAIL" and prior["error"]=="RuntimeError: owned client output growth cap"
  assert prior["controllerSHA256"]=="80488d446e2c5e61f36411e79767520504f59d5de976fab5674bd6afa8915315"
  assert prior["ownedBuildGrowthCapBytes"]==128*1024**2 and prior["ownedEvidenceGrowthCapBytes"]==EVIDENCE_GROWTH_CAP
  assert len(prior["commands"])==1 and prior["commands"][0]["sampledOwnedBytesPeak"]==134627328
  assert prior["commands"][0]["processGroupAbsent"] and prior["commands"][0]["cleanupErrors"]==[]
  closed_path=retained.PARENT/"controls/client-physical3-final-inputs1/result.json"
  closed_pin="793f3da4ec4bd9414f1c6996e093076d85ba7228cf6ef1f7256e9204cb3d8d58"
  closed=json.loads(base.pinned(closed_path,closed_pin).read_text())
  assert closed["status"]=="PASS_CLOSED_FAILED_COMPILE_INPUTS_UNCHANGED_NO_TEST_ACCEPTANCE"
  assert closed["failedReceipt"]["sha256"]==prior_pin
  original_live[str(prior_path)]=base.row(prior_path);original_live[str(closed_path)]=base.row(closed_path)
  result["explicitResourceAllocation"]={"buildBytes":CLIENT_GROWTH_CAP,"evidenceBytes":EVIDENCE_GROWTH_CAP,
   "previousAllocationBytes":128*1024**2,"previousMeasuredBuildPeakBytes":134627328,
   "previousFailureReceipt":{"path":str(prior_path),**base.row(prior_path)},
   "previousClosedInputsReceipt":{"path":str(closed_path),**base.row(closed_path)},
   "freshAttempt":True,"previousPartialProductsReused":False,"functionalAcceptanceUnchanged":True}
  result["relocatedSourceAdmission"]=retained.qualify(a.custody_receipt,a.custody_sha)
  assert a.native_root==retained.RUN/"rpc-core-attempt5" and a.native_root.resolve()==a.native_root
  base.pinned(a.native_root/"receipt.json",retained.RECEIPT_PINS["rpc-core-attempt5/receipt.json"])
  assert a.generated_root.parent==retained.SUCCESSOR_PARENT and re.fullmatch(r"swift-generation-physical[1-9][0-9]{0,2}",a.generated_root.name)
  assert a.generated_root.resolve()==a.generated_root
  assert re.fullmatch("[a-f0-9]{64}",a.rpc_manifest_sha)
  base.pinned(base.HERE/"rpc-source-candidate.json",a.rpc_manifest_sha)
  generated=json.loads((a.generated_root/"receipt.json").read_text())
  assert generated["status"]=="CANONICAL_SWIFT_GENERATED_NOT_RUNTIME_ACCEPTANCE"
  assert generated["rpcManifestSHA256"]==a.rpc_manifest_sha
  assert generated["relocatedSourceAdmission"]["custodySHA256"]==retained.CUSTODY_SHA
  assert generated["relocatedSourceAdmission"]["exactOriginalToPhysicalRoots"]==retained.ROOT_MAP
  assert generated["generatorCommit"]=="c6fe6442e6a64250495669325044052e113e990c"
  native=json.loads((a.native_root/"receipt.json").read_text())
  assert native["status"]=="PASS_GENERATED_GRPC_AND_OFFLINE_PROCESS_CRASH_NOT_PEER_OR_APPLE"
  assert native["manifestSHA256"]==a.rpc_manifest_sha and native["retainedSourceUnchanged"]
  result["nativeReceipt"]={"path":str(a.native_root/"receipt.json"),**base.row(a.native_root/"receipt.json")}
  result["generatorReceipt"]={"path":str(a.generated_root/"receipt.json"),**base.row(a.generated_root/"receipt.json")}
  original_wire=a.native_root/"private/TestPinkhaTorahCutoverActualGeneratedRPCAndReopen"
  wire=root/"captured-native-frames";wire.mkdir(mode=0o700)
  wire_manifest={}
  for name in FRAMES:
   p=original_wire/name
   assert p.is_file() and not p.is_symlink()
   rel=str(p.relative_to(retained.RUN))
   retained.verify_file(retained.RUN,rel,retained.manifest("current8ac")[rel])
   before=base.row(p);shutil.copyfile(p,wire/name);assert base.row(wire/name)==before
   wire_manifest[name]=before;original_live[str(p)]=before
  base.save(root/"native-wire-manifest.json",wire_manifest)

  source_rows={}
  # The handwritten boundary and existing lifetime observer remain the exact
  # production source, including their real account-response activation rules.
  for rel in [MODULE+"Sources/PinkhaHeartCutoverClient.swift",MODULE+"Sources/PinkhaHeartCutoverIdentity.swift"]:
   p=REPO/rel;original_live[str(p)]=base.row(p)
   dest=put("Sources/ProtobufMessages/"+p.name,p.read_bytes());source_rows[rel]=base.row(dest)
  for rel in [MODULE+"Sources/PinkhaNativeReadLifetime.swift",MODULE+"Sources/ResponceProtocols.swift"]:
   data=git(rel);dest=put("Sources/ProtobufMessages/"+Path(rel).name,data);source_rows[rel]=base.row(dest)
  for rel in GENERATED:
   p=REPO/rel;assert base.row(p)==generated["generatedFiles"][rel]
   original_live[str(p)]=base.row(p)
   dest=put("Sources/ProtobufMessages/Protocol/"+p.name,p.read_bytes());source_rows[rel]=base.row(dest)
  for rel in [MODULE+"Tests/ProtobufMessagesTests/PinkhaHeartCutoverClientTests.swift",
              str((base.HERE/"swift/Tests/PinkhaHeartCutoverInteropTests.swift").relative_to(REPO))]:
   p=REPO/rel;original_live[str(p)]=base.row(p)
   dest=put("Tests/ProtobufMessagesTests/"+p.name,p.read_bytes());source_rows[rel]=base.row(dest)

  # Preserve the original generated conformance bodies; no fixture protocol,
  # hand-authored Account model, or weakened lifetime checker is introduced.
  rel=MODULE+"Sources/Generated/CommandsInvocation/invocation-adoption.generated.swift"
  adoption=git(rel).decode();excerpts=[]
  for symbol in ["Anytype_Rpc.Account.Create.Response","Anytype_Rpc.Account.Select.Response","Anytype_Rpc.Workspace.Open.Response"]:
   pattern=r"extension "+re.escape(symbol)+r": ResultWithError \{\}\n"+"extension "+re.escape(symbol)+r"\.Error: ResponseError \{\n.*?\n\}"
   matches=re.findall(pattern,adoption,re.S);assert len(matches)==1,symbol
   excerpts.append(matches[0])
  conformance=put("Sources/ProtobufMessages/OriginalResponseConformances.swift",
   ("// Exact excerpts of the production Sourcery output.\n"+"\n\n".join(excerpts)+"\n").encode())
  source_rows[rel]={"originalSHA256":hashlib.sha256(adoption.encode()).hexdigest(),
   "exactExcerptSHA256":base.sha(conformance),"symbols":["Account.Create.Response","Account.Select.Response","Workspace.Open.Response"]}
  paths=subprocess.check_output(["git","-C",str(REPO),"ls-tree","-r","--name-only",BASE_COMMIT,MODULE+"Sources/Protocol"],text=True).splitlines()
  by_type={Path(p).stem:p for p in paths if p.endswith(".swift") and Path(p).stem.startswith("Anytype_")}
  # Original aggregate protobuf files do not use a type name as their filename.
  # Resolve their actual public declarations, retaining complete original bytes
  # only when a referenced symbol pulls that file into the closure below.
  aggregate_declarations={}
  for rel in paths:
   if not rel.endswith(".pb.swift") or Path(rel).stem.startswith("Anytype_"):continue
   data=git(rel)
   declarations=re.findall(r"\bpublic (?:struct|enum) (Anytype_[A-Za-z0-9_]+)\b",data.decode())
   assert declarations and len(declarations)==len(set(declarations)),rel
   aggregate_declarations[rel]={"sha256":hashlib.sha256(data).hexdigest(),"symbols":declarations}
   for symbol in declarations:
    assert symbol not in by_type or by_type[symbol]==rel,symbol
    by_type[symbol]=rel
  assert set(aggregate_declarations)=={MODULE+"Sources/Protocol/export_report.pb.swift",MODULE+"Sources/Protocol/localstore.pb.swift"}
  result["originalAggregateDeclarations"]=aggregate_declarations
  # New canonical namespace declarations supersede no original declaration.
  provided={"Anytype_PinkhaTorahCutover","Anytype_Rpc.Pinkha","Anytype_Rpc.Pinkha.TorahOperations"}
  seen=set();queue=[p for p in (root/"package").rglob("*.swift")]
  while queue:
   p=queue.pop()
   refs=re.findall(r"\bAnytype_[A-Za-z0-9_]+(?:\.[A-Za-z_][A-Za-z0-9_]*)*",p.read_text())
   for ref in refs:
    pieces=ref.split(".")
    for n in range(1,len(pieces)+1):
     symbol=".".join(pieces[:n])
     if symbol in provided or symbol not in by_type:continue
     rel=by_type[symbol]
     if rel in seen:continue
     seen.add(rel);data=git(rel)
     dest=put("Sources/ProtobufMessages/Protocol/"+Path(rel).name,data)
     source_rows[rel]=base.row(dest);queue.append(dest)
  assert len(seen)>5
  dependency=Path(generated["generatorCheckout"])
  assert subprocess.check_output(["git","-C",str(dependency),"rev-parse","HEAD"],text=True).strip()==generated["generatorCommit"]
  crypto=reuse.CACHE/"checkouts/swift-crypto"
  asn1=crypto.parent/"swift-asn1"
  dependencies=[(dependency,generated["generatorCommit"]),(crypto,"e8d6eba1fef23ae5b359c46b03f7d94be2f41fed"),(asn1,"917b472dbe53ba699cbb0495f9a95a084bc6364d")]
  dependency_rows={}
  for checkout,pin in dependencies:
   assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==pin
   assert subprocess.check_output(["git","-C",str(checkout),"status","--porcelain"],text=True).strip()==""
   tracked=subprocess.check_output(["git","-C",str(checkout),"ls-files","-z"]).decode().split("\0")
   dependency_rows[str(checkout)]={"commit":pin,"trackedFiles":{rel:base.row(checkout/rel) for rel in tracked if rel and (checkout/rel).is_file()}}
  base.save(root/"dependency-before.json",dependency_rows)
  reused=reuse.qualify(generated,dependency,crypto,asn1,root,base)
  original_live.update(reused["immutableInputs"])
  result["reusedCompilerProducts"]=reused["receipt"]
  compiler_flags=reused["compilerFlags"]
  link_objects=reused["linkObjects"]
  package='''// swift-tools-version:6.0
import PackageDescription
let imports: [String] = COMPILER_FLAGS
let objects: [String] = LINK_OBJECTS
let package = Package(name: "CutoverClientQualification",
 targets: [
  .target(name: "ProtobufMessages",
    swiftSettings: [.swiftLanguageMode(.v6), .define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1"), .unsafeFlags(imports)]),
  .testTarget(name: "ProtobufMessagesTests", dependencies: ["ProtobufMessages"],
    swiftSettings: [.swiftLanguageMode(.v6), .define("PINKHA_NATIVE_T2_AUTHORIZED_READ_V1"), .unsafeFlags(imports)],
    linkerSettings: [.unsafeFlags(objects), .linkedLibrary("stdc++")])
 ])
'''.replace("COMPILER_FLAGS",json.dumps(compiler_flags)).replace("LINK_OBJECTS",json.dumps(link_objects))
  put("Package.swift",package.encode())
  base.save(root/"source-inputs.json",source_rows)
  base.save(root/"package-before.json",{str(p.relative_to(root/"package")):base.row(p) for p in sorted((root/"package").rglob("*")) if p.is_file()})
  result["resourceAdmission"]={x:shutil.disk_usage(x).free for x in ["/","/mnt/development"]}
  minimum_root=2*1024**3+128*1024**2
  minimum_development=512*1024**2+CLIENT_GROWTH_CAP+EVIDENCE_GROWTH_CAP
  result["resourcePolicy"]={"rootAdmissionBytes":minimum_root,"developmentAdmissionBytes":minimum_development,
   "rootRuntimeFloorBytes":2*1024**3,"developmentRuntimeFloorBytes":512*1024**2,"ownedBuildGrowthCapBytes":CLIENT_GROWTH_CAP,"ownedEvidenceGrowthCapBytes":EVIDENCE_GROWTH_CAP}
  assert result["resourceAdmission"]["/"]>minimum_root and result["resourceAdmission"]["/mnt/development"]>minimum_development,"coordinated Swift reserve unavailable"
  temporary=build_root/"temporary";temporary.mkdir()
  env=dict(os.environ,GIT_OPTIONAL_LOCKS="0",TMPDIR=str(temporary),SWIFTPM_MODULECACHE_OVERRIDE=str(build_root/"module-cache"),
   CLANG_MODULE_CACHE_PATH=str(build_root/"clang-module-cache"),SWIFTCI_USE_LOCAL_DEPS="1",PROTOBUF_NO_PROTOC="1",
   PINKHA_CUTOVER_NATIVE_WIRE_ROOT=str(wire),PINKHA_CUTOVER_NATIVE_RPC_MANIFEST=a.rpc_manifest_sha)
  swift=reused["swiftDriver"];assert Path(swift).is_file()
  # Swift 6.4 XCTest discovery requires its normal index; the same owned-output
  # growth cap remains enforced while that canonical discovery runs.
  log=run("exact-swift-client-tests",[swift,"test","--package-path",str(root/"package"),"--scratch-path",str(build_root/"swift-build"),
   "--cache-path",str(build_root/"swiftpm-cache"),"--jobs","1","-Xswiftc","-gnone","--filter","PinkhaHeartCutover(Client|Interop)Tests",
   "--xunit-output",str(root/"tests.xml")],env,900)
  matches=re.findall(r"Test Case '([^']+)' (started|passed|failed|skipped)",log.read_text())
  starts=[name for name,state in matches if state=="started"]
  passes=[name for name,state in matches if state=="passed"]
  assert sorted(starts)==sorted(EXPECTED) and sorted(passes)==sorted(EXPECTED),(starts,passes)
  assert not any(state in ["failed","skipped"] for name,state in matches)
  reuse.validate_modes(reused)
  for p,want in original_live.items():assert base.row(Path(p))==want,p+" changed during qualification"
  for directory,evidence in dependency_rows.items():
   checkout=Path(directory)
   assert subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()==evidence["commit"]
   assert subprocess.check_output(["git","-C",str(checkout),"status","--porcelain"],text=True).strip()==""
   for rel,want in evidence["trackedFiles"].items():assert base.row(checkout/rel)==want,str(checkout/rel)+" dependency changed"
  result["dependencies"]={p:{"commit":e["commit"],"trackedFiles":len(e["trackedFiles"])} for p,e in dependency_rows.items()}
  result["dependencyManifestSHA256"]=base.sha(root/"dependency-before.json")
  before=json.loads((root/"package-before.json").read_text())
  assert {str(p.relative_to(root/"package")):base.row(p) for p in sorted((root/"package").rglob("*")) if p.is_file()}==before
  result.update(status="PASS_EXACT_SWIFT_CLIENT_OWNERSHIP_AND_CAPTURED_NATIVE_WIRE",
   methods=sorted(EXPECTED),skips=0,sourceFiles=source_rows,sourceBaseCommit=BASE_COMMIT,
   rpcManifestSHA256=a.rpc_manifest_sha,capturedNativeFrames=wire_manifest,
   sourceInputSHA256=base.sha(root/"source-inputs.json"),originalSourcesAndFramesUnchanged=True)
 except Exception as error:result["error"]=type(error).__name__+": "+str(error)
 finally:
  owned.ignore_interrupts()
  completion_errors=[]
  try:
   result["ownedEvidenceBytesAtCompletion"]=evidence_bytes()
   if result["ownedEvidenceBytesAtCompletion"]>=EVIDENCE_GROWTH_CAP:
    completion_errors.append("owned successor evidence growth cap")
  except Exception as error:
   completion_errors.append("completion accounting: "+type(error).__name__+": "+str(error))
  result["completionErrors"]=completion_errors
  if completion_errors:
   result["status"]="FAIL";result.setdefault("error",completion_errors[0])
  result["completedUTC"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
  receipt_retained=False
  try:
   base.save(root/"receipt.json",result);receipt_retained=True
  except Exception as error:
   completion_errors.append("receipt retention: "+type(error).__name__+": "+str(error))
   result["status"]="FAIL";result.setdefault("error",completion_errors[-1])
 print(json.dumps({"status":result["status"],"error":result.get("error"),"completionErrors":result["completionErrors"],"receiptRetained":receipt_retained,"receipt":str(root/"receipt.json")}))
 return 0 if result["status"]=="PASS_EXACT_SWIFT_CLIENT_OWNERSHIP_AND_CAPTURED_NATIVE_WIRE" else 1
if __name__=="__main__":raise SystemExit(main())
