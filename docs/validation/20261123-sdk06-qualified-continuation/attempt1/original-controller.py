from pathlib import Path
import datetime,hashlib,importlib,json,os,subprocess,sys,time,unittest
w=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk06-qualified-continuation-20261123")
out=Path("/mnt/development/projects/diagnostics/sdk06-qualified-continuation-20261123/attempt1")
out.mkdir(parents=True,exist_ok=False)
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=w,text=True).strip()=="d6239119604cfb3eac9af6251094beeda8ae0202"
assert subprocess.check_output(["git","status","--porcelain"],cwd=w,text=True)==""
sys.path.insert(0,str(w/"Tools/PinkhaSimulatorGate"))
os.chdir(w)
meta={"source_sha":"d6239119604cfb3eac9af6251094beeda8ae0202","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"scope":"18 new SDK qualified-selector/lifecycle/transport controller methods only","old_control_methods_executed":0,"product_tests_executed":0}
(out/"intent.json").write_text(json.dumps(meta,indent=2)+"\n")
modules=[importlib.import_module(n) for n in ["test_sdk06_qualified_selector","test_sdk06_qualified_lifecycle"]]
def snapshot():
 result={}
 for module in tuple(sys.modules.values()):
  raw=getattr(module,"__file__",None)
  if raw:
   p=Path(raw).resolve()
   if p.suffix==".py" and p.is_relative_to(w/"Tools"):
    result[p.relative_to(w).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 for name in [".github/workflows/pinkha-sdk06-qualified-continuation.yml","Tools/PinkhaNativeDerived/package_evidence.py"]:
  result[name]=hashlib.sha256((w/name).read_bytes()).hexdigest()
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
suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromModule(m) for m in modules)
assert suite.countTestCases()==18,suite.countTestCases()
with (out/"controls.log").open("x") as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
after=snapshot();(out/"source-after.json").write_text(json.dumps(after,indent=2)+"\n")
(out/"events.json").write_text(json.dumps(events,indent=2)+"\n")
meta.update(status="PASS" if result.wasSuccessful() and before==after else "FAIL",tests_run=result.testsRun,
 failures=len(result.failures),errors=len(result.errors),source_unchanged=before==after,
 finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
 logs_sha256=hashlib.sha256((out/"controls.log").read_bytes()).hexdigest())
(out/"result.json").write_text(json.dumps(meta,indent=2)+"\n")
print((out/"controls.log").read_text())
print(json.dumps(meta,sort_keys=True))
