#!/usr/bin/env python3
from pathlib import Path
import ast,datetime,hashlib,importlib,json,os,platform,subprocess,sys,time,unittest
ROOT=Path("/mnt/development/projects/worktrees/anytype-wave15-native-ui-original-products-20261123")
SOURCE="e72cbbdad01f2ef745d3fd24a0a6389b6ed0e75d"
OUT=Path("/mnt/development/projects/evidence/native-ui-original-products-20261123/attempt1")
NAMES=[
"test_two_origins_zero_builds_and_unexecuted_scope_refuse_relabeling",
"test_restoration_preserves_modes_and_refuses_links_extras_missing_or_changed_bytes",
"test_exact_27_2_runtime_and_original_descriptor_allow_only_one_bound_token_change",
"test_fixed_commands_and_workflow_never_build_or_repeat_twenty_two_retained_methods"]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(name,value):
 with (OUT/name).open("x",encoding="utf-8") as stream:
  json.dump(value,stream,sort_keys=True,indent=2);stream.write("\n")
def git(*args):return subprocess.check_output(["git",*args],cwd=ROOT,timeout=30)
def snapshot():
 paths={p for directory in ("Tools/AnyEnginePort","Tools/PinkhaSimulatorGate") for p in (ROOT/directory).rglob("*.py") if p.is_file()}
 review=json.loads((ROOT/"docs/validation/20261123-native-ui-original-products/source-review.json").read_bytes())
 paths.update(ROOT/p for p in review["sourceInputs"])
 fixed=json.loads((ROOT/"Tools/AnyEnginePort/native-ui-original-products-451082.json").read_bytes())
 paths.update(ROOT/p for p in fixed["providerQualification"]["proofFiles"])
 paths.update(ROOT/p for p in fixed["providerQualification"]["inputs"])
 return {p.relative_to(ROOT).as_posix():sha(p.read_bytes()) for p in sorted(paths)}
assert git("rev-parse","HEAD").decode().strip()==SOURCE
assert not git("status","--porcelain")
assert not OUT.exists()
OUT.mkdir()
before=snapshot()
write("source-before.json",before)
review=json.loads((ROOT/"docs/validation/20261123-native-ui-original-products/source-review.json").read_bytes())
assert all(before[p]==digest for p,digest in review["sourceInputs"].items())
write("intent.json",{"sourceCommit":SOURCE,"methods":NAMES,"oldControllerTestsRequested":0,"productMethodsRequested":0,
"sourceReviewSHA256":sha((ROOT/"docs/validation/20261123-native-ui-original-products/source-review.json").read_bytes()),
"newControlOnly":True,"gitSourceDataInputs":[{"commit":"846c33eac1b399f625b5d3bc6ead9ebed39c43c2",
"path":".github/workflows/torah-inspector-ipados27.yml","sha256":sha(git("show","846c33eac1b399f625b5d3bc6ead9ebed39c43c2:.github/workflows/torah-inspector-ipados27.yml"))}],
"originalDescriptorSHA256":"67228dbc1e1636b9e877d487528ea1fa37023a9a3ff8e53c8d92a94d38c897e6"})
events=[]
class Recording(unittest.TextTestResult):
 def startTest(self,test):
  events.append({"method":test.id(),"event":"START"});super().startTest(test)
 def addSuccess(self,test):
  events.append({"method":test.id(),"event":"PASS"});super().addSuccess(test)
 def addFailure(self,test,error):
  events.append({"method":test.id(),"event":"FAIL","kind":error[0].__name__});super().addFailure(test,error)
 def addError(self,test,error):
  events.append({"method":test.id(),"event":"ERROR","kind":error[0].__name__});super().addError(test,error)
 def addSkip(self,test,reason):
  events.append({"method":test.id(),"event":"SKIP","reason":reason});super().addSkip(test,reason)
 def addSubTest(self,test,subtest,error):
  if error is not None:events.append({"method":test.id(),"event":"SUBTEST_FAIL","subtest":str(subtest),"kind":error[0].__name__})
  super().addSubTest(test,subtest,error)
sys.path.insert(0,str(ROOT/"Tools/AnyEnginePort"))
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
begin=time.monotonic()
module=importlib.import_module("test_native_ui_original_products")
suite=unittest.TestSuite(module.OriginalNativeUIProductsControls(name) for name in NAMES)
with (OUT/"controls.log").open("x",encoding="utf-8") as log:
 result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Recording).run(suite)
elapsed=time.monotonic()-begin
write("events.json",events)
after=snapshot();write("source-after.json",after)
loaded={}
for module in list(sys.modules.values()):
 path=getattr(module,"__file__",None)
 if not path:continue
 p=Path(path).resolve()
 if p.is_file() and p.is_relative_to(ROOT) and p.suffix==".py":
  loaded[p.relative_to(ROOT).as_posix()]=sha(p.read_bytes())
loaded=dict(sorted(loaded.items()))
loaded_git={p:sha(git("show",SOURCE+":"+p)) for p in loaded}
changed=before!=after or loaded!=loaded_git or git("rev-parse","HEAD").decode().strip()!=SOURCE or bool(git("status","--porcelain"))
qualified=result.wasSuccessful() and result.testsRun==4 and not result.skipped and not changed
write("result.json",{"sourceCommit":SOURCE,"passed":qualified,"testsRun":result.testsRun,"failures":len(result.failures),
"errors":len(result.errors),"skips":len(result.skipped),"elapsedSeconds":elapsed,"sourceInputs":len(before),
"sourceUnchanged":before==after,"loadedSourceMatchesFrozenGit":loaded==loaded_git,"loadedRepositoryModules":loaded,
"oldControllerMethodsExecuted":0,"AppleMethodsExecuted":0,"newBuilds":0,"python":sys.version,"platform":platform.platform()})
(OUT/"original-controller.py").write_bytes(Path(__file__).read_bytes())
originals={p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file()}
write("audit.json",{"schemaVersion":1,"status":"PASS" if qualified else "FAIL","sourceCommit":SOURCE,"startedAt":started,
"finishedAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"originals":originals,"actualNamedEvents":events,
"sourceInputs":len(before),"actualLoadedSourceInputs":len(loaded),"loadedSourceMatchesFrozenGit":loaded==loaded_git,
"sourceUnchanged":before==after,"oldControllerMethodsExecuted":0,"AppleMethodsExecuted":0,"newBuilds":0})
print(json.dumps({"status":"PASS" if qualified else "FAIL","testsRun":result.testsRun,"failures":len(result.failures),
"errors":len(result.errors),"sourceInputs":len(before),"loadedInputs":len(loaded),"elapsedSeconds":elapsed,
"evidence":str(OUT),"auditSHA256":sha((OUT/"audit.json").read_bytes())},sort_keys=True))
sys.exit(0 if qualified else 1)
