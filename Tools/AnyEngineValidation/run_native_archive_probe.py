#!/usr/bin/env python3
"""Exercise the production canonical archive on an explicitly disposable native fixture."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,sys,urllib.request
sys.stdout.reconfigure(encoding="utf-8",errors="backslashreplace")
ROOT=Path(__file__).resolve().parents[2]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def manifest():
    result={}
    for name in ("PinkhaAnyEngine","PinkhaAnyIntegration","PinkhaKit"):
        module=ROOT/"Modules"/name
        files=[module/"Package.swift",module/"Package.resolved"]+list((module/"Sources").rglob("*.swift"))
        for path in sorted(set(files)):
            if path.is_file():result[path.relative_to(ROOT).as_posix()]=sha(path)
    return result
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ("swift","native-binary","native-manifest"):ap.add_argument("--"+name,type=Path,required=True)
    for name in ("endpoint","account-id","space-id"):ap.add_argument("--"+name,required=True)
    ap.add_argument("--allow-disposable-writes",action="store_true")
    args=ap.parse_args()
    if not args.allow_disposable_writes:ap.error("explicit disposable fixture authorization required")
    source=manifest();binary_hash=sha(args.native_binary);native_manifest_hash=sha(args.native_manifest)
    if binary_hash!="cbe1a7f79ac4a6fa490c4f8ba33ebddbf15ff7e979879031eecd040d808eb7f3":
        ap.error("this runner pins the actual v5 native creation binary")
    if native_manifest_hash!="46cf3ffbbfe03f174e0d226652cc4e4de228a38e5cd569100e3f8c6416e416d3":
        ap.error("native v5 source manifest mismatch")
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    evidence=ROOT/"docs/any-engine-port/evidence/20261119"
    evidence.mkdir(parents=True,exist_ok=True)
    prefix=evidence/("canonical-archive-native-"+stamp)
    env=dict(os.environ);env["PATH"]=str(args.swift.parent)+os.pathsep+env.get("PATH","")
    record={"schemaVersion":1,"status":"FAIL","startedAt":stamp,"sourceManifest":source,
            "nativeBinarySHA256":binary_hash,"nativeSourceManifestSHA256":native_manifest_hash,
            "scope":"Real Swift production canonical association archive; existing native v5 local fixture; full Heart/editor/file migration excluded"}
    try:
        buildlog=prefix.with_suffix(".build.log")
        with buildlog.open("w",encoding="utf-8") as output:
            build=subprocess.run([str(args.swift),"build","--product","pinkha-any-integration-probe",
                "--jobs","2","--disable-automatic-resolution"],
                cwd=ROOT/"Modules/PinkhaAnyIntegration",env=env,stdout=output,stderr=subprocess.STDOUT,timeout=900)
        record.update(buildExitCode=build.returncode,buildLog=buildlog.relative_to(ROOT).as_posix(),buildLogSHA256=sha(buildlog))
        if build.returncode:raise RuntimeError("Swift production probe did not build")
        probe=ROOT/"Modules/PinkhaAnyIntegration/.build/x86_64-unknown-windows-msvc/debug/pinkha-any-integration-probe.exe"
        record["probeSHA256"]=sha(probe)
        with urllib.request.urlopen(args.endpoint+"/v1/health",timeout=10) as response:
            health=json.load(response)
        record["health"]={key:health.get(key) for key in ("status","version","buildCommit") if key in health}
        run=subprocess.run([str(probe),"--archive","--disposable",args.endpoint,args.account_id,args.space_id],
            cwd=ROOT,env=env,capture_output=True,timeout=240)
        record["probeExitCode"]=run.returncode
        lines=run.stdout.decode("utf-8").strip().splitlines()
        result=json.loads(lines[-1]) if lines else {}
        record["result"]=result
        record["probeUnchanged"]=sha(probe)==record["probeSHA256"]
        if run.returncode:record["failureOutput"]=run.stderr.decode("utf-8",errors="replace")[-6000:]
        valid=(run.returncode==0 and result.get("status")=="PASS" and result.get("count")==16
               and len(result.get("checks",{}))==16 and all(result["checks"].values()) and record["probeUnchanged"])
    except Exception as error:
        valid=False
        record["failure"]={"kind":type(error).__name__,"description":str(error)}
    record["sourceStable"]=source==manifest()
    record["nativeBinaryUnchanged"]=sha(args.native_binary)==binary_hash
    record["nativeManifestUnchanged"]=sha(args.native_manifest)==native_manifest_hash
    record["status"]="PASS" if valid and record["sourceStable"] and record["nativeBinaryUnchanged"] and record["nativeManifestUnchanged"] else "FAIL"
    output=prefix.with_suffix(".json")
    output.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in record.items() if k!="sourceManifest"},indent=2))
    print(json.dumps({"receipt":output.relative_to(ROOT).as_posix()}))
    return 0 if record["status"]=="PASS" else 1
if __name__=="__main__":sys.exit(main())
