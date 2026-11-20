from pathlib import Path
import hashlib, json, re, shutil, subprocess, zipfile, zstandard, datetime
ROOT=Path(r"C:\Users\DAVID\Code\anytype-swift-any-engine-20261119")
PRIVATE=ROOT/"build/any-engine-port/apple57-patched-runtime-v2"
FIRST=ROOT/"build/any-engine-port/apple57-patched-runtime-v1"
FIX=ROOT/"build/any-engine-port/apple57-backup-toggle-fix-v1"
DEST=ROOT/"docs/any-engine-port/evidence/20261120/apple57-patched-runtime-v1"
HEAD="57c116e02ee6dbce21f3bbffcc297841d2bd1235"
ARTIFACT_SHA="3d85d2d7afca90108112a297068f17779d4dbbcfacc30e4719a57bbc885143ac"
def sha(raw): return hashlib.sha256(raw).hexdigest()
def save_json(path,obj):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(obj,ensure_ascii=True,indent=2)+"\n",encoding="utf-8",newline="")
def copy(src,dest):
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
def git_blob(rel):
 return subprocess.run(["git","show",HEAD+":"+rel],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=30).stdout
assert not DEST.exists(), "Do not overwrite sealed evidence."
artifact=(PRIVATE/"artifact.zip").read_bytes()
assert len(artifact)==93907567 and sha(artifact)==ARTIFACT_SHA
metadata=json.loads((PRIVATE/"selected-artifact.json").read_text())
assert metadata["id"]==14603642711 and metadata["workflow_run"]["head_sha"]==HEAD
assert metadata["digest"]=="sha256:"+ARTIFACT_SHA
# Detect mnemonic-shaped AX labels only in memory. Neither phrase text nor its
# digest is written. This scope is additional screening, not a universal scanner.
member="native-ui.xcresult/Data/data.0~zyM2uDzDf2_U7t5Nyyzc8pVgxPyeEOalaQCvsQMR3d15vNtvBKXx7Sb6v2oXiT5WM8Ca5T8_6wfBBo5GBA-KpA=="
with zipfile.ZipFile(PRIVATE/"artifact.zip") as z:
 raw_ax=zstandard.ZstdDecompressor().decompress(z.read(member),max_output_size=33554432)
private_text=raw_ax.decode("utf-8","replace")
mnemonics={s for s in re.findall(r"label: '([a-z]+(?: [a-z]+){11,23})'",private_text) if len(s.split()) in (12,24)}
assert len(mnemonics)==5
DEST.mkdir(parents=True)
(DEST/".gitattributes").write_bytes(b"* -text\n")
for name in ("collection-result.json","selected-artifact.json","artifact-contents.json","job.json","run.json","artifacts.json","executed-collector.py"):
 copy(PRIVATE/name,DEST/"collection"/name)
for name in ("collection-result.json","executed-collector.py"):
 if (FIRST/name).exists(): copy(FIRST/name,DEST/"collection/first-download-attempt"/name)
# Exact original summaries, trees, named reports and toolchain/build metadata.
selected=[]
for p in (PRIVATE/"extracted").iterdir():
 if p.name.endswith(("-named-execution.json","-test-counts.json","-test-methods.json")) or p.name in ("native-source.json","native-app-bundle.json","source-sha.txt","simulator.json","xcode-version.txt","hanlin-scheme-selected.json","hanlin-schemes.json"):
  assert not any(m.encode() in p.read_bytes() for m in mnemonics)
  copy(p,DEST/"apple-results"/p.name); selected.append(p.name)
# Rebind every named gate's exact test sources and runner, as well as reviewed app sites.
prior_pins=json.loads((PRIVATE/"pinned-source.json").read_text())
missing_prior_pins=[row for row in prior_pins if "sha256" not in row]
pins={row["path"]:row["sha256"] for row in prior_pins if "sha256" in row}
runner="Tools/AnyEnginePort/verify_native_test_execution.py"
named_proofs=[]
for p in (PRIVATE/"extracted").glob("*-named-execution.json"):
 obj=json.loads(p.read_text())
 assert obj["commit"]==HEAD
 for rel,digest in obj["testSources"].items():
  raw=git_blob(rel); assert sha(raw)==digest, (rel,sha(raw),digest)
  pins[rel]=digest
 assert sha(git_blob(runner))==obj["runnerSHA256"]
 prefix=p.name.removesuffix("-named-execution.json")
 assert sha((PRIVATE/"extracted"/(prefix+"-test-counts.json")).read_bytes())==obj["summarySHA256"]
 assert sha((PRIVATE/"extracted"/(prefix+"-test-methods.json")).read_bytes())==obj["testTreeSHA256"]
 named_proofs.append({"profile":obj["profile"],"namedReport":p.name,"summaryAndTreeHashesVerified":True,"testSourcesVerified":obj["testSources"],"runnerSHA256":obj["runnerSHA256"]})
