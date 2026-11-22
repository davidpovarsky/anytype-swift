import json,hashlib,subprocess,io
from pathlib import Path
from datetime import datetime,timezone
R=Path(r"C:\Users\DAVID\Code\anytype-original-annotation-metadata-20261122")
T=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122")
P=R/"docs/pinkha/torah-integration/production-native-metadata-20261122"
PREFIX=P.relative_to(R).as_posix()
SOURCE="032a8320178ca702ed05327de168cbc2578f11eb"
BASE="b854e7f3f59690134bcabdef88527b61517d5ab5"
PRODUCT="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationNativeMetadata.swift"
STATE=T/"metadata_publication_state.json"
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args,input=None):
 p=subprocess.run(["git","-c","core.autocrlf=false","-C",str(R),*args],input=input,capture_output=True,timeout=90)
 if p.returncode:raise RuntimeError((args,p.returncode,p.stdout.decode("utf-8","replace"),p.stderr.decode("utf-8","replace")))
 return p.stdout
def gt(*args):return git(*args).decode("utf-8").strip()
assert gt("rev-parse","HEAD")==SOURCE and gt("rev-parse",SOURCE+"^")==BASE
assert not gt("diff","--name-only") and not gt("diff","--cached","--name-only")
assert json.loads(STATE.read_bytes())["phase"]=="SOURCE_COMMITTED_EVIDENCE_PENDING"
assert not (P/"publication").exists() and not (P/"EVIDENCE_INDEX.json").exists()
assert sha((P/"PRE_EDIT_PROVENANCE.json").read_bytes())=="b574bc0c224f3a32a9af9c89f21735959697f3700eb5c00e799e49fbf17fcc1a"
pre=json.loads((P/"PRE_EDIT_PROVENANCE.json").read_bytes())
assert pre["base"]==BASE and pre["classification"]=="DOWNSTREAM_OWNED_NEW_INTERNAL_ADAPTER" and pre["native_mutations"]==0
assert len([p for p in P.rglob("*") if p.is_file()])==76
prod=(R/PRODUCT).read_bytes()
assert sha(prod)=="21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5"
assert git("show",SOURCE+":"+PRODUCT)==prod
assert sha((P/"ROOT_REVIEW.json").read_bytes())=="7fb7862193f91dd2f4ba1f4ae49420f1048928bec1476954f35a2d4fb2610f8f"
binding=json.loads((P/"SOURCE_BINDING.json").read_bytes())
assert binding["source_commit"]==SOURCE and binding["tested_bytes_equal_committed_bytes"]
ci_raw=(P/"controls/FILE_INDEX.json").read_bytes()
assert sha(ci_raw)=="ffac49d17c87592d13594aa6574ae7d8e09609751dac90dfca17d951de8c9d92"
for row in json.loads(ci_raw)["files"]:
 b=(P/"controls"/row["path"]).read_bytes()
 assert len(b)==row["bytes"] and sha(b)==row["sha256"]
