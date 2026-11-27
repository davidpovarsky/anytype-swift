#!/usr/bin/env python3
"""Canonical Swift RPC generation; never substitutes fixtures for protocol authority."""
import argparse,hashlib,json,os,re,shutil,signal,subprocess,time
from pathlib import Path
import qualify_current8ac_core as base
import cutover_retained_location as retained
import owned_swift_commands as owned

REPO=base.HERE.parents[2]
PIN="c6fe6442e6a64250495669325044052e113e990c"
PROTOC=retained.BASE.parent/"rpc-toolchain/bin/protoc"
PROTOC_SHA="aa609ec1d4b08375a140b1a42340684932cd2cd0cd56ffe8d791a72f9f3894bc"
BASE_COMMIT="4488a43443cbb09e25f02ae593d8cc8cb3d2b470"
SPLITTER="Tools/anytype-swift-filesplit/Sources/AnytypeSwiftFilesplit/"
TARGETS={
 "Anytype_Rpc.Pinkha.swift":"Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Pinkha.swift",
 "Anytype_Rpc.Pinkha.TorahOperations.swift":"Modules/ProtobufMessages/Sources/Protocol/Commands/Anytype_Rpc.Pinkha.TorahOperations.swift",
 "pinkha_torah_cutover.pb.swift":"Modules/ProtobufMessages/Sources/Protocol/pinkha_torah_cutover.pb.swift"}