for rel in ("NativeApp/UITests/NativeLaunchTests.swift","NativeApp/AnyNative.xcodeproj/project.pbxproj","Modules/PinkhaAnyNative/Sources/PinkhaAnyNative/AnyNativeRootView.swift",runner):
 pins[rel]=sha(git_blob(rel))
source_rows=[]
for rel,digest in sorted(pins.items()):
 raw=git_blob(rel); assert sha(raw)==digest
 target=DEST/"pinned-source"/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
 source_rows.append({"path":rel,"bytes":len(raw),"sha256":digest,"commit":HEAD})
save_json(DEST/"source-provenance.json",{"commit":HEAD,"files":source_rows,"namedGateVerifications":named_proofs,"priorCollectorMissingPaths":missing_prior_pins})
for name in ("sealing-failure.json","failed-sealer.py"):
 copy(ROOT/"build/any-engine-port/apple57-patched-seal-attempt1"/name,DEST/"collection/first-sealing-attempt"/name)
# Strict allowlist of control-only extraction outputs; raw AX/video stay private.
for name in ("safe-backup-child-controls.json","safe-backup-control-attributes.json","safe-backup-switch-geometry.json","safe-control-crop-final.json"):
 copy(PRIVATE/name,DEST/"controls"/name)
crop=PRIVATE/"safe-control-crops/6b5a0fca36892e18-last-controls.png"
assert sha(crop.read_bytes())=="1100e5fc76097fed1566eb2c909a4942856cfa52f9a1f9c4ea8bb3378b6599b1"
copy(crop,DEST/"controls/backup-switch-and-disabled-continue.png")
geometry=json.loads((PRIVATE/"safe-backup-switch-geometry.json").read_text())
by_pid={}
for row in geometry["rows"]:
 if row["control"]!="any-native-backup-acknowledged":continue
 match=re.search(r"pid:\s*(\d+)",row["lineMetadata"])
 value=re.search(r"value:\s*([01])\b",row["lineMetadata"])
 if not match:continue
 d=by_pid.setdefault(match.group(1),{"rows":0,"values":[],"childSwitchEntries":0,"childValues":[]})
 d["rows"]+=1
 if value:d["values"].append(int(value.group(1)))
 for n in row["neighbors"]:
  if n["offset"]==2 and n["type"]=="Switch":
   d["childSwitchEntries"]+=1
   if n["numericValue"] is not None:d["childValues"].append(int(n["numericValue"]))
for d in by_pid.values():
 d["values"]=sorted(set(d["values"]));d["childValues"]=sorted(set(d["childValues"]))
assert len(by_pid)==5 and all(d["values"]==[0] and d["childValues"]==[0] for d in by_pid.values())
save_json(DEST/"controls/control-state-summary.json",{"artifactSHA256":ARTIFACT_SHA,"sourceMember":member,"decodedSourceSHA256":sha(raw_ax),"fiveProcesses":by_pid,"showPhraseIdentifierOccurrencesInSuccessfullyDecodedControlMembers":sum(x["any-native-backup-show-phrase"] for x in geometry["members"].values()),"decodeFailures":geometry["decodeFailures"],"frameLimit":"Original AX switch rows omit frames. Observed nested Switch is targeted, without inferred coordinates.","safeCrop":{"sha256":sha(crop.read_bytes()),"pixelCrop":{"x":40,"y":620,"width":1432,"height":184},"scope":"Only bottom backup toggle strip and Continue; no phrase displayed."}})
# Preserve exact closed-log bytes privately; publish bounded literal excerpts only.
log_rows=[]
for name in ("runtime.log","native-ui.log"):
 src=PRIVATE/"extracted"/name; raw=src.read_bytes()
 text=raw.decode("utf-8","replace")
 out=[]
 for i,line in enumerate(text.splitlines(),1):
  allowed = ("NativeLaunchTests" in line and ("Test Case" in line or "error:" in line)) or "any-native-backup-acknowledged" in line or "any-native-backup-continue" in line or "Expected UI state was not reached" in line
  if name=="runtime.log":
   allowed = "Test Case" in line or ("pinkha/capabilities" in line and ("error:" in line or "method" in line or "NSURLError" in line or "FailingURL" in line)) or ("Code=-1001" in line and "Error Domain=" in line)
  if allowed:
   assert not any(m in line for m in mnemonics)
   assert len(line)<6000
   out.append({"line":i,"text":line})
 save_json(DEST/"logs"/(name+".selected-lines.json"),{"sourceBytes":len(raw),"sourceSHA256":sha(raw),"privateSourcePath":str(src),"scope":"Exact allowlisted test/control/error lines only; not a re-execution.","lines":out})
 log_rows.append({"name":name,"bytes":len(raw),"sha256":sha(raw),"selectedLineCount":len(out)})
