"""Compose the qualified Page selector only; retain prior source and all original outcomes."""
from pathlib import Path
import os,subprocess,json,hashlib,shutil
W=Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
D=Path("/mnt/development/projects/diagnostics/page-menu-selector-composition-20261123")
BASE="5180bc5fd4b1d45475ad068153257fce4ae0e169"
SOURCE="894bb60f5d0d47a8629a5ace0bd5f0316f4905f5"
DONOR="205aaae5f35f8b4e7ece84e02477f99d2e805a45"
CHAIN=[SOURCE,DONOR]
DONOR_DOC="docs/validation/20261123-semantic-page-menu-selector"
DOC="docs/validation/20261123-page-menu-selector-composition"
QSHA="499190e00cb2d660f2d9281ece3450cb92b651daf775027bdfa9186ddbc5c80d"
SSHA="218cf187445a4b9f2dbd476a486b41411c59f40cce8fa9285646b471a1c17e94"
RUNTIME={
"PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift":"ad527c3082a29932af15ddc5a0bcaca7da5585845960cdebbdab65b4f50a78e2",
"Tools/PinkhaSemanticAnchorWire/apple_mounted/warning-ui-inputs.json":"ab399ceba07a88db6e572bccfdf00b0455a24887dcf6b6ae7a6443c4b8356bba",
"Tools/PinkhaSemanticAnchorWire/apple_mounted/warning_profile.py":"837a246cec6e5bf0aa4f6e5a1005acade0c052e3c2c675a6b8696a5a5a09e19f"}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):
 return subprocess.check_output(["git","--no-optional-locks","-c","gc.auto=0","-c","user.name=davidpovarsky","-c","user.email=your-email@example.com","-C",str(W),*args],stderr=subprocess.PIPE,timeout=90)
def blob(ref,path):return git("show",ref+":"+path)
def tree(ref):
 answer={}
 for line in git("ls-tree","-r","-z",ref).split(b"\0"):
  if line:
   value,name=line.split(b"\t",1);answer[name.decode()]=value.decode()
 return answer
def save(p,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+"\n").encode()
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,"wb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {"path":str(p),"bytes":len(b),"sha256":sha(b)}
free_before=shutil.disk_usage(W).free
assert free_before>=1073741824
assert git("rev-parse","HEAD").decode().strip()=="4f7329e67bd224d0bc5eb36384a61fb2793e0d31" and not git("status","--porcelain=v1","--untracked-files=all")
assert git("rev-list","--reverse",BASE+"..HEAD").decode().splitlines()==["80b8aff86a5c4a9cc755ef6f9762e9f60841455f","4f7329e67bd224d0bc5eb36384a61fb2793e0d31"]
assert git("rev-list","--reverse",BASE+".."+DONOR).decode().splitlines()==CHAIN
qraw=blob(DONOR,DONOR_DOC+"/qualification.json");sraw=blob(DONOR,DONOR_DOC+"/seal.json")
assert sha(qraw)==QSHA and sha(sraw)==SSHA
q=json.loads(qraw);seal=json.loads(sraw)
assert q["source_commit"]==SOURCE and q["base"]==BASE and q["changed_source_paths"]==RUNTIME
assert q["qualification"]=="STATIC_SOURCE_AND_SYNTAX_SCOPES_QUALIFIED_APPLE_NOT_RUN"
assert q["static_source_scope"]["result"]==q["syntax_scope"]["result"]=="PASS"
assert q["static_source_scope"]["actual_invocations"]==q["syntax_scope"]["actual_invocations"]==1
assert q["original_wrapper_status"]=="FAIL" and q["new_test_invocations"]==q["passing_controls_replayed"]==q["product_builds"]==0
assert len(seal["files"])==37 and seal["qualification_sha256"]==QSHA
for name,row in seal["files"].items():
 b=blob(DONOR,DONOR_DOC+"/"+name);assert len(b)==row["bytes"] and sha(b)==row["sha256"]
for name,row in q["copied_originals"].items():
 b=blob(DONOR,DONOR_DOC+"/"+name)
 assert len(b)==row["bytes"] and sha(b)==row["sha256"] and Path(row["original_path"]).read_bytes()==b
before=tree(BASE);donor=tree(DONOR)
changed={p for p in set(before)|set(donor) if before.get(p)!=donor.get(p)}
assert len(changed)==41 and {p for p in changed if not p.startswith(DONOR_DOC+"/")}==set(RUNTIME)
assert len(set(donor)-set(before))==38 and not(set(before)-set(donor))
for name,digest in RUNTIME.items():assert sha(blob(DONOR,name))==digest
contract_path="Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
contract_raw=blob(BASE,contract_path)
assert sha(contract_raw)=="ddc7588bb76ae2e80dc73926313d5e0192954625a1d48111ea919a134ed812da"
contract=json.loads(contract_raw);assert len(contract["inputs"])==82 and not(set(RUNTIME)&set(contract["inputs"]))
save(D/"resume-intent.json",{"base":BASE,"donor":DONOR,"commits":CHAIN,"exact_changed_paths":sorted(changed),"source_qualification_sha256":QSHA,"source_evidence_seal_sha256":SSHA,"source_only_admission":{"minimum_free":1073741824,"transient_limit":8388608,"retained_composition_limit":1048576,"reason":"Finite source/doc/index changes only; native and Apple execution guards unchanged."},"tests_replayed":0,"new_builds":0,"free_before":free_before})
assert tree("HEAD")==donor,"preserve_original_applied_donor_tree_without_replay"
composed=git("rev-parse","HEAD").decode().strip();current=tree("HEAD")
assert all(current.get(p)==donor.get(p) for p in changed)
assert all(current.get(p)==row for p,row in before.items() if p not in changed)
for name,digest in RUNTIME.items():assert sha((W/name).read_bytes())==digest
assert (W/contract_path).read_bytes()==contract_raw
for name,row in contract["inputs"].items():
 b=(W/name).read_bytes()
 assert sha(b)==row["sha256"] and b==blob(BASE,name) and current[name].split()[0]==row["git_mode"],name
