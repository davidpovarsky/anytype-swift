import ast,base64,difflib,gzip,hashlib,io,json,os,pathlib,shutil,stat,subprocess,zipfile
from datetime import datetime,timezone
P=json.loads(base64.b64decode(PACKET_B64))
SHARED=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-shared-20261123")
ROOT=pathlib.Path(P["root"]);BASE=P["base"];NS=P["namespace"]
CONTRACT="Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json"
OLD_SHA="338607c77a36158187183e817192b2339ead2722ee6c6fae3601e7350e62d67e"
MIN_FREE=1024**3;MAX_NEW=8*1024**2
def sha(b):return hashlib.sha256(b).hexdigest()
def stamp():return datetime.now(timezone.utc).isoformat()
env={**os.environ,"GIT_OPTIONAL_LOCKS":"0","PYTHONDONTWRITEBYTECODE":"1"}
def git(root,*args,payload=None):
 return subprocess.check_output(["git","-C",str(root),*args],input=payload,env=env,timeout=30)
def usage():
 roots=[ROOT]
 if ROOT.exists():
  gp=git(ROOT,"rev-parse","--absolute-git-dir").decode().strip()
  roots.append(pathlib.Path(gp))
 logical=allocated=count=0
 for root in roots:
  if not root.exists():continue
  for p in (root,*root.rglob("*")):
   s=p.lstat();assert stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),("unexpected_new_type",str(p))
   logical+=s.st_size;allocated+=s.st_blocks*512;count+=1
 return {"logical":logical,"allocated":allocated,"entries":count}
def guard():
 free=shutil.disk_usage(SHARED).free
 assert free>=MIN_FREE,("source_only_1gib_floor",free)
 u=usage();assert max(u["logical"],u["allocated"])<=MAX_NEW,("source_only_8mib_budget",u)
 return {"free":free,"owned":u}
def write(path,raw):
 guard();path.parent.mkdir(parents=True,exist_ok=True)
 with path.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 path.chmod(0o644)
def jwrite(path,value):write(path,(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=True)+"\n").encode())
assert not ROOT.exists(),"new_source_writer_required"
assert git(SHARED,"config","--get","extensions.worktreeConfig").decode().strip()=="true","per_worktree_sparse_configuration_required"
assert git(SHARED,"rev-parse",BASE).decode().strip()==BASE
old=git(SHARED,"show",BASE+":"+CONTRACT);assert sha(old)==OLD_SHA
original=json.loads(old);assert len(original["inputs"])==85
hunks=[
 {"before":'    "sdk06_basename_enumeration_probe",\n    "sdk06_component_projection",',
  "after":'    "sdk06_basename_enumeration_probe",\n    "sdk06_compile_support",\n    "sdk06_component_projection",'},
 {"before":'    "wave15_diagnostics",\n    "sdk06_compile_support"\n',
  "after":'    "wave15_diagnostics"\n'}
]
new=old.decode()
for h in hunks:
 assert new.count(h["before"])==1
 new=new.replace(h["before"],h["after"],1)
new=new.encode();current=json.loads(new)
assert len(new)==len(old)
assert current["preload_modules"]==sorted(n for n in current["modules"] if not n.startswith("test_") and n!="sdk06_original_native_continuation")
assert current["preload_modules"].index("sdk06_compile_support")==33
assert original["preload_modules"].index("sdk06_compile_support")==66
assert current["inputs"]==original["inputs"] and current["modules"]==original["modules"]
assert {k:v for k,v in current.items() if k!="preload_modules"}=={k:v for k,v in original.items() if k!="preload_modules"}
restored=new.decode()
for h in reversed(hunks):
 assert restored.count(h["after"])==1
 restored=restored.replace(h["after"],h["before"],1)
assert restored.encode()==old
production_paths=sorted(set(original["inputs"])|{CONTRACT})
initial=guard()
git(SHARED,"worktree","add","--no-checkout","-b",P["branch"],str(ROOT),BASE)
git(ROOT,"config","--worktree","core.sparseCheckout","true")
git(ROOT,"config","--worktree","core.sparseCheckoutCone","false")
patterns=git(ROOT,"rev-parse","--git-path","info/sparse-checkout").decode().strip()
patterns=pathlib.Path(patterns)
if not patterns.is_absolute():patterns=ROOT/patterns
patterns.parent.mkdir(parents=True,exist_ok=True)
assert not patterns.exists()
# Exact files plus the new namespace; no broad root or documentation cone.
patterns.write_text("\n".join("/"+p for p in production_paths+["AGENTS.md"])+ "\n/"+NS+"/**\n")
git(ROOT,"read-tree","-mu","HEAD")
after_materialize=guard()
assert git(ROOT,"status","--porcelain","--untracked-files=no").strip()==b""
assert (ROOT/CONTRACT).read_bytes()==old
for p,r in original["inputs"].items():
 b=(ROOT/p).read_bytes()
 assert sha(b)==r["sha256"],("base_input_not_exact",p)
