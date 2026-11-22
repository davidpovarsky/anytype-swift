from pathlib import Path
import json,hashlib,subprocess,datetime
R=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
P=R/"docs/pinkha/torah-integration/original-held-read-integration-20261122"
def sha(b):return hashlib.sha256(b).hexdigest()
def cmd(*a,check=True):
 p=subprocess.run(["git","-c","core.autocrlf=false",*a],cwd=R,capture_output=True,timeout=30)
 if check and p.returncode:raise RuntimeError((a,p.returncode,p.stdout.decode(errors="replace"),p.stderr.decode(errors="replace")))
 return p
def git(*a):return cmd(*a).stdout.decode().strip()
def write(p,x):p.write_bytes((json.dumps(x,indent=2,ensure_ascii=False)+"\n").encode())
receipt=json.loads((P/"INTEGRATION.json").read_bytes())
merge=git("rev-parse","HEAD")
assert merge==receipt["mergeCommit"] and git("show","-s","--format=%P",merge).split()==receipt["parents"]
assert receipt["parents"]==["217308ae2859c250295bbbdfa3d69f8dbf28a1e4","f81582f4773f8a472723fa31ab9f024591704432"]
assert sha((R/receipt["onlyChangedProduct"]).read_bytes())==receipt["sourceSHA256"]
lint=cmd("diff","--cached","--check",check=False)
expected="docs/pinkha/torah-integration/original-held-read-integration-20261122/OWNER_COMPOSITION_ONLY.patch"
lines=lint.stdout.decode().splitlines()
assert lint.returncode==2 and lines==[expected+":9: trailing whitespace.","+ ",expected+":15: trailing whitespace.","+ "],lines
for p,b in receipt["preservedGitObjects"].items():assert git("rev-parse",merge+":"+p)==b
paths=git("diff","--cached","--name-only").splitlines()
assert all(x.startswith(P.relative_to(R).as_posix()+"/") for x in paths)
assert not git("diff","--name-only")
attrs=P/".gitattributes";raw=attrs.read_bytes()
assert raw==b"*.py -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n"
attrs.write_bytes(raw+b"OWNER_COMPOSITION_ONLY.patch -text -whitespace\nPACKAGING_LINT.txt -text -whitespace\n")
(P/"PACKAGING_LINT.txt").write_bytes(lint.stdout)
failed=json.loads("{\"ok\":true,\"job\":{\"id\":\"job_10a1ff0d3d02\",\"type\":\"job_result\",\"source\":\"script_run@host_7ec8382e82747448\",\"severity\":\"warning\",\"tool\":\"script_run\",\"host\":\"host_7ec8382e82747448\",\"status\":\"failed\",\"exit_code\":1,\"created_at\":1795338242.2349138,\"started_at\":\"2026-11-22T09:04:02.301317+00:00\",\"finished_at\":\"2026-11-22T09:04:19.646189+00:00\",\"duration_s\":17.34,\"error\":null,\"output_truncated\":false,\"timeout_s\":120,\"read\":false,\"notified\":{\"telegram\":null,\"resend\":null},\"notify_spec\":{},\"output\":\"Traceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_7917028ff2304f8c98673f5d4e1d70f5\\\\held_read_root_integration.py\\\", line 82, in <module>\\r\\n    run(\\\"diff\\\",\\\"--cached\\\",\\\"--check\\\")\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_7917028ff2304f8c98673f5d4e1d70f5\\\\held_read_root_integration.py\\\", line 14, in run\\r\\n    if p.returncode:raise RuntimeError(json.dumps({\\\"command\\\":list(args),\\\"exit\\\":p.returncode,\\\"stdout\\\":p.stdout.decode(errors=\\\"replace\\\"),\\\"stderr\\\":p.stderr.decode(errors=\\\"replace\\\")}))\\r\\n                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\nRuntimeError: {\\\"command\\\": [\\\"diff\\\", \\\"--cached\\\", \\\"--check\\\"], \\\"exit\\\": 2, \\\"stdout\\\": \\\"docs/pinkha/torah-integration/original-held-read-integration-20261122/OWNER_COMPOSITION_ONLY.patch:9: trailing whitespace.\\\\n+ \\\\ndocs/pinkha/torah-integration/original-held-read-integration-20261122/OWNER_COMPOSITION_ONLY.patch:15: trailing whitespace.\\\\n+ \\\\n\\\", \\\"stderr\\\": \\\"\\\"}\"}}")
write(P/"INTEGRATION_JOB_FIRST.json",failed)
write(P/"PACKAGING_ERRATUM.json",{"schema":1,"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"firstJob":"job_10a1ff0d3d02","actualMerge":merge,"failedStep":"Evidence-only cached whitespace check after successful true merge","cause":"Exact original Git diff retains two blank context lines consisting of one required diff context prefix space.","correction":"Preserve raw patch and original lint; exempt only these raw evidence paths from whitespace lint, retaining ordinary product and documentation checks.","rootReadReviewSHA256":receipt["rootFinalReviewSHA256"],"productChanged":False,"mergeRepeated":False,"newTestExecutions":0})
(P/"ACTUAL_PACKAGING_CONTINUATION.py").write_bytes(Path(__file__).read_bytes())
with (P/"README.md").open("ab") as f:f.write(b"\n## Raw diff packaging continuation\n\nThe true merge completed successfully before evidence lint reported the two required blank context prefixes in the retained original Git patch. The original failure, raw lint and exact patch are retained. Only those raw evidence paths have scoped whitespace attributes. This documentation continuation does not repeat the merge, source admission or any test.\n")
rows=[{"path":p.relative_to(P).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(P.rglob("*")) if p.is_file() and p.name!="FILE_INDEX.json"]
write(P/"FILE_INDEX.json",{"schema":"otzaria.held-read-integration-evidence/1","payloadCount":len(rows),"payloadBytes":sum(x["bytes"] for x in rows),"payloads":rows})
cmd("add","--",P.relative_to(R).as_posix());cmd("diff","--cached","--check")
assert len(git("diff","--cached","--name-only").splitlines())==len(rows)+1
cmd("commit","-m","Record independent held-read evidence admission and integration")
head=git("rev-parse","HEAD")
assert not git("status","--porcelain")
assert git("rev-parse",head+":Anytype")==git("rev-parse",merge+":Anytype")
print(json.dumps({"status":"MERGED_AND_EVIDENCE_COMMITTED","before":receipt["targetBefore"],"incoming":receipt["incoming"],"merge":merge,"head":head,"proofFiles":len(rows)+1,"proofIndexSHA256":sha((P/"FILE_INDEX.json").read_bytes()),"productChanges":1,"testsReplayed":0,"clean":True}))
