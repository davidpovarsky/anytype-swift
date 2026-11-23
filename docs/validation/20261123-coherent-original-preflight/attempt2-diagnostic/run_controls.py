from pathlib import Path
import datetime, hashlib, json, platform, subprocess, sys, time, unittest
ROOT = Path("/mnt/development/projects/worktrees/anytype-wave15-coherent-original-preflight-20261123")
OUT = Path(__file__).resolve().parent
SOURCE = "8ae1318bb71221d02c26315f8b1ba6ff929fac4c"
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "Tools/PinkhaSimulatorGate"))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name, value): (OUT/name).write_text(json.dumps(value, indent=2, sort_keys=True)+"\n")
def head(): return subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.strip()
assert head() == SOURCE
import test_coherent_original_preflight as controls
methods = ["test_quiescence_timeout_and_late_zero_observations_remain_on_original_failed_command"]
assert len(methods) == 1
sources = {}
for name,module in list(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if filename:
        path = Path(filename).resolve()
        if path.is_file() and path.is_relative_to(ROOT):
            sources[name] = dict(path=str(path), relative_path=path.relative_to(ROOT).as_posix(),
                                sha256=sha(path), bytes=path.stat().st_size)
save("source-before.json", sources)
save("command.json", dict(argv=[sys.executable,"-B",str(Path(__file__).resolve())],
    source_sha=SOURCE, python=sys.version, platform=platform.platform(), methods=methods,
    module_search_path=str(ROOT/"Tools/PinkhaSimulatorGate"), previous_control_methods_rerun=0,
    simulator_commands=0, actual_product_methods=0))
events=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),action="start",test=test.id()))
        super().startTest(test)
    def addSuccess(self,test):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),action="pass",test=test.id()))
        super().addSuccess(test)
    def addFailure(self,test,error):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),action="fail",test=test.id()))
        super().addFailure(test,error)
    def addError(self,test,error):
        events.append(dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(),action="error",test=test.id()))
        super().addError(test,error)
suite=unittest.defaultTestLoader.loadTestsFromNames(
 ["test_coherent_original_preflight.CoherentOriginalPreflightControls."+name for name in methods])
assert suite.countTestCases()==1
started=time.monotonic()
result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2,resultclass=Result).run(suite)
save("events.json",events)
after={name:dict(row,sha256=sha(Path(row["path"])),bytes=Path(row["path"]).stat().st_size) for name,row in sources.items()}
save("source-after.json",after)
unchanged=after==sources and head()==SOURCE
save("result.json",dict(status="PASS_NEW_PREFLIGHT_CONTROLS" if result.wasSuccessful() and unchanged else "FAIL",
 source_sha=SOURCE,methods=methods,started=1,passed=sum(row["action"]=="pass" for row in events),
 failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
 elapsed_seconds=time.monotonic()-started,source_unchanged=unchanged,
 previous_control_methods_rerun=0,retained_original_methods=7,simulator_commands=0,actual_product_methods=0,
 actual_mac_preflight="NOT_RUN",finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat()))
sys.exit(0 if result.wasSuccessful() and unchanged else 1)
