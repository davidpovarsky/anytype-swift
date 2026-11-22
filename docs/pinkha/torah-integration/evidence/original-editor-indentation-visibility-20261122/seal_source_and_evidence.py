import pathlib,subprocess,json,hashlib,shutil,zipfile,datetime,os
w=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-editor-visibility-20261122")
failure=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-45006133053-failure")
observer=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-45006133053-observation")
base="7b594f6f28961258d81b0eb2e7a29c7b047bb1d2"
branch="codex/otzaria-original-editor-framework-v11-host-reviewed-20261122"
path="Anytype/Sources/PresentationLayer/TextEditor/EditorPage/FlowLayout/Models/BlockIndentationStyle.swift"
proofpath="docs/pinkha/torah-integration/evidence/original-editor-indentation-visibility-20261122"
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")
def run(*args):
 p=subprocess.run(["git",*args],cwd=w,capture_output=True,timeout=180)
 assert p.returncode==0,{"args":args,"returncode":p.returncode,"stderr":p.stderr.decode("utf-8","replace")}
 return p.stdout
def git(*args):return run(*args).decode().strip()
def phase(name):write(out/"SEAL_PHASE.json",{"phase":name,"pid":os.getpid(),"time":datetime.datetime.now(datetime.timezone.utc).isoformat()})
assert git("rev-parse","HEAD")==base and git("branch","--show-current")==branch
assert not run("status","--porcelain=v1","--untracked-files=all")
assert git("ls-remote","--heads","origin","refs/heads/"+branch).split()[0]==base
assert not (out/"SEALED_HEAD.json").exists() and not (w/proofpath).exists()
phase("VERIFYING_FROZEN_VISIBILITY_RESULT_AND_PRIOR_APPLE_OUTCOME")
inputs=json.loads((out/"COMPILER_INPUTS_V2.json").read_bytes())
result=json.loads((out/"COMPILER_RESULT_V2.json").read_bytes())
execution=json.loads((out/"COMPILER_EXECUTION_V2.json").read_bytes())
assert result["status"]=="PASS_FULL_CANDIDATE_PARSE_AND_PORTABLE_INTERNAL_LAYOUT_AND_EXTERNAL_REJECTION"
assert result["inputs_sha256"]==sha((out/"COMPILER_INPUTS_V2.json").read_bytes())=="fe33d37e071d97ac07c277a222bb42d153d07ccc523e6296ee924511d10c5f46"
assert result["new_compiler_boundary_checks"]==3 and result["all_inputs_unchanged"]
assert len(execution["commands"])==3 and [r["returncode"] for r in execution["commands"]]==[0,0,1]
assert all(r["phase"]=="TERMINAL" and not r["timed_out"] for r in execution["commands"])
assert execution["runner_sha256"]==sha((out/"run_visibility_boundary_v2.py").read_bytes())=="b61ce5e74313d664a09e35d1915553598e0a0e801f9fbd045120b809e6d82225"
first=json.loads((out/"COMPILER_EXECUTION.json").read_bytes())
assert len(first["commands"])==1 and first["commands"][0]["returncode"]==1 and not first["commands"][0]["timed_out"]
assert sha((out/"complete-original-candidate-module.stderr.log").read_bytes())=="278993221e35da6d0b8dd26cd0edbd9315c9b30cc8cf61eb191ad6bbdb1fb332"
candidate=(out/"BlockIndentationStyle.candidate.swift").read_bytes()
assert sha(candidate)==result["candidate_sha256"]=="fc996c217bf56e7b1f07a81c034ac966e075f8fac7daa0d5fd3d6d6905622153"
original=run("show",base+":"+path)
assert sha(original)=="7fe0c774f9748899659d3062aeef5ccf759bd0655fc5a5667a08c6caae2da605"
assert candidate==original.replace(b"public enum BlockIndentationStyle:",b"enum BlockIndentationStyle:",1)
assert candidate.replace(b"enum BlockIndentationStyle:",b"public enum BlockIndentationStyle:",1)==original
working=(w/path).read_bytes();assert working.replace(b"\r\n",b"\n")==original
assert sha((out/"VISIBILITY.patch").read_bytes())=="093d406efe1b2332f33066be6e56515e061696e72b345ffbf63453647affb933"
for item in inputs["compiled_inputs"]:assert sha((out/item["path"]).read_bytes())==item["sha256"]
for item in inputs["original_inputs"]:
 assert sha(run("show",base+":"+item["path"]))==item["sha256"]
 assert sha((out/item["snapshot"]).read_bytes())==item["sha256"]
