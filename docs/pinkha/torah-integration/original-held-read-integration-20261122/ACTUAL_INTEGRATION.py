from pathlib import Path
import datetime,hashlib,json,subprocess,shutil
R=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
S=Path(r"C:\Users\DAVID\Code\anytype-original-held-read-20261122")
REVIEW=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\held-read-root-final-review")
BEFORE="217308ae2859c250295bbbdfa3d69f8dbf28a1e4"
INCOMING="f81582f4773f8a472723fa31ab9f024591704432"
PRODUCT="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift"
PACKET="docs/pinkha/torah-integration/production-held-read-20261122"
P=R/"docs/pinkha/torah-integration/original-held-read-integration-20261122"
def sha(b):return hashlib.sha256(b).hexdigest()
def run(*args):
 p=subprocess.run(["git","-c","core.autocrlf=false",*args],cwd=R,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
 if p.returncode:raise RuntimeError(json.dumps({"command":list(args),"exit":p.returncode,"stdout":p.stdout.decode(errors="replace"),"stderr":p.stderr.decode(errors="replace")}))
 return p.stdout
def text(*args):return run(*args).decode().strip()
def write(p,x):p.write_bytes((json.dumps(x,ensure_ascii=False,indent=2)+"\n").encode())
assert text("rev-parse","HEAD")==BEFORE and not text("status","--porcelain")
review_raw=(REVIEW/"ROOT_FINAL_REVIEW.json").read_bytes()
assert sha(review_raw)=="c1a998c7c3b2f30f2187a8281706721326b01de66e47b22eb5466ee766c9ed82"
review=json.loads(review_raw);assert review["incoming"]==INCOMING and review["targetHead"]==BEFORE
assert not P.exists()
run("fetch",str(S),"codex/otzaria-original-held-read-adapter-20261122")
assert text("rev-parse","FETCH_HEAD")==INCOMING
run("merge-base","--is-ancestor",review["sourceCommit"],INCOMING)
run("merge-base","--is-ancestor","18ac6d39dfe76b12e5dead9627c831c6a88d073c",BEFORE)
merge_out=run("merge","--no-ff","-m","Merge original held-read adapter and 26 focused controls",INCOMING)
MERGE=text("rev-parse","HEAD")
assert text("show","-s","--format=%P",MERGE).split()==[BEFORE,INCOMING]
assert not text("status","--porcelain")
assert sha((R/PRODUCT).read_bytes())==review["productSHA256"]
for path,blob in review["preservedGitObjects"].items():assert text("rev-parse",MERGE+":"+path)==blob,path
changed=text("diff","--name-only",BEFORE,MERGE).splitlines()
assert [p for p in changed if not p.startswith("docs/")]==[PRODUCT],changed
assert text("rev-parse",MERGE+":"+PACKET)==text("rev-parse",INCOMING+":"+PACKET)
P.mkdir()
for item in REVIEW.iterdir():
 assert item.is_file()
 shutil.copyfile(item,P/item.name)
(P/"ACTUAL_INTEGRATION.py").write_bytes(Path(__file__).read_bytes())
jobs=json.loads("{\"first\":{\"ok\":true,\"job\":{\"id\":\"job_4dfa99fbb7fd\",\"type\":\"job_result\",\"source\":\"script_run@host_7ec8382e82747448\",\"severity\":\"warning\",\"tool\":\"script_run\",\"host\":\"host_7ec8382e82747448\",\"status\":\"failed\",\"exit_code\":1,\"created_at\":1795337977.8904,\"started_at\":\"2026-11-22T08:59:37.965243+00:00\",\"finished_at\":\"2026-11-22T08:59:44.456516+00:00\",\"duration_s\":6.49,\"error\":null,\"output_truncated\":false,\"timeout_s\":180,\"read\":false,\"notified\":{\"telegram\":null,\"resend\":null},\"notify_spec\":{},\"output\":\"Traceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_1b703f3335964164995301b189305773\\\\held_read_root_final_review.py\\\", line 87, in <module>\\r\\n    assert sum(1 for x in git_inputs if x[\\\"source\\\"].startswith(\\\"Modules/ProtobufMessages/\\\"))==74\\r\\n           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\nAssertionError\"}},\"continuation\":{\"ok\":true,\"job\":{\"id\":\"job_17d64dcb9501\",\"type\":\"job_result\",\"source\":\"script_run@host_7ec8382e82747448\",\"severity\":\"info\",\"tool\":\"script_run\",\"host\":\"host_7ec8382e82747448\",\"status\":\"succeeded\",\"exit_code\":0,\"created_at\":1795338078.2442305,\"started_at\":\"2026-11-22T09:01:18.319101+00:00\",\"finished_at\":\"2026-11-22T09:02:03.146196+00:00\",\"duration_s\":44.83,\"error\":null,\"output_truncated\":false,\"timeout_s\":180,\"read\":false,\"notified\":{\"telegram\":null,\"resend\":null},\"notify_spec\":{},\"output\":\"{\\\"status\\\": \\\"PASS_IMMUTABLE_EVIDENCE_NO_TEST_REPLAY\\\", \\\"receipt\\\": \\\"C:\\\\\\\\Users\\\\\\\\DAVID\\\\\\\\AppData\\\\\\\\Local\\\\\\\\Temp\\\\\\\\otzaria-continuation-20261122\\\\\\\\held-read-root-final-review\\\\\\\\ROOT_FINAL_REVIEW.json\\\", \\\"sha256\\\": \\\"c1a998c7c3b2f30f2187a8281706721326b01de66e47b22eb5466ee766c9ed82\\\", \\\"payloads\\\": 230, \\\"gitBlobs\\\": 231, \\\"originals\\\": 109, \\\"cases\\\": 26, \\\"compilerSources\\\": 213, \\\"dependencyGitFiles\\\": 745, \\\"testsReplayed\\\": 0, \\\"ownerReadUnchanged\\\": true}\"}}}")
remote=json.loads("{\"ref\":\"refs/heads/codex/otzaria-original-held-read-adapter-20261122\",\"node_id\":\"REF_kwDOTOG_cdoAPHJlZnMvaGVhZHMvY29kZXgvb3R6YXJpYS1vcmlnaW5hbC1oZWxkLXJlYWQtYWRhcHRlci0yMDI2MTEyMg\",\"url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/git/refs/heads/codex/otzaria-original-held-read-adapter-20261122\",\"object\":{\"sha\":\"f81582f4773f8a472723fa31ab9f024591704432\",\"type\":\"commit\",\"url\":\"https://api.github.com/repos/davidpovarsky/anytype-swift/git/commits/f81582f4773f8a472723fa31ab9f024591704432\"}}")
write(P/"ROOT_REVIEW_JOB_FIRST.json",jobs["first"])
write(P/"ROOT_REVIEW_JOB_CONTINUATION.json",jobs["continuation"])
write(P/"INCOMING_REMOTE.json",remote)
receipt={"schema":"otzaria.original-held-read-integration/1","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "targetBefore":BEFORE,"incoming":INCOMING,"mergeCommit":MERGE,"parents":[BEFORE,INCOMING],
 "sourceCommit":review["sourceCommit"],"rootFinalReviewSHA256":sha(review_raw),"sourceSHA256":review["productSHA256"],
 "incomingPacketTree":text("rev-parse",MERGE+":"+PACKET),"preservedGitObjects":review["preservedGitObjects"],
 "onlyChangedProduct":PRODUCT,"exactIncomingPacket":True,"actualCasesReused":26,"newTestsExecuted":0,
 "artifactDownloads":0,"ownerReadImplementationByteUnchanged":True,"sourceReviewCorrection":"Preserved wrong generated-count assumption; exact74 generated inputs distinguished from original InvocationDispatchBinding module input."}
write(P/"INTEGRATION.json",receipt)
readme="""# Original held-read adapter integration

The reviewed full original annotation read adapter and its 26 new portable Swift Testing controls are integrated by a true merge. The incoming source is 3bbe081753f84a36370ac545bdc0271e0aad8f58 and immutable evidence head is f81582f4773f8a472723fa31ab9f024591704432. INTEGRATION.json records both actual parents and the resulting merge.

## Independent evidence admission

Root verified all 230 payloads (13,405,757 bytes), all 231 exact packet Git blobs including the index, all 170 frozen first-failure payloads, 116 declared inputs and 109 original Git sources. The 74 generated protobuf files are complete. The genuine InvocationDispatchBinding is an additional original module input; an initial root counting assumption treated it as generated and failed before any merge. The first actual script/failure and the bounded correction are retained.

The continuation changed one unsupported null fixture initializer to the actual pinned protobuf API. Its exact inverse recovers the original test. Every product byte and test assertion is unchanged. The first actual compile failure ran no cases and remains recorded.

The actual second Swift command ran for 95.391 seconds, exit 0, no timeout. Its original Swift Testing XML contains exactly 26 distinct passing cases and no failures, errors or skips. Root independently inspected the exact 213-entry compiler archive (115 harness, 94 SwiftProtobuf, four generated build files), all 745 original dependency Git files, and the actual 20,249,600-byte PE executable against its retained ZIP. The complete test result, raw logs and before/after source/dependency inventories remain in the incoming packet. No test was replayed for this integration.

## Composition and limits

The sole changed product file is OriginalAnnotationObjectReadback.swift. All original module/resource/project/workflow/tool trees and previously integrated participant/Space authority source remain unchanged.

The 26 cases compiled their declared base Owner. The current integration Owner additionally contains the separately reviewed and tested restricting Space-permission composition. Root verified that removing only that added import and method group recovers the original Owner byte-for-byte; the read implementation is unchanged. This is a bounded source-composition argument, not a claim that the full merged Apple application was executed.

The new synchronous consumer receives the complete fresh ObjectView and strict root Struct inside the same original exclusive read. A returned value is retained when later ownership validation fails. A thrown consumer preserves its original error and side-effect uncertainty. These outcomes do not create a durability or acknowledgement receipt.

Native engine/RPC, Apple UI, schema creation, full body/reference/version equality, native identity, SQLite COMMIT and delivery ACK acceptance remain open. Metadata digest remains unproven. Existing passed suites were reused only through their immutable source and execution evidence.

The raw executed Python scripts retain their actual host line endings through scoped attributes; all other whitespace checks remain active.
"""
(P/"README.md").write_bytes(readme.encode())
(P/".gitattributes").write_bytes(b"*.py -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n")
rows=[{"path":p.relative_to(P).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(P.rglob("*")) if p.is_file()]
write(P/"FILE_INDEX.json",{"schema":"otzaria.held-read-integration-evidence/1","payloadCount":len(rows),"payloadBytes":sum(x["bytes"] for x in rows),"payloads":rows})
run("add","--",P.relative_to(R).as_posix())
run("diff","--cached","--check")
staged=text("diff","--cached","--name-only").splitlines()
assert len(staged)==len(rows)+1 and all(p.startswith(P.relative_to(R).as_posix()+"/") for p in staged)
run("commit","-m","Record independent held-read evidence admission and integration")
AFTER=text("rev-parse","HEAD")
assert not text("status","--porcelain")
assert text("rev-parse",AFTER+":Anytype")==text("rev-parse",MERGE+":Anytype")
print(json.dumps({"status":"MERGED_AND_EVIDENCE_COMMITTED","before":BEFORE,"incoming":INCOMING,"merge":MERGE,"head":AFTER,"rootReviewSHA256":sha(review_raw),"proofFiles":len(rows)+1,"proofIndexSHA256":sha((P/"FILE_INDEX.json").read_bytes()),"productChanges":1,"testsReplayed":0,"clean":True}))
