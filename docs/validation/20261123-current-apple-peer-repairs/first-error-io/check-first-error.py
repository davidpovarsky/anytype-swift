"""One new injected final-I/O control; no real product/process helper execution."""
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
    start=time.monotonic();events=[];result={"status":"FAIL","productExecutions":0,"oldControls":0,"method":"test_late_evidence_io_preserves_first_command_failure","subcases":[]}
    before=snapshot();write(out/"source-before.json",before)
    primary=None
    try:
        for name in ("contracts","current_execution"):
            assert name not in sys.modules
            path=ROOT/"Tools/CurrentAppleValidation"/(name+".py")
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module;spec.loader.exec_module(module)
        c=sys.modules["contracts"];driver=sys.modules["current_execution"]
        import copy
        from types import SimpleNamespace
        from unittest import mock
        class OriginalFailure(RuntimeError):pass
        class PreservationFailure(OSError):pass
        def scenario(stage,has_primary=True):
            name=stage+("-original" if has_primary else "-without-original")
            events.append({"event":"start","case":name})
            directory=out/name;directory.mkdir()
            original=OriginalFailure("original-command-wait-failure")
            secondary=PreservationFailure("injected-"+stage)
            commands=driver.Commands.__new__(driver.Commands);commands.root=directory
            commands.context={"scope":"injected host control only"};commands.deadline=time.monotonic()+7200;commands.cleanup_mode=False
            trace=[];state={"stream":None,"closed":False,"fsyncs":0,"record":None}
            process=SimpleNamespace(pid=123456789,returncode=0)
            def wait(timeout):
                trace.append("wait");assert timeout==1
                if has_primary:raise original
                return 0
            process.wait=wait
            def terminate(p):assert p is process;trace.append("owned-helper")
            def kernel(pid,deadline):
                assert pid==process.pid and 0<deadline-time.monotonic()<=10
                trace.append("kernel-helper");return {"outcome":"ABSENT_ESRCH","testDouble":True}
            commands.helpers={"wave15_batch":SimpleNamespace(terminate_owned=terminate),"run_owned_single_lane":SimpleNamespace(_sdk06_kernel_group_observation=kernel)}
            log=directory/"new-control-command.log"
            original_open=pathlib.Path.open;original_stat=pathlib.Path.stat
            original_digest=driver.digest;original_write=driver.write;original_fsync=os.fsync
            class Stream:
                def __init__(self,inner):self.inner=inner;self.flushes=0
                def flush(self):
                    self.flushes+=1
                    if stage=="flush" and self.flushes==2:raise secondary
                    return self.inner.flush()
                def fileno(self):return self.inner.fileno()
                def close(self):
                    self.inner.close();state["closed"]=True
                    if stage=="close":raise secondary
            def opened(path,*a,**kw):
                raw=original_open(path,*a,**kw)
                if path==log and a and a[0]=="xb":
                    state["stream"]=Stream(raw);return state["stream"]
                return raw
            def fsync(fd):
                if state["stream"] is not None and not state["closed"] and fd==state["stream"].fileno():
                    state["fsyncs"]+=1
                    if stage=="fsync" and state["fsyncs"]==2:raise secondary
                return original_fsync(fd)
            def stat_file(path,*a,**kw):
                if path==log and state["closed"] and stage=="stat":raise secondary
                return original_stat(path,*a,**kw)
            def dig(path):
                if path==log and stage=="digest":raise secondary
                return original_digest(path)
            def save(path,value):
                if path.name.endswith(".command.json"):
                    state["record"]=copy.deepcopy(value)
                    if stage=="receipt":raise secondary
                return original_write(path,value)
            caught=None
            with mock.patch.object(pathlib.Path,"open",opened),mock.patch.object(pathlib.Path,"stat",stat_file),mock.patch.object(driver.subprocess,"Popen",return_value=process),mock.patch.object(driver.os,"fsync",fsync),mock.patch.object(driver,"digest",dig),mock.patch.object(driver,"write",save):
                try:commands.run(["injected-no-real-process"],"new-control-command",1)
                except BaseException as e:caught=e
            assert caught is (original if has_primary else secondary),(stage,repr(caught))
            assert trace==["wait","owned-helper","kernel-helper"],trace
            assert state["closed"] and state["record"] is not None
            rec=state["record"];assert rec["status"]=="FAIL"
            assert rec["firstFailure"]["type"]==("OriginalFailure" if has_primary else "PreservationFailure")
            assert rec["firstFailure"]["message"]==str(original if has_primary else secondary)
            if stage in ("digest","stat"):
                assert rec["logMetadataStatus"]=="UNAVAILABLE" and rec["logSHA256"] is None and rec["logBytes"] is None
            else:assert rec["logMetadataStatus"]=="AVAILABLE"
            if stage=="receipt":
                assert caught.__cause__ is secondary and not(directory/"new-control-command.command.json").exists()
            else:
                assert rec["preservationFailures"] and read(directory/"new-control-command.command.json")==rec
            write(directory/"control-observation.json",{"caughtType":type(caught).__name__,"caughtSameOriginalObject":caught is original,"secondaryStage":stage,"record":rec,"trace":trace,"actualProcessesStarted":0,"actualKernelQueries":0})
            events.append({"event":"pass","case":name});result["subcases"].append(name)
        for stage in ("flush","fsync","close","digest","stat","receipt"):scenario(stage)
        scenario("digest",False)
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
