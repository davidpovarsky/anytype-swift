#!/usr/bin/env python3
"""Source-only, Foundation-only controls; never launches native Apple or importer work."""
import datetime, hashlib, io, json, os, pathlib, shutil, signal, subprocess, sys, zipfile

SOURCE = "257c49a5871c62611d88fab00a8124c7ff072166"
POLICY_SHA = "818bd440374cd49072f018065d300209bd2dafc506ec16d8c2c686736bde7077"
PACKET = pathlib.Path(__file__).resolve().parents[1]
ROOT = PACKET.parents[3]
SCRATCH = pathlib.Path("/mnt/development/projects/diagnostics/otzaria-original-annotation-budget-20261123/controls")
OUT = PACKET / "controls" / "run-1"
COMMANDS = []
def sha(data): return hashlib.sha256(data).hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    os.chown(path, 1001, 1001)
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args):
    return subprocess.run(["runuser","-u","ubuntu","--","git","-C",str(ROOT),*args],
                          capture_output=True, check=True).stdout
def execute(name, argv, cwd=None, timeout=120):
    i=len(COMMANDS)
    out=OUT/f"{i:02d}-{name}.stdout"
    err=OUT/f"{i:02d}-{name}.stderr"
    record={"index":i,"name":name,"argv":argv,"cwd":str(cwd or ROOT),"started_at":now(),
            "timeout_seconds":timeout,"timed_out":False}
    with out.open("wb") as stdout, err.open("wb") as stderr:
        child=subprocess.Popen(argv,cwd=cwd or ROOT,stdout=stdout,stderr=stderr,start_new_session=True)
        record["pid"]=child.pid
        try: child.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            record["timed_out"]=True
            os.killpg(child.pid,signal.SIGTERM)
            try: child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=5)
        record["exit_code"]=child.returncode
    try:
        os.killpg(child.pid,0);gone=False
    except ProcessLookupError: gone=True
    record.update(finished_at=now(),child_reaped=child.returncode is not None,process_group_gone=gone,
                  stdout={"path":str(out.relative_to(PACKET)),"bytes":out.stat().st_size,"sha256":sha(out.read_bytes())},
                  stderr={"path":str(err.relative_to(PACKET)),"bytes":err.stat().st_size,"sha256":sha(err.read_bytes())})
    COMMANDS.append(record);write(OUT/f"{i:02d}-{name}.command.json",record)
    if child.returncode != 0 or record["timed_out"] or not gone:
        raise RuntimeError("command failed: "+name)
    return out.read_bytes()
def summary(data, scope):
    rows=[json.loads(line) for line in data.decode().splitlines()]
    matches=[r for r in rows if r.get("scope")==scope]
    assert len(matches)==1 and matches[0]["status"]=="PASS"
    return matches[0]
def own_tree(path):
    for item in [path,*path.rglob("*")]:
        os.chown(item,1001,1001)

result={"status":"FAIL","source_base":SOURCE,"started_at":now(),
        "scope":"SOURCE_AND_FOUNDATION_ZIP_LAYOUT_ONLY","native_or_apple_runtime_executed":False,
        "complete_snapshot_modules_compiled":False,"production_import_authority_granted":False}
