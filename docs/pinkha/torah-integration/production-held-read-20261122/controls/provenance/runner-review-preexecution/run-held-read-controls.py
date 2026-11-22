from pathlib import Path
import datetime,hashlib,json,os,re,shutil,subprocess,sys,time,traceback,xml.etree.ElementTree as ET,zipfile

PACKET=Path(__file__).resolve().parent
REPO=PACKET.parents[4]
BASE="18ac6d39dfe76b12e5dead9627c831c6a88d073c"
PRODUCT="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift"
PRODUCT_SHA="dcb942bbbdc799989134da1f84256641ac750437749ca67d4412e352a0f0a252"
INPUTS_SHA="bf16b93b5ab6badcd405f436258f2b4e40d5069bdf58004f6249fa03adf241ad"
DEPENDENCY=Path(r"C:\Users\DAVID\AppData\Local\Temp\omd-protobuf-20261122")
DEPENDENCY_REV="c6fe6442e6a64250495669325044052e113e990c"
SWIFT_BIN=Path(r"C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin")
WORK=Path(r"C:\Users\DAVID\AppData\Local\Temp\ohr-20261122")
RESULT=PACKET/"validation"/"windows-held-read-26"
TIMEOUT_SECONDS=900

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode("utf-8"))

def record(path):
    raw=path.read_bytes()
    return {"path":str(path),"bytes":len(raw),"sha256":digest(raw)}

def git(args,cwd=REPO):
    return subprocess.check_output(["git",*args],cwd=cwd).decode("utf-8").strip()

def inspect_dependency():
    assert git(["rev-parse","HEAD"],DEPENDENCY)==DEPENDENCY_REV
    assert git(["status","--porcelain=v1","--untracked-files=normal"],DEPENDENCY)==""
    paths=subprocess.check_output(["git","ls-files","-z"],cwd=DEPENDENCY).decode("utf-8").split("\0")
    return [{"relative":p,**record(DEPENDENCY/p)} for p in paths if p and (DEPENDENCY/p).is_file()]

def source_snapshot(inputs):
    rows=[]
    for row in inputs["sourceInputs"]:
        p=PACKET/row["compiled"]
        actual=record(p)
        assert actual["bytes"]==row["bytes"] and actual["sha256"]==row["sha256"],row["compiled"]
        rows.append({"relative":row["compiled"],**actual})
    assert digest((REPO/PRODUCT).read_bytes())==PRODUCT_SHA
    return rows

