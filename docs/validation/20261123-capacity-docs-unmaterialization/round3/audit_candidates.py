import os, pathlib, subprocess, json, hashlib, stat, datetime, collections
ROOT=pathlib.Path("/mnt/development/projects")
OUT=ROOT/"diagnostics/completed-worktree-docs-capacity-round3-20261123"
BASE=ROOT/"worktrees/anytype-swift-shared-20261121"
EXPECTED_BASE="e7fd39b763d3d0244996c207552096f169de85ed"
TARGETS={'anytype-wave15-sdk06-quiescence-20261123': '3641a01b04e31592476aea6429a637003f4861f3', 'anytype-wave15-original-products-workflows-20261123': 'fe54c73de19e104b641318899985513295302bac', 'anytype-wave15-release-original-products-20261123': '05045b0d51a3afe3ca221a41e19b7fa45a5167e7', 'anytype-wave15-sdk06-selector-continuation-20261123': '5d5de0c7c7baa01f2ae69b05cec38da3ec698eb3', 'anytype-wave15-inline-cleanup-20261123': 'daa0bb8cd15966807403834b63fcc750ffc02ffa', 'anytype-wave15-release-cleanup-20261123': '643d33dff1f7a933385b5784e67738846d00795e', 'anytype-wave15-semantic-apple-consumer-20261123': '4aefb6e429afe27414597e9a8c1b01f5a1506bb6', 'anytype-wave15-sdk06-enumeration-runtime-20261123': '8e2600111a0bf8903b417780d2cd42529cd1c200', 'anytype-wave15-inline-apple-controller-20261123': 'e408c4c761799a88028de461058499d1ae107b4b', 'anytype-wave15-sdk06-enumeration-20261123': '5a0f79b25e4d7c68c4485e697209f0e0191df58a', 'anytype-wave15-nativeui-20261123': 'd8882e926aabca21117c24ee460ed1d40de5bfb9', 'anytype-wave15-original-ui-export-v2-20261123': 'a27a0a6cb02fcbc2cc15ee1a96b654d6cb71ff63', 'anytype-wave15-hanlin-observer-20261123': 'be938dd8d860b4be3b8c8a407ba8cd22ed9a3f40', 'anytype-wave15-original-ui-export-20261123': '59d87891d7235429187599bd02d7ed8178ea8c22'}

def git(w,*a):
 return subprocess.run(["git","--no-optional-locks","-C",str(w),*a],capture_output=True,check=True).stdout
def sha(b):return hashlib.sha256(b).hexdigest()
def tree(w):
 out={}
 for r in git(w,"ls-tree","-r","-z","HEAD","--","docs").split(b"\0"):
  if not r:continue
  h,p=r.split(b"\t",1); mode,kind,oid=h.decode().split()
  out[p.decode()]={"mode":mode,"kind":kind,"oid":oid}
 return out
def snapshot(p):
 s=p.lstat()
 return {"dev":s.st_dev,"inode":s.st_ino,"uid":s.st_uid,"gid":s.st_gid,"mode":stat.S_IMODE(s.st_mode),"size":s.st_size,"allocated":s.st_blocks*512,"nlink":s.st_nlink,"mtime_ns":s.st_mtime_ns}
def verify_file(p,meta):
 s=snapshot(p)
 assert stat.S_ISREG(p.lstat().st_mode) and s["uid"]==1001 and s["nlink"]==1,(str(p),"type/owner/link")
 assert meta["kind"]=="blob" and meta["mode"] in ["100644","100755"],str(p)
 b=p.read_bytes()
 assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==meta["oid"],(str(p),"git-bytes")
 assert snapshot(p)==s,(str(p),"changed-during-read")
 assert bool(s["mode"]&0o111)==(meta["mode"]=="100755"),(str(p),"mode")
 return {**s,"sha256":sha(b)}
assert git(BASE,"rev-parse","HEAD").decode().strip()==EXPECTED_BASE
old_audit=ROOT/"diagnostics/completed-worktree-docs-capacity-review-20261123"
prior_rows=json.loads((old_audit/"candidates.json").read_bytes())+json.loads((old_audit/"additional-inline-evidence/candidates.json").read_bytes())+json.loads((ROOT/"diagnostics/completed-worktree-docs-capacity-extension-20261123/candidates.json").read_bytes())
prior={(x["worktree"],x["path"]) for x in prior_rows}
assert len(prior)==24207
def verify_previous_absence():
 for name,p in prior:
  assert not (ROOT/"worktrees"/name/p).exists(), (name,p,"old exclusion changed")
