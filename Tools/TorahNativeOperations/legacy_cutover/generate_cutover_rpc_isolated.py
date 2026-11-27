#!/usr/bin/env python3
"""Generate additive cutover RPC in an isolated Go package with unchanged wire identity."""
import argparse,json,os,shutil,subprocess,time
from pathlib import Path
import qualify_current8ac_core as base
import continue_current8ac_core as retained
import generate_cutover_rpc as canonical

PRIOR=retained.BASE.parent/"rpc-generation1"
SUPERSEDED=retained.BASE.parent/"rpc-package-boundary-revision1"
SUPERSEDED_SHA="74b2efd9a679a69e57e9a1d8b7e9288e1bdaab228c3b20b80e4193a72a1178e5"
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);ap.add_argument("--generator-receipt-sha",required=True);a=ap.parse_args()
 root=a.root;assert root.is_absolute() and root.parent==retained.BASE.parent and not root.exists()
 os.umask(0o077);root.mkdir(mode=0o700)
 result={"status":"FAIL","nativeAcceptance":False,"commands":[],"controllerSHA256":base.sha(Path(__file__))}
 try:
  prior=json.loads(base.pinned(PRIOR/"receipt.json",a.generator_receipt_sha).read_text())
  assert prior["status"]=="GENERATED_CANDIDATE_NOT_NATIVE_ACCEPTANCE"
  plugin=base.pinned(PRIOR/"protoc-gen-gogofaster",prior["generatorSHA256"])
  protoc=base.pinned(canonical.TOOLS/"bin/protoc",canonical.PROTOC_SHA)
  superseded=json.loads(base.pinned(SUPERSEDED/"superseded-candidate.json",SUPERSEDED_SHA).read_text())
  proto=base.HERE/"overlay/pb/protos/pinkha_torah_cutover.proto"
  old=SUPERSEDED/"source/pb/protos/pinkha_torah_cutover.proto"
  assert old.read_text().count('option go_package = "pb";')==1
  assert proto.read_text()==old.read_text().replace('option go_package = "pb";','option go_package = "cutoverpb";')
  module=json.loads((PRIOR/"generator-module.json").read_text());replacement=module["Replace"]
  assert replacement["Path"]=="github.com/anyproto/protobuf" and replacement["Version"]=="v1.3.3-0.20240201225420-6e325cf0ac38"
  assert replacement["Sum"]=="h1:80jke82/c+bNQQpnx4VO3Mi/lAxARyyfUpZvFaPxdzE="
  native=canonical.SOURCE/"heart"
  original_pb={str(p.relative_to(native)):base.row(p) for p in sorted((native/"pb").glob("*.go"))}
  # The legacy message package depends on model protobufs only, never its service
  # package. The new message package imports legacy pb, and the existing separate
  # service package imports both; no legacy pb -> new package edge is introduced.
  for rel in original_pb:
   text=(native/rel).read_text()
   assert '"github.com/anyproto/anytype-heart/pb/service"' not in text
   assert '"github.com/anyproto/anytype-heart/pb/cutoverpb"' not in text
  stage=root/"inputs"
  for rel in ["pb/protos/pinkha_torah_cutover.proto","pb/protos/service/service.proto"]:
   src=base.HERE/"overlay"/rel;dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
  original=base.pinned(native/"pb/protos/service/service.proto",canonical.SERVICE_BEFORE)
  s=(stage/"pb/protos/service/service.proto").read_text().replace('import "pb/protos/pinkha_torah_cutover.proto";\n',"")
  s="".join(line for line in s.splitlines(keepends=True) if "rpc PinkhaTorahCutover" not in line and "Separate cutover metadata;" not in line)
  assert s==original.read_text()
  env=dict(os.environ,GOGO_NO_UNDERSCORE="1",GOGO_EXPORT_ONEOF_INTERFACE="1",PACKAGE_PATH="github.com/anyproto/anytype-heart/pb")
  def run(label,argv,command_env=None,input_bytes=None):
   start=time.time();p=subprocess.run(argv,cwd=native,env=command_env or env,input=input_bytes,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=120)
   (root/(label+".stdout")).write_bytes(p.stdout);(root/(label+".stderr")).write_bytes(p.stderr)
   row={"argv":argv,"exitCode":p.returncode,"seconds":time.time()-start,"stdoutSHA256":base.sha(root/(label+".stdout")),"stderrSHA256":base.sha(root/(label+".stderr"))}
   result["commands"].append(row);assert p.returncode==0,label+" failed"
   return p.stdout
  maps=[
   "Mgoogle/protobuf/timestamp.proto=github.com/gogo/protobuf/types",
   "Mgoogle/protobuf/struct.proto=github.com/gogo/protobuf/types",
   "Mgoogle/protobuf/descriptor.proto=github.com/gogo/protobuf/protoc-gen-gogo/descriptor",
   "Mmodel/protos/models.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
   "Mmodel/protos/export_report.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
   "Mmodel/protos/localstore.proto=github.com/anyproto/anytype-heart/pkg/lib/pb/model",
   "Mpb/protos/commands.proto=github.com/anyproto/anytype-heart/pb",
   "Mpb/protos/events.proto=github.com/anyproto/anytype-heart/pb",
   "Mpb/protos/pinkha_authorized_operation_read.proto=github.com/anyproto/anytype-heart/pb",
   "Mpb/protos/pinkha_torah_cutover.proto=github.com/anyproto/anytype-heart/pb/cutoverpb"]
  prefix=[str(protoc),"--plugin=protoc-gen-gogofaster="+str(plugin),"-I",str(stage),"-I",str(native),"-I",str(canonical.TOOLS/"include"),"-I",replacement["Dir"]]
  generated={}
  for label,target,rel,plugin_name in [
   ("messages","pb/protos/pinkha_torah_cutover.proto","pb/cutoverpb/pinkha_torah_cutover.pb.go",None),
   ("grpc","pb/protos/service/service.proto","pb/service/service.pb.go","grpc"),
   ("gomobile","pb/protos/service/service.proto","clientlibrary/service/service.pb.go","gomobile")]:
   destination=root/label;destination.mkdir();options=list(maps);e=dict(env)
   if plugin_name:options.append("plugins="+plugin_name);e["GOGO_GRPC_SERVER_METHOD_NO_ERROR"]="1"
   else:e["PACKAGE_PATH"]="github.com/anyproto/anytype-heart/pb/cutoverpb"
   if plugin_name=="gomobile":e["GOGO_GOMOBILE_WITH_CONTEXT"]="1"
   run("generate-"+label,prefix+["--gogofaster_out="+",".join(options)+":"+str(destination),target],e)
   outputs=list(destination.rglob("*.go"));assert len(outputs)==1
   generated[rel]=outputs[0]
  new_message=generated["pb/cutoverpb/pinkha_torah_cutover.pb.go"].read_text()
  assert "\npackage cutoverpb\n" in new_message
  assert '"github.com/anyproto/anytype-heart/pb"' in new_message
  assert '"github.com/anyproto/anytype-heart/pb/cutoverpb"' not in new_message
  # Canonical descriptor comparison: Go package metadata is the only difference.
  descriptors={}
  for label,first in [("before",SUPERSEDED/"source"),("after",stage)]:
   path=root/(label+".descriptor")
   run(label+"-descriptor",[str(protoc),"-I",str(first),"-I",str(native),"-I",str(canonical.TOOLS/"include"),"-I",replacement["Dir"],
       "--descriptor_set_out="+str(path),"pb/protos/pinkha_torah_cutover.proto"])
   decoded=run(label+"-descriptor-text",[str(protoc),"-I",str(canonical.TOOLS/"include"),"--decode=google.protobuf.FileDescriptorSet","google/protobuf/descriptor.proto"],input_bytes=path.read_bytes())
   descriptors[label]=decoded
  assert descriptors["before"].count(b'go_package: "pb"')==1
  assert descriptors["after"]==descriptors["before"].replace(b'go_package: "pb"',b'go_package: "cutoverpb"')
  outputs={}
  for rel,src in generated.items():
   dst=base.HERE/"overlay"/rel
   if dst.exists():
    assert rel in superseded["files"] and base.row(dst)==superseded["files"][rel]["after"]
   dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);outputs[rel]=base.row(dst)
  old_go=base.HERE/"overlay/pb/pinkha_torah_cutover.pb.go"
  assert base.row(old_go)==superseded["files"]["pb/pinkha_torah_cutover.pb.go"]["after"]
  assert (SUPERSEDED/"source/pb/pinkha_torah_cutover.pb.go").read_bytes()==old_go.read_bytes()
  old_go.unlink()
  assert original_pb=={str(p.relative_to(native)):base.row(p) for p in sorted((native/"pb").glob("*.go"))}
  result.update(status="GENERATED_ISOLATED_GO_PACKAGE_NOT_NATIVE_ACCEPTANCE",generatedFiles=outputs,
    sourceInputs={str(p.relative_to(stage)):base.row(p) for p in stage.rglob("*") if p.is_file()},
    protocSHA256=canonical.PROTOC_SHA,generatorSHA256=prior["generatorSHA256"],reusedCanonicalGeneratorReceiptSHA256=a.generator_receipt_sha,
    supersededManifestSHA256=SUPERSEDED_SHA,descriptorIdentityPreservedExceptGoPackage=True,
    originalPBPackageUnchanged=original_pb,goPackage="github.com/anyproto/anytype-heart/pb/cutoverpb",noOriginalPBImportCycle=True)
 except Exception as e:result["error"]=type(e).__name__+": "+str(e)
 finally:
  result["completedUTC"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime());base.save(root/"receipt.json",result)
 print(json.dumps({"status":result["status"],"error":result.get("error"),"receipt":str(root/"receipt.json")}))
 return 0 if result["status"]=="GENERATED_ISOLATED_GO_PACKAGE_NOT_NATIVE_ACCEPTANCE" else 1
if __name__=="__main__":raise SystemExit(main())
