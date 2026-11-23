"""One new injected cleanup-order control; no process/device actions."""
import argparse, hashlib, importlib.util, json, os, pathlib, subprocess, sys, time, traceback
ROOT=pathlib.Path(__file__).resolve().parents[4]
HERE=pathlib.Path(__file__).resolve().parent
os.environ["GIT_OPTIONAL_LOCKS"]="0"
sys.dont_write_bytecode=True
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def write(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+"\n")
def snapshot():
    m=read(HERE/"control-inputs.json");out={}
    for rel,want in m["inputs"].items():
        p=ROOT/rel;st=p.lstat();assert p.is_file() and not p.is_symlink()
        got={"sha256":sha(p.read_bytes()),"bytes":st.st_size,"mode":st.st_mode&0o777}
        assert got==want,(rel,got,want)
        blob=subprocess.check_output(["git","-C",str(ROOT),"show","HEAD:"+rel])
        assert sha(blob)==got["sha256"],rel
        out[rel]=got
    return out
def main():
    a=argparse.ArgumentParser();a.add_argument("--expected-head",required=True);args=a.parse_args()
    assert subprocess.check_output(["git","-C",str(ROOT),"rev-parse","HEAD"],text=True).strip()==args.expected_head
    assert not subprocess.check_output(["git","-C",str(ROOT),"status","--porcelain","--untracked-files=no"]).strip()
    out=HERE/"attempt1";out.mkdir(mode=0o700)
    start=time.monotonic();events=[];result={"status":"FAIL","productExecutions":0,"oldControls":0,"method":"test_provider_failure_does_not_skip_owned_device_cleanup","subcases":[]}
    before=snapshot();write(out/"source-before.json",before)
    primary=None
    try:
        for name in ("contracts","current_execution"):
            assert name not in sys.modules
            path=ROOT/"Tools/CurrentAppleValidation"/(name+".py")
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module;spec.loader.exec_module(module)
        c=sys.modules["contracts"];driver=sys.modules["current_execution"]
        from unittest import mock
        class ProviderFailure(RuntimeError):pass
        class DeviceFailure(RuntimeError):pass
        class SourceFailure(RuntimeError):pass
        class FakeCommands:
            def __init__(self,*a):self.cleanup_mode=False
        def scenario(name,provider_bad=False,device_bad=False,source_bad=False,admission_bad=False):
            events.append({"event":"start","case":name})
            work=out/name;ev=work/"evidence";ev.mkdir(parents=True)
            source={"testOnly":"source hook is injected; no real source admission claimed"}
            driver.write(ev/"source-before.json",source)
            context={"profile":"native-ui-failed","sourceCommit":args.expected_head,"runID":"1","runAttempt":"1","repository":c.REPOSITORY}
            driver.write(ev/"execution-intent.json",{"context":context,"sourceAdmissionSHA256":driver.digest(ev/"source-before.json")})
            trace=[];checks=0
            def check(value):
                nonlocal checks
                checks+=1;trace.append("source-"+str(checks));assert value==source
                if admission_bad or (source_bad and checks==2):raise SourceFailure("source-boundary")
                return {"readOnlyFixture":True}
            def provider(*a):
                trace.append("provider");assert a[1:3]==("cleanup",None)
                if provider_bad:raise ProviderFailure("original-provider-failure")
                return {"status":"COMPLETE"}
            def recover(*a):trace.append("recover");return ["owned-test-uuid"]
            def devices(*a):
                trace.append("devices");assert a[2]==["owned-test-uuid"]
                if device_bad:raise DeviceFailure("later-device-failure")
                return [{"owned_simulator_cleanup_status":"COMPLETE"}]
            def groups(*a):trace.append("groups");return []
            with mock.patch.dict(os.environ,{"GITHUB_ACTIONS":"true","GITHUB_REPOSITORY":c.REPOSITORY,"GITHUB_SHA":args.expected_head,"GITHUB_RUN_ID":"1","GITHUB_RUN_ATTEMPT":"1"}),mock.patch.object(driver.platform,"system",return_value="Darwin"),mock.patch.object(driver.platform,"machine",return_value="arm64"),mock.patch.multiple(driver,evidence_root=lambda p:work,git=lambda *a:(args.expected_head+"\n").encode(),recheck=check,helpers=lambda s:{},Commands=FakeCommands,unfinished_groups=groups,recover_owned=recover,cleanup_devices=devices):
                got=driver.cleanup_only("native-ui-failed",args.expected_head,provider)
            if admission_bad:
                assert trace==["source-1"] and got["firstFailure"]["type"]=="SourceFailure"
                assert "devices" not in got and "provider" not in got
            else:
                assert trace==["source-1","groups","provider","recover","devices","source-2"],trace
                if provider_bad:
                    assert got["status"]=="FAIL" and got["firstFailure"]=={"type":"ProviderFailure","message":"original-provider-failure"}
                    assert "providerFailure" in got
                    if device_bad:assert got["deviceFailure"]["type"]=="DeviceFailure"
                    else:assert got["devices"]==[{"owned_simulator_cleanup_status":"COMPLETE"}]
                    if source_bad:assert got["loadedFailure"]["type"]=="SourceFailure"
                    else:assert got["loadedAfter"]=={"readOnlyFixture":True}
                else:assert got["status"]=="PASS"
            assert read(ev/"cleanup-final.json")==got
            events.append({"event":"pass","case":name,"trace":trace});result["subcases"].append(name)
        scenario("provider_error_still_attempts_devices_and_loaded_check",provider_bad=True)
        scenario("three_failures_keep_first_provider_error",provider_bad=True,device_bad=True,source_bad=True)
        scenario("successful_independent_cleanup_remains_complete")
        scenario("initial_source_rejection_never_grants_cleanup",admission_bad=True)
        result["loaded"]={n:{"path":str(pathlib.Path(sys.modules[n].__file__).resolve()),"sha256":sha(pathlib.Path(sys.modules[n].__file__).read_bytes())}for n in ("contracts","current_execution")}
        assert all(pathlib.Path(v["path"]).is_relative_to(ROOT) for v in result["loaded"].values())
        assert time.monotonic()-start<10
        result["status"]="PASS"
    except BaseException as e:
        primary=e;result["failure"]={"type":type(e).__name__,"message":str(e),"traceback":traceback.format_exc()}
    finally:
        write(out/"events.json",events)
        try:
            after=snapshot();write(out/"source-after.json",after);assert before==after
        except BaseException as e:
            result["sourceAfterFailure"]={"type":type(e).__name__,"message":str(e)};result["status"]="FAIL";primary=primary or e
        result["elapsedSeconds"]=time.monotonic()-start
        write(out/"result.json",result)
        print(json.dumps(result,sort_keys=True))
    return 0 if primary is None and result["status"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
