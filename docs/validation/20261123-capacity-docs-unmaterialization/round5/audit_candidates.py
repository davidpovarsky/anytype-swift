import os, pathlib, subprocess, json, hashlib, stat, datetime, collections, gzip
ROOT=pathlib.Path("/mnt/development/projects")
OUT=ROOT/"diagnostics/completed-worktree-docs-capacity-round5-20261123"
BASE=ROOT/"worktrees/anytype-swift-shared-20261121"
EXPECTED_BASE="e7fd39b763d3d0244996c207552096f169de85ed"
TARGETS={"anytype-swift-acceptance-continuation-20261122":"c8839d7ef090c95197443227e4c51fac471a07e6","anytype-swift-shared-authority-sdk-20261122":"34aa28f0090ddaf88adc884bc73abeb0082734c5","anytype-swift-shared-coherent-heart-20261122":"e630b9b4d54120d6192d86f6418d19eabd642ed9","anytype-swift-shared-combined-release-20261122":"642fb8eb786801e456cfad786e451a5fd5220b3a","anytype-swift-shared-custom-type-ui-20261122":"db12bc847c582292b94f922383610b5ec18788e7","anytype-swift-shared-related-pins-20261122":"32ce579082b12a3d300b47ae01c93e5ac2032772"}

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
base_tree=tree(BASE)
base_verified={}
candidate_rows=[]
retained_rows=[]
worktrees=[]
for name,head in TARGETS.items():
 w=ROOT/"worktrees"/name
 assert git(w,"rev-parse","HEAD").decode().strip()==head
 assert subprocess.run(["git","--no-optional-locks","-C",str(w),"symbolic-ref","-q","HEAD"],capture_output=True,timeout=25).returncode==1, (name,"must remain detached")
 before=git(w,"status","--porcelain","--untracked-files=all")
 assert before==b"", (name,"nonclean")
 t=tree(w)
 wp=[]
 for p,meta in t.items():
  f=w/p
  if meta!=base_tree.get(p) or not f.exists():
   kept={"worktree":name,"path":p,"git":meta,"reason":"not exact baseline documentation","materialized":f.exists()}
   if f.exists(): kept["protected_physical"]=verify_file(f,meta)
   retained_rows.append(kept)
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
 skip=sorted(v[2:].decode() for v in git(w,"ls-files","-t","-z").split(b"\0") if v.startswith(b"S "))
 worktrees.append({"name":name,"path":str(w),"head":head,"branch":None,"detached":True,"head_state":"DETACHED_HISTORICAL_SNAPSHOT","clean_before":True,"gitfile_sha256":sha(gitfile),"gitdir":str(gd),"index_sha256":sha(index.read_bytes()),"current_skip_worktree_paths":skip,"current_skip_worktree_count":len(skip),"current_skip_worktree_sha256":sha((json.dumps(skip,sort_keys=True)+"\n").encode()),"sparse_file_exists":sparse.exists(),"sparse_file_sha256":sha(sparse.read_bytes()) if sparse.exists() else None,"candidate_count":len(wp),"candidate_allocated_bytes":sum(x["allocated"] for x in wp),"candidate_logical_bytes":sum(x["size"] for x in wp),"retained_nonbaseline_docs":sum(x["worktree"]==name for x in retained_rows)})
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
 compressed=name in {"candidates.json","retained-nonbaseline-docs.json","protected-original-baseline.json"}
 payload=gzip.compress(raw,mtime=0) if compressed else raw
 q=OUT/(name+".gz" if compressed else name)
 with q.open("xb") as f:f.write(payload)
 return {"path":str(q),"sha256":sha(payload),"bytes":len(payload),"encoding":"gzip" if compressed else "json","uncompressed_sha256":sha(raw),"uncompressed_bytes":len(raw)}
c=save("candidates.json",candidate_rows)
r=save("retained-nonbaseline-docs.json",retained_rows)
b=save("protected-original-baseline.json",{"worktree":str(BASE),"head":EXPECTED_BASE,"entries":base_verified})
p=save("process-observation.json",{"uid":os.getuid(),"scanned_pids":scanned,"matching_references":refs,"permission_denied_by_surface":dict(denied),"vanished_surfaces":vanished,"complete_root_process_proof":False,"fresh_sudo_scan_required_before_change":True})
v=os.statvfs("/mnt/development")
review={"status":"READ_ONLY_CANDIDATE_PLAN_NO_UNMATERIALIZATION","captured_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"worktrees":worktrees,"candidates":c,"retained_new_or_changed_documentation":r,"protected_baseline_copies":b,"accessible_process_observation":p,"total_count":len(candidate_rows),"total_allocated_bytes":sum(x["allocated"] for x in candidate_rows),"total_logical_bytes":sum(x["size"] for x in candidate_rows),"free_bytes":v.f_bavail*v.f_frsize,"mutations_to_worktrees":0,"proof":"Every proposed file is byte-identical to its tracked Git blob and an independently hashed materialized protected original baseline file at a distinct inode. All new/changed documentation, source code, external originals, Git objects, refs and registrations are outside the candidate set.","proposed_action":"Root-reviewed reversible non-cone sparse exclusion of only exact admitted paths; never git clean/worktree removal or deletion of original baseline. Save per-worktree config/sparse/index metadata before any change. Restore exact materialization from pinned Git HEAD without network. Root must verify inactive ownership and fresh sudo process absence first.","remaining_limitations":["No mutation is authorized by this receipt alone; root owns action.","Accessible-user proc scan does not replace fresh privileged scan.","This keeps every worktree registration/source/branch and exact baseline documentation physically present; only redundant materializations are candidates.","Candidate allocation excludes directory blocks."]}

review["excluded_active_or_audited_worktrees"]=["anytype-wave15-shared-20261123","anytype-wave15-sdk06-tagged-continuation-20261123","anytype-wave15-sdk06-qualified-continuation-20261123","anytype-wave15-native-ui-readiness-20261123","anytype-wave15-coherent-owned-continuation-20261123","anytype-wave15-local-tree-census-20261123","all-native-census-worktrees","anytype-wave15-page154-mounted-admission-20261123","anytype-wave15-ui-qualified-continuation-20261123","anytype-wave15-coherent-kernel-20261123","anytype-swift-shared-20261121"]
review["scope"]="Only exact current materialized e7 baseline documentation in six completed detached historical Anytype snapshots. Every nonbaseline/private doc, all sources/Products/originals/caches, Git objects/registrations, active writers and other projects excluded."
review["source_script"]={"path":str(pathlib.Path(__file__).resolve()),"sha256":sha(pathlib.Path(__file__).read_bytes())}
review["parent_mechanism"]="diagnostics/completed-worktree-docs-capacity-round4-20261123/audit_candidates.py"
q=save("review.json",review)
combined=save("combined-plan.json",{"first_review":q,"total_count":review["total_count"],"total_allocated_bytes":review["total_allocated_bytes"],"apply_authorized_by_this_plan":False,"mutations_to_worktrees":0})
print(json.dumps({"review":q,"combined_plan":combined,"total_count":review["total_count"],"total_allocated_bytes":review["total_allocated_bytes"],"free_bytes":review["free_bytes"],"worktrees":worktrees,"matching_refs":len(refs),"permission_denied":dict(denied)}))
