from pathlib import Path
import contextlib,datetime,hashlib,importlib,json,os,subprocess,sys,time,traceback,unittest
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-coherent-nested-repair-20261123")
OUT=Path(__file__).resolve().parent
EXPECTED="9980c31979bce6898bd1bf2f57b88a415e60d0d9"
sys.dont_write_bytecode=True
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,value): (OUT/name).write_text(json.dumps(value,indent=2)+"\n")
head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
assert head==EXPECTED
assert not subprocess.check_output(["git","status","--porcelain"],cwd=ROOT,text=True)
paths=sorted(p for p in (ROOT/"Tools").rglob("*.py") if p.is_file() and not p.is_symlink())
before={p.relative_to(ROOT).as_posix():sha(p) for p in paths}
write("source-before.json",before)
os.environ["PINKHA_NESTED_REPAIR_CONTROL_EVIDENCE"]=str(OUT)
sys.path.insert(0,str(ROOT/"Tools/PinkhaSimulatorGate"))
events=[]
class Result(unittest.TextTestResult):
 def startTest(self,test):
  self.case_started=time.monotonic();super().startTest(test)
 def addSuccess(self,test):
  events.append({"id":test.id(),"outcome":"PASS","seconds":time.monotonic()-self.case_started});super().addSuccess(test)
 def addFailure(self,test,err):
  events.append({"id":test.id(),"outcome":"FAIL","seconds":time.monotonic()-self.case_started});super().addFailure(test,err)
 def addError(self,test,err):
  events.append({"id":test.id(),"outcome":"ERROR","seconds":time.monotonic()-self.case_started});super().addError(test,err)
 def addSkip(self,test,reason):
  events.append({"id":test.id(),"outcome":"SKIP","reason":reason});super().addSkip(test,reason)
started=datetime.datetime.now(datetime.timezone.utc).isoformat();clock=time.monotonic()
result=None;exception=None
with (OUT/"controls.log").open("x") as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
 try:
  module=importlib.import_module("test_coherent_original_nested_cleanup")
  names=["OriginalProductsNestedCleanupTests.test_current_fixed_roots_reject_foreign_origin_symlink_and_forged_cwd","OriginalProductsNestedCleanupTests.test_future_coherent_original_records_actual_cwd_without_changing_default"]
  suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n,module) for n in names)
  assert suite.countTestCases()==2
  result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
 except BaseException as error:
  exception=type(error).__name__;traceback.print_exc()
write("events.json",events)
after={p.relative_to(ROOT).as_posix():sha(p) for p in paths};write("source-after.json",after)
loaded={}
for module in list(sys.modules.values()):
 filename=getattr(module,"__file__",None)
 if not filename:continue
 p=Path(filename).resolve()
 if p.suffix==".py" and p.is_relative_to(ROOT) and p.is_file():
  name=p.relative_to(ROOT).as_posix();assert name in before and sha(p)==before[name]
  loaded[name]=sha(p)
write("loaded-inputs.json",loaded)
assert before==after
status="PASS" if result is not None and result.wasSuccessful() and result.testsRun==2 and len(events)==2 and all(e["outcome"]=="PASS" for e in events) else "FAIL"
receipt={"schema":"pinkha-coherent-original-nested-new-controls-v1","status":status,"source_commit":head,"started_at":started,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"seconds":time.monotonic()-clock,"methods":events,"tests_run":result.testsRun if result else 0,"exception":exception,"source_inputs":len(before),"source_before_after_unchanged":before==after,"loaded_inputs":loaded,"old_controls_executed":0,"product_tests_executed":0,"simulator_commands_executed":0,"log_sha256":sha(OUT/"controls.log"),"events_sha256":sha(OUT/"events.json"),"source_before_sha256":sha(OUT/"source-before.json"),"source_after_sha256":sha(OUT/"source-after.json"),"runner_sha256":sha(Path(__file__)),"original_child_files":{p.relative_to(OUT).as_posix():sha(p) for p in sorted((OUT/"actual-owned-commands").glob("*")) if p.is_file()}}
write("receipt.json",receipt)
print(json.dumps({"status":status,"source":head,"tests_run":receipt["tests_run"],"seconds":receipt["seconds"],"source_inputs":len(before),"loaded_inputs":len(loaded),"receipt_sha256":sha(OUT/"receipt.json"),"original_child_files":len(receipt["original_child_files"])}))
sys.exit(0 if status=="PASS" else 1)