GENERATOR_GROWTH_CAP=256*1024**2
EVIDENCE_GROWTH_CAP=64*1024**2
WRAPPER=r'''import Foundation
@main
struct CanonicalSplitCommand {
    static func main() throws {
        let args = CommandLine.arguments
        precondition(args.count == 3)
        let source = try String(contentsOfFile: args[1], encoding: .utf8)
        let destination = URL(fileURLWithPath: args[2], isDirectory: true)
        precondition(!FileManager.default.fileExists(atPath: destination.path))
        try FileManager.default.createDirectory(at: destination, withIntermediateDirectories: true)
        let rows = FileSplitrer(source: source, otherName: "commands-other.swift", maxDepth: 3).split()
        precondition(Set(rows.map(\.fileName)).count == rows.count)
        for row in rows.sorted(by: { $0.fileName < $1.fileName }) {
            precondition(!row.fileName.contains("/") && row.fileName.hasSuffix(".swift"))
            try row.source.write(to: destination.appendingPathComponent(row.fileName), atomically: true, encoding: .utf8)
        }
    }
}
'''
def main():
 owned.install_interrupt_handlers()
 ap=argparse.ArgumentParser();ap.add_argument("--root",required=True,type=Path);ap.add_argument("--rpc-manifest-sha",required=True);ap.add_argument("--checkout",required=True,type=Path);ap.add_argument("--build-root",required=True,type=Path);ap.add_argument("--custody-receipt",required=True,type=Path);ap.add_argument("--custody-sha",required=True);a=ap.parse_args()
 os.umask(0o077);root=retained.reserve_successor_output(a.root,"swift-generation")
 build_root=a.build_root
 assert build_root!=root
 if build_root!=root:
  assert build_root.parent==Path("/mnt/development/projects/caches") and build_root.parent.resolve()==build_root.parent
  assert build_root.name=="pinkha-e-cutover-"+root.name+"-20261127" and not build_root.exists()
  build_root.mkdir(mode=0o700)
 result={"status":"FAIL","nativeAcceptance":False,"appleAcceptance":False,"commands":[],"controllerSHA256":base.sha(Path(__file__)),"buildRoot":str(build_root),
  "scope":"Canonical protoc-gen-swift only, three original targets; no tests/client/Crypto/index store or downloaded protoc",
  "ownedBuildGrowthCapBytes":GENERATOR_GROWTH_CAP,"ownedEvidenceGrowthCapBytes":EVIDENCE_GROWTH_CAP}
 source=retained.BASE/"source";expected=None
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
    count+=1;assert count<=20000,"unexpected generator output topology"
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
 def run(label,argv,cwd,timeout=900):
  env=dict(os.environ,GIT_OPTIONAL_LOCKS="0",TMPDIR=str(build_root/"temporary"),SWIFTPM_MODULECACHE_OVERRIDE=str(build_root/"module-cache"),CLANG_MODULE_CACHE_PATH=str(build_root/"clang-module-cache"),PROTOBUF_NO_PROTOC="1")
  statistics={"sampledOwnedBytesPeak":owned_bytes(),"resourceSamples":0}
  def observe():
   used=owned_bytes();statistics["sampledOwnedBytesPeak"]=max(statistics["sampledOwnedBytesPeak"],used);statistics["resourceSamples"]+=1
   if used>=GENERATOR_GROWTH_CAP:return "owned generator output growth cap"
   if evidence_bytes()>=EVIDENCE_GROWTH_CAP:return "owned successor evidence growth cap"
   if shutil.disk_usage("/").free<2*1024**3:return "root reserve"
   if shutil.disk_usage(base.CACHE).free<512*1024**2:return "development reserve"
   return None
  log,row=owned.run(root/"commands"/label,argv,cwd,env,timeout,observe,base.save,base.sha,result["commands"],statistics)
  return log.read_text()

 try:
  result["relocatedSourceAdmission"]=retained.qualify(a.custody_receipt,a.custody_sha)
  result["retainedGeneratorSourceAdmission"]=retained.verify_subtree("current8ac","swift-protobuf-source1/swift-protobuf")
  result["retainedProtocSourceAdmission"]=retained.verify_subtree("current8ac","rpc-toolchain")
  result["resourceAdmission"]={p:shutil.disk_usage(p).free for p in ["/","/mnt/development"]}
  minimum_root=2*1024**3+128*1024**2
  minimum_development=512*1024**2+GENERATOR_GROWTH_CAP+EVIDENCE_GROWTH_CAP
  result["resourcePolicy"]={"rootAdmissionBytes":minimum_root,"developmentAdmissionBytes":minimum_development,
   "rootRuntimeFloorBytes":2*1024**3,"developmentRuntimeFloorBytes":512*1024**2,"ownedBuildGrowthCapBytes":GENERATOR_GROWTH_CAP,"ownedEvidenceGrowthCapBytes":EVIDENCE_GROWTH_CAP}
  assert result["resourceAdmission"]["/"]>minimum_root and result["resourceAdmission"]["/mnt/development"]>minimum_development,"coordinated generator reserve unavailable"
  (build_root/"temporary").mkdir(mode=0o700)
  expected=json.loads(base.pinned(retained.BASE/"source-before.json",retained.SOURCE_MANIFEST).read_text())
  manifest=json.loads(base.pinned(base.HERE/"rpc-source-candidate.json",a.rpc_manifest_sha).read_text())
  native=source/"heart"
  commands=native/"pb/protos/commands.proto"
  assert base.row(commands)==expected["heart/pb/protos/commands.proto"]
  assert base.row(base.HERE/"overlay/pb/protos/pinkha_torah_cutover.proto")==manifest["files"]["pb/protos/pinkha_torah_cutover.proto"]["after"]
  protoc=base.pinned(PROTOC,PROTOC_SHA)
  module_path=retained.RUN/"rpc-generation1/generator-module.json"
  retained.verify_file(retained.RUN,"rpc-generation1/generator-module.json",retained.manifest("current8ac")["rpc-generation1/generator-module.json"])
  module=json.loads(module_path.read_text())
  replacement=module["Replace"]
  assert replacement["Path"]=="github.com/anyproto/protobuf" and replacement["Version"]=="v1.3.3-0.20240201225420-6e325cf0ac38"
  checkout=a.checkout or root/"swift-protobuf"
  if a.checkout is None:
   run("clone-original-generator",["git","clone","--depth=1","--branch=1.32.0","https://github.com/apple/swift-protobuf.git",str(checkout)],root,180)
  else:
   assert checkout==retained.BASE.parent/"swift-protobuf-source1/swift-protobuf"
   assert checkout.is_dir() and checkout.resolve()==checkout
   assert run("generator-original-remote",["git","config","--get","remote.origin.url"],checkout,30).strip()=="https://github.com/apple/swift-protobuf.git"
   assert run("generator-clean-source",["git","status","--porcelain"],checkout,30).strip()==""
   source_receipt=checkout.parent/"receipt.json"
   pinned_source=json.loads(source_receipt.read_text())
   assert pinned_source["status"]=="PINNED_ORIGINAL_SWIFT_PROTOBUF_SOURCE_ONLY" and pinned_source["commit"]==PIN
   result["reusedPinnedSourceReceipt"]={"path":str(source_receipt),**base.row(source_receipt)}
  result["generatorCheckout"]=str(checkout)
  assert run("generator-commit",["git","rev-parse","HEAD"],checkout,30).strip()==PIN
  run("generator-objects",["git","fsck","--full"],checkout,60)
  swift=Path(shutil.which("swift"));swiftc=Path(shutil.which("swiftc"))
  result["swift"]={"path":str(swift),"sha256":base.sha(swift),"version":run("swift-version",[str(swift),"--version"],root,30)}
  result["generatorCommit"]=PIN
  result["originalGeneratorSource"]={str(p.relative_to(checkout)):base.row(p) for p in sorted(checkout.rglob("*")) if p.is_file() and ".git" not in p.parts}
  scope={}
  for name in ["SwiftProtobuf","SwiftProtobufPluginLibrary","protoc-gen-swift"]:
   files=[p for p in (checkout/"Sources"/name).rglob("*") if p.is_file()]
   scope[name]={"files":len(files),"bytes":sum(p.stat().st_size for p in files),"swiftFiles":sum(p.suffix==".swift" for p in files)}
  assert scope=={"SwiftProtobuf":{"files":98,"bytes":1169113,"swiftFiles":94},"SwiftProtobufPluginLibrary":{"files":29,"bytes":219582,"swiftFiles":26},"protoc-gen-swift":{"files":27,"bytes":175443,"swiftFiles":24}}
  result["exactGeneratorScope"]=scope
  build=build_root/"swift-build"
  run("build-original-generator",[str(swift),"build","--scratch-path",str(build),"--cache-path",str(build_root/"swiftpm-cache"),"--product","protoc-gen-swift","--configuration","debug","--jobs","1","--disable-index-store","-Xswiftc","-gnone"],checkout,900)
  # Ask the original SwiftPM driver for its product path. Swift 6.4's native
  # build system uses out/Products; older llbuild uses <triple>/debug. Neither
  # topology is inferred from a guessed directory glob.
  product_text=run("original-generator-product-path",[str(swift),"build","--scratch-path",str(build),
   "--cache-path",str(build_root/"swiftpm-cache"),"--configuration","debug","--show-bin-path"],checkout,60).strip()
  product=Path(product_text)
  assert product.is_absolute() and product.is_dir() and product.resolve().is_relative_to(build.resolve())
  plugin=product/"protoc-gen-swift";assert plugin.is_file() and not plugin.is_symlink()
  result["generatorBinary"]=base.row(plugin)
  result["generatorProductDirectory"]=str(product)
  generated=root/"generated";generated.mkdir()
  prefix=[str(protoc),"--plugin=protoc-gen-swift="+str(plugin),"-I",str(base.HERE/"overlay"),"-I",str(native),"-I",str(PROTOC.parent.parent/"include"),"-I",replacement["Dir"]]
  run("canonical-swift-generation",prefix+["--swift_opt=Visibility=Public","--swift_out="+str(generated),"pb/protos/commands.proto","pb/protos/pinkha_torah_cutover.proto"],root,120)
  commands_generated=list(generated.rglob("commands.pb.swift"));cutover_generated=list(generated.rglob("pinkha_torah_cutover.pb.swift"))
  assert len(commands_generated)==len(cutover_generated)==1
  split_source=root/"split-source";split_source.mkdir()
  exact={}
  for name in ["Parser.swift","MemberTypeSyntax+Extension.swift"]:
   original=subprocess.check_output(["git","-C",str(REPO),"show",BASE_COMMIT+":"+SPLITTER+name])
   p=split_source/name;p.write_bytes(original);exact[SPLITTER+name]=base.row(p)
  wrapper=split_source/"CanonicalSplitCommand.swift";wrapper.write_text(WRAPPER)
  host=swiftc.resolve().parent.parent/"lib/swift/host"
  assert (host/"SwiftSyntax.swiftmodule").exists() and (host/"SwiftParser.swiftmodule").exists()
  splitter=build_root/"canonical-filesplit"
  run("build-original-splitter",[str(swiftc),"-parse-as-library","-I",str(host),"-L",str(host),"-Xlinker","-rpath","-Xlinker",str(host),
       str(split_source/"Parser.swift"),str(split_source/"MemberTypeSyntax+Extension.swift"),str(wrapper),"-o",str(splitter)],root,180)
  split=root/"split"
  run("split-original-commands",[str(splitter),str(commands_generated[0]),str(split)],root,120)
  outputs={}
  for name,rel in TARGETS.items():
   src=cutover_generated[0] if name=="pinkha_torah_cutover.pb.swift" else split/name
   assert src.is_file() and b"SwiftProtobuf" in src.read_bytes()
   destination=REPO/rel
   assert not destination.exists(),"never replace an existing protocol file"
   destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,destination)
   outputs[rel]=base.row(destination)
  for rel,want in result["originalGeneratorSource"].items():assert base.row(checkout/rel)==want
  assert base.row(commands)==expected["heart/pb/protos/commands.proto"]
  result.update(status="CANONICAL_SWIFT_GENERATED_NOT_RUNTIME_ACCEPTANCE",generatedFiles=outputs,
     rpcManifestSHA256=a.rpc_manifest_sha,protoInputs={"commands.proto":base.row(commands),"pinkha_torah_cutover.proto":base.row(base.HERE/"overlay/pb/protos/pinkha_torah_cutover.proto")},
     originalSplitterSources=exact,splitterBinary=base.row(splitter),splitterWrapper=base.row(wrapper),
     protocolFilesReplaced=0,sourceBaseCommit=BASE_COMMIT)
 except Exception as e:result["error"]=type(e).__name__+": "+str(e)
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
 return 0 if result["status"]=="CANONICAL_SWIFT_GENERATED_NOT_RUNTIME_ACCEPTANCE" else 1
if __name__=="__main__":raise SystemExit(main())
