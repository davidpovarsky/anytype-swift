#!/usr/bin/env python3
"""Two actual-child receipt/absence fault controls; zero engine calls."""
import argparse,hashlib,importlib.util,json,os
from pathlib import Path
from unittest.mock import patch
HELPER_SHA="64b4310f7b1db57df0236074d4c7a9058041f6c06e6667797ceafe0099360a21"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);a=ap.parse_args()
    directory=Path(__file__).resolve().parent;helper=directory/"darwin_owned_commands.py"
    if hashlib.sha256(helper.read_bytes()).hexdigest()!=HELPER_SHA:raise ValueError("helper identity")
    spec=importlib.util.spec_from_file_location("owned_component_faults",helper)
    c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
    root=a.root.resolve();root.mkdir(parents=True,exist_ok=False)
    result={"protocol":"pinkha-owned-component-command-fault-controls-v1","status":"FAIL","nativeCalls":0,"appBuilds":0,"helperSHA256":HELPER_SHA,"controls":[]}
    try:
        denied=c.Commands(root/"denied",0)
        calls=[]
        def permission(pgid,sig):
            calls.append((pgid,sig))
            if sig!=0:raise AssertionError("fault control attempted a signal")
            raise PermissionError("injected post-exit observation refusal")
        with patch.object(c.os,"killpg",permission):
            try:denied.run("actual-true",["/usr/bin/true"],root,dict(os.environ),10)
            except RuntimeError:pass
            else:raise AssertionError("denied observation became command success")
            failures=denied.cleanup()
        row=json.loads((root/"denied/commands/actual-true/result.json").read_text())
        original=json.loads((root/"denied/commands/actual-true/original-exit.json").read_text())
        assert row["status"]=="FAIL" and row["exitCode"]==0 and original["exitCode"]==0
        assert row["groupState"]=="UNRESOLVED_EPERM" and failures and all(sig==0 for _,sig in calls)
        result["controls"].append({"name":"actual_child_exit_survives_denied_observer","passed":True,"signals":0,"originalExitCode":0,"originalCommandStatus":"FAIL"})
        absent=c.Commands(root/"absent",0)
        absent.run("actual-true",["/usr/bin/true"],root,dict(os.environ),10)
        assert len(absent.absent)==1
        with patch.object(c.os,"killpg",side_effect=AssertionError("historical group re-probed")):
            assert absent.cleanup()==[]
            assert absent.observe(next(iter(absent.absent)))=="ABSENT_PREVIOUSLY_PROVED"
        result["controls"].append({"name":"positive_absence_never_reprobes_recycled_group","passed":True,"signals":0})
        assert hashlib.sha256(helper.read_bytes()).hexdigest()==HELPER_SHA
        result.update(status="PASS_TWO_COMMAND_FAULT_CONTROLS_NOT_NATIVE_ACCEPTANCE",passed=2,failed=0)
    except Exception as error:result["error"]=type(error).__name__+": "+str(error)
    c.save(root/"receipt.json",result);print(json.dumps(result))
    return 0 if result["status"].startswith("PASS_") else 1
if __name__=="__main__":raise SystemExit(main())