try:
    assert git("rev-parse","HEAD").decode().strip()==SOURCE
    assert not OUT.exists(),"one-shot control output already exists"
    assert not SCRATCH.exists(),"owned scratch control output already exists"
    OUT.mkdir(parents=True);SCRATCH.mkdir(parents=True);own_tree(OUT);own_tree(SCRATCH)
    rows=json.loads((PACKET/"AFTERIMAGES.json").read_text())
    paths=[r["path"] for r in rows]
    actual=git("diff","--name-only").decode().splitlines()
    assert sorted(actual)==sorted(paths)
    assert sha((PACKET/"ANNOTATION_PAYLOAD_POLICY.json").read_bytes())==POLICY_SHA
    policy=json.loads((PACKET/"ANNOTATION_PAYLOAD_POLICY.json").read_text())
    assert policy["snapshot_body_max_bytes"]==16+16384+1048576
    originals={}
    for row in rows:
        path=row["path"];before=git("show",SOURCE+":"+path);after=(ROOT/path).read_bytes()
        assert before==(PACKET/"before"/path).read_bytes()
        assert after==(PACKET/"after"/path).read_bytes()
        assert len(after)==row["bytes"] and sha(after)==row["sha256"]
        originals[path]=before
    for name,expected in [
        ("OriginalEditorFramework/AnytypeOriginalEditorNativeFixture.swift","491759ed0032c24f103716f27672a1f2357a7cb2a10d670a5a5fca92d5cbf088"),
        ("OriginalEditorFramework/AnytypeOriginalEditorHost.swift","a83337834a54d70db883076e0556316c85aae4bdf03b14d8400293936ba3cb2a")]:
        assert sha(git("show",SOURCE+":"+name))==expected
        assert (ROOT/name).read_bytes()==git("show",SOURCE+":"+name)
    inventory=json.loads((PACKET/"GENUINE_EXPORT_INVENTORY.json").read_text())
    genuine=[]
    for specimen in inventory["specimens"]:
        path=PACKET/"fixtures"/(specimen["kind"]+".zip");data=path.read_bytes()
        assert len(data)==specimen["bytes"] and sha(data)==specimen["sha256"]
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert z.testzip() is None
            assert len(z.infolist())==specimen["members"]
            assert [x.filename for x in z.infolist()]==[x["path"] for x in specimen["inventory"]]
            for info,row in zip(z.infolist(),specimen["inventory"]):
                assert info.file_size==row["bytes"] and info.compress_size==row["compressed_bytes"]
                assert sha(z.read(info))==row["sha256"]
        genuine.append({"kind":specimen["kind"],"bytes":len(data),"sha256":sha(data),"members":specimen["members"]})
    synthetic=SCRATCH/"synthetic";synthetic.mkdir()
    generated=[]
    for name,total in [("exact-limit.zip",policy["archive_max_bytes"]),("one-over.zip",policy["archive_max_bytes"]+1)]:
        path=synthetic/name
        info=zipfile.ZipInfo("a",date_time=(2020,1,1,0,0,0));info.compress_type=zipfile.ZIP_STORED
        with zipfile.ZipFile(path,"w") as z:z.writestr(info,b"x"*(total-100))
        assert path.stat().st_size==total
        generated.append({"path":str(path),"bytes":total,"sha256":sha(path.read_bytes()),"synthetic":True,
                          "authoritative_annotation_or_snapshot":False})
    write(OUT/"INPUTS.json",{"source_base":SOURCE,"afterimages":rows,"policy_sha256":POLICY_SHA,
          "genuine_archives":genuine,"synthetic_capacity_fixtures":generated,
          "historical_controls_replayed":False,"old_source_on_new_genuine_fixtures_is_new_execution":True})

    inverse=SCRATCH/"inverse";inverse.mkdir()
    for path in paths:
        target=inverse/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/path).read_bytes())
    own_tree(SCRATCH)
    prefix=["runuser","-u","ubuntu","--"]
    execute("reverse-check",prefix+["git","apply","--reverse","--check",str(PACKET/"FOUR_PATHS.diff")],cwd=inverse)
    execute("reverse-apply",prefix+["git","apply","--reverse",str(PACKET/"FOUR_PATHS.diff")],cwd=inverse)
    for path in paths:assert (inverse/path).read_bytes()==originals[path]
    snapshot=paths[0];layout=paths[1]
    before=originals[snapshot].decode();after=(ROOT/snapshot).read_text()
    same=[]
    for name,start,end in [
        ("snapshot-provenance","    public struct Provenance:","    /// These are the exact"),
        ("snapshot-header","    private struct Header:","    /// Inspect only"),
    ]:
        left=before[before.index(start):before.index(end)]
        right=after[after.index(start):after.index(end)]
        assert left==right;same.append({"segment":name,"bytes":len(left.encode()),"sha256":sha(left.encode())})
    start="        guard archive.isFileURL,"
    left=before[before.index(start):];right=after[after.index(start):]
    assert left==right
    same.append({"segment":"entire-original-no-follow-owned-file-read-tail","bytes":len(left.encode()),"sha256":sha(left.encode())})
    left=originals[layout].decode().split("    static let maximumEntries",1)[1]
    right=(ROOT/layout).read_text().split("    static let maximumEntries",1)[1]
    assert left==right
    same.append({"segment":"entire-original-zip-parser-after-archive-cap","bytes":len(left.encode()),"sha256":sha(left.encode())})
    public_before=[line for path in paths for line in originals[path].decode().splitlines() if "public " in line]
    public_after=[line for path in paths for line in (ROOT/path).read_text().splitlines() if "public " in line]
    assert public_before==public_after
    assert "bytes.count - boundary, maximumBodyBytes: maximumBodyBytes" in after
    assert after.index("bytes.count - boundary, maximumBodyBytes: maximumBodyBytes")<after.index("let archive = bytes.subdata")
    assert "allowedMaximumBytes: 65_536)" in after
    write(PACKET/"SOURCE_CORRESPONDENCE.json",{"status":"PASS","source_base":SOURCE,
        "full_four_file_reverse_apply_matches_original_blobs":True,"unchanged_segments":same,
        "public_declaration_lines_unchanged":True,"public_declaration_line_count":len(public_before),
        "attachment_file_download_cap_unchanged":65536,
        "archive_length_checked_before_subdata":True,"native_auth_or_generated_product_edits":False})

    execute("swift-version",prefix+["/usr/local/bin/swiftc","--version"])
    for i,path in enumerate(paths):
        execute("syntax-"+str(i+1),prefix+["/usr/local/bin/swiftc","-frontend","-parse",str(ROOT/path)])
    current=SCRATCH/"candidate-controls"
    execute("candidate-compile",prefix+["/usr/local/bin/swiftc","-swift-version","6","-O",
        str(ROOT/layout),str(PACKET/"controls/AnnotationBudgetControls.swift"),"-o",str(current)])
    data=execute("candidate-controls",prefix+[str(current),str(PACKET),str(synthetic)],timeout=60)
    candidate=summary(data,"FOUNDATION_BUDGET_AND_ZIP_LAYOUT_ONLY")
    assert len(candidate["passed"])==10
    original=SCRATCH/"original-controls"
    execute("original-compile",prefix+["/usr/local/bin/swiftc","-swift-version","6","-O",
        str(PACKET/"before"/layout),str(PACKET/"controls/OriginalArchiveLimitControls.swift"),"-o",str(original)])
    data=execute("original-controls",prefix+[str(original),str(PACKET)],timeout=60)
    baseline=summary(data,"NEW_CONTROLS_OF_UNCHANGED_ORIGINAL_LAYOUT_ON_ACTUAL_EXPORT_BYTES")
    assert len(baseline["passed"])==4
    result.update(status="PASS",candidate=candidate,original_source_baseline=baseline,
                  binaries=[{"path":str(path),"bytes":path.stat().st_size,"sha256":sha(path.read_bytes())} for path in [current,original]])
except BaseException as exc:
    result["error"]=type(exc).__name__+": "+str(exc)
finally:
    result.update(finished_at=now(),command_count=len(COMMANDS),commands=COMMANDS)
    if OUT.exists():write(OUT/"RESULT.json",result)
    if OUT.exists():own_tree(OUT)
    print(json.dumps({k:v for k,v in result.items() if k!="commands"},sort_keys=True,indent=2))
    if result["status"]!="PASS":sys.exit(1)
