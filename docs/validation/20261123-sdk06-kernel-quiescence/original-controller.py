from pathlib import Path
import datetime,hashlib,importlib,json,os,subprocess,sys,time,unittest
w=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-kernel-quiescence-20261123")
out=Path("/mnt/development/projects/diagnostics/sdk06-kernel-quiescence-20261123/attempt1")
out.mkdir(exist_ok=False)
source="6283ea15a3c921da1c8bd7565c5bbc50dfae4739"
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=w,text=True).strip()==source
assert subprocess.check_output(["git","status","--porcelain"],cwd=w,text=True)==""
sys.path.insert(0,str(w/"Tools/PinkhaSimulatorGate"));os.chdir(w)
os.environ["PINKHA_SDK_KERNEL_CONTROL_EVIDENCE"]=str(out/"real-owned-process")
meta={"source_sha":source,"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "scope":"Nine new SDK-enumeration kernel/ownership/deadline controls only",
 "old_control_methods_executed":0,"product_tests_executed":0,"apple_commands_executed":0}
(out/"intent.json").write_text(json.dumps(meta,indent=2)+"\n")
module=importlib.import_module("test_sdk06_kernel_quiescence")
def snapshot():
 result={}
 for m in tuple(sys.modules.values()):
  raw=getattr(m,"__file__",None)
  if raw:
   p=Path(raw).resolve()
   if p.suffix==".py" and p.is_relative_to(w/"Tools"):
    result[p.relative_to(w).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 return dict(sorted(result.items()))
before=snapshot();(out/"source-before.json").write_text(json.dumps(before,indent=2)+"\n")
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
suite=unittest.defaultTestLoader.loadTestsFromModule(module);assert suite.countTestCases()==9
with (out/"controls.log").open("x") as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
after=snapshot();(out/"source-after.json").write_text(json.dumps(after,indent=2)+"\n")
(out/"events.json").write_text(json.dumps(events,indent=2)+"\n")
meta.update(status="PASS" if result.wasSuccessful() and before==after else "FAIL",tests_run=result.testsRun,
 failures=len(result.failures),errors=len(result.errors),source_unchanged=before==after,
 finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 logs_sha256=hashlib.sha256((out/"controls.log").read_bytes()).hexdigest())
(out/"result.json").write_text(json.dumps(meta,indent=2)+"\n")
print((out/"controls.log").read_text());print(json.dumps(meta,sort_keys=True))
print("REAL_INTEGRATION="+(out/"real-owned-process/actual-kernel-quiescence.json").read_text())
