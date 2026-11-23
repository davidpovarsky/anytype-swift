import pathlib,subprocess,hashlib,json,datetime,sys,time,unittest,io,importlib
w=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
d=pathlib.Path(__file__).resolve().parent
head="20e90f32cc4071e775f5547dd5b93df78e7f54a3"
method="test_coherent_container_observation.CoherentLookupObservationTests.test_original_results_and_failures_remain_exact_with_unchanged_thirty_second_query"
sys.dont_write_bytecode=True
sys.path.insert(0,str(w/"Tools/PinkhaSimulatorGate"))
def git(*a):return subprocess.check_output(["git",*a],cwd=w).decode().strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,o):
 with (d/name).open("x") as f:f.write(json.dumps(o,indent=2,sort_keys=True)+"\n")
assert git("rev-parse","HEAD")==head and not git("status","--porcelain")
write("intent.json",{"source":head,"method":method,"controller_sha256":sha(pathlib.Path(__file__)),"started_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"new_control_methods":1,"old_control_methods":0,"product_methods":0,"actual_simulator_queries":0})
module=importlib.import_module("test_coherent_container_observation")
paths=["Tools/PinkhaSimulatorGate/coherent_container_observation.py","Tools/PinkhaSimulatorGate/test_coherent_container_observation.py","Tools/PinkhaSimulatorGate/wave15_batch.py","docs/validation/20261123-coherent-container-observation/source-review.json"]
def snapshot():
 files={}
 for rel in paths:
  p=w/rel
  files[rel]={"sha256":sha(p),"bytes":p.stat().st_size,"git_blob":git("rev-parse",head+":"+rel)}
 loaded={}
 for m in tuple(sys.modules.values()):
  p=getattr(m,"__file__",None)
  if not p:continue
  p=pathlib.Path(p).resolve()
  if p.suffix==".py" and p.is_relative_to(w):
   loaded[str(p.relative_to(w))]={"sha256":sha(p),"bytes":p.stat().st_size}
 return {"source":head,"files":files,"loaded":dict(sorted(loaded.items()))}
before=snapshot();write("source-before.json",before)
events=[]
class Result(unittest.TextTestResult):
 def startTest(self,test):events.append({"event":"START","test":test.id()});super().startTest(test)
 def addSuccess(self,test):events.append({"event":"PASS","test":test.id()});super().addSuccess(test)
 def addFailure(self,test,err):events.append({"event":"FAIL","test":test.id()});super().addFailure(test,err)
 def addError(self,test,err):events.append({"event":"ERROR","test":test.id()});super().addError(test,err)
 def addSubTest(self,test,subtest,error):
  events.append({"event":"SUBCASE_PASS" if error is None else "SUBCASE_FAIL","test":subtest.id()})
  super().addSubTest(test,subtest,error)
suite=unittest.defaultTestLoader.loadTestsFromName(method)
assert suite.countTestCases()==1
stream=io.StringIO();started=time.monotonic()
result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
elapsed=time.monotonic()-started
with (d/"controls.log").open("x") as f:f.write(stream.getvalue())
write("events.json",events)
after=snapshot();write("source-after.json",after)
unchanged=before==after and git("rev-parse","HEAD")==head and not git("status","--porcelain")
receipt={"status":"PASS" if result.wasSuccessful() and unchanged else "FAIL","source":head,"method":method,"new_control_methods":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"old_control_methods":0,"product_methods":0,"actual_simulator_queries":0,"subcases_passed":sum(e["event"]=="SUBCASE_PASS" for e in events),"input_count":len(before["files"]),"loaded_source_count":len(before["loaded"]),"before_after_unchanged":unchanged,"elapsed_seconds":elapsed,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"originals":{p.name:{"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(d.iterdir()) if p.is_file()}}
write("receipt.json",receipt)
print(json.dumps(receipt))
raise SystemExit(0 if receipt["status"]=="PASS" else 1)