verify_previous_absence()
base_tree=tree(BASE)
base_verified={}
candidate_rows=[]
retained_rows=[]
worktrees=[]
for name,head in TARGETS.items():
 w=ROOT/"worktrees"/name
 assert git(w,"rev-parse","HEAD").decode().strip()==head
 before=git(w,"status","--porcelain","--untracked-files=all")
 assert before==b"", (name,"nonclean")
 t=tree(w)
 wp=[]
 for p,meta in t.items():
  f=w/p
  if (name,p) in prior:
   assert not f.exists(), (name,p,"prior exclusion materialized")
   continue
  if meta!=base_tree.get(p) or not f.exists():
   retained_rows.append({"worktree":name,"path":p,"git":meta,"reason":"not exact baseline documentation"})
   continue
  a=verify_file(f,meta)
  if p not in base_verified:base_verified[p]=verify_file(BASE/p,meta)
  b=base_verified[p]
  assert a["sha256"]==b["sha256"] and (a["dev"],a["inode"])!=(b["dev"],b["inode"])
  row={"worktree":name,"path":p,"git":meta,**a,"protected_copy_path":str(BASE/p),"protected_copy_sha256":b["sha256"]}
  candidate_rows.append(row); wp.append(row)
 gitfile=(w/".git").read_bytes()
 gd=pathlib.Path(gitfile.decode().strip().removeprefix("gitdir: "))
 assert gd.is_dir()
 index=gd/"index"
 sparse=gd/"info/sparse-checkout"
 worktrees.append({"name":name,"path":str(w),"head":head,"branch":git(w,"symbolic-ref","HEAD").decode().strip(),"clean_before":True,"gitfile_sha256":sha(gitfile),"gitdir":str(gd),"index_sha256":sha(index.read_bytes()),"sparse_file_exists":sparse.exists(),"sparse_file_sha256":sha(sparse.read_bytes()) if sparse.exists() else None,"candidate_count":len(wp),"candidate_allocated_bytes":sum(x["allocated"] for x in wp),"candidate_logical_bytes":sum(x["size"] for x in wp),"retained_nonbaseline_docs":sum(x["worktree"]==name for x in retained_rows)})
 assert git(w,"status","--porcelain","--untracked-files=all")==before
prefixes=[str(ROOT/"worktrees"/n) for n in TARGETS]
refs=[]; denied=collections.Counter(); vanished=0; scanned=0
def inspect(kind,p,pid,readlinks=False):
 global vanished
 try:
  data=os.readlink(p) if readlinks else p.read_bytes().decode("utf-8","surrogateescape")
 except PermissionError:denied[kind]+=1;return
 except (FileNotFoundError,ProcessLookupError):vanished+=1;return
 except OSError:return
 matched=[x for x in prefixes if x in data]
 if matched:refs.append({"pid":int(pid),"surface":kind,"matched_owned_roots":matched})
for p in pathlib.Path("/proc").iterdir():
 if not p.name.isdigit():continue
 scanned+=1
 for name in ["cwd","exe"]:inspect(name,p/name,p.name,True)
 for name in ["cmdline","maps","environ"]:inspect(name,p/name,p.name)
 try:
  for fd in (p/"fd").iterdir():inspect("fd",fd,p.name,True)
 except PermissionError:denied["fd-directory"]+=1
 except FileNotFoundError:vanished+=1
def save(name,obj):
 raw=(json.dumps(obj,sort_keys=True,separators=(",",":"))+"\n").encode()
 q=OUT/name
 with q.open("xb") as f:f.write(raw)
 return {"path":str(q),"sha256":sha(raw),"bytes":len(raw)}
c=save("candidates.json",candidate_rows)
r=save("retained-nonbaseline-docs.json",retained_rows)
b=save("protected-original-baseline.json",{"worktree":str(BASE),"head":EXPECTED_BASE,"entries":base_verified})
p=save("process-observation.json",{"uid":os.getuid(),"scanned_pids":scanned,"matching_references":refs,"permission_denied_by_surface":dict(denied),"vanished_surfaces":vanished,"complete_root_process_proof":False,"fresh_sudo_scan_required_before_change":True})
v=os.statvfs("/mnt/development")
review={"status":"READ_ONLY_CANDIDATE_PLAN_NO_UNMATERIALIZATION","captured_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"worktrees":worktrees,"candidates":c,"retained_new_or_changed_documentation":r,"protected_baseline_copies":b,"accessible_process_observation":p,"total_count":len(candidate_rows),"total_allocated_bytes":sum(x["allocated"] for x in candidate_rows),"total_logical_bytes":sum(x["size"] for x in candidate_rows),"free_bytes":v.f_bavail*v.f_frsize,"mutations_to_worktrees":0,"proof":"Every proposed file is byte-identical to its tracked Git blob and an independently hashed materialized protected original baseline file at a distinct inode. All new/changed documentation, source code, external originals, Git objects, refs and registrations are outside the candidate set.","proposed_action":"Root-reviewed reversible non-cone sparse exclusion of only exact admitted paths; never git clean/worktree removal or deletion of original baseline. Save per-worktree config/sparse/index metadata before any change. Restore exact materialization from pinned Git HEAD without network. Root must verify inactive ownership and fresh sudo process absence first.","remaining_limitations":["No mutation is authorized by this receipt alone; root owns action.","Accessible-user proc scan does not replace fresh privileged scan.","This keeps every worktree registration/source/branch and exact baseline documentation physically present; only redundant materializations are candidates.","Candidate allocation excludes directory blocks."]}
verify_previous_absence()
review["prior_24207_exclusions_absent_before_and_after"]=True
review["previous_reclaim_receipt_sha256"]="454aff89cebd3dc11fd815d6f8e39a4b79f8491e3a2a6d547e221432ebd36e7d"
review["excluded_active_or_audited_worktrees"]=["coherent-kernel", "shared", "mounted", "sdk-tagged", "census", "original-e7"]
review["scope"]="Only currently materialized exact baseline documentation in the fourteen completed prior-phase worktrees, excluding every current writer and all source/Products paths"
q=save("review.json",review)
print(json.dumps({"review":q,"total_count":review["total_count"],"total_allocated_bytes":review["total_allocated_bytes"],"free_bytes":review["free_bytes"],"worktrees":worktrees,"matching_refs":len(refs),"permission_denied":dict(denied)}))
