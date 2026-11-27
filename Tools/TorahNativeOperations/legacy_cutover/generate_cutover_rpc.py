#!/usr/bin/env python3
"""Generate additive cutover protobuf/grpc/gomobile code with the pinned native generator."""
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
import qualify_current8ac_core as base
SOURCE=Path("/var/tmp/pinkha-e-cutover-current8ac-20261127/attempt2/source")
TOOLS=Path("/var/tmp/pinkha-e-cutover-current8ac-20261127/rpc-toolchain")
PROTOC_SHA="aa609ec1d4b08375a140b1a42340684932cd2cd0cd56ffe8d791a72f9f3894bc"
SERVICE_BEFORE="76fb0fea3dc1e77e48853810ebb4521ed8c41965bea3761da3a5115d8ffb738e"
def main():
    parser=argparse.ArgumentParser();parser.add_argument("--root",required=True,type=Path);args=parser.parse_args()
    root=args.root
    assert root.is_absolute() and str(root).startswith("/var/tmp/pinkha-e-cutover-current8ac-20261127/")
    assert root.parent.resolve()==root.parent and not root.exists()
    os.umask(0o077);root.mkdir(mode=0o700)
    result={"status":"FAIL","generatedRPC":False,"nativeAcceptance":False,"commands":[]}
    try:
        env=dict(os.environ,GOWORK=str(SOURCE/"go.work"),GOTOOLCHAIN="local",GOMAXPROCS="2",GOMEMLIMIT="1GiB",
            GOCACHE=str(base.CACHE),GOFLAGS="",GOEXPERIMENT="",GOTMPDIR=str(root))
        def run(label,argv,commandEnv=None,timeout=120):
            path=root/(label+".log")
            start=time.time()
            with path.open("wb") as out:
                proc=subprocess.run(argv,cwd=SOURCE/"heart",env=commandEnv or env,stdout=out,stderr=subprocess.STDOUT,timeout=timeout)
            row={"argv":argv,"exitCode":proc.returncode,"seconds":time.time()-start,"logSHA256":base.sha(path)}
            result["commands"].append(row);base.save(root/(label+".json"),row)
            assert proc.returncode==0,label+" failed"
            return path.read_text()
        protoc=base.pinned(TOOLS/"bin/protoc",PROTOC_SHA)
        assert run("protoc-version",[str(protoc),"--version"]).strip()=="libprotoc 3.21.12"
        module=json.loads(run("generator-module",[str(base.GO),"list","-mod=readonly","-m","-json","github.com/gogo/protobuf"]))
        replacement=module["Replace"]
        assert replacement["Path"]=="github.com/anyproto/protobuf"
        assert replacement["Version"]=="v1.3.3-0.20240201225420-6e325cf0ac38"
        assert replacement["Sum"]=="h1:80jke82/c+bNQQpnx4VO3Mi/lAxARyyfUpZvFaPxdzE="
        assert replacement["GoModSum"]=="h1:P1XiOD3dCwIKUDQYPy72D8LYyHL2YPYrpS2s69NZV8Q="
        base.save(root/"generator-module.json",module)
        plugin=root/"protoc-gen-gogofaster"
        run("build-gogofaster",[str(base.GO),"build","-mod=readonly","-p","1","-o",str(plugin),"github.com/gogo/protobuf/protoc-gen-gogofaster"],timeout=300)
        original=base.pinned(SOURCE/"heart/pb/protos/service/service.proto",SERVICE_BEFORE)
        stage=root/"inputs"
        for rel in ["pb/protos/pinkha_torah_cutover.proto","pb/protos/service/service.proto"]:
            src=base.HERE/"overlay"/rel;dst=stage/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
        expectedImport='import "pb/protos/pinkha_torah_cutover.proto";'
        candidate=(stage/"pb/protos/service/service.proto").read_text()
        assert candidate.count(expectedImport)==1
        # Existing service/proto methods stay byte-for-byte intact. Exactly one
        # import and five new declarations are the entire source delta.
        removed=candidate.replace(expectedImport+"\n","")
        lines=removed.splitlines(keepends=True)
        removed="".join(line for line in lines if "rpc PinkhaTorahCutover" not in line and "Separate cutover metadata;" not in line)
        assert removed==original.read_text(),"unreviewed original service change"
        generationEnv=dict(env,PATH=str(root)+":"+os.environ.get("PATH",""),GOGO_NO_UNDERSCORE="1",
            GOGO_EXPORT_ONEOF_INTERFACE="1",PACKAGE_PATH="github.com/anyproto/anytype-heart/pb")
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
          "Mpb/protos/pinkha_torah_cutover.proto=github.com/anyproto/anytype-heart/pb"]
        prefix=[str(protoc),"-I",str(stage),"-I",str(SOURCE/"heart"),"-I",str(TOOLS/"include"),"-I",replacement["Dir"]]
        targets=[
          ("messages","pb/protos/pinkha_torah_cutover.proto","pb/pinkha_torah_cutover.pb.go",None),
          ("grpc","pb/protos/service/service.proto","pb/service/service.pb.go","grpc"),
          ("gomobile","pb/protos/service/service.proto","clientlibrary/service/service.pb.go","gomobile")]
        outputs={}
        for label,proto,rel,pluginName in targets:
            destination=root/label;destination.mkdir()
            options=list(maps)
            commandEnv=dict(generationEnv)
            if pluginName:
                options.append("plugins="+pluginName)
                commandEnv["GOGO_GRPC_SERVER_METHOD_NO_ERROR"]="1"
            if pluginName=="gomobile":commandEnv["GOGO_GOMOBILE_WITH_CONTEXT"]="1"
            run("generate-"+label,prefix+["--gogofaster_out="+",".join(options)+":"+str(destination),proto],commandEnv,60)
            generated=list(destination.rglob("*.go"))
            assert len(generated)==1,"unexpected generator outputs"
            value=generated[0]
            assert b"Code generated by protoc-gen-gogo" in value.read_bytes(),"not generated source"
            dst=base.HERE/"overlay"/rel;dst.parent.mkdir(parents=True,exist_ok=True)
            assert not dst.exists(),"do not overwrite any prior generated candidate"
            shutil.copyfile(value,dst);outputs[rel]=base.row(dst)
        result.update(status="GENERATED_CANDIDATE_NOT_NATIVE_ACCEPTANCE",protocSHA256=PROTOC_SHA,
            generatorSHA256=base.sha(plugin),sourceInputs={str(p.relative_to(stage)):base.row(p) for p in stage.rglob("*") if p.is_file()},
            generatedFiles=outputs,baseServiceUnchanged=base.sha(original)==SERVICE_BEFORE)
    except Exception as error:result["error"]=type(error).__name__+": "+str(error)
    finally:
        result["completedUTC"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime());base.save(root/"receipt.json",result)
    print(json.dumps({"status":result["status"],"error":result.get("error"),"receipt":str(root/"receipt.json")}))
    return 0 if result["status"]=="GENERATED_CANDIDATE_NOT_NATIVE_ACCEPTANCE" else 1
if __name__=="__main__":raise SystemExit(main())