first = json.loads(r"""{"id":"job_f8525de792d7","type":"job_result","source":"script_run@host_7ec8382e82747448","severity":"warning","tool":"script_run","host":"host_7ec8382e82747448","status":"failed","exit_code":1,"created_at":1795331097.0033047,"started_at":"2026-11-22T07:04:57.284143+00:00","finished_at":"2026-11-22T07:05:03.221770+00:00","duration_s":5.94,"error":null,"output_truncated":false,"timeout_s":600,"read":false,"notified":{"telegram":null,"resend":null},"notify_spec":{},"output":"{\"phase\": \"VERIFIED_BEFORE_SOURCE_COMMIT\", \"at\": \"2026-11-22T07:04:59.996930+00:00\", \"base\": \"b854e7f3f59690134bcabdef88527b61517d5ab5\", \"product_sha256\": \"21321e2e69bcb29dc784620dd459f1152528f117caa13695e689b6d024813dc5\", \"controls_index_sha256\": \"ffac49d17c87592d13594aa6574ae7d8e09609751dac90dfca17d951de8c9d92\"}\r\n{\"phase\": \"SOURCE_COMMITTED_EVIDENCE_PENDING\", \"at\": \"2026-11-22T07:05:02.510839+00:00\", \"source_commit\": \"032a8320178ca702ed05327de168cbc2578f11eb\"}\nTraceback (most recent call last):\r\n  File \"C:\\ProgramData\\SentinelX\\uploads\\.sentinelx_uploads\\script_job_db11d08d06394c1d82b0ebeb797efa6a\\metadata_publish.py\", line 147, in <module>\r\n    assert len(payload)==75,len(payload)\r\n           ^^^^^^^^^^^^^^^^\r\nAssertionError: 76"}""")
assert first["id"]=="job_f8525de792d7" and first["exit_code"]==1 and "AssertionError: 76" in first["output"]
pub=P/"publication";pub.mkdir()
original=Path(r"C:\ProgramData\SentinelX\uploads\.sentinelx_uploads\script_job_db11d08d06394c1d82b0ebeb797efa6a\metadata_publish.py").read_bytes()
(pub/"first-attempt.py").write_bytes(original)
(pub/"FIRST_ATTEMPT_TERMINAL.json").write_bytes((json.dumps(first,indent=2)+"\n").encode())
(pub/"finish-evidence.py").write_bytes(Path(__file__).read_bytes())
history={"schema_version":1,"first_job":"job_f8525de792d7","source_commit":SOURCE,
"stopped_phase":"SOURCE_COMMITTED_EVIDENCE_PENDING","reason":"Packet count guard expected75 but found76 because the existing PRE_EDIT_PROVENANCE.json was not included in the planning count.",
"existing_provenance_sha256":sha((P/"PRE_EDIT_PROVENANCE.json").read_bytes()),
"resolution":"Inspected and retained the original815-byte pre-edit provenance from06:14; source/controls unchanged. Continue only evidence indexing from the actual committed source.",
"first_attempt_script_sha256":sha(original),"product_changed_during_recovery":False,"tests_reexecuted":0,
"source_commit_repeated":False,"at":datetime.now(timezone.utc).isoformat()}
(pub/"PUBLICATION_HISTORY.json").write_bytes((json.dumps(history,indent=2)+"\n").encode())
payload=[]
for p in sorted(P.rglob("*")):
 if p.is_file():
  b=p.read_bytes();payload.append({"path":p.relative_to(P).as_posix(),"bytes":len(b),"sha256":sha(b)})
assert len(payload)==80,len(payload)
index={"schema_version":1,"source_commit":SOURCE,"product_sha256":sha(prod),"payload_count":80,
"payload_bytes":sum(x["bytes"] for x in payload),"payloads":payload,"excluded_self":"EVIDENCE_INDEX.json"}
index_raw=(json.dumps(index,indent=2)+"\n").encode();(P/"EVIDENCE_INDEX.json").write_bytes(index_raw)
git("add","--",PREFIX)
staged=gt("diff","--cached","--name-only").splitlines()
assert all(x.startswith(PREFIX+"/") for x in staged)
git("diff","--cached","--check")
refs=[":"+PREFIX+"/"+x["path"] for x in payload]+[":"+PREFIX+"/EVIDENCE_INDEX.json"]
out=io.BytesIO(git("cat-file","--batch",input=("\n".join(refs)+"\n").encode()))
for ref,item in zip(refs,payload+[{"bytes":len(index_raw),"sha256":sha(index_raw)}]):
 h=out.readline().decode().strip().split();assert len(h)==3 and h[1]=="blob"
 b=out.read(int(h[2]));assert out.read(1)==b"\n"
 assert len(b)==item["bytes"] and sha(b)==item["sha256"],ref
assert not out.read()
git("commit","-m","test(otzaria): retain 26 real protobuf metadata controls and root review")
head=gt("rev-parse","HEAD")
assert gt("rev-parse",head+"^")==SOURCE
assert not gt("status","--porcelain")
for p,t in binding["preserved_trees"].items():assert gt("rev-parse","HEAD:"+p)==t
assert git("show","HEAD:"+PRODUCT)==prod
result={"phase":"SOURCE_AND_EVIDENCE_SEALED_CLEAN_READY_FOR_PUSH","at":datetime.now(timezone.utc).isoformat(),
"head":head,"source_commit":SOURCE,"product_sha256":sha(prod),"packet_payloads":80,"packet_files":81,
"packet_index_sha256":sha(index_raw),"controls_payloads_unchanged":69,
"branch":gt("branch","--show-current"),"tests_reexecuted":0,"prior_packaging_failure_retained":True}
STATE.write_bytes((json.dumps(result,indent=2)+"\n").encode());print(json.dumps(result),flush=True)
