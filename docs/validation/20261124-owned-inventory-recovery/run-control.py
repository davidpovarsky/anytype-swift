"""Fixed new pure policy method; execution supervision belongs to launch-control.py."""
import argparse
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import time
import traceback
import unittest

NAMESPACE = "docs/validation/20261124-owned-inventory-recovery"
METHOD = "test_inventory_policy.InventoryRecoveryControl.test_exact_timeout_recovery_and_first_failure_contract"
MODULES = {
    "contracts": "Tools/CurrentAppleValidation/contracts.py",
    "current_execution": "Tools/CurrentAppleValidation/current_execution.py",
    "owned_inventory_recovery": "Tools/CurrentAppleValidation/owned_inventory_recovery.py",
    "cleanup_policy": "Tools/CurrentAppleValidation/cleanup_policy.py",
    "test_inventory_policy": NAMESPACE + "/test_inventory_policy.py",
}
INPUTS = tuple(sorted([
    *MODULES.values(), "Tools/CurrentAppleValidation/source-inputs.json",
    NAMESPACE + "/control-data/origins.json",
    NAMESPACE + "/control-data/commands/booted-0.command.json",
    NAMESPACE + "/control-data/commands/booted-0.started.json",
    NAMESPACE + "/control-data/commands/booted-0.log",
    NAMESPACE + "/control-data/device-0/created.json",
    NAMESPACE + "/control-data/device-0/intent.json",
    NAMESPACE + "/control-profile.json", NAMESPACE + "/run-control.py",
]))
parser = argparse.ArgumentParser()
parser.add_argument("--root", required=True)
parser.add_argument("--source", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
ROOT = Path(args.root)
OUT = Path(args.output)
MANIFEST = ROOT / NAMESPACE / "control-inputs.json"
sys.dont_write_bytecode = True
os.umask(0o077)

def require(value, reason):
    if not value:
        raise ValueError(reason)

def error(failure):
    return {"type": type(failure).__name__, "message": str(failure), "traceback": traceback.format_exc()}

def raw(path, maximum=65536):
    before = path.lstat()
    require(path.resolve() == path and stat.S_ISREG(before.st_mode) and before.st_nlink == 1
            and before.st_uid == os.getuid() and before.st_size <= maximum, "bounded_owned_source_file")
    value = path.read_bytes()
    after = path.lstat()
    require((before.st_dev,before.st_ino,before.st_mode,before.st_size,before.st_mtime_ns) ==
            (after.st_dev,after.st_ino,after.st_mode,after.st_size,after.st_mtime_ns), "source_changed_during_read")
    return value

def sha(value):
    return hashlib.sha256(value).hexdigest()

def save(path, value):
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    require(len(encoded) <= 65536, "finite_control_receipt")
    with path.open("xb") as stream:
        stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
    path.chmod(0o600)

def git(*parts):
    return subprocess.check_output(["git", "-c", "core.packedGitWindowSize=16m",
        "-c", "core.packedGitLimit=64m", "-C", str(ROOT), *parts], timeout=15,
        env={**os.environ, "GIT_OPTIONAL_LOCKS":"0"})

def source_map(fixed):
    require(git("rev-parse", "HEAD").decode().strip() == args.source, "frozen_control_head_changed")
    paths = [*INPUTS, NAMESPACE + "/control-inputs.json"]
    rows = {}
    for row in git("ls-tree", "-r", "-z", args.source, "--", *paths).split(b"\0"):
        if row:
            header, name = row.split(b"\t",1)
            mode, kind, oid = header.decode().split()
            require(kind == "blob" and mode == "100644", "control_input_git_type")
            rows[name.decode()] = (mode, oid)
    require(set(rows) == set(paths), "control_input_git_closure")
    result = {}
    for name in paths:
        value = raw(ROOT/name)
        oid = hashlib.sha1(b"blob " + str(len(value)).encode() + b"\0" + value).hexdigest()
        mode, expected_oid = rows[name]
        require(oid == expected_oid and not (ROOT/name).stat().st_mode & 0o111, "physical_git_input_changed")
        observed = {"bytes":len(value),"sha256":sha(value),"gitBlob":oid,"gitMode":mode,
                    "physicalMode":stat.S_IMODE((ROOT/name).stat().st_mode)}
        if name in fixed["inputs"]:
            require({k:observed[k] for k in ("bytes","sha256","gitBlob","gitMode")} == fixed["inputs"][name],
                    "frozen_input_changed:"+name)
        result[name] = observed
    return result

def loaded():
    observed = {}
    for name, relative in MODULES.items():
        if name in sys.modules:
            require(Path(sys.modules[name].__file__).resolve() == ROOT/relative, "foreign_required_module:"+name)
    allowed = set(MODULES.values())
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module,"__file__",None)
        if not filename:
            continue
        path = Path(filename).absolute()
        if path.resolve().is_relative_to(ROOT):
            relative = path.resolve().relative_to(ROOT).as_posix()
            require(path == path.resolve() and relative in allowed, "unexpected_loaded_repository_source:"+name)
            observed[relative] = sha(raw(path))
    return observed

