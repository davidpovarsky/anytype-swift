"""Compose qualified SDK host-link source and original evidence; no repository code execution."""
from pathlib import Path
import os,subprocess,json,hashlib,shutil,stat,traceback
W=Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
DONOR_W=Path("/mnt/development/projects/worktrees/anytype-wave15-sdk-external-host-projection-20261123")
D=Path("/mnt/development/projects/diagnostics/sdk06-external-host-composition-20261123")
BASE="9178f18736244851657279761ad492618fab53c1"
ANCESTOR="5180bc5fd4b1d45475ad068153257fce4ae0e169"
DONOR="431838490e77ce7ffd4599b78e6a6cda016e3fc3"
SOURCE="b50858335e25f2f42f0cdb96d4928005ab14662d"
CHAIN=["145648c8388bdd01db9023e447f42fee3cfbcb20","cb7c3edcd4c5e83bfb3f6b6b5163602a64f8825a","310c35de7615dd614891e3474b5dc7abae73d17e","b50858335e25f2f42f0cdb96d4928005ab14662d",DONOR]
P="docs/validation/20261123-sdk06-external-host-projection"
DOC="docs/validation/20261123-sdk06-external-host-composition"
GEN="Tools/PinkhaSimulatorGate/sdk06_component_projection.py"
CONTRACT="Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
TEST="Tools/PinkhaSimulatorGate/test_sdk06_external_host_projection.py"
QSHA="4ada57d08375ac805f49732e3d2b2b85efef93186196ffa10ceee287faba9365"
SSHA="9bdac88670a61b0a27429202973cded5f2d02d0475effcd309074a8308c8cc93"
ASHA="f9f9bf5c8869180645eb235fa9c3e04b69eea7e6742d7f66b1f9b008792e83b2"
PAGE={
"PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift":"ad527c3082a29932af15ddc5a0bcaca7da5585845960cdebbdab65b4f50a78e2",
"Tools/PinkhaSemanticAnchorWire/apple_mounted/warning-ui-inputs.json":"ab399ceba07a88db6e572bccfdf00b0455a24887dcf6b6ae7a6443c4b8356bba",
"Tools/PinkhaSemanticAnchorWire/apple_mounted/warning_profile.py":"837a246cec6e5bf0aa4f6e5a1005acade0c052e3c2c675a6b8696a5a5a09e19f"}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*args):
 return subprocess.check_output(["git","--no-optional-locks","-c","gc.auto=0","-c","user.name=davidpovarsky","-c","user.email=your-email@example.com","-C",str(W),*args],stderr=subprocess.PIPE,timeout=90)
def blob(ref,path):return git("show",ref+":"+path)
def tree(ref):
 out={}
 for line in git("ls-tree","-r","-z",ref).split(b"\0"):
  if line:
   value,name=line.split(b"\t",1);out[name.decode()]=value.decode()
 return out
def save(path,value):
 b=(json.dumps(value,sort_keys=True,indent=2)+"\n").encode()
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,"wb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 return {"path":str(path),"bytes":len(b),"sha256":sha(b)}
def contract_check(raw,ref,current):
 value=json.loads(raw)
 assert len(value["inputs"])==82
 for name,row in value["inputs"].items():
  assert set(row)=={"git_mode","sha256"},name
  b=(W/name).read_bytes()
  assert sha(b)==row["sha256"] and b==blob(ref,name),name
  assert current[name].split()[0]==row["git_mode"],name
  executable=bool((W/name).stat().st_mode&0o111)
  assert executable==(row["git_mode"]=="100755"),name
 return value