for item in inputs["import_mapping"]:
 raw=(out/item["original_input"]).read_bytes();portable=(out/item["portable_input"]).read_bytes()
 assert raw.replace(b"import CoreFoundation",b"import Foundation")==portable
 assert portable.replace(b"import Foundation",b"import CoreFoundation",1)==raw
archive=failure/"github-artifact-14747819041.zip"
assert archive.stat().st_size==14871793 and sha(archive.read_bytes())=="c9e75bf524bb2fc4c9ed25e16153bb494009cb9ebfb7ac824bf6009aba183c98"
diagnosis=json.loads((failure/"FAILURE_DIAGNOSIS.json").read_bytes())
assert diagnosis["head"]==base and diagnosis["original_framework_build"]=="PASS"
assert diagnosis["framework_build_command"]["returncode"]==0 and not diagnosis["framework_build_command"]["timed_out"]
assert diagnosis["source_error_count"]==0 and len(diagnosis["unlocated_driver_errors"])==4
assert diagnosis["external_consumer_build"]=="NOT_RUN" and diagnosis["native_editor_ui_tests"]==0
assert diagnosis["source_before_after_bytes_equal"] and diagnosis["actual_pin_count"]==51
assert diagnosis["source_controls_summary"]["status"]=="PASS_SOURCE_CONTROLS_221"
assert diagnosis["macro_restoration"]["status"]=="EXACT_ORIGINAL_MACRO_TRUST_RESTORED"
rootreview=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122")
reviews=[("original-enum-visibility-root-source-review.json","bde02c3067e1d5d4b0eb6fdb147f0785afdf8951cc15accca61a2e71fef55db2"),("original-enum-visibility-portable-review.json","a9007fbda9bcd59f6f3e2d2bfd007c239fcd54659b2d705dab27ea6e8c2c76e4")]
for name,expected in reviews:assert sha((rootreview/name).read_bytes())==expected
proof=out/"evidence-ready";assert not proof.exists();proof.mkdir()
(proof/".gitattributes").write_bytes(b"* -text\n")
for f in sorted(out.iterdir()):
 if f.is_file() and f.suffix.lower() in (".swift",".patch",".json",".log",".txt",".py") and f.name!="SEAL_PHASE.json":
  shutil.copyfile(f,proof/f.name)
for name,_ in reviews:shutil.copyfile(rootreview/name,proof/name)
shutil.copyfile(pathlib.Path(__file__),proof/"seal_source_and_evidence.py")
failed=proof/"prior-7b59";failed.mkdir()
for name in ("github-artifact-14747819041.zip","ARTIFACT_RECEIPT.json","FAILURE_DIAGNOSIS.json","GITHUB_ARTIFACTS.json","GITHUB_JOBS.json","download_and_diagnose.py"):
 shutil.copyfile(failure/name,failed/name)
selected=["execution.json","framework-build.command.json","actual-target-public-symbol-graph.command.json","compiler-symbolgraph-collection.json","source-before.json","source-after.json","source-admission.json","source-controls-result.json","macro-trust/macro-approval.json","macro-trust/macro-restoration.json","macro-trust/owned-trust-state.json","owned-simulator-cleanup.json","framework-distribution-after-observed-swift-protobuf-signing.json"]
for name in selected:
 dest=failed/"selected"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(failure/"inner-0"/name,dest)
for name in ("OBSERVER_STARTED.json","SUMMARY.json","terminal-run.json","terminal-jobs.json","terminal-artifacts.json"):
 dest=failed/"observer"/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(observer/name,dest)
module=out/result["module"]["path"];assert sha(module.read_bytes())==result["module"]["sha256"]
module_files=sorted(p for p in module.parent.glob("OriginalIndentationVisibility.*") if p.is_file())
assert module in module_files and len(module_files)<=6
with zipfile.ZipFile(proof/"actual-visibility-compiler-module.zip","x",compression=zipfile.ZIP_DEFLATED) as z:
 for p in module_files:z.write(p,p.name)
