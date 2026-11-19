#!/usr/bin/env python3
"""Build and exercise the actual Swift native property and custom document APIs on synthetic Any data."""
import argparse, hashlib, json, os, shutil, subprocess, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def manifest(root):
    result={}
    for name in ("PinkhaAnyEngine","PinkhaAnyHost","PinkhaAnyIntegration","PinkhaKit"):
        module=root/"Modules"/name
        paths=[module/"Package.swift",module/"Package.resolved"]+list((module/"Sources").rglob("*.swift"))
        for path in sorted(set(paths)):
            if path.is_file(): result[path.relative_to(root).as_posix()]=sha(path)
    return result
def main():
    ap=argparse.ArgumentParser()
    for name in ("root","swift","native-binary","output"): ap.add_argument("--"+name,type=Path,required=True)
    for name in ("endpoint","space-id","account-id","custom-type-id","collection-id","text-property-id","number-property-id"): ap.add_argument("--"+name,required=True)
    ap.add_argument("--allow-disposable-writes",action="store_true")
    args=ap.parse_args()
    if not args.allow_disposable_writes: ap.error("explicit synthetic fixture authorization required")
    root=args.root.resolve();module=root/"Modules/PinkhaAnyHost";scratch=root/"Modules/PinkhaAnyEngine/.build"
    before=manifest(root);native_sha=sha(args.native_binary)
    if native_sha!="424678167895c6130dd5c98c542d7845b659711716ce3bf7b47db3ff33cbafbe":
        ap.error("this receipt runner requires the source-bound native v6 document binary")
    receipt={"startedAt":now(),"scope":"real Swift production native properties, document Type policy, collection membership, visibility and conditional Undo; synthetic creation metadata fixture",
             "sourceManifest":before,"scriptSHA256":sha(Path(__file__)),"nativeBinarySHA256":native_sha}
    env=dict(os.environ);env["PATH"]=str(args.swift.parent)+os.pathsep+env.get("PATH","")
    buildlog=module/"native-property-probe-build.log"
    with buildlog.open("w",encoding="utf-8") as output:
        result=subprocess.run([str(args.swift),"build","--package-path",str(module),"--scratch-path",str(scratch),
            "--product","pinkha-any-host-probe","--jobs","2","--disable-automatic-resolution"],
            cwd=module,env=env,stdout=output,stderr=subprocess.STDOUT,timeout=900)
    receipt["buildExitCode"]=result.returncode;receipt["buildLogSHA256"]=sha(buildlog)
    valid=result.returncode==0
    if valid:
        source=scratch/"x86_64-unknown-windows-msvc/debug/pinkha-any-host-probe.exe"
        binary=root/"build/any-engine-port/host-property-probe-v1.exe"
        shutil.copyfile(source,binary);receipt["probeSHA256"]=sha(binary)
        receipt["probe"]=binary.relative_to(root).as_posix()
        try:
            with urllib.request.urlopen(args.endpoint+"/v1/health",timeout=10) as response: health=json.load(response)
            receipt["health"]={key:health.get(key) for key in ("status","version","buildCommit","startedAt") if key in health}
            run=subprocess.run([str(binary),args.endpoint,args.space_id,args.account_id,"--properties","--allow-disposable-writes",
                "--custom-type-id",args.custom_type_id,"--collection-id",args.collection_id,
                "--text-property-id",args.text_property_id,"--number-property-id",args.number_property_id],
                cwd=root,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=150)
            receipt["probeExitCode"]=run.returncode
            text=run.stdout.decode("utf-8",errors="strict")
            try: proof=json.loads(text.strip().splitlines()[-1])
            except (ValueError,IndexError): proof={"status":"FAIL","reason":"missing structured probe result"}
            receipt["result"]=proof
            if run.returncode!=0:
                receipt["failure"]=run.stderr.decode("utf-8",errors="replace")[-6000:]
            valid=run.returncode==0 and proof.get("status")=="PASS" and proof.get("count")==15 and len(proof.get("checks",[]))==15
            receipt["probeUnchanged"]=sha(binary)==receipt["probeSHA256"]
            valid=valid and receipt["probeUnchanged"]
        except Exception as error:
            valid=False
            receipt["failure"]={"kind":type(error).__name__,"description":str(error)}

    else:
        print("\n".join(buildlog.read_text(encoding="utf-8",errors="replace").splitlines()[-90:]),flush=True)
    receipt["sourceStable"]=manifest(root)==before
    receipt["nativeBinaryUnchanged"]=sha(args.native_binary)==native_sha
    receipt["status"]="PASS" if valid and receipt["sourceStable"] and receipt["nativeBinaryUnchanged"] else "FAIL"
    receipt["finishedAt"]=now()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":receipt["status"],"sourceStable":receipt["sourceStable"],"receipt":str(args.output),
        "result":receipt.get("result"),"failure":receipt.get("failure")},ensure_ascii=False),flush=True)
    return 0 if receipt["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