private_originals={"scope":"Original complete ZIP, xcresults, AX attachments, videos and complete logs remain private/ignored. No full backup screen or phrase is copied into this archive.","artifactID":14603642711,"artifactBytes":len(artifact),"artifactSHA256":sha(artifact),"privateArtifactPath":str(PRIVATE/"artifact.zip"),"workflowJobLog":{"bytes":(PRIVATE/"workflow-job.log").stat().st_size,"sha256":sha((PRIVATE/"workflow-job.log").read_bytes()),"path":str(PRIVATE/"workflow-job.log")},"logExcerpts":log_rows}
save_json(DEST/"private-originals.json",private_originals)
# The fix is helper-only and remains Apple-pending; preserve all tested methods.
for name in ("NativeLaunchTests.before.swift","NativeLaunchTests.after.swift","helper.patch","source-proof.json","parse-result.json","parse.stdout.log","parse.stderr.log","parse_backup_toggle_helper.py"):
 copy(FIX/name,DEST/"helper-fix"/name)
def method_bodies(raw):
 text=raw.decode("utf-8")
 starts=list(re.finditer(r"^    func (test\w+)\([^\n]*\) \{",text,re.M));out={}
 for idx,m in enumerate(starts):
  boundary=starts[idx+1].start() if idx+1<len(starts) else text.index("    private func ",m.end())
  out[m.group(1)]=text[m.start():boundary].encode()
 return out
baseline=method_bodies(git_blob("NativeApp/UITests/NativeLaunchTests.swift"))
before=method_bodies((FIX/"NativeLaunchTests.before.swift").read_bytes())
after=method_bodies((FIX/"NativeLaunchTests.after.swift").read_bytes())
assert len(baseline)==7 and len(before)==len(after)==8 and before==after
originals=[]
for name,body in baseline.items():
 assert after[name]==body,(name,"Original method changed")
 originals.append({"name":name,"bytes":len(body),"sha256":sha(body),"unchangedFromExecuted57":True})
save_json(DEST/"helper-fix/executed-seven-methods-preserved.json",{"executedCommit":HEAD,"originalSeven":originals,"currentEighthAlsoUnchanged":True,"stateInjection":False,"tapRetries":0,"keychainEntitlementOrProductChanges":False,"actualAppleExecutionOfHelper":"pending"})
profiles=("runtime","hanlin-ios","ui-ios","application","native-ui")
counts={}
for prefix in profiles:
 obj=json.loads((PRIVATE/"extracted"/(prefix+"-test-counts.json")).read_text())
 counts[prefix]={k:obj[k] for k in ("totalTestCount","passedTests","failedTests","skippedTests")}
