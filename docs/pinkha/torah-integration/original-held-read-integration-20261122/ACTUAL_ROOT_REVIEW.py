from pathlib import Path, PurePosixPath
import datetime, hashlib, json, subprocess, zipfile, xml.etree.ElementTree as ET, re, difflib, collections
SOURCE=Path(r"C:\Users\DAVID\Code\anytype-original-held-read-20261122")
TARGET=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
PACKET="docs/pinkha/torah-integration/production-held-read-20261122"
D=SOURCE/PACKET
N=D/"controls-null-fixture-continuation"
V=N/"validation/windows-first-26-after-null-fixture"
B=D/"controls"
OUT=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\held-read-root-final-review")
INCOMING="f81582f4773f8a472723fa31ab9f024591704432"
HEAD="217308ae2859c250295bbbdfa3d69f8dbf28a1e4"
BASE="18ac6d39dfe76b12e5dead9627c831c6a88d073c"
PRODUCT="Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationObjectReadback.swift"
OWNER="Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift"
def sha(b):return hashlib.sha256(b).hexdigest()
def git(repo,*args):return subprocess.check_output(["git","-c","core.autocrlf=false",*args],cwd=repo,timeout=30)
def gtext(repo,*args):return git(repo,*args).decode("utf-8").strip()
def load(p):return json.loads(p.read_bytes())
def exact(raw,row,label):
 assert len(raw)==row["bytes"] and sha(raw)==row["sha256"],label
