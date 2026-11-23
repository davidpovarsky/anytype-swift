#!/usr/bin/env python3
"""Audit original static/syntax results; never invoke their programs again."""
import datetime,hashlib,json,os,pathlib,shutil,stat,subprocess
D=pathlib.Path(__file__).resolve().parent
A=D/"attempt1"
O=D/"independent-audit1"
W=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-page-menu-selector-20261123")
H="894bb60f5d0d47a8629a5ace0bd5f0316f4905f5"
N="docs/validation/20261123-semantic-page-menu-selector"
def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def g(*a):return subprocess.run(["git","-C",str(W),*a],check=True,capture_output=True,timeout=20,env={**os.environ,"GIT_OPTIONAL_LOCKS":"0"}).stdout
def exact(p,n,h):
 s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and p.resolve()==p
 b=p.read_bytes();assert len(b)==n and sha(b)==h;return b
assert shutil.disk_usage("/mnt/development").free>=1073741824+1024**2 and not O.exists()
assert g("rev-parse","HEAD").decode().strip()==H and not g("status","--porcelain=v1").strip()
index=read(A/"original-files.json");assert len(index)==14
originals={}
for name,row in index.items():
 assert not name.startswith("/") and ".." not in pathlib.PurePosixPath(name).parts
 raw=exact(A/name,row["bytes"],row["sha256"]);originals[name]=dict(row)
actual_files={p.relative_to(A).as_posix() for p in A.rglob("*") if p.is_file()}
assert actual_files==set(index)|{"original-files.json"}
receipt=read(A/"receipt.json")
assert sha((A/"receipt.json").read_bytes())=="641269211cde44c0998d747c1840c17b3dbbc5cf422be2b2697aa7188bb5a1bc"
assert receipt["status"]=="FAIL" and receipt["source"]==H
assert receipt["firstFailure"]["phase"]=="final-source-check" and receipt["firstFailure"]["message"]=="syntax_only_created_unexpected_cache_output"
assert receipt["static_source_audit"]=="PASS" and receipt["syntax_only_result"]=="PASS" and receipt["syntax_only_invocations"]==1
assert receipt["test_methods"]==receipt["old_controls_replayed"]==receipt["product_builds"]==0
assert receipt["source_unchanged"] is True and receipt["command_count"]==3
labels=["01-static-source","02-swift-version","03-swift-syntax"]
expected=[
 ["python3","-B",str(W/N/"source-check.py"),"--expected-head",H],
 ["/usr/local/bin/swiftc","--version"],
 ["/usr/local/bin/swiftc","-frontend","-parse",str(W/"PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift")]]
for label,argv,row in zip(labels,expected,receipt["commands"]):
 assert read(A/(label+".command.json"))==row and row["label"]==label and row["argv"]==argv
 assert row["returncode"]==0 and row["ownedGroupAbsent"] is True and row["firstFailure"] is None and row["cleanupFailure"] is None
 assert row["pid"]==row["pgid"] and row["pid"]>1 and row["elapsedSeconds"]<row["timeoutSeconds"]
 for kind in ["stdout","stderr"]:
  raw=(A/(label+"."+kind)).read_bytes();assert len(raw)==row[kind]["bytes"] and sha(raw)==row[kind]["sha256"]
assert len({x["pgid"] for x in receipt["commands"]})==3
assert (A/"02-swift-version.stdout").read_bytes()==b"Swift version 6.4.3 (swift-6.4.3-RELEASE)\nTarget: aarch64-unknown-linux-gnu\n"
assert (A/"03-swift-syntax.stdout").read_bytes()==(A/"03-swift-syntax.stderr").read_bytes()==b""
before=read(A/"source-before.json");after=read(A/"source-after.json");assert before==after and len(before)==19
static=read(A/"01-static-source.stdout");assert static["head"]==H and static["status"]=="PASS"
assert set(static["source_inputs"])==set(before) and len(static["original_app_plan_inputs"])==9
for name,row in before.items():
 p=W/name;raw=p.read_bytes();s=p.stat();observed=static["source_inputs"][name]
 assert raw==g("show",H+":"+name) and sha(raw)==row["sha256"]==observed["sha256"] and len(raw)==row["bytes"]==observed["bytes"]
 assert s.st_mode&0o7777==row["mode"]==observed["physical_mode"] and str(s.st_ino)==row["inode"]==observed["inode"]
for name,row in static["metadata_inputs"].items():
 raw=(W/name).read_bytes();assert raw==g("show",H+":"+name) and sha(raw)==row["sha256"] and len(raw)==row["bytes"]
wanted={"tmp/TemporaryDirectory.tFdr5l":"directory","tmp/TemporaryDirectory.tFdr5l/.keep-directory":"file","tmp/modules.timestamp":"file"}
actual={p.relative_to(A).as_posix():p for p in (A/"tmp").rglob("*")}
assert set(actual)==set(wanted)
entries={}
for name,kind in wanted.items():
 p=actual[name];s=p.lstat();assert p.resolve()==p and s.st_uid==1001 and s.st_gid==1002
 if kind=="file":
  assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size==0 and p.read_bytes()==b""
 else:assert stat.S_ISDIR(s.st_mode)
 entries[name]={"kind":kind,"mode":stat.S_IMODE(s.st_mode),"uid":s.st_uid,"gid":s.st_gid,
 "bytes":s.st_size,"allocated":s.st_blocks*512,"inode":str(s.st_ino),"mtime_ns":str(s.st_mtime_ns),
 "sha256":sha(b"") if kind=="file" else None}
assert not g("status","--porcelain=v1").strip()
result={"schema":"pinkha-page154-menu-selector-original-only-audit-v1","status":"PASS_AUDIT_OF_SEPARATE_SOURCE_SYNTAX_SCOPES",
 "source":H,"original_wrapper_status":"FAIL","original_wrapper_receipt_sha256":sha((A/"receipt.json").read_bytes()),
 "original_wrapper_failure_preserved":receipt["firstFailure"],"static_source_scope":"PASS","syntax_only_scope":"PASS",
 "original_file_bindings":originals,"original_input_index_sha256":sha((A/"original-files.json").read_bytes()),
 "source_rows_verified":19,"static_metadata_rows_verified":len(static["metadata_inputs"]),"original_app_plan_rows":9,
 "source_before_after_identical":True,"actual_commands":receipt["commands"],"owned_tmp_exact_entries":entries,
 "ancillary_classification":"Only a directory plus two zero-byte marker files are present in the owned Swift-command tmp namespace; no compiled payload there. The original overly strict empty-namespace assertion remains failed.",
 "files_deleted_or_normalized":0,"new_source_or_parser_invocations":0,"new_test_invocations":0,"product_builds":0,
 "apple_typecheck":"NOT_RUN","actual_menu_behavior":"NOT_RUN","audited_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
O.mkdir(mode=0o700);raw=(json.dumps(result,sort_keys=True,indent=2)+"\n").encode()
with (O/"audit.json").open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
(O/"audit.json").chmod(0o600)
print(json.dumps({"status":result["status"],"audit_sha256":sha(raw),"audit_bytes":len(raw),"source_rows_verified":19,"originals":len(originals),"original_wrapper_status":"FAIL","new_source_or_parser_invocations":0},sort_keys=True))
