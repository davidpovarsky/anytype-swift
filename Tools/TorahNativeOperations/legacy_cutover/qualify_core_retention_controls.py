#!/usr/bin/env python3
"""Actual isolated retention faults; no Go, core/account, native or Apple call."""
import argparse,contextlib,hashlib,importlib.util,io,json,os,pathlib,sys
PINS={"retained_core_materialization.py":"840229d10ff94e2c77027a42b06dc3b57e3e08e47830771a46a5aae29b7e7bff","resume_core_registry.py":"2de96ab0e021d9c259f2d8619d4aadc28a84cf071a8e682775f9c73031022e05","owned_volume_commands.py":"f95e3dd28817ae5e892fc2768eb4edee2cb105c6dbb81ad5bfaceea4c09f39dd"}
BASE=pathlib.Path("/mnt/development/projects/evidence/page154-final-validation-20261125/heart-cutover-native-store/attempt1")
def load(directory,name):
 path=directory/name
 raw=path.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=PINS[name]:raise ValueError("exact control source")
 spec=importlib.util.spec_from_file_location("retention_"+name.replace(".","_"),path)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=pathlib.Path,required=True);args=ap.parse_args()
 os.umask(0o077);root=args.root
 if root.resolve()!=root or not str(root).startswith("/var/tmp/pinkha-e-core-retention-controls-20261126/"):raise ValueError("private control root")
 root.mkdir(mode=0o700,parents=True,exist_ok=False)
 directory=pathlib.Path(__file__).resolve().parent
 c=load(directory,"owned_volume_commands.py");retained=load(directory,"retained_core_materialization.py")
 result={"status":"FAIL","scope":"isolated retention controls only","nativeCalls":0,"accounts":0,"goBuilds":0,"appleBuilds":0,"sourcePins":PINS,"controls":[]}
 try:
  wanted={retained.PRIOR/"receipt.json",retained.PRIOR/"commands/build/result.json",retained.PRIOR/"source-before.json",retained.PRIOR/"source-after.json",retained.PRIOR/"candidate.json",directory/"native-core-registry-candidate.json"}
  counts={str(path):0 for path in wanted};originalRead=pathlib.Path.read_bytes
  def counted(path):
   if path in wanted:counts[str(path)]+=1
   return originalRead(path)
  pathlib.Path.read_bytes=counted
  try:source,expected,proof=retained.admit(directory)
  finally:pathlib.Path.read_bytes=originalRead
  if set(counts.values())!={1}:raise ValueError("hash/parse reread a pinned original")
  c.save(root/"retained-admission.json",proof)
  result["controls"].append({"name":"single_original_read_for_hash_and_decode","status":"PASS","reads":counts,"sourceFiles":len(expected)})
  child=root/"log-hash-failure";child.mkdir(mode=0o700)
  commands=c.Commands(child,2<<30,[child,BASE/"cache"]);originalDigest=c.digest
  def denied(path):
   if pathlib.Path(path).name=="original.log":raise OSError("injected log hashing refusal")
   return originalDigest(path)
  c.digest=denied
  try:
   try:commands.run("owned-short-child",["/usr/bin/python3","-c","print('retention control')"],child,dict(os.environ),20)
   except OSError as error:
    if str(error)!="injected log hashing refusal":raise
   else:raise ValueError("log retention error incorrectly passed")
  finally:c.digest=originalDigest
  commandRoot=child/"commands/owned-short-child";row=json.loads((commandRoot/"result.json").read_bytes())
  exitRow=json.loads((commandRoot/"original-exit.json").read_bytes())
  if row["status"]!="FAIL" or row["exitCode"]!=0 or row["groupState"]!="ABSENT_ESRCH" or "logRetentionError" not in row or exitRow["exitCode"]!=0 or commands.cleanup()!=[]:raise ValueError("original child outcome was not retained")
  result["controls"].append({"name":"log_hash_failure_retains_original_exit_and_terminal_failure","status":"PASS","resultSHA256":c.digest(commandRoot/"result.json"),"originalExitSHA256":c.digest(commandRoot/"original-exit.json"),"groupState":row["groupState"]})
  privateControl=root/"missing-final-files";privateControl.mkdir(mode=0o700)
  for name in ["resume_core_registry.py","owned_volume_commands.py"]:(privateControl/name).write_bytes((directory/name).read_bytes())
  resume=load(privateControl,"resume_core_registry.py")
  runtime=pathlib.Path("/var/tmp/pinkha-e-cutover-core-runtime-20261126")/("retention-fault-"+root.name)
  oldArgv=sys.argv;sys.argv=[str(privateControl/"resume_core_registry.py"),"--root",str(runtime)]
  stdout=io.StringIO()
  try:
   with contextlib.redirect_stdout(stdout):code=resume.main()
  finally:sys.argv=oldArgv
  (root/"terminal-controller-stdout.txt").write_text(stdout.getvalue())
  terminal=json.loads((runtime/"receipt.json").read_bytes())
  required={"metadataControlError","retainedControlError","dependencyControlError"}
  if code!=1 or terminal["status"]!="FAIL" or terminal["commands"]!=[] or terminal["cleanupFailures"]!=[] or not required.issubset(terminal) or (runtime/"private").exists():raise ValueError("final verification failure suppressed receipt or invoked account")
  result["controls"].append({"name":"multiple_missing_final_helpers_still_save_terminal_failure","status":"PASS","receipt":str(runtime/"receipt.json"),"receiptSHA256":c.digest(runtime/"receipt.json"),"recordedFailures":sorted(required)})
  for name,sha in PINS.items():
   if c.digest(directory/name)!=sha:raise ValueError("control source changed")
  result["status"]="PASS_3_RETENTION_CONTROLS_NOT_NATIVE_ACCEPTANCE"
 except Exception as error:result["error"]=type(error).__name__+": "+str(error)
 finally:c.save(root/"receipt.json",result)
 print(json.dumps(result));return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
