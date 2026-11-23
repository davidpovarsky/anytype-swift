import pathlib,json,hashlib,gzip,os,stat,subprocess,datetime,ast
D=pathlib.Path('/mnt/development/projects/diagnostics/completed-worktree-docs-capacity-review-20261123')
P=D/'root-exact-unmaterialization'; O=D/'root-exact-unmaterialization-resume';O.mkdir(exist_ok=False)
def sha(b):return hashlib.sha256(b).hexdigest()
def save(n,o):(O/n).write_text(json.dumps(o,sort_keys=True,indent=2)+'\n')
def run(w,args):
 r=subprocess.run(['git','-C',str(w)]+args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=45)
 if r.returncode:raise RuntimeError((args,r.stderr.decode(errors='replace')[:1000]))
 return r.stdout
def meta(p):
 s=p.lstat();return {'dev':s.st_dev,'inode':s.st_ino,'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,'nlink':s.st_nlink,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'allocated':s.st_blocks*512}
def snapshot(w,excluded):
 out={}
 for root,dirs,files in os.walk(w,followlinks=False):
  if root==str(w):dirs[:]=[n for n in dirs if n!='.git']
  for n in files:
   p=pathlib.Path(root)/n;rel=p.relative_to(w).as_posix()
   if rel=='.git' or rel in excluded:continue
   out[rel]=meta(p)
  for n in list(dirs):
   p=pathlib.Path(root)/n
   if p.is_symlink():out[p.relative_to(w).as_posix()]={**meta(p),'target':os.readlink(p)};dirs.remove(n)
 return out
plan=json.loads((D/'combined-plan.json').read_text())
assert sha((D/'combined-plan.json').read_bytes())=='04f236ea9752671c8a467b52b8588a776514c4db681bed3b3091211fde2062bc'
proof=json.loads((P/'preflight.json').read_text());assert proof['status']=='EXACT_GIT_AND_DISTINCT_PHYSICAL_ORIGINALS_REVERIFIED'
common=pathlib.Path('/mnt/development/projects/git-mirrors/anytype-swift.git/config');common_bytes=common.read_bytes()
assert sha(common_bytes)==proof['common_config_sha256']
states={};worktrees=[];rows=[]
for key in ('first_review','additional_review'):
 entry=plan[key];b=pathlib.Path(entry['path']).read_bytes();assert sha(b)==entry['sha256'];q=json.loads(b)
 worktrees.extend(q['worktrees']); e=q['candidates'];b=pathlib.Path(e['path']).read_bytes();assert sha(b)==e['sha256'];rows.extend(json.loads(b))
assert len(rows)==12047
protected=json.loads(gzip.decompress((P/'protected-originals-before.json.gz').read_bytes()))
for w in worktrees:
 p=pathlib.Path(w['path']);s=json.loads(gzip.decompress((P/(w['name']+'--before.json.gz')).read_bytes()));states[w['name']]=s
 assert run(p,['rev-parse','HEAD']).decode().strip()==w['head']
 assert run(p,['symbolic-ref','HEAD']).decode().strip()==w['branch']
 assert run(p,['status','--porcelain=v1','--untracked-files=all'])==b''
 assert sha(run(p,['ls-tree','-r','-z','HEAD']))==s['tree_sha256']
 assert sha(run(p,['ls-files','--stage','-z']))==s['index_entries_sha256']
 excluded={r['path'] for r in rows if r['worktree']==w['name']}
 assert snapshot(p,excluded)==s['protected_files']
 for r in [r for r in rows if r['worktree']==w['name']]:
  m=meta(p/r['path']); assert m=={k:r[k] for k in m}
 for rel,b in s['backup'].items():
  f=pathlib.Path(w['gitdir'])/rel
  if rel=='index':continue
  assert f.exists()==b['existed']
  if b['existed']:assert sha(f.read_bytes())==b['sha256']
for p,r in protected.items():assert meta(pathlib.Path(p))==r['metadata']
node=next(n for n in ast.parse((D/'root_apply_exact.py').read_text()).body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=='scanner' for x in n.targets))
scanner=ast.literal_eval(node.value)
old="exclude.add(os.getpid())"
new="""exclude.add(os.getpid())
pp=os.getpid()
while pp>1 and pp not in {-1}:
 exclude.add(pp)
 try:pp=int(pathlib.Path('/proc/'+str(pp)+'/stat').read_text().rsplit(')',1)[1].split()[1])
 except (FileNotFoundError,ValueError):break"""