write(proof/"ACTUAL_COMPILER_MODULE.json",{"files":[{"name":p.name,"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size} for p in module_files],"archive_sha256":sha((proof/"actual-visibility-compiler-module.zip").read_bytes()),"scope":"Emitted Windows Swift visibility-control module only, not an Apple framework or runtime acceptance"})
write(proof/"WORKING_BYTE_PROVENANCE.json",{"path":path,"working_before_sha256":sha(working),"canonical_before_sha256":sha(original),"pure_crlf_normalization":working!=original,"product_change":"remove one public modifier only","candidate_sha256":sha(candidate)})
(proof/"PRE_APPLY_WORKING_BlockIndentationStyle.swift").write_bytes(working)
(proof/"README.md").write_bytes("# Original editor public visibility repair\n\n## Actual previous Apple outcome\n\nThe original framework at source9da8ab3d5c3d3f597a3fd0e1908a6b3c93f00457 / head7b594f6f28961258d81b0eb2e7a29c7b047bb1d2 genuinely built under Xcode27 for arm64 iOS Simulator. Run45006133053's xcodebuild command returned0 without timeout at09:26:35.474UTC after starting09:10:29.948UTC. Its complete original source closure contains2259 Swift inputs (2252 original app inputs and7 facade files);51 package pins remained exact. All221 required source controls passed, and source-before/source-after bytes match.\n\nThe later public compiler-graph gate failed because the original BlockIndentationStyle enum and its none/quote/callout cases were public. The compiler graph collection command itself returned0. External consumer build was NOT_RUN, native editor UI tests0, and no qualified distribution was emitted. Four unlocated corrupted-JSON driver lines are retained alongside the successful build command; they are not relabelled as the failure's cause.\n\nThe original outer artifact14747819041 is retained once with GitHub SHA256 c9e75bf524bb2fc4c9ed25e16153bb494009cb9ebfb7ac824bf6009aba183c98. Its inner archive SHA256 is325502129547943ae16ea2e98e86df5c7a0aa997ba3d1ccceb9a7a3bfe17eb7b;544 safe entries passed CRC inspection. The full archive retains the actual logs, graph files, xcresult and signature/source evidence. Selected receipts are also included for direct inspection.\n\n## Exact source change\n\nThe only original product source change removes the one public modifier from BlockIndentationStyle. The enum's three cases, original CoreFoundation import, Hashable/Equatable conformance and complete padding/extraHeight bodies are unchanged. Adding the seven original bytes back reproduces the615-byte preimage exactly. The three complete original use files are retained; all affected references are internal/private within the original editor. The strict verify_public_surface gate and all51 pins remain unchanged.\n\nA new real Apple build is required because this changes the compiled module's public surface. The earlier successful framework build is retained as evidence for its exact7b59 input, not relabelled as acceptance of this new input.\n\n## Focused compiler boundary and honest limits\n\nThe first actual Windows command failed because this installed toolchain has no CoreFoundation module. It did not run the external negative and did not establish a product defect. Its frozen original inputs, full runner, command, hashes and raw logs remain intact.\n\nThe reviewed continuation preserves the actual product candidate and separately parses its full source. For the two remaining Windows access-control checks, exactly two retained portable input copies replace import CoreFoundation with import Foundation: the enum and full original LayoutConstants. Genuine Windows Foundation supplies CGFloat; no type, body, protocol, dispatch or native substitute is introduced. Both import mappings have exact byte inverses.\n\nThe continuation compiles the complete mapped enum, complete original layout constants and complete unchanged BlockLayoutDetails into a module, then requires an external consumer's direct type reference to fail with the intended cannot-find-type diagnostic. This is a Windows Swift visibility boundary, not an Apple graph result, full original framework or native UI test. The unsupported first command and any previously passing suites are not replayed.\n\nAll input hashes, explicit compiler argv/cwd/PIDs/timeouts, raw logs, module bytes and independent root source reviews are retained. The compiler module archive contains only the emitted boundary module, not an app or framework distribution. The mandatory source/profile admission after sealing is labelled a local fixture, never a GitHub/native attestation.\n\n## Remaining acceptance\n\nThe next genuine producer run must pass the unchanged compiled public/SPI graph, external binary consumer, resource/signature/runtime checks and distribution admission before a consumer can use a qualified SDK. Original editor StageB, production account/Space authority, native annotation identity/body application, CloudKit exchange and device/Release acceptance remain separate open gates.\n".encode())
composition={"schema":1,"base":base,"prior_run":45006133053,"prior_apple_framework_build":"PASS_EXACT_PRIOR_INPUT","prior_public_surface_gate":"FAIL","changed_product_files":1,"path":path,"preimage_sha256":sha(original),"candidate_sha256":sha(candidate),"inverse_exact":True,"new_compiler_commands":3,"first_portable_dependency_red_retained":True,"old_tests_replayed":False,"new_native_tests":0,"gate_unchanged_sha256":"11ca6a3128fdc2c47cd9f63cd274e8896b5633af8753acfdb37fb02396fc0ebd"}
write(proof/"COMPOSITION.json",composition)
phase("APPLYING_EXACT_ONE_KEYWORD_VISIBILITY_REPAIR")
(w/path).write_bytes(candidate)
shutil.copytree(proof,w/proofpath);proof=w/proofpath
def index():
 files=[{"path":p.relative_to(proof).as_posix(),"sha256":sha(p.read_bytes()),"bytes":p.stat().st_size} for p in sorted(proof.rglob("*")) if p.is_file() and p.name!="INDEX.json"]
 write(proof/"INDEX.json",{"schema":1,"count":len(files),"files":files,"scope":"Exact packet bytes; index excludes itself."})
def stage_verify():
 paths=[proofpath+"/"+p.relative_to(proof).as_posix() for p in sorted(proof.rglob("*")) if p.is_file()]
 request="".join(":"+p+"\n" for p in paths).encode()
 p=subprocess.run(["git","cat-file","--batch"],cwd=w,input=request,capture_output=True,timeout=180);p.check_returncode();cursor=0
 for name in paths:
  end=p.stdout.index(b"\n",cursor);header=p.stdout[cursor:end].decode().split()
  assert len(header)==3 and header[1]=="blob",(name,header)
  size=int(header[2]);data=p.stdout[end+1:end+1+size]
  assert data==(w/name).read_bytes(),name
  cursor=end+size+2
 assert cursor==len(p.stdout);return len(paths)
index();run("diff","--check","--",path);run("add","--",path,proofpath);n=stage_verify()
phase("COMMITTING_ORIGINAL_ENUM_VISIBILITY_SOURCE")
run("commit","-m","fix(editor): keep original indentation style inside qualified module")
source=git("rev-parse","HEAD")
assert not run("status","--porcelain=v1","--untracked-files=all")
assert sha(run("show","HEAD:"+path))==sha(candidate)
changed={p for p in run("diff","--name-only","-z",base,"HEAD","--","Anytype/Sources","Modules","Tools","OriginalEditorFramework",".github").decode().split("\0") if p}
assert changed=={path},changed
trees={p:git("rev-parse","HEAD:"+p) for p in ("Anytype/Sources","Modules","Anytype/Resources")}
assert trees["Modules"]=="ce24c8510d0e5adc3e1daca46eb040c30f074900"
assert trees["Anytype/Resources"]=="0827010674c089cfe9846e592e1d801e9d3f7a9b"
gate=run("show","HEAD:Tools/OriginalEditor/framework_products.py")
assert sha(gate)==composition["gate_unchanged_sha256"]
assert (w/"Tools/OriginalEditor/framework_products.py").read_bytes().replace(b"\r\n",b"\n")==gate
join={**composition,"source_checkpoint":source,"original_trees":trees,"packet_blobs_verified_before_source_commit":n}
profilepath="Tools/OriginalEditor/framework_profile.json";pf=w/profilepath;prior=pf.read_bytes();profile=json.loads(prior)
assert profile["source_checkpoint"]=="9da8ab3d5c3d3f597a3fd0e1908a6b3c93f00457" and profile["package_pin_count"]==51
assert git("rev-parse","HEAD:"+profile["package_resolved_path"])==profile["package_resolved_blob"]=="b011914658931c21b97dcf14355d961ab6248b8f"
profile["source_checkpoint"]=source;profile["original_trees"]=trees
pf.write_text(json.dumps(profile,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
join.update({"profile_before_sha256":sha(prior),"profile_after_sha256":sha(pf.read_bytes()),"package_resolved_blob":profile["package_resolved_blob"],"package_pin_count":51})
write(out/"INTEGRATED_SOURCE.json",join);write(proof/"COHERENT_SOURCE_JOIN.json",join);index()
run("add","--",profilepath,proofpath+"/COHERENT_SOURCE_JOIN.json",proofpath+"/INDEX.json");nfinal=stage_verify()
phase("COMMITTING_EXACT_PROFILE_BINDING")
run("commit","-m","build(editor): bind original indentation visibility source")
head=git("rev-parse","HEAD")
assert not run("status","--porcelain=v1","--untracked-files=all")
sealed={"head":head,"sealed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),**join,"final_packet_files_verified":nfinal,"packet_index_sha256":sha((proof/"INDEX.json").read_bytes())}
write(out/"SEALED_HEAD.json",sealed);phase("SEALED_SOURCE_AND_PROFILE_ADMISSION_PENDING")
print(json.dumps({"status":"SOURCE_AND_PROFILE_SEALED_LOCAL_ADMISSION_PENDING","head":head,"source_checkpoint":source,"original_trees":trees,"changed_product_files":1,"native_tests":0,"packet_files":nfinal,"packet_index_sha256":sealed["packet_index_sha256"]}))