def main():
    assert not RESULT.exists(),str(RESULT)
    RESULT.mkdir(parents=True)
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    write_json(RESULT/"LAUNCH.json",{"status":"PREPARING","started_at":started,"pid":os.getpid(),"runner":record(Path(__file__))})
    assert git(["rev-parse","HEAD"])==BASE
    assert digest((PACKET/"INPUTS.json").read_bytes())==INPUTS_SHA
    inputs=json.loads((PACKET/"INPUTS.json").read_bytes())
    before=source_snapshot(inputs)
    dependency_before=inspect_dependency()
    write_json(RESULT/"SOURCE_BEFORE.json",before)
    write_json(RESULT/"DEPENDENCY_BEFORE.json",dependency_before)
    assert not WORK.exists(),str(WORK)
    WORK.mkdir()
    harness=WORK/"h"
    shutil.copytree(PACKET/"harness",harness)
    copy_rows=[]
    for row in inputs["sourceInputs"]:
        relative=Path(row["compiled"]).relative_to("harness")
        p=harness/relative
        actual=record(p)
        assert actual["sha256"]==row["sha256"],str(relative)
        copy_rows.append({"relative":relative.as_posix(),**actual})
    write_json(RESULT/"COMPILER_INPUT_COPIES.json",copy_rows)
    compiler={"swift":record(SWIFT_BIN/"swift.exe"),"swiftc":record(SWIFT_BIN/"swiftc.exe")}
    version=subprocess.run([str(SWIFT_BIN/"swiftc.exe"),"--version"],capture_output=True,timeout=30,check=True)
    (RESULT/"swift-version.stdout").write_bytes(version.stdout)
    (RESULT/"swift-version.stderr").write_bytes(version.stderr)
    compiler["version_stdout_sha256"]=digest(version.stdout)
    compiler["version_stderr_sha256"]=digest(version.stderr)
    write_json(RESULT/"COMPILER.json",compiler)
    build=WORK/"b"
    xunit=WORK/"held-read-26.xml"
    args=[
        str(SWIFT_BIN/"swift.exe"),"test","--package-path",str(harness),
        "--scratch-path",str(build),"--configuration","debug","--jobs","4",
        "--disable-xctest","--enable-swift-testing","--filter","OriginalHeldReadTests",
        "--xunit-output",str(xunit),"--verbose"
    ]
    env=os.environ.copy()
    env.update({
        "OTZARIA_HELD_READ_SWIFTPROTOBUF_CHECKOUT":str(DEPENDENCY),
        "PROTOBUF_NO_PROTOC":"true","NO_COLOR":"1","CLICOLOR":"0"
    })
    env["PATH"]=str(SWIFT_BIN)+os.pathsep+env.get("PATH","")
    invocation={
        "schemaVersion":1,"args":args,"cwd":str(WORK),
        "environment_overrides":{
            "OTZARIA_HELD_READ_SWIFTPROTOBUF_CHECKOUT":str(DEPENDENCY),
            "PROTOBUF_NO_PROTOC":"true","NO_COLOR":"1","CLICOLOR":"0",
            "PATH_prepend":str(SWIFT_BIN)
        },
        "parent_pid":os.getpid(),"timeout_s":TIMEOUT_SECONDS,
        "runner":record(Path(__file__)),"inputs":record(PACKET/"INPUTS.json")
    }
    write_json(RESULT/"EXECUTION.json",invocation)
    print(json.dumps({"status":"STARTING_ONE_FOCUSED_SUITE","cases":26,"inputs":len(before),"work":str(WORK)}),flush=True)
    stdout_path=RESULT/"swift-test.stdout"
    stderr_path=RESULT/"swift-test.stderr"
    timing=time.monotonic()
    cleanup=None
    timed_out=False
    with stdout_path.open("wb") as stdout,stderr_path.open("wb") as stderr:
        proc=subprocess.Popen(args,cwd=WORK,env=env,stdout=stdout,stderr=stderr)
        invocation["child_pid"]=proc.pid
        invocation["started_at"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
        write_json(RESULT/"EXECUTION.json",invocation)
        try:
            code=proc.wait(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out=True
            stopped=subprocess.run(["taskkill","/PID",str(proc.pid),"/T","/F"],capture_output=True,timeout=30)
            (RESULT/"owned-timeout-cleanup.stdout").write_bytes(stopped.stdout)
            (RESULT/"owned-timeout-cleanup.stderr").write_bytes(stopped.stderr)
            cleanup={"args":["taskkill","/PID",str(proc.pid),"/T","/F"],"exitCode":stopped.returncode}
            code=proc.wait(timeout=30)
    invocation.update({
        "exit_code":code,"timed_out":timed_out,"owned_timeout_cleanup":cleanup,
        "duration_s":round(time.monotonic()-timing,6),
        "finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stdout":record(stdout_path),"stderr":record(stderr_path)
    })
    write_json(RESULT/"EXECUTION.json",invocation)
    after=source_snapshot(inputs)
    dependency_after=inspect_dependency()
    write_json(RESULT/"SOURCE_AFTER.json",after)
    write_json(RESULT/"DEPENDENCY_AFTER.json",dependency_after)
    assert before==after
    assert dependency_before==dependency_after
    result={
        "schemaVersion":1,"status":"FAIL","execution":invocation,
        "candidate_sha256":PRODUCT_SHA,"inputs_sha256":INPUTS_SHA,
        "source_inputs_unchanged":True,"dependency_unchanged":True,
        "original_test_methods":inputs["testMethods"],"expected_count":26,
        "scope":"Portable new adapter controls with genuine generated protobuf/Services values and original Owner/capture/binding. Explicit native RPC, prepared UI/document/DI and Combine/OS storage boundaries; no Apple/native engine/identity/body/COMMIT/ACK qualification."
    }
    binaries=sorted(build.rglob("OriginalHeldReadControlsPackageTests.exe")) if build.exists() else []
    if binaries:
        assert len(binaries)==1
        result["test_binary"]=record(binaries[0])
        binary_zip=RESULT/"actual-test-binary.zip"
        with zipfile.ZipFile(binary_zip,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            z.write(binaries[0],binaries[0].name)
        result["test_binary_archive"]=record(binary_zip)
    command_files=[]
    sources=set()
    if build.exists():
        for p in sorted(build.rglob("*")):
            if not p.is_file():
                continue
            if p.name in ["debug.yaml","build.yaml","description.json","workspace-state.json","sources"] or p.suffix==".SwiftFileList":
                rel=p.relative_to(build)
                dest=RESULT/"build-description"/rel
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(p,dest)
                command_files.append({"relative":rel.as_posix(),**record(dest)})
                if p.name=="sources" or p.suffix==".SwiftFileList":
                    for line in p.read_text(encoding="utf-8").splitlines():
                        candidate=Path(line.strip().strip('"'))
                        if candidate.is_file() and candidate.suffix in [".swift",".c",".h",".cpp"]:
                            sources.add(candidate.resolve())
    write_json(RESULT/"BUILD_DESCRIPTION_FILES.json",command_files)
    compiled_sources=[]
    compiled_zip=RESULT/"actual-compiler-sources.zip"
    with zipfile.ZipFile(compiled_zip,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(sources,key=str):
            provenance=None
            for label,parent in [("harness",harness),("SwiftProtobuf",DEPENDENCY),("generated-build",build)]:
                if p.is_relative_to(parent):
                    provenance=label+"/"+p.relative_to(parent).as_posix()
                    break
            assert provenance is not None,str(p)
            raw=p.read_bytes()
            z.writestr(provenance,raw)
            compiled_sources.append({"archive_path":provenance,**record(p)})
    write_json(RESULT/"ACTUAL_COMPILER_SOURCES.json",compiled_sources)
    result["actual_compiler_sources_count"]=len(compiled_sources)
    result["actual_compiler_sources_archive"]=record(compiled_zip)
    if xunit.exists():
        shutil.copyfile(xunit,RESULT/"swift-testing-26.xml")
        root=ET.parse(xunit).getroot()
        cases=root.findall(".//testcase")
        case_rows=[{"name":case.attrib.get("name"),"classname":case.attrib.get("classname"),
                    "time":case.attrib.get("time"),"failures":len(case.findall("failure")),
                    "errors":len(case.findall("error")),"skipped":len(case.findall("skipped"))} for case in cases]
        write_json(RESULT/"CASES.json",case_rows)
        names=[]
        for row in case_rows:
            match=re.search(r"(test[A-Za-z0-9_]+)",row["name"] or "")
            if match:names.append(match.group(1))
        result.update({
            "actual_count":len(cases),"actual_names":names,
            "failures":sum(x["failures"] for x in case_rows),
            "errors":sum(x["errors"] for x in case_rows),
            "skipped":sum(x["skipped"] for x in case_rows),
            "xunit":record(RESULT/"swift-testing-26.xml")
        })
        exact_names=len(names)==26 and sorted(names)==sorted(inputs["testMethods"])
        result["exact_new_test_names"]=exact_names
        if code==0 and not timed_out and exact_names and len(cases)==26 and not any(
            row["failures"] or row["errors"] or row["skipped"] for row in case_rows
        ):
            result["status"]="PASS"
    else:
        result["test_cases_unavailable"]=True
    write_json(RESULT/"RESULT.json",result)
    print(json.dumps({"status":result["status"],"exitCode":code,"duration_s":invocation["duration_s"],
                      "test_count":result.get("actual_count"),"actual_compiler_sources":len(compiled_sources),
                      "result":str(RESULT/"RESULT.json"),"resultSHA256":digest((RESULT/"RESULT.json").read_bytes())}),flush=True)
    return 0 if result["status"]=="PASS" else 1

if __name__=="__main__":
    try:
        sys.exit(main())
    except Exception as error:
        RESULT.mkdir(parents=True,exist_ok=True)
        write_json(RESULT/"RUNNER_FAILURE.json",{
            "status":"RUNNER_FAILURE","type":type(error).__name__,"message":str(error),
            "traceback":traceback.format_exc(),"at":datetime.datetime.now(datetime.timezone.utc).isoformat()
        })
        print(json.dumps({"status":"RUNNER_FAILURE","type":type(error).__name__,"message":str(error)}),flush=True)
        raise