with (ROOT/CONTRACT).open("wb") as f:f.write(new);f.flush();os.fsync(f.fileno())
d=ROOT/NS
write(d/"control-data/original-controller-source.json",old)
inner=P["inner"].encode();ast.parse(inner)
outer=P["outer"].replace("__INNER_SHA256__",sha(inner)).encode();ast.parse(outer)
write(d/"run-control.py",inner);write(d/"launch-control.py",outer)
jwrite(d/"execution-profile.json",P["profile"]);write(d/"README.md",P["readme"].encode())
packet=P["joblogPacket"];packed=base64.b64decode(packet["gzip_base64"])
assert len(packed)==packet["gzip_bytes"] and sha(packed)==packet["gzip_sha256"]
unpacked=gzip.decompress(packed)
assert len(unpacked)==packet["bytes"] and sha(unpacked)==packet["sha256"]
observed_original=json.loads(unpacked)
original_rows={}
for row in observed_original["files"]:
 name=row["path"];assert name in {"intent.json","read-selected-job-log.py","job137914443694.stdout.log","job137914443694.stderr.log","result.json"}
 b=base64.b64decode(row["base64"]);assert len(b)==row["bytes"] and sha(b)==row["sha256"]
 write(d/"original-failure"/name,b)
 original_rows[name]={"bytes":len(b),"sha256":sha(b)}
log=(d/"original-failure/job137914443694.stdout.log").read_bytes()
assert sha(log)=="13d7ef8be6da3fb7177d834dde658cfd1a0847d3d16d95c0127d774926a3e537"
# Original masked job output is retained, not normalized.
assert b"ValueError: Current production preloads must equal the fixed declared closure" in log
assert not any(token in log for token in (b"ghp_",b"github_pat_",b"gho_",b"ghs_")),"unexpected_unmasked_credential_prefix"
carrier=pathlib.Path("/mnt/development/projects/diagnostics/sdk06-compile-support-45237901921-attempt1-result-20261123/original-14850775236.zip")
artifact=carrier.read_bytes()
assert len(artifact)==525 and sha(artifact)=="6b6756e708502fd9e0554c357f070c1079fcd592da0b453837e4e5e87bf33776"
write(d/"original-failure/original-14850775236.zip",artifact)
with zipfile.ZipFile(io.BytesIO(artifact)) as z:
 assert z.namelist()==["Pinkha-Native-Derived-Evidence.zip"]
 nested=z.read(z.namelist()[0])
assert len(nested)==395 and sha(nested)=="dc5d6761562e774e83d0436ac62e8d53d6871fbd9afb4cfd593bc0548ab96568"
write(d/"original-failure/Pinkha-Native-Derived-Evidence.zip",nested)
with zipfile.ZipFile(io.BytesIO(nested)) as z:
 assert z.namelist()==["preflight/lifecycle-cleanup.json"]
 cleanup=z.read(z.namelist()[0])
assert len(cleanup)==351 and sha(cleanup)=="27de420b1d572012da236fe3a29ece686e1244710d1919cdf89031db1fbbb66a"
write(d/"original-failure/lifecycle-cleanup.json",cleanup)
assert json.loads(cleanup)["status"]=="NO_OWNED_CREATION"
for n in ["original-14850775236.zip","Pinkha-Native-Derived-Evidence.zip","lifecycle-cleanup.json"]:
 b=(d/"original-failure"/n).read_bytes();original_rows[n]={"bytes":len(b),"sha256":sha(b)}