def main():
    require(ROOT.is_absolute() and ROOT.resolve() == ROOT and ROOT.name == "owned-inventory-recovery",
            "fixed_source_writer_required")
    require(re.fullmatch("[0-9a-f]{40}",args.source), "full_frozen_source_required")
    require(OUT.is_absolute() and not OUT.exists() and OUT.parent.resolve() == OUT.parent,
            "fresh_outside_control_root")
    require(not OUT.is_relative_to(ROOT), "control_outputs_must_be_outside_source")
    OUT.mkdir(mode=0o700)
    started = time.monotonic()
    manifest_raw = raw(MANIFEST)
    manifest_sha256 = sha(manifest_raw)
    fixed = json.loads(manifest_raw)
    require(fixed["method"] == METHOD and tuple(sorted(fixed["inputs"])) == INPUTS
            and fixed["moduleOrigins"] == MODULES, "fixed_one_method_closure_changed")
    require(raw(Path(__file__)) == raw(ROOT/NAMESPACE/"run-control.py"), "outside_wrapper_differs_from_git_source")
    before = source_map(fixed)
    save(OUT/"source-before.json", {"head":args.source,"files":before})
    require(not git("status","--porcelain","--untracked-files=no").strip(), "tracked_source_dirty")
    for directory in (ROOT/"Tools/CurrentAppleValidation",ROOT/NAMESPACE):
        sys.path.insert(0,str(directory))
    for name, relative in MODULES.items():
        spec = importlib.util.find_spec(name)
        require(spec is not None and spec.origin is not None and Path(spec.origin).resolve() == ROOT/relative,
                "foreign_preimport_origin:"+name)
    os.environ["OWNED_INVENTORY_CONTROL_OUTPUT"] = str(OUT/"cases")
    (OUT/"cases").mkdir(mode=0o700)
    primary = None
    final_failures = []
    result = None
    named = {"methodPass":0,"methodFail":0,"methodError":0,"subcasePass":0,"subcaseFail":0}
    events = (OUT/"events.jsonl").open("xb")
    def event(kind, case, detail=None):
        row={"kind":kind,"case":case,"elapsed":time.monotonic()-started}
        if detail is not None:row["detail"]=detail
        encoded=(json.dumps(row,sort_keys=True)+"\n").encode()
        events.write(encoded);events.flush();os.fsync(events.fileno())
    class NamedResult(unittest.TextTestResult):
        def startTest(self, test):
            event("method-start",test.id());super().startTest(test)
        def addSuccess(self, test):
            named["methodPass"]+=1;event("method-pass",test.id());super().addSuccess(test)
        def addFailure(self, test, failure):
            named["methodFail"]+=1;event("method-fail",test.id(),str(failure[1]));super().addFailure(test,failure)
        def addError(self, test, failure):
            named["methodError"]+=1;event("method-error",test.id(),str(failure[1]));super().addError(test,failure)
        def addSubTest(self, test, subtest, failure):
            key="subcasePass" if failure is None else "subcaseFail"
            named[key]+=1;event("subcase-pass" if failure is None else "subcase-fail",subtest.id(),
                               None if failure is None else str(failure[1]))
            super().addSubTest(test,subtest,failure)
    try:
        module=importlib.import_module("test_inventory_policy")
        before_loaded=loaded()
        require(set(before_loaded)==set(MODULES.values())-{"Tools/CurrentAppleValidation/cleanup_policy.py"},
                "initial_loaded_closure_changed")
        save(OUT/"loaded-before.json",before_loaded)
        suite=unittest.defaultTestLoader.loadTestsFromName(METHOD)
        require(suite.countTestCases()==1,"exactly_one_new_method_required")
        result=unittest.TextTestRunner(stream=sys.stderr,verbosity=2,resultclass=NamedResult).run(suite)
        require(result.testsRun==1 and not result.skipped and result.wasSuccessful(),"new_policy_control_failed")
    except BaseException as failure:
        primary=error(failure)
    finally:
        for phase, action in (
            ("events_close",lambda:events.close()),
            ("source_after",lambda:source_map(fixed)),
            ("loaded_after",loaded)):
            try:
                value=action()
                if phase=="source_after":
                    save(OUT/"source-after.json",{"head":args.source,"files":value})
                    require(value==before,"source_after_differs")
                elif phase=="loaded_after":
                    save(OUT/"loaded-after.json",value)
                    require(set(value)==set(MODULES.values()),"final_loaded_closure_changed")
                    require(all(before[p]["sha256"]==v for p,v in value.items()),"loaded_source_hash_changed")
            except BaseException as failure:
                final_failures.append({"phase":phase,**error(failure)})
        receipt={"status":"PASS" if primary is None and not final_failures else "FAIL",
            "source":args.source,"manifestSHA256":manifest_sha256,"method":METHOD,"namedOutcomes":named,
            "primaryFailure":primary,"finalFailures":final_failures,"testMethods":0 if result is None else result.testsRun,
            "allCommandsInMethodSimulated":True,"simulatorCommands":0,"productMethods":0,
            "nativeBuilds":0,"appleBuilds":0,"oldTestsImportedOrExecuted":False,
            "elapsedSeconds":time.monotonic()-started}
        try:
            save(OUT/"control-result.json",receipt)
        except BaseException as failure:
            receipt["status"]="FAIL"
            receipt["resultPersistenceFailure"]=error(failure)
        print(json.dumps(receipt,sort_keys=True))
    return 0 if receipt["status"]=="PASS" else 1

if __name__=="__main__":
    raise SystemExit(main())