def batch(repo,queries):
 p=subprocess.run(["git","cat-file","--batch"],cwd=repo,input=("\n".join(queries)+"\n").encode(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45,check=True)
 out=p.stdout; at=0; values=[]
 for query in queries:
  stop=out.index(b"\n",at); header=out[at:stop].decode().split(); assert len(header)==3 and header[1]=="blob",(query,header)
  size=int(header[2]); raw=out[stop+1:stop+1+size]; assert out[stop+1+size:stop+2+size]==b"\n"
  at=stop+2+size; values.append((header[0],raw))
 assert at==len(out)
 return values
assert not OUT.exists()
assert gtext(SOURCE,"rev-parse","HEAD")==INCOMING and not gtext(SOURCE,"status","--porcelain")
assert gtext(TARGET,"rev-parse","HEAD")==HEAD and not gtext(TARGET,"status","--porcelain")
index_raw=(D/"FILE_INDEX.json").read_bytes()
assert sha(index_raw)=="fb9778d7cce1abadd41663d7c73bad44664e9f96c6c0de75e5cf3816199febf9"
index=json.loads(index_raw); rows=index["payloads"]; assert len(rows)==index["payloadCount"]==230
assert len({x["path"] for x in rows})==230
for row in rows:
 path=PurePosixPath(row["path"]); assert not path.is_absolute() and ".." not in path.parts
 p=D/row["path"]; assert p.is_file() and not p.is_symlink()
 exact(p.read_bytes(),row,row["path"])
assert sum(x["bytes"] for x in rows)==index["payloadBytes"]==13405757
expected={x["path"] for x in rows}|{"FILE_INDEX.json"}
assert {p.relative_to(D).as_posix() for p in D.rglob("*") if p.is_file()}==expected
tree_lines=git(SOURCE,"ls-tree","-r","-z",INCOMING,"--",PACKET).decode().split("\0")
tree={}
for line in filter(None,tree_lines):
 meta,p=line.split("\t",1); mode,kind,blob=meta.split()
 assert kind=="blob" and mode=="100644"
 tree[p[len(PACKET)+1:]]=blob
assert set(tree)==expected
for rel,(blob,raw) in zip(tree,batch(SOURCE,[INCOMING+":"+PACKET+"/"+p for p in tree])):
 assert blob==tree[rel] and raw==(D/rel).read_bytes(),rel
assert gtext(SOURCE,"diff","--name-only",BASE,"3bbe081753f84a36370ac545bdc0271e0aad8f58")==PRODUCT
assert all(x.startswith(PACKET+"/") for x in gtext(SOURCE,"diff","--name-only","3bbe081753f84a36370ac545bdc0271e0aad8f58",INCOMING).splitlines())
product_raw=git(SOURCE,"show",INCOMING+":"+PRODUCT)
assert product_raw==(SOURCE/PRODUCT).read_bytes()
assert sha(product_raw)=="dcb942bbbdc799989134da1f84256641ac750437749ca67d4412e352a0f0a252"
first=load(B/"RED_INDEX.json")
assert sha((B/"RED_INDEX.json").read_bytes())==index["firstRedIndexSHA256"]
assert len(first["payloads"])==170 and first["payloadBytes"]==5668098
for row in first["payloads"]:exact((B/row["path"]).read_bytes(),row,"first-red/"+row["path"])
old=load(B/"INPUTS.json"); new=load(N/"INPUTS.json")
assert sha((B/"INPUTS.json").read_bytes())=="bf16b93b5ab6badcd405f436258f2b4e40d5069bdf58004f6249fa03adf241ad"
assert sha((N/"INPUTS.json").read_bytes())=="afdec7917149611b064631589085388d26ff5bdcb2d0d6b24c097b818bf3efea"
assert len(old["sourceInputs"])==len(new["sourceInputs"])==116
oldmap={x["compiled"]:x for x in old["sourceInputs"]}
newmap={x["compiled"]:x for x in new["sourceInputs"]}
assert set(oldmap)==set(newmap)
changes=[k for k in oldmap if oldmap[k]!=newmap[k]]
assert changes==["harness/tests/HeldReadTests.swift"],changes
oldtest=(B/"harness/tests/HeldReadTests.swift").read_bytes()
newtest=(N/"HeldReadTests.swift").read_bytes()
needle=b"Google_Protobuf_Value(nullValue: .nullValue)"
replacement=b"Google_Protobuf_Value.with { $0.nullValue = .nullValue }"
assert oldtest.count(needle)==1 and oldtest.replace(needle,replacement)==newtest
for x in new["sourceInputs"]:
 raw=(N/x["retainedOverride"] if "retainedOverride" in x else B/x["compiled"]).read_bytes()
 exact(raw,x,x["compiled"])
for x in old["sourceInputs"]:exact((B/x["compiled"]).read_bytes(),x,x["compiled"])
git_inputs=[x for x in new["sourceInputs"] if "gitBlob" in x]
assert len(git_inputs)==109
for x,(blob,raw) in zip(git_inputs,batch(SOURCE,[x["base"]+":"+x["source"] for x in git_inputs])):
 assert blob==x["gitBlob"] and sha(raw)==x["sourceSHA256"] and len(raw)==x["sourceBytes"],x["source"]
 if x.get("retainedOriginal"): assert raw==(B/x["retainedOriginal"]).read_bytes()
 elif x["projection"]=="none":assert raw==(B/x["compiled"]).read_bytes()
assert len(new["generatedEdges"])==new["generatedFiles"]==74
assert set(new["generatedEdges"]).issubset({x["source"] for x in git_inputs})
pre=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\held_read_root_preexecution_review.json")
assert sha(pre.read_bytes())=="185f977b99f552d5c37df7c5808e7f4016f587bf7a3a45fda193a635c7150d84"
res=load(V/"RESULT.json"); inv=load(V/"EXECUTION.json")
assert sha((V/"RESULT.json").read_bytes())==index["actualResultSHA256"]
assert res["status"]=="PASS" and inv==res["execution"] and inv["exit_code"]==0 and inv["timed_out"] is False
assert inv["duration_s"]==95.391 and inv["args"][inv["args"].index("--filter")+1]=="OriginalHeldReadTests"
assert "--disable-xctest" in inv["args"] and "--enable-swift-testing" in inv["args"]
for key in ["runner","inputs","stdout","stderr"]:exact(Path(inv[key]["path"]).read_bytes(),inv[key],key)
assert sha(Path(inv["runner"]["path"]).read_bytes())=="8c7a4fb6abeba4207afcfe1b6940640c3c02a6512f666509ab09b8957d53cde9"
xml=ET.fromstring((V/"swift-testing-26.xml").read_bytes()); suites=xml.findall("testsuite")
assert len(suites)==1
assert {k:suites[0].get(k) for k in ["tests","errors","failures","skipped"]}=={"tests":"26","errors":"0","failures":"0","skipped":"0"}
cases=xml.findall(".//testcase"); assert len(cases)==26 and not any(list(x) for x in cases)
names=[x.get("name").removesuffix("()") for x in cases]
assert len(set(names))==26 and set(names)==set(old["testMethods"])==set(new["testMethods"])==set(res["actual_names"])
assert all(x.get("classname")=="OriginalHeldReadTests.OriginalHeldReadTests" for x in cases)
stdout=(V/"swift-test.stdout").read_text(encoding="utf-8")
assert "26 tests" in stdout and all(x in stdout for x in names)
for basev in [B/"validation/windows-held-read-26",V]:
 assert (basev/"SOURCE_BEFORE.json").read_bytes()==(basev/"SOURCE_AFTER.json").read_bytes()
 assert (basev/"DEPENDENCY_BEFORE.json").read_bytes()==(basev/"DEPENDENCY_AFTER.json").read_bytes()
before=load(V/"SOURCE_BEFORE.json")
assert len(before)==116
for x in before:
 y=newmap[x["relative"]];assert (x["bytes"],x["sha256"])==(y["bytes"],y["sha256"])
dep=Path(new["swiftProtobuf"]["path"]); rev=new["swiftProtobuf"]["commit"]
assert rev=="c6fe6442e6a64250495669325044052e113e990c"
assert gtext(dep,"rev-parse","HEAD")==rev and not gtext(dep,"status","--porcelain")
dep_rows=load(V/"DEPENDENCY_BEFORE.json")
assert len(dep_rows)==745
for row,(blob,raw) in zip(dep_rows,batch(dep,[rev+":"+x["relative"] for x in dep_rows])):
 exact(raw,row,"dependency/"+row["relative"])
source_rows=load(V/"ACTUAL_COMPILER_SOURCES.json")
assert len(source_rows)==213 and len({x["archive_path"] for x in source_rows})==213
groups=collections.Counter(x["archive_path"].split("/")[0] for x in source_rows)
assert dict(groups)=={"generated-build":4,"harness":115,"SwiftProtobuf":94}
with zipfile.ZipFile(V/"actual-compiler-sources.zip") as z:
 assert z.testzip() is None and set(z.namelist())=={x["archive_path"] for x in source_rows}
 for row in source_rows:
  raw=z.read(row["archive_path"]);exact(raw,row,row["archive_path"])
  assert raw==Path(row["path"]).read_bytes()
  if row["archive_path"].startswith("harness/"):exact(raw,newmap[row["archive_path"]],row["archive_path"])
  if row["archive_path"].startswith("SwiftProtobuf/"):
   assert raw==git(dep,"show",rev+":"+row["archive_path"].split("/",1)[1])
 assert {x["archive_path"] for x in source_rows if x["archive_path"].startswith("harness/")}=={x["compiled"] for x in new["sourceInputs"] if x["compiled"].endswith(".swift") and x["compiled"]!="harness/Package.swift"}
binary=res["test_binary"]; rawbinary=Path(binary["path"]).read_bytes(); exact(rawbinary,binary,"actual test PE")
assert rawbinary[:2]==b"MZ" and binary["bytes"]==20249600 and binary["sha256"]=="03e589cca509acdeb6e9058799901e1b9a288a01e3ef8b4889bbf71b00a6a303"
with zipfile.ZipFile(V/"actual-test-binary.zip") as z:
 assert z.testzip() is None and z.namelist()==["OriginalHeldReadControlsPackageTests.xctest"] and z.read(z.namelist()[0])==rawbinary
first_result=load(B/"validation/windows-held-read-26/RESULT.json")
assert first_result["status"]=="FAIL" and first_result["execution"]["exit_code"]==1 and first_result["test_cases_unavailable"] is True and not first_result["binary_evidence_complete"]
ownerold=git(TARGET,"show",BASE+":"+OWNER)
ownernow=git(TARGET,"show",HEAD+":"+OWNER)
# Composition adds one import and one restricting method group before the unchanged committed-event binding.
ownernorm=ownernow.replace(b"import Services\n",b"",1)
start=ownernorm.index(b"    private init(restricting original: Self, additionalCaptures:")
end=ownernorm.index(b"    var committedEventBinding:",start)
assert ownernorm[:start]+ownernorm[end:]==ownerold
owner_delta=git(TARGET,"diff",BASE,HEAD,"--",OWNER)
kept_paths=["Modules","Anytype/Resources","Scripts","scripts",".github","OriginalEditorFramework","Anytype.xcodeproj",OWNER,
 "Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift"]
kept={p:gtext(TARGET,"rev-parse",HEAD+":"+p) for p in kept_paths}
assert sha(ownernow)=="bf619f8e022c99d6f7f5f8e374b7213989639502801d36b754dcd95aedae9873"
OUT.mkdir()
(OUT/"ACTUAL_ROOT_REVIEW.py").write_bytes(Path(__file__).read_bytes())
first_review=Path(r"C:\ProgramData\SentinelX\uploads\.sentinelx_uploads\script_job_1b703f3335964164995301b189305773\held_read_root_final_review.py")
(OUT/"FIRST_ROOT_REVIEW.py").write_bytes(first_review.read_bytes())
(OUT/"ROOT_REVIEW_ERRATUM.json").write_bytes((json.dumps({"firstJob":"job_4dfa99fbb7fd","failedAt":"2026-11-22T08:59:44.456516Z","cause":"Root incorrectly counted every ProtobufMessages module source as generated. Actual closure has74 generated files plus genuine InvocationDispatchBinding.swift.","correction":"Count original generatedEdges entries and verify all are independently source-bound; preserve all109 original Git inputs and actual115 compiled targets.","firstJobTestsExecuted":0,"firstJobProductMutations":0,"productionOrTestChanges":0},indent=2)+"\n").encode())
(OUT/"ROOT_PREEXECUTION_REVIEW.json").write_bytes(pre.read_bytes())
(OUT/"OWNER_COMPOSITION_ONLY.patch").write_bytes(owner_delta)
receipt={"schema":"otzaria.original-held-read-root-final-review/1","utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "status":"PASS_IMMUTABLE_EVIDENCE_NO_TEST_REPLAY","targetHead":HEAD,"incoming":INCOMING,"sourceCommit":index["sourceCommit"],
 "packetIndexSHA256":sha(index_raw),"payloadCount":230,"payloadBytes":index["payloadBytes"],"exactPacketGitBlobs":231,
 "firstRedPayloadsVerified":170,"firstRedIndexSHA256":sha((B/"RED_INDEX.json").read_bytes()),
 "declaredInputsVerified":116,"originalGitInputsVerified":109,"fullOriginalGeneratedFiles":74,
 "rootPreexecutionReviewSHA256":sha(pre.read_bytes()),"fixtureOnlyExactInverse":True,"productSHA256":sha(product_raw),
 "actualResultSHA256":sha((V/"RESULT.json").read_bytes()),"actualCases":26,"failures":0,"errors":0,"skips":0,
 "swiftCommandSeconds":95.391,"suiteReportedSeconds":suites[0].get("time"),"actualCompilerSources":213,"compilerGroups":dict(groups),
 "actualDependencyGitFiles":745,"actualBinary":binary,"sourceArchiveSHA256":sha((V/"actual-compiler-sources.zip").read_bytes()),
 "binaryArchiveSHA256":sha((V/"actual-test-binary.zip").read_bytes()),"sourceSnapshotsEqual":True,"dependencySnapshotsEqual":True,
 "ownerReadImplementationByteUnchanged":True,"ownerCompositionDifference":"import Services plus previously reviewed restricting SourceBinding methods only",
 "ownerDeltaSHA256":sha(owner_delta),"preservedGitObjects":kept,
 "limitations":["Portable subset, genuine protobuf/original Owner; no Apple/native RPC/engine/UI/body/identity/COMMIT/ACK acceptance",
 "26 cases compiled the declared base Owner; target composition additions separately reviewed/tested, original read implementation exact",
 "Same callback completion can precede owner retirement; returned value is not a durability receipt"],
 "rootScriptSHA256":sha(Path(__file__).read_bytes()),"newTestRuns":0,"artifactDownloads":0}
raw=(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n").encode();(OUT/"ROOT_FINAL_REVIEW.json").write_bytes(raw)
print(json.dumps({"status":receipt["status"],"receipt":str(OUT/"ROOT_FINAL_REVIEW.json"),"sha256":sha(raw),
 "payloads":230,"gitBlobs":231,"originals":109,"cases":26,"compilerSources":213,"dependencyGitFiles":745,"testsReplayed":0,"ownerReadUnchanged":True},ensure_ascii=False))
