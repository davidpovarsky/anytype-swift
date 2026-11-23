#!/usr/bin/env python3
import json,sys,time,unittest,hashlib
from pathlib import Path
from datetime import datetime,timezone
sys.dont_write_bytecode=True
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-page154-mounted-admission-20261123")
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/"Tools/PinkhaSemanticAnchorWire/apple_mounted"))
NAME="test_mounted_known_pair.MountedKnownPairAdapterControl.test_mounted_import_and_owned_region_use_qualified_pair_without_fallback"
events=(OUT/"events.jsonl").open("x")
def emit(kind,test,**extra):
 events.write(json.dumps(dict(event=kind,method=test.id(),time=datetime.now(timezone.utc).isoformat(),**extra),sort_keys=True)+"\n");events.flush()
class Result(unittest.TextTestResult):
 def startTest(self,test):emit("START",test);super().startTest(test)
 def addSuccess(self,test):emit("PASS",test);super().addSuccess(test)
 def addFailure(self,test,error):emit("FAIL",test);super().addFailure(test,error)
 def addError(self,test,error):emit("ERROR",test);super().addError(test,error)
 def addSkip(self,test,reason):emit("SKIP",test,reason=reason);super().addSkip(test,reason)
suite=unittest.TestLoader().loadTestsFromName(NAME)
assert suite.countTestCases()==1
started=time.monotonic()
result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
events.close()
scope=json.loads((ROOT/"docs/validation/20261123-semantic-page-mounted-known-pair/source-review.json").read_text())["source_sha256"]
loaded={}
for module in tuple(sys.modules.values()):
 raw=getattr(module,"__file__",None)
 if not raw:continue
 path=Path(raw).resolve()
 if path.suffix==".py" and path.is_relative_to(ROOT):
  relative=path.relative_to(ROOT).as_posix()
  digest=hashlib.sha256(path.read_bytes()).hexdigest()
  assert relative in scope and digest==scope[relative],relative
  loaded[relative]=digest
with (OUT/"loaded-repo-modules.json").open("x") as f:f.write(json.dumps(loaded,sort_keys=True,indent=2)+"\n")
actual={"selector":NAME,"tests_run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),"success":result.wasSuccessful(),"elapsed_seconds":time.monotonic()-started,"loaded_repo_modules":len(loaded),"old_controls_rerun":0,"simulator_commands_executed":0,"product_tests_executed":0}
with (OUT/"result.json").open("x") as f:f.write(json.dumps(actual,sort_keys=True,indent=2)+"\n")
sys.exit(0 if actual["success"] and actual["tests_run"]==1 and not actual["skips"] else 1)