audit={
 "protocol":"sdk06-preload-order-original-failure-audit-v1","status":"FAILED_CURRENT_CONTROLLER_ADMISSION",
 "run":"45237901921","attempt":"1","source":BASE,"job":"137914443694","artifact":"14850775236",
 "failure":"Current production preloads must equal the fixed declared closure",
 "callChain":["main","admit","verify_controller","preload_current_sources","require"],
 "originalJobLog":original_rows["job137914443694.stdout.log"],
 "selectedJobLogFetchReceipt":original_rows["result.json"],
 "oneSelectedLogFetchOnly":True,"newArtifactDownloads":0,
 "physicalOriginalArtifact":str(carrier),"windowsJobLogOrigin":observed_original["root"],
 "archiveRestorationStarted":False,"ownedSimulatorCreated":False,"componentBuilds":0,"productMethods":0,"uiBuilds":0,
 "cleanupReceiptStatus":"NO_OWNED_CREATION","cleanupCommands":0,
 "sourceDerived":{"declaredInputs":85,"moduleMappings":70,"preloads":67,
                  "setsEqual":set(original["preload_modules"])==set(current["preload_modules"]),
                  "originalSupportIndexZeroBased":66,"requiredSupportIndexZeroBased":33,
                  "productionGuardByteSHA256":"ba1dab0f02c508acbc222234d7930ee159bfc5d30f6ce3c47269d9a5b93025a6",
                  "priorPureControlDoesNotProveActualPreloaderExecution":True},
 "remainingUnknowns":["restoration on corrected current controller","actual component compilation/linkage",
                      "exact 23-method/32-case result","subsequent UI and acknowledgment acceptance"],
 "originals":original_rows,"auditMode":"bounded original ZIP/selected original job log and exact Git source; no replay"
}
jwrite(d/"original-failure/audit.json",audit)
jwrite(d/"exact-source-inverses.json",{
 "protocol":"sdk06-preload-order-exact-inverse-v1","base":BASE,"path":CONTRACT,
 "before":{"bytes":len(old),"sha256":sha(old)},"after":{"bytes":len(new),"sha256":sha(new)},
 "forwardHunks":hunks,"wholeFileInverseVerified":True,"all85InputRowsUnchanged":True,
 "all70ModuleMappingsUnchanged":True,"allOtherManifestFieldsUnchanged":True,
 "productionPythonChanges":0,"workflowChanges":0,"actualControls":"NOT_RUN"
})
write(d/"production.diff",git(ROOT,"diff","--",CONTRACT))
profile_path=NS+"/execution-profile.json"
control_paths=production_paths+[NS+"/control-data/original-controller-source.json",NS+"/run-control.py",NS+"/launch-control.py",profile_path]
assert len(control_paths)==90 and len(set(control_paths))==90
tree=git(ROOT,"ls-tree","-r","--full-tree","-z",BASE,"--",*production_paths)
modes={}
for item in tree.split(b"\0"):
 if item:
  meta,p=item.split(b"\t",1);mode,kind,oid=meta.decode().split();assert kind=="blob";modes[p.decode()]=mode
rows=[]
for p in sorted(control_paths):
 b=(ROOT/p).read_bytes();s=(ROOT/p).lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
 rows.append({"path":p,"bytes":len(b),"sha256":sha(b),"gitMode":modes.get(p,"100644"),"physicalMode":stat.S_IMODE(s.st_mode)})
