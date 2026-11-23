import sys,unittest,json,pathlib,hashlib,time
w=pathlib.Path(sys.argv[1]);e=pathlib.Path(sys.argv[2]);sys.path.insert(0,str(w/"Tools/AnyEnginePort"))
events=[]
class R(unittest.TextTestResult):
 def startTest(self,test):
  events.append({"event":"start","method":test.id()});super().startTest(test)
 def addSuccess(self,test):
  events.append({"event":"pass","method":test.id()});super().addSuccess(test)
 def addError(self,test,err):
  events.append({"event":"error","method":test.id(),"error_type":err[0].__name__});super().addError(test,err)
 def addFailure(self,test,err):
  events.append({"event":"fail","method":test.id(),"error_type":err[0].__name__});super().addFailure(test,err)
names=["test_hanlin_fixture_start_observation.StarterObservationTests.test_real_owned_starter_failure_preserves_finite_original_and_private_bytes","test_hanlin_fixture_start_observation.StarterObservationTests.test_bounded_timeout_os_error_and_untrusted_output_never_create_readiness"]
start=time.monotonic()
r=unittest.TextTestRunner(verbosity=2,resultclass=R).run(unittest.TestLoader().loadTestsFromNames(names))
loaded={}
for mod in tuple(sys.modules.values()):
 f=getattr(mod,"__file__",None)
 if f:
  p=pathlib.Path(f).resolve()
  if p.is_relative_to(w) and p.is_file():loaded[str(p.relative_to(w))]=hashlib.sha256(p.read_bytes()).hexdigest()
(e/"events.json").write_text(json.dumps(events,indent=2)+"\n")
(e/"result.json").write_text(json.dumps({"passed":r.wasSuccessful(),"tests_run":r.testsRun,"failures":len(r.failures),"errors":len(r.errors),"skips":len(r.skipped),"elapsed_seconds":time.monotonic()-start,"methods":names,"loaded_repo_modules":loaded,"old_controls_executed":0,"product_methods":0},indent=2)+"\n")
raise SystemExit(0 if r.wasSuccessful() else 1)
