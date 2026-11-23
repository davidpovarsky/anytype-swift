from __future__ import annotations
import os,sys,json,pathlib,hashlib,stat,subprocess,gzip,datetime
D=pathlib.Path('/mnt/development/projects/diagnostics/completed-worktree-docs-capacity-round4-20261123')
O=D/'root-exact-unmaterialization'; O.mkdir(exist_ok=False)
def sha(b): return hashlib.sha256(b).hexdigest()
def save(n,o):
 b=(json.dumps(o,sort_keys=True,indent=2)+'\n').encode()
 if n.endswith('.gz'): (O/n).write_bytes(gzip.compress(b,mtime=0))
 else: (O/n).write_bytes(b)
 return {'path':str(O/n),'sha256':sha((O/n).read_bytes()),'raw_sha256':sha(b),'raw_bytes':len(b)}
def run(w,args,input=None):
 r=subprocess.run(['git','-C',str(w)]+args,input=input,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
 if r.returncode: raise RuntimeError((str(w),args,r.returncode,r.stderr.decode(errors='replace')[:1000]))
 return r.stdout
def check(p,h):
 b=p.read_bytes(); assert sha(b)==h,str(p);return b
def meta(p):
 s=p.lstat()
 return {'dev':s.st_dev,'inode':s.st_ino,'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'nlink':s.st_nlink,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'allocated':s.st_blocks*512}
def snapshot(w,excluded):
 out={}
 for root,dirs,files in os.walk(w,followlinks=False):
  if root==str(w): dirs[:]=[n for n in dirs if n!='.git']
  for n in files:
   p=pathlib.Path(root)/n; rel=p.relative_to(w).as_posix()
   if rel=='.git' or rel in excluded: continue
   out[rel]=meta(p)
  for n in list(dirs):
   p=pathlib.Path(root)/n
   if p.is_symlink():
    out[p.relative_to(w).as_posix()]={**meta(p),'target':os.readlink(p)}
    dirs.remove(n)
 return out
plan=json.loads(check(D/'combined-plan.json','d05f83fe90be0d4f7998de5be14d4cbac53b0aeac497413e9ba73c8628e67c17'))
worktrees=[];rows=[]
for key in ('first_review',):
 a=plan[key];q=json.loads(check(pathlib.Path(a['path']),a['sha256'])); worktrees.extend(q['worktrees'])
 for k in ('candidates','protected_baseline_copies','retained_new_or_changed_documentation'):
  a=q[k];check(pathlib.Path(a['path']),a['sha256'])
 rows.extend(json.loads(pathlib.Path(q['candidates']['path']).read_text()))
assert len(rows)==13539 and sum(r['allocated'] for r in rows)==585797632
assert len(worktrees)==4
common=pathlib.Path('/mnt/development/projects/git-mirrors/anytype-swift.git/config')
common_bytes=common.read_bytes()
assert run(pathlib.Path(worktrees[0]['path']),['config','--get','extensions.worktreeConfig']).strip()==b'true'
verified_originals={}; states={}; prepared=[]
for w in worktrees:
 p=pathlib.Path(w['path']); mine=[r for r in rows if r['worktree']==w['name']]
 excluded={r['path'] for r in mine}; assert len(excluded)==len(mine)
 assert run(p,['rev-parse','HEAD']).decode().strip()==w['head']
 assert run(p,['symbolic-ref','HEAD']).decode().strip()==w['branch']
 assert run(p,['status','--porcelain=v1','--untracked-files=all'])==b''
 gitdir=pathlib.Path(run(p,['rev-parse','--absolute-git-dir']).decode().strip());assert str(gitdir)==w['gitdir']
 paths=run(p,['ls-files','-t','-z']).split(b'\0')
 assert not [v for v in paths if v.startswith(b'S ')],w['name']
 tree=run(p,['ls-tree','-r','-z','HEAD']); index=run(p,['ls-files','--stage','-z'])
 bypath={}
 for item in tree.split(b'\0'):
  if not item: continue
  header,rel=item.split(b'\t',1);mode,kind,oid=header.decode().split()
  bypath[rel.decode()]={'mode':mode,'kind':kind,'oid':oid}
 for r in mine:
  rel=r['path']; assert rel.startswith('docs/') and '..' not in pathlib.PurePosixPath(rel).parts
  f=p/rel; assert f.is_file() and not f.is_symlink()
  assert meta(f)=={k:r[k] for k in meta(f)},str(f)
  b=check(f,r['sha256']);assert bypath[rel]==r['git']
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==r['git']['oid']
  origin=pathlib.Path(r['protected_copy_path'])
  assert origin.is_relative_to('/mnt/development/projects/worktrees/anytype-swift-shared-20261121/docs')
  assert not origin.is_symlink() and origin.is_file()
  om=meta(origin);assert (om['dev'],om['inode'])!=(r['dev'],r['inode'])
  if str(origin) not in verified_originals:
   ob=check(origin,r['protected_copy_sha256']);assert sha(ob)==r['sha256']
   verified_originals[str(origin)]={'metadata':om,'sha256':sha(ob)}
  else: assert verified_originals[str(origin)]['sha256']==r['sha256']
 before=snapshot(p,excluded); states[w['name']]={'metadata':before,'tree_sha256':sha(tree),'index_entries_sha256':sha(index)}
 backup={}
 for rel in ('config.worktree','info/sparse-checkout','index'):
  f=gitdir/rel
  if f.exists():
   b=f.read_bytes();n=w['name']+'--'+rel.replace('/','_')+'.gz';(O/n).write_bytes(gzip.compress(b,mtime=0))
   backup[rel]={'existed':True,'backup':n,'sha256':sha(b),'bytes':len(b)}
  else: backup[rel]={'existed':False}
 save(w['name']+'--before.json.gz',{'worktree':w,'protected_files':before,'backup':backup,'index_entries_sha256':sha(index),'tree_sha256':sha(tree)})
 def pattern(rel):
  s=rel
  for c in ('\\','*','?','[',']','!'): s=s.replace(c,'\\'+c)
  if s.endswith(' '): s=s[:-1]+'\\ '
  assert '\n' not in s and '\r' not in s
  return '!/'+s
 patterns='/*\n'+'\n'.join(pattern(r) for r in sorted(excluded))+'\n'
 prepared.append((w,p,gitdir,excluded,patterns,backup))
save('protected-originals-before.json.gz',verified_originals)
save('preflight.json',{'status':'EXACT_GIT_AND_DISTINCT_PHYSICAL_ORIGINALS_REVERIFIED','candidate_count':len(rows),'allocated_bytes':sum(r['allocated'] for r in rows),'physical_originals':len(verified_originals),'common_config_sha256':sha(common_bytes),'preserved_non_candidate_files':sum(len(v['metadata']) for v in states.values()),'worktrees':[w['name'] for w in worktrees],'no_mutation_yet':True})
scanner=r"""import pathlib,os,json,sys
targets=json.loads(sys.argv[1]); exclude=set(json.loads(sys.argv[2])); exclude.add(os.getpid())
pp=os.getpid()
while pp>1:
 exclude.add(pp)
 try:pp=int(pathlib.Path('/proc/'+str(pp)+'/stat').read_text().rsplit(')',1)[1].split()[1])
 except (FileNotFoundError,ValueError):break
denied=[];hits=[];seen=0
for d in pathlib.Path('/proc').iterdir():
 if not d.name.isdigit() or int(d.name) in exclude: continue
 pid=int(d.name);seen+=1
 def record(kind,s):
  for t in targets:
   if t in s: hits.append({'pid':pid,'kind':kind,'path':t});break
 for kind in ('cwd','root'):
  try: record(kind,os.readlink(d/kind))
  except (FileNotFoundError,ProcessLookupError):pass
  except PermissionError:denied.append([pid,kind])
 for kind in ('cmdline','maps'):
  try: record(kind,(d/kind).read_bytes().decode(errors='replace'))
  except (FileNotFoundError,ProcessLookupError):pass
  except PermissionError:denied.append([pid,kind])
 try:
  for f in (d/'fd').iterdir():
   try:record('fd',os.readlink(f))
   except (FileNotFoundError,ProcessLookupError):pass
   except PermissionError:denied.append([pid,'fd'])
 except (FileNotFoundError,ProcessLookupError):pass
 except PermissionError:denied.append([pid,'fd-directory'])
print(json.dumps({'uid':os.geteuid(),'processes':seen,'hits':hits,'denied':denied}))
"""
anc=[];pid=os.getpid()
while pid>1 and pid not in anc:
 anc.append(pid)
 try:pid=int(pathlib.Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[1])
 except (FileNotFoundError,ValueError):break
sr=subprocess.run(['sudo','-n','python3','-B','-c',scanner,json.dumps([w['path'] for w in worktrees]),json.dumps(anc)],capture_output=True,timeout=25)
(O/'process-scan.stdout').write_bytes(sr.stdout);(O/'process-scan.stderr').write_bytes(sr.stderr)
assert sr.returncode==0,sr.stderr.decode(errors='replace')
scan=json.loads(sr.stdout);assert scan['uid']==0 and not scan['hits'] and not scan['denied'],scan
save('fresh-privileged-process-check.json',scan)
free_before=os.statvfs('/mnt/development').f_bavail*os.statvfs('/mnt/development').f_frsize
results=[]
for w,p,g,excluded,patterns,backup in prepared:
 assert common.read_bytes()==common_bytes
 assert run(p,['rev-parse','HEAD']).decode().strip()==w['head']
 assert run(p,['status','--porcelain=v1','--untracked-files=all'])==b''
 assert snapshot(p,excluded)==states[w['name']]['metadata']
 # Only per-worktree sparse settings are written; common mirror config is invariant.
 run(p,['config','--worktree','core.sparseCheckout','true'])
 run(p,['config','--worktree','core.sparseCheckoutCone','false'])
 sp=g/'info/sparse-checkout';sp.parent.mkdir(exist_ok=True)
 sp.write_text(patterns)
 raw=run(p,['read-tree','-mu','HEAD'])
 assert all(not (p/rel).exists() for rel in excluded)
 assert snapshot(p,excluded)==states[w['name']]['metadata']
 skip={v[2:].decode() for v in run(p,['ls-files','-t','-z']).split(b'\0') if v.startswith(b'S ')}
 assert skip==excluded,(w['name'],len(skip),len(excluded))
 assert sha(run(p,['ls-tree','-r','-z','HEAD']))==states[w['name']]['tree_sha256']
 assert sha(run(p,['ls-files','--stage','-z']))==states[w['name']]['index_entries_sha256']
 assert run(p,['rev-parse','HEAD']).decode().strip()==w['head']
 assert run(p,['symbolic-ref','HEAD']).decode().strip()==w['branch']
 assert run(p,['status','--porcelain=v1','--untracked-files=all'])==b''
 assert common.read_bytes()==common_bytes
 row={'worktree':w['path'],'head':w['head'],'branch':w['branch'],'excluded_count':len(excluded),'preserved_file_count':len(states[w['name']]['metadata']),'patterns_sha256':sha(patterns.encode()),'exact_skip_set':True,'head_branch_tree_and_index_entries_unchanged':True,'all_other_materialized_files_unchanged':True,'clean_after':True,'common_config_unchanged':True}
 results.append(row);save('completed-'+w['name']+'.json',row)
for p,r in verified_originals.items():
 assert meta(pathlib.Path(p))==r['metadata'];assert sha(pathlib.Path(p).read_bytes())==r['sha256']
free_after=os.statvfs('/mnt/development').f_bavail*os.statvfs('/mnt/development').f_frsize
receipt={'status':'PASS_EXACT_REVERSIBLE_DUPLICATE_DOCS_UNMATERIALIZATION','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_sha256':'d05f83fe90be0d4f7998de5be14d4cbac53b0aeac497413e9ba73c8628e67c17','excluded_files':len(rows),'allocated_bytes_released':sum(r['allocated'] for r in rows),'free_bytes_before':free_before,'free_bytes_after':free_after,'observed_free_delta':free_after-free_before,'worktrees':results,'physical_originals_preserved':len(verified_originals),'source_product_original_files_deleted':0,'worktrees_removed':0,'git_refs_or_objects_removed':0,'common_git_config_unchanged':True,'restoration':'For each exact pinned unchanged worktree, first verify HEAD and clean index. With adequate capacity run git -c core.sparseCheckout=false -c core.sparseCheckoutCone=false read-tree -mu HEAD, then restore saved config.worktree and info/sparse-checkout bytes (or remove only if previously absent). Index object entries remain unchanged; original index backup is diagnostic, not to overwrite later legitimate work.'}
save('receipt.json',receipt)
print(json.dumps(receipt,sort_keys=True))
