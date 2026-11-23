"""One new pure parser control; no Apple/native/old product execution."""
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
    start=time.monotonic();events=[];result={"status":"FAIL","productExecutions":0,"oldControls":0,"method":"test_actual_swift_testing_marker_format_is_not_question_mark","subcases":[]}
    before=snapshot();write(out/"source-before.json",before)
    primary=None
    try:
        for name in ("contracts","current_execution"):
            assert name not in sys.modules
            path=ROOT/"Tools/CurrentAppleValidation"/(name+".py")
            spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
            sys.modules[name]=module;spec.loader.exec_module(module)
        c=sys.modules["contracts"];driver=sys.modules["current_execution"]
        actual=(HERE/"original-marker-lines.log").read_bytes()
        failed=actual.decode().splitlines(keepends=True)
        assert len(failed)==2 and failed[0].startswith("\u25c7 ") and failed[1].startswith("\u2718 ")
        positive=(failed[0]+failed[1].replace("\u2718 ","\u2714 ",1).replace('" failed after','" passed after',1)).encode()
        def run(name,raw,accept):
            events.append({"event":"start","case":name})
            try:driver.raw_terminal(raw,"release-return-rtl","preparation",{},{});ok=True
            except ValueError as e:
                assert str(e)=="original_swift_testing_named_log_not_exact";ok=False
            assert ok==accept,(name,ok,accept)
            events.append({"event":"pass","case":name});result["subcases"].append(name)
        run("derived_positive_using_original_named_format",positive,True)
        run("original_actual_failed_preparation",actual,False)
        run("missing_start",positive.splitlines(keepends=True)[1],False)
        run("missing_terminal",positive.splitlines(keepends=True)[0],False)
        run("duplicate_start",positive+positive.splitlines(keepends=True)[0],False)
        run("duplicate_terminal",positive+positive.splitlines(keepends=True)[1],False)
        run("question_mark_is_not_a_swift_marker",positive.decode().replace("\u25c7","?").replace("\u2714","?").encode(),False)
        run("unexpected_named_title",positive.replace(b"ordinary Note",b"unexpected Note"),False)
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