assert scanner.count(old)==1;scanner=scanner.replace(old,new)
sr=subprocess.run(['sudo','-n','python3','-B','-c',scanner,json.dumps([w['path'] for w in worktrees]),json.dumps([os.getpid()])],capture_output=True,timeout=25)
(O/'process-scan.stdout').write_bytes(sr.stdout);(O/'process-scan.stderr').write_bytes(sr.stderr)
assert sr.returncode==0
scan=json.loads(sr.stdout);assert scan['uid']==0 and not scan['hits'] and not scan['denied'],scan
save('fresh-privileged-process-check.json',scan)
free_before=os.statvfs('/mnt/development').f_bavail*os.statvfs('/mnt/development').f_frsize
results=[]
for w in worktrees:
 p=pathlib.Path(w['path']);g=pathlib.Path(w['gitdir']);s=states[w['name']]
 excluded={r['path'] for r in rows if r['worktree']==w['name']}
 assert snapshot(p,excluded)==s['protected_files'] and common.read_bytes()==common_bytes
 assert run(p,['rev-parse','HEAD']).decode().strip()==w['head']
 assert run(p,['status','--porcelain=v1','--untracked-files=all'])==b''
 def pattern(rel):
  x=rel
  for c in ('\\','*','?','[',']','!'):x=x.replace(c,'\\'+c)
  if x.endswith(' '):x=x[:-1]+'\\ '
  assert '\n' not in x and '\r' not in x
  return '!/'+x
 patterns='/*\n'+'\n'.join(pattern(rel) for rel in sorted(excluded))+'\n'
 run(p,['config','--worktree','core.sparseCheckout','true']);run(p,['config','--worktree','core.sparseCheckoutCone','false'])
 f=g/'info/sparse-checkout';f.parent.mkdir(exist_ok=True);f.write_text(patterns)
 run(p,['read-tree','-mu','HEAD'])
 assert all(not (p/rel).exists() for rel in excluded)
 assert snapshot(p,excluded)==s['protected_files']
 skip={v[2:].decode() for v in run(p,['ls-files','-t','-z']).split(b'\0') if v.startswith(b'S ')}
 assert skip==excluded,(w['name'],len(skip),len(excluded))
 assert sha(run(p,['ls-tree','-r','-z','HEAD']))==s['tree_sha256']
 assert sha(run(p,['ls-files','--stage','-z']))==s['index_entries_sha256']
 assert run(p,['rev-parse','HEAD']).decode().strip()==w['head']
 assert run(p,['symbolic-ref','HEAD']).decode().strip()==w['branch']
 assert run(p,['status','--porcelain=v1','--untracked-files=all'])==b''
 assert common.read_bytes()==common_bytes
 r={'worktree':str(p),'head':w['head'],'branch':w['branch'],'excluded_count':len(excluded),'preserved_file_count':len(s['protected_files']),'patterns_sha256':sha(patterns.encode()),'exact_skip_set':True,'head_branch_tree_and_index_entries_unchanged':True,'all_other_materialized_files_unchanged':True,'clean_after':True,'common_config_unchanged':True}
 results.append(r);save('completed-'+w['name']+'.json',r)
for p,r in protected.items():assert meta(pathlib.Path(p))==r['metadata'];assert sha(pathlib.Path(p).read_bytes())==r['sha256']
free_after=os.statvfs('/mnt/development').f_bavail*os.statvfs('/mnt/development').f_frsize
receipt={'status':'PASS_EXACT_REVERSIBLE_DUPLICATE_DOCS_UNMATERIALIZATION','finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'plan_sha256':sha((D/'combined-plan.json').read_bytes()),'retained_preflight':{'path':str(P/'preflight.json'),'sha256':sha((P/'preflight.json').read_bytes()),'scope':'Full original Git/blob SHA256 and distinct physical-original hashing completed before first scanner rejected its own sudo parent. All original metadata and current Git entries were revalidated before continuation; only scanner ancestry handling changed.'},'first_attempt':'NO_WORKTREE_MUTATION; fresh sudo scan self-parent commandline hit retained verbatim','excluded_files':len(rows),'allocated_bytes_released':sum(r['allocated'] for r in rows),'free_bytes_before':free_before,'free_bytes_after':free_after,'observed_free_delta':free_after-free_before,'worktrees':results,'physical_originals_preserved':len(protected),'source_product_original_files_deleted':0,'worktrees_removed':0,'git_refs_or_objects_removed':0,'common_git_config_unchanged':True,'restoration':'At exact unchanged pinned HEAD and with adequate capacity, run git -c core.sparseCheckout=false -c core.sparseCheckoutCone=false read-tree -mu HEAD; restore each saved config.worktree and info/sparse-checkout bytes, or remove only if absent before. Do not overwrite later legitimate changes with diagnostic index backup.'}
save('receipt.json',receipt);print(json.dumps(receipt,sort_keys=True))