summary={"status":"FAIL_ACTUAL_APPLE_ACCEPTANCE_WITH_SOURCE_BOUND_DIAGNOSIS","commit":HEAD,"runID":44673740725,"jobID":136080515969,"artifactID":14603642711,"artifactSHA256":ARTIFACT_SHA,"counts":counts,"runtimeFailure":{"test":"AnyEmbeddedRuntimeTests/testRealManagedRuntimeLifecycleAndControlBoundary","stage":"initial unauthenticated managed-route negative read; before shutdown/control/restart","method":"GET","path":"/v1/pinkha/capabilities","errorDomain":"NSURLErrorDomain","errorCode":-1001,"timeoutApproxSeconds":60,"native403LogDoesNotProveResponseFlush":True,"sourceReviewOwnedBy":"any_runtime"},"uiFailures":{"count":5,"sharedBoundary":"createOwnedWorkspace waits for Continue enabled after tapping the outer backup Switch row","continueObserved":"present and Disabled","observedBackupValues":[0],"allFiveProcessesHaveNestedPhysicalSwitch":True,"spaceAndDocumentScenariosNotReached":True,"showPhraseAbsenceScope":"Only successfully decoded control-bearing attachments; one zstd body failed decoding"},"helperFix":{"sourceSHA256":"a6281a92153e6d93bc3e5a100b662571d9a19fffb722a0eb0d398180b640ee4f","syntax":"PASS","appleExecution":"pending","sevenExecutedMethodBodiesPreserved":True,"eighthSourceDragMethodPreserved":True,"oneObservedChildControlTap":True,"requiresActualChildAndRowValue1":True,"continueEnabledGuardUnchanged":True},"privacy":{"privateMnemonicShapedCandidateCount":len(mnemonics),"fullZIPAndRawAXNotPublished":True,"screenedControlCropOnly":True},"newCIExecution":False}
save_json(DEST/"result.json",summary)
readme="""# Apple57 patched native acceptance: preserved failures and diagnosis

This archive records the completed run 44673740725, patched job 136080515969,
at app commit 57c116e02ee6dbce21f3bbffcc297841d2bd1235. It is not a rerun.

| Actual suite | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Linked native runtime | 2 | 1 | 0 |
| Hanlin on iOS | 36 | 0 | 0 |
| UIKit package | 108 | 0 | 0 |
| Hosted native application | 5 | 0 | 0 |
| Native executable UI | 2 | 5 | 0 |

The original five UI failures remain recorded. Each stopped at the shared
backup acknowledgement helper, before creating its Space or reaching editor,
hierarchy, Inspector or Note assertions. Continue existed and was disabled.
The control-only AX extraction identifies five independent process IDs. Every
reported outer backup Switch and nested child Switch value was zero. In each
tree, the identified SwiftUI row contains StaticText and a distinct child Switch.
The original AX text omits Switch frames; no coordinates were inferred from it.

The cropped visual contains only the bottom toggle strip and disabled Continue.
It corroborates an off physical switch on the left in the Hebrew layout.
The helper-only correction now targets the unique observed descendant Switch,
requires it enabled, hittable and off, taps once, and waits for both actual child
and row values to become one before the unchanged Continue enabled guard.
All seven executed test method bodies and the current eighth source-drag method
are byte-identical. The corrected source passed syntax parsing only. Actual
Apple execution of this helper remains pending. No product binding, Keychain
entitlement, authority state or stored backup acknowledgement was changed.

The runtime failure is a separate initial denied GET to /v1/pinkha/capabilities,
before shutdown or restart. CFNetwork reported -1001 after roughly 60 seconds.
A native 403 access log is not proof that bytes completed socket delivery.
The native agent owns the corresponding source-boundary review and passive
test-only metrics. This archive does not claim a transport root cause or fix.

The exact complete 93,907,567-byte artifact ZIP was downloaded and verified
against GitHub's digest and workflow commit. It, full xcresults, videos, raw AX
and complete logs remain in ignored private storage. This repository archive
contains original count/named/tree JSON, exact source pins, allowlisted log
excerpts, control-only metadata, the screened crop, and helper source proof.
A literal screen for five privately extracted mnemonic-shaped 12-word AX labels
found no occurrence in the published files. The screen is additional protection,
not a claim of universal secret detection. No phrase text or phrase hash is saved.

The first artifact-download attempt timed out before finishing the file; its
failed collection receipt is preserved. That was a download failure, not another
test execution. The final archive manifest hashes every included file.
"""
(DEST/"README.md").write_text(readme,encoding="utf-8",newline="")
# Include this exact sealing/extraction program for reproducibility.
copy(Path(__file__),DEST/"seal_apple57_patched_runtime.py")
# Final phrase screening must cover every published text/binary file.
for p in DEST.rglob("*"):
 if p.is_file():
  raw=p.read_bytes()
  assert not any(m.encode() in raw for m in mnemonics),str(p)
files=[]
for p in sorted(DEST.rglob("*")):
 if p.is_file():
  raw=p.read_bytes();files.append({"path":p.relative_to(DEST).as_posix(),"bytes":len(raw),"sha256":sha(raw)})
manifest={"schemaVersion":1,"createdAt":datetime.datetime.now(datetime.timezone.utc).isoformat(),"scope":"Completed Apple57 patched native evidence, safe selective archive; complete original artifact stays private.","sourceCommit":HEAD,"fileCount":len(files),"totalBytes":sum(x["bytes"] for x in files),"files":files}
save_json(DEST/"MANIFEST.json",manifest)
print(json.dumps({"path":str(DEST),"fileCount":len(files),"totalBytes":manifest["totalBytes"],"manifestSHA256":sha((DEST/"MANIFEST.json").read_bytes()),"resultSHA256":sha((DEST/"result.json").read_bytes()),"sourceFileCount":len(source_rows),"allNamedGateSourceHashesVerified":True,"allSevenExecutedMethodBodiesPreserved":True,"noActiveChildProcessesCreated":True}))
