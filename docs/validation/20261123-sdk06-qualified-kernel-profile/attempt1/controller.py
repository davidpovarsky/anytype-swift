from pathlib import Path
import datetime,hashlib,importlib,json,os,subprocess,sys,time,unittest
w=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-qualified-continuation-20261123")
out=Path("/mnt/development/projects/diagnostics/sdk06-qualified-kernel-profile-20261123/attempt1")
source="6ec9b4f26ed92350aee29f29febadbd27929393d"
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=w,text=True).strip()==source
assert subprocess.check_output(["git","status","--porcelain"],cwd=w,text=True)==""
out.mkdir(parents=True,exist_ok=False)
(out/"controller.py").write_bytes(Path(__file__).read_bytes())
selected=[
 "test_sdk06_qualified_lifecycle.QualifiedLifecycleControls.test_explicit_sdk_quiescence_uses_same_ten_seconds_and_rejects_late_zero",
 "test_sdk06_qualified_kernel_profile.QualifiedKernelProfileControls.test_sdk_qualified_kernel_wiring_preserves_identity_fallback_and_original_deadline"]
meta={"source_sha":source,"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "scope":"one directly affected lifecycle fixture plus one new SDK-qualified kernel-wiring method",
 "selected_methods":selected,"old_control_methods_executed":1,"directly_affected_control_methods_executed":1,
 "new_control_methods_executed":1,"other_previously_passed_methods_executed":0,
 "original_18_suite_repeated":False,"original_kernel9_repeated":False,"product_tests_executed":0,"mac_builds":0,
 "python":sys.version}
(out/"intent.json").write_text(json.dumps(meta,indent=2)+"\n")
sys.path.insert(0,str(w/"Tools/PinkhaSimulatorGate"))
os.chdir(w)
for name in ("test_sdk06_qualified_lifecycle","test_sdk06_qualified_kernel_profile"):importlib.import_module(name)
def snapshot():
 result={}
 for module in tuple(sys.modules.values()):
  raw=getattr(module,"__file__",None)
  if raw:
   path=Path(raw).resolve()
   if path.suffix==".py" and path.is_relative_to(w/"Tools"):
    result[path.relative_to(w).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
 for name in (".github/workflows/pinkha-sdk06-qualified-continuation.yml","Tools/PinkhaNativeDerived/package_evidence.py",
   "docs/validation/20261123-sdk06-qualified-kernel-profile/source-review.json",
   "docs/validation/20261123-sdk06-qualified-kernel-profile/originals/run_owned_single_lane.py",
   "docs/validation/20261123-sdk06-qualified-kernel-profile/originals/test_sdk06_qualified_lifecycle.py"):
  result[name]=hashlib.sha256((w/name).read_bytes()).hexdigest()
 return dict(sorted(result.items()))
before=snapshot()
(out/"source-before.json").write_text(json.dumps(before,indent=2)+"\n")
events=[]
class Result(unittest.TextTestResult):
 def startTest(self,test):
  events.append({"event":"start","name":test.id(),"monotonic":time.monotonic()});super().startTest(test)
 def addSuccess(self,test):
  events.append({"event":"terminal","name":test.id(),"status":"PASS"});super().addSuccess(test)
 def addFailure(self,test,error):
  events.append({"event":"terminal","name":test.id(),"status":"FAIL","error":str(error[1])});super().addFailure(test,error)
 def addError(self,test,error):
  events.append({"event":"terminal","name":test.id(),"status":"ERROR","error":str(error[1])});super().addError(test,error)
 def addSubTest(self,test,subtest,error):
  if error is not None:events.append({"event":"subtest_failure","name":test.id(),"subtest":str(subtest),"error":str(error[1])})
  super().addSubTest(test,subtest,error)
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in selected)
assert suite.countTestCases()==2
started=time.monotonic()
with (out/"controls.log").open("x") as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
elapsed=time.monotonic()-started
after=snapshot()
(out/"source-after.json").write_text(json.dumps(after,indent=2)+"\n")
(out/"events.json").write_text(json.dumps(events,indent=2)+"\n")
meta.update(status="PASS" if result.wasSuccessful() and before==after else "FAIL",tests_run=result.testsRun,
 failures=len(result.failures),errors=len(result.errors),source_unchanged=before==after,
 source_input_count=len(before),elapsed_seconds=elapsed,
 finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 logs_sha256=hashlib.sha256((out/"controls.log").read_bytes()).hexdigest())
(out/"result.json").write_text(json.dumps(meta,indent=2)+"\n")
print((out/"controls.log").read_text())
print(json.dumps(meta,sort_keys=True))
raise SystemExit(0 if meta["status"]=="PASS" else 1)