def main():
 free_before=shutil.disk_usage(W).free
 assert free_before>=1073741824,free_before
 assert git("rev-parse","HEAD").decode().strip()==BASE
 assert not git("status","--porcelain=v1","--untracked-files=all")
 assert subprocess.check_output(["git","--no-optional-locks","-C",str(DONOR_W),"rev-parse","HEAD"],text=True).strip()==DONOR
 assert not subprocess.check_output(["git","--no-optional-locks","-C",str(DONOR_W),"status","--porcelain=v1","--untracked-files=all"])
 assert git("rev-list","--reverse",ANCESTOR+".."+DONOR).decode().splitlines()==CHAIN
 qraw=blob(DONOR,P+"/qualification.json")
 sraw=blob(DONOR,P+"/attempt2-originals/seal.json")
 araw=blob(DONOR,P+"/qualification-source-audit.json")
 assert sha(qraw)==QSHA and sha(sraw)==SSHA and sha(araw)==ASHA
 q,seal,audit=map(json.loads,(qraw,sraw,araw))
 assert q["source"]==SOURCE and q["status"]=="QUALIFIED_PURE_CONTROL_ONLY"
 assert q["actual"]["returncode"]==0 and q["actual"]["subcasesPassed"]==4 and q["actual"]["subcasesFailed"]==0
 assert len(q["actual"]["methodsStarted"])==len(q["actual"]["methodsPassed"])==1
 assert q["actual"]["ownedGroupAbsent"] and q["actual"]["sourceUnchanged"] and q["actual"]["sourceInputs"]==40
 assert q["actual"]["builds"]==q["actual"]["oldMethods"]==q["actual"]["productMethods"]==0
 assert q["originalAttempt1"]["status"]=="FAIL" and q["originalAttempt1"]["subcasesPassed"]==3 and q["originalAttempt1"]["subcasesFailed"]==1
 assert seal["fileCount"]==len(seal["files"])==23 and audit["sourceRows"]==len(audit["rows"])==40
 for name,row in seal["files"].items():
  b=blob(DONOR,P+"/attempt2-originals/"+name)
  assert len(b)==row["bytes"] and sha(b)==row["sha256"],name
  if "originalPath" in row:
   p=Path(row["originalPath"])
   assert p.read_bytes()==b and str(p.stat().st_ino)==row["originalInode"] and str(p.stat().st_mtime_ns)==row["originalMtimeNs"],name
 donor=tree(DONOR);ancestral=tree(ANCESTOR);before=tree(BASE)
 for name,row in audit["rows"].items():
  b=blob(DONOR,name)
  assert len(b)==row["bytes"] and sha(b)==row["sha256"] and (DONOR_W/name).read_bytes()==b,name
  assert donor[name].split()[0]==row["gitMode"],name
 changed={p for p in set(ancestral)|set(donor) if ancestral.get(p)!=donor.get(p)}
 assert not(set(ancestral)-set(donor))
 assert {p for p in changed if not p.startswith(P+"/")}=={GEN,CONTRACT,TEST}
 assert {p for p in changed if p in ancestral}=={GEN,CONTRACT}
 assert all(p not in before for p in changed if p not in ancestral),"fresh_additive_paths_required"
 inverses=json.loads(blob(DONOR,P+"/exact-source-inverses.json"))
 for item in inverses["production"]:
  b=blob(DONOR,item["path"]);assert sha(b)==item["after"]
  text=b.decode()
  for h in reversed(item["hunks"]):
   assert text.count(h["after"])==1
   text=text.replace(h["after"],h["before"])
  assert text.encode()==blob(ANCESTOR,item["path"]) and sha(text.encode())==item["before"]
 oldraw=blob(BASE,CONTRACT);newraw=blob(DONOR,CONTRACT)
 assert sha(oldraw)=="ddc7588bb76ae2e80dc73926313d5e0192954625a1d48111ea919a134ed812da"
 assert sha(newraw)=="8d3045bc1dbe2f943b73b26e5d92c57f5523a9d3771d0800b6689040df889987"
 old=contract_check(oldraw,BASE,before);new=json.loads(newraw)
 restored=json.loads(newraw);restored["inputs"][GEN]=old["inputs"][GEN]
 assert restored==old and len(new["inputs"])==82 and not(set(PAGE)&set(old["inputs"]))
 for name,digest in PAGE.items():assert sha((W/name).read_bytes())==digest and sha(blob(BASE,name))==digest
 expected=dict(before)
 for name in changed:expected[name]=donor[name]
 intent={"base":BASE,"donor_base":ANCESTOR,"donor":DONOR,"donor_commits":CHAIN,"source_control":SOURCE,"source_qualification_sha256":QSHA,"seal_sha256":SSHA,"source_audit_sha256":ASHA,"changed_paths":sorted(changed),"preserved_page":PAGE,"source_only_free_floor":1073741824,"retained_new_worktree_and_diagnostics_budget":2097152,"transient_index_and_source_budget":8388608,"new_tests":0,"new_builds":0,"execution_gates_changed":False,"free_before":free_before}
 save(D/"integration-intent.json",intent)
 applied=[]
 for index,commit in enumerate(CHAIN,1):
  out=git("cherry-pick",commit)
  value={"source_commit":commit,"result_commit":git("rev-parse","HEAD").decode().strip(),"stdout":out.decode(),"index":index}
  save(D/("cherry-pick-"+str(index)+".json"),value);applied.append(value)
 assert tree("HEAD")==expected,"exact_union_tree_required"
 assert not git("status","--porcelain=v1","--untracked-files=all")
 git("diff","--check",BASE,"HEAD","--",GEN,CONTRACT,TEST)
 for name,digest in PAGE.items():assert sha((W/name).read_bytes())==digest
 assert (W/CONTRACT).read_bytes()==newraw
 contract_check(newraw,"HEAD",tree("HEAD"))
 root=W/DOC;root.mkdir(parents=True)
 record={"status":"QUALIFIED_SDK_EXTERNAL_HOST_SOURCE_COMPOSED_MAC_PENDING","base":BASE,"donor":DONOR,"donor_commits":CHAIN,"applied_commits":applied,"control_source":SOURCE,"source_qualification_sha256":QSHA,"source_audit_sha256":ASHA,"originals_seal_sha256":SSHA,"verified_original_seal_members":23,"verified_control_inputs":40,"all_available_live_originals_matched_byte_inode_mtime":True,"original_attempt1_status":"FAIL_PRESERVED_3PASS_1FAIL","corrected_control_actual_methods":1,"corrected_control_actual_subcases":4,"corrected_control_original_receipt_sha256":q["evidence"]["receipt"]["sha256"],"generator_sha256":q["production"]["generatorSHA256"],"controller_source_sha256":q["production"]["controllerSourceSHA256"],"runtime_descriptor_unchanged":True,"whole_tree_integrity_unchanged":True,"sdk82_contract_verified":True,"contract81_other_rows_and_all_other_fields_unchanged":True,"page_original_bytes_preserved":PAGE,"all_other_prior_paths_unchanged":True,"new_tests_now":0,"new_builds_now":0,"old24_and_old7_replayed":0,"planned_route":"sdk06-projected-components","actual_repaired_mac_compilation_linking_enumeration_23methods_32cases":"NOT_RUN","source_only_free_floor":1073741824,"execution_gates_changed":False,"integrator_sha256":sha(Path(__file__).read_bytes())}
 save(root/"qualification.json",record)
 with (root/"integrate-sdk-external-host.py").open("xb") as f:f.write(Path(__file__).read_bytes());f.flush();os.fsync(f.fileno())
 git("add","--",DOC)
 git("diff","--cached","--check")
 git("commit","-m","Compose qualified SDK external host linkage with retained original outcomes")
 head=git("rev-parse","HEAD").decode().strip();after=tree(head)
 additions={p for p in after if p.startswith(DOC+"/")}
 assert set(after)==set(expected)|additions
 assert all(after[p]==v for p,v in expected.items())
 assert not git("status","--porcelain=v1","--untracked-files=all")
 free_after=shutil.disk_usage(W).free;assert free_after>=1073741824
 measured=sum(p.lstat().st_blocks*512 for p in [root,*root.rglob("*"),D,*D.rglob("*")])
 measured+=sum((W/p).lstat().st_blocks*512 for p in changed if p not in before)
 assert measured<=2097152,measured
 gate={"status":"PASS_SOURCE_RETENTION_BEFORE_DISPATCH","head":head,"base":BASE,"remote_before":BASE,"donor":DONOR,"routes":["sdk06-projected-components"],"changed_paths":sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p)),"qualified_source_sha256":QSHA,"source_evidence_seal_sha256":SSHA,"all_other_c_ui_release_page_paths_unchanged":True,"sdk82_inputs_verified":82,"tests_replayed_now":0,"builds_now":0,"original_failures_retained":True,"new_source_only_admission_floor":1073741824,"heavy_execution_gates_changed":False,"composition_allocated_bytes":measured,"free_bytes":free_after}
 gref=save(D/"source-retention-before-dispatch.json",gate)
 save(D/"source-gate-seal.json",{"status":"PASS_SOURCE_GATE","publishedCandidate":head,"sourceGateSHA256":gref["sha256"]})
 return {"status":gate["status"],"head":head,"base":BASE,"gate_sha256":gref["sha256"],"changed_count":len(gate["changed_paths"]),"source_only_allocated_bytes":measured,"free_bytes":free_after}
try:
 result=main()
except BaseException as error:
 result={"status":"FAIL_PRESERVED_NO_AUTOMATIC_RETRY","type":type(error).__name__,"message":str(error),"traceback":traceback.format_exc()}
 if isinstance(error,subprocess.CalledProcessError):
  result["stdout"]=error.output.decode(errors="replace") if error.output else ""
  result["stderr"]=error.stderr.decode(errors="replace") if error.stderr else ""
 save(D/"integration-failure.json",result)
 print(json.dumps(result))
 raise
else:
 save(D/"integration-result.json",result)
 print(json.dumps(result))