manifest={
 "protocol":"sdk06-preload-order-control-v1","base":BASE,
 "methods":["test_actual_preloader_refuses_original_order_and_loads_fixed_closure"],
 "outsideTestPath":NS+"/run-control.py","oldMethodsToExecute":0,"productTestsToExecute":0,"buildsToExecute":0,
 "productionContractPath":CONTRACT,"productionSourcePaths":production_paths,
 "productionModuleNames":sorted(n for n in current["modules"] if not n.startswith("test_")),
 "oldTestModuleNames":sorted(n for n in current["modules"] if n.startswith("test_")),
 "originalContractOrigin":{"source":BASE,"path":CONTRACT,"sha256":sha(old),"bytes":len(old)},
 "inputs":rows,"note":"Input manifest itself is bound to frozen Git; outside control copy is compared byte-for-byte."
}
assert len(manifest["productionModuleNames"])==68 and len(manifest["oldTestModuleNames"])==2
jwrite(d/"control-inputs.json",manifest)
actual_functions={n.name:ast.get_source_segment(inner.decode(),n) for n in ast.parse(inner).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
prior_inner=git(ROOT,"show",BASE+":docs/validation/20261123-sdk06-compile-support/run-control.py")
prior_functions={n.name:ast.get_source_segment(prior_inner.decode(),n) for n in ast.parse(prior_inner).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
unchanged=sorted(n for n in actual_functions if n in prior_functions and actual_functions[n]==prior_functions[n])
review={
 "protocol":"sdk06-preload-order-source-review-v1","base":BASE,"branch":P["branch"],"writer":str(ROOT),
 "approvedProductionScope":"one preload list entry moved into sorted position; strict unchanged equality guard",
 "productionManifest":{"path":CONTRACT,"oldSHA256":sha(old),"newSHA256":sha(new),"bytes":len(new)},
 "inputRows":rows,"totalControlInputRows":90,"productionRowsIncludingContract":86,
 "inner":{"path":NS+"/run-control.py","bytes":len(inner),"sha256":sha(inner)},
 "outer":{"path":NS+"/launch-control.py","bytes":len(outer),"sha256":sha(outer)},
 "manifest":{"path":NS+"/control-inputs.json","sha256":sha((d/"control-inputs.json").read_bytes())},
 "originalFailureAudit":{"path":NS+"/original-failure/audit.json","sha256":sha((d/"original-failure/audit.json").read_bytes())},
 "priorWrapperOrigin":{"source":BASE,"path":"docs/validation/20261123-sdk06-compile-support/run-control.py","sha256":sha(prior_inner)},
 "unchangedWrapperFunctions":unchanged,"outsideActualControlReason":"production loaded_sources must not include the new test/wrapper source",
 "newScopes":["actual original equality refusal before import loop","actual fixed 68-module canonical production import closure"],
 "sourceAndLoadedBeforeAfter":True,"readonlyGitOnlyDuringMethod":True,"oldTestModulesRefused":True,
 "nativeBuildGateChanged":False,"noCurrentRunIdentityFabricated":True,
 "authoringStart":initial,"afterSparseMaterialization":after_materialize,
 "controls":"NOT_RUN","products":"NOT_RUN","newBuilds":0
}
jwrite(d/"source-review.json",review)
# Parse only the new control/launcher; never import any repository module during authoring.
ast.parse((d/"run-control.py").read_bytes());ast.parse((d/"launch-control.py").read_bytes())
assert git(ROOT,"diff","--name-only").decode().splitlines()==[CONTRACT]
git(ROOT,"add","--",CONTRACT,NS)
# Immutable raw original log is deliberately excluded from whitespace lint only.
git(ROOT,"diff","--cached","--check","--",".",":(exclude)"+NS+"/original-failure/job137914443694.stdout.log")
git(ROOT,"-c","user.name=davidpovarsky","-c","user.email=your-email@example.com","commit","-m","Fix exact SDK production preload order and freeze actual-loader control")
head=git(ROOT,"rev-parse","HEAD").decode().strip()
assert not git(ROOT,"status","--porcelain").strip()
# Direct final physical/Git/hash/mode preflight; no import or control execution.
direct={}
for r in rows:
 p=r["path"];b=(ROOT/p).read_bytes();g=git(ROOT,"show",head+":"+p);s=(ROOT/p).lstat()
 assert b==g and sha(b)==r["sha256"] and len(b)==r["bytes"] and stat.S_IMODE(s.st_mode)==r["physicalMode"]
 direct[p]={"sha256":sha(b),"bytes":len(b),"physicalMode":stat.S_IMODE(s.st_mode)}
assert git(ROOT,"show",head+":"+NS+"/control-inputs.json")==(d/"control-inputs.json").read_bytes()
final=guard()
print(json.dumps({"status":"SOURCE_FROZEN_NOT_RUN","head":head,"writer":str(ROOT),"branch":P["branch"],
 "productionManifestSHA256":sha(new),"oldManifestSHA256":sha(old),"wholeFileInverse":True,
 "all85RowsUnchanged":True,"fixedRowsPhysicalGitVerified":len(direct),"manifestSelfGitVerified":True,
 "innerSHA256":sha(inner),"outerSHA256":sha(outer),
 "manifestSHA256":sha((d/"control-inputs.json").read_bytes()),"sourceReviewSHA256":sha((d/"source-review.json").read_bytes()),
 "failureAuditSHA256":sha((d/"original-failure/audit.json").read_bytes()),
 "initial":initial,"final":final,"productionDiff":(d/"production.diff").read_text(),
 "actualControls":0,"actualRepositoryImports":0,"oldMethods":0,"builds":0},sort_keys=True))