root=W/DOC;root.mkdir(parents=True)
(root/"integration-originals").mkdir()
first_error=(D/"integration.stderr").read_bytes()
assert b"KeyError: 'bytes'" in first_error
with (root/"integration-originals"/"first-integration.stderr").open("xb") as f:f.write(first_error);f.flush();os.fsync(f.fileno())
with (root/"integration-originals"/"first-integrator.py").open("xb") as f:f.write((D/"integrate-page-selector.py").read_bytes());f.flush();os.fsync(f.fileno())

(root/"operational-originals").mkdir()
operations=[
("six-cold-relocation.json","/mnt/development/projects/diagnostics/native-cold-binaries-relocation-20261123/relocation-result.json","004d861512cdf9668ac8db796e3d86cff46dc863787bbc35ca181874cf0d1734"),
("eight-cold-relocation.json","/mnt/development/projects/diagnostics/anytype-cold-carriers-relocation-20261123/relocation-result-v2.json","70dbd522667e668bbbf2bf28fbcbdad3cc800a4231a8d200c97a66a81003ecba"),
("cold-ui-tree-relocation.json","/mnt/development/projects/diagnostics/native-ui-451483-cold-tree-relocation-20261123/relocation-result.json","d127510c9aa4ee5a85da8fa864638bc342bd2219229cc439e29f1f83286193e0")]
refs=[]
for name,path,digest in operations:
 b=Path(path).read_bytes();assert sha(b)==digest
 dest=root/"operational-originals"/name
 with dest.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 refs.append({"original_path":path,"copy":str(dest.relative_to(W)),"bytes":len(b),"sha256":digest})
record={"status":"QUALIFIED_PAGE_SELECTOR_SOURCE_COMPOSED_APPLE_PENDING","base":BASE,"donor":DONOR,"donor_commits":CHAIN,"composed_donor_head":composed,"source_qualification_sha256":QSHA,"evidence_seal_sha256":SSHA,"all37_original_seal_members_preserved":True,"all_copied_originals_verified_against_live_original_bytes":True,"changed_runtime_paths":RUNTIME,"all_other_prior_source_paths_unchanged":True,"sdk82_contract_unchanged":True,"retained_static_audit_invocations":1,"retained_syntax_parse_invocations":1,"original_wrapper_status":"FAIL_PRESERVED","separate_original_only_audit_sha256":q["independent_original_only_audit_sha256"],"tests_replayed_now":0,"builds_now":0,"route":"semantic-page-startup-warning","planned_new_ui_builds":1,"planned_app_native_builds":0,"planned_fresh_preparation":1,"new_preparation_acceptance_credit":0,"actual_new_menu_and_downstream_acceptance":"NOT_RUN","cold_relocation_originals":refs,"cold_relocation_allocated_bytes":1132679168,"source_only_free_floor":1073741824,"heavy_execution_gates_changed":False,"integrator_sha256":sha(Path(__file__).read_bytes()),"original_integration_failure_sha256":sha(first_error),"composition_recovery":"Both donor commits were already applied cleanly; root schema guard requested nonexistent bytes field. Resume preserves original failure, compares all82 physical inputs byte-exact to unchanged baseline Git blobs and verifies their declared git_mode/sha256; no donor, control, parser or build replay."}
save(root/"qualification.json",record)
with (root/"integrate-page-selector.py").open("xb") as f:f.write(Path(__file__).read_bytes());f.flush();os.fsync(f.fileno())
git("add","--",DOC)
git("diff","--cached","--check")
git("commit","-m","Compose exact Page menu selector with retained original evidence")
head=git("rev-parse","HEAD").decode().strip();after=tree(head)
allowed=changed|{p for p in after if p.startswith(DOC+"/")}
assert all(after.get(p)==row for p,row in before.items() if p not in allowed)
assert all(p in allowed for p in set(after)-set(before))
assert not git("status","--porcelain=v1","--untracked-files=all")
allocation=sum(p.lstat().st_blocks*512 for p in [root,*root.rglob("*"),D,*D.rglob("*")])
allocation+=sum((W/p).lstat().st_blocks*512 for p in changed if p not in before)
assert allocation<=1048576,allocation
free_after=shutil.disk_usage(W).free;assert free_after>=1073741824
gate={"status":"PASS_SOURCE_RETENTION_BEFORE_DISPATCH","head":head,"base":BASE,"remote_before":BASE,"donor":DONOR,"routes":["semantic-page-startup-warning"],"changed_paths":sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p)),"qualified_source_sha256":QSHA,"source_evidence_seal_sha256":SSHA,"all_other_c_ui_release_sdk_paths_unchanged":True,"sdk82_inputs_verified":82,"tests_replayed_now":0,"builds_now":0,"original_wrapper_failure_retained":True,"new_source_only_admission_floor":1073741824,"heavy_execution_gates_changed":False,"composition_allocated_bytes":allocation,"free_bytes":free_after}
gref=save(D/"source-retention-before-dispatch.json",gate)
save(D/"source-gate-seal.json",{"status":"PASS_SOURCE_GATE","publishedCandidate":head,"sourceGateSHA256":gref["sha256"]})
print(json.dumps({"status":gate["status"],"head":head,"base":BASE,"gate_sha256":gref["sha256"],"changed_count":len(gate["changed_paths"]),"source_only_allocated_bytes":allocation,"free_bytes":free_after}))
