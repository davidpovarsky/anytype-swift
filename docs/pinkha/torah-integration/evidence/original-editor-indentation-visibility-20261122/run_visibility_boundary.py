import pathlib,subprocess,json,hashlib,os,datetime,re,sys
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-editor-visibility-20261122")
def sha(raw): return hashlib.sha256(raw).hexdigest()
assert len(sys.argv)==2
assert sha((out/"COMPILER_INPUTS.json").read_bytes())==sys.argv[1]
inputs=json.loads((out/"COMPILER_INPUTS.json").read_bytes())
assert not (out/"COMPILER_EXECUTION.json").exists(),"Do not repeat this frozen boundary"
swiftc=pathlib.Path(inputs["compiler"]["path"])
runtime=pathlib.Path(inputs["runtime_bin"])
assert sha(swiftc.read_bytes())==inputs["compiler"]["sha256"]
def verify():
 for row in inputs["compiled_inputs"]:
  assert sha((out/row["path"]).read_bytes())==row["sha256"],row["path"]
 for row in inputs["original_inputs"]:
  assert sha((out/row["snapshot"]).read_bytes())==row["sha256"],row["snapshot"]
 assert sha((out/"VISIBILITY.patch").read_bytes())==inputs["patch_sha256"]
verify()
module=out/"compiler-module";module.mkdir()
env=dict(os.environ)
env["PATH"]=str(runtime)+os.pathsep+str(swiftc.parent)+os.pathsep+env.get("PATH","")
env["PYTHONUTF8"]="1"
execution={"schema":1,"wrapper_pid":os.getpid(),"inputs_sha256":sys.argv[1],"runner_sha256":sha(pathlib.Path(__file__).read_bytes()),"commands":[]}
def persist():
 (out/"COMPILER_EXECUTION.json").write_text(json.dumps(execution,indent=2)+"\n",encoding="utf-8")
def run(label,args,timeout,expected):
 row={"label":label,"command":list(map(str,args)),"cwd":str(out),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"timeout_seconds":timeout,"phase":"STARTING"}
 execution["commands"].append(row);persist()
 with (out/(label+".stdout.log")).open("wb") as so,(out/(label+".stderr.log")).open("wb") as se:
  child=subprocess.Popen(list(map(str,args)),cwd=out,env=env,stdout=so,stderr=se)
  row["child_pid"]=child.pid;row["phase"]="RUNNING";persist()
  try:
   row["returncode"]=child.wait(timeout=timeout);row["timed_out"]=False
  except subprocess.TimeoutExpired:
   row["timed_out"]=True
   if child.poll() is None:
    killed=subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],capture_output=True,timeout=30)
    row["owned_child_cleanup"]={"returncode":killed.returncode,"stdout":killed.stdout.decode(errors="replace"),"stderr":killed.stderr.decode(errors="replace")}
   try:row["returncode"]=child.wait(timeout=30)
   except subprocess.TimeoutExpired:row["returncode"]=None
 row["finished_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
 row["phase"]="TERMINAL" if row.get("returncode") is not None else "UNRESOLVED_NO_RETRY"
 for key in ("stdout","stderr"):row[key+"_sha256"]=sha((out/(label+"."+key+".log")).read_bytes())
 verify();row["all_inputs_unchanged"]=True;persist()
 if row["returncode"]!=expected or row["timed_out"]:
  print(json.dumps({"status":"ACTUAL_BOUNDARY_FAILURE_PRESERVED","record":row,"stderr":(out/(label+".stderr.log")).read_text(encoding="utf-8",errors="replace")[-14000:]}));raise SystemExit(1)
 return row
run("complete-original-candidate-module",[swiftc,"-emit-module","-parse-as-library","-module-name","OriginalIndentationVisibility","-emit-module-path",module/"OriginalIndentationVisibility.swiftmodule","-swift-version","5","-strict-concurrency=complete","-module-cache-path",module/"ModuleCache",out/"BlockIndentationStyle.candidate.swift",out/"layout-0.swift",out/"dependency-2-BlockLayoutDetails.swift"],120,0)
negative=run("expected-external-visibility-rejection",[swiftc,"-typecheck","-swift-version","5","-I",module,"-module-cache-path",module/"ModuleCache",out/"ExternalConsumer.swift"],120,1)
stderr=(out/"expected-external-visibility-rejection.stderr.log").read_text(encoding="utf-8",errors="replace")
errors=[line for line in stderr.splitlines() if re.search(r"\.swift:\d+:\d+: error:",line)]
assert len(errors)==1 and "cannot find type 'BlockIndentationStyle' in scope" in errors[0],errors
module_file=module/"OriginalIndentationVisibility.swiftmodule"
assert module_file.is_file() and module_file.stat().st_size>0
verify()
result={"schema":1,"status":"PASS_ORIGINAL_INTERNAL_LAYOUT_COMPILE_AND_EXTERNAL_VISIBILITY_REJECTION","candidate_sha256":inputs["candidate_sha256"],"inputs_sha256":sys.argv[1],"same_module_compiler_exit":0,"external_rejection_exit":negative["returncode"],"external_errors":errors,"module":{"path":str(module_file.relative_to(out)),"bytes":module_file.stat().st_size,"sha256":sha(module_file.read_bytes())},"new_compiler_boundary_checks":2,"old_tests_replayed":0,"apple_framework_or_native_ui_acceptance":False,"all_inputs_unchanged":True,"limits":inputs["limits"]}
(out/"COMPILER_RESULT.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"result":result,"execution":execution}))
