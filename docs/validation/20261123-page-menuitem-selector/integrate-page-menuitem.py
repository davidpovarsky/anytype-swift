import pathlib,subprocess,json,hashlib,os,shutil,datetime
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
R=W.parent/'anytype-wave15-page-menuitem-selector-20261123'
D=pathlib.Path('/mnt/development/projects/diagnostics/page-menuitem-selector-composition-20261123')
E=pathlib.Path('/mnt/development/projects/diagnostics/page-menu-selector-45222136118-attempt1-result-20261123')
BASE='283c1eb7e7dd42b47f4f91f9a0e1f7ec4dfbfdba';DONOR='1ab4f822cce0be54d10b391967e85c7471d68591'
DOC='docs/validation/20261123-page-menuitem-selector'
UI='PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift'
PLAN='Tools/PinkhaSemanticAnchorWire/apple_mounted/warning-ui-inputs.json'
PROFILE='Tools/PinkhaSemanticAnchorWire/apple_mounted/warning_profile.py'
EXPECTED={UI:'711cfe8660bdb315a2b40d85e67a41ba79d846303a93d2a7460c77d8e0cd99a1',PLAN:'d7f2a98ce38d338092af814f075c2fd02ada145bdb5e4e4f57aa82da36527f49',PROFILE:'fa561fa2823047cd92177920779dbebc0ced35d3fce9869773b05a374932adbf'}
def sha(b):return hashlib.sha256(b).hexdigest()
def git(root,*args):return subprocess.check_output(['git','-C',str(root),'-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com',*args],timeout=30)
def save(p,b):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==b
 return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def dump(p,v):return save(p,(json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
assert shutil.disk_usage(W).free>=1024**3+8*1024**2
assert git(W,'rev-parse','HEAD').decode().strip()==BASE and git(W,'status','--porcelain')==b''
assert git(R,'rev-parse','HEAD').decode().strip()==DONOR and git(R,'status','--porcelain')==b''
q=(R/DOC/'source-qualification.json').read_bytes();assert sha(q)=='1f3c2cafbc5cacb4a378ad6d63a676d691579072332af75b49bf90f2bf8de5a6'
qualification=json.loads(q)
assert qualification['status']=='SOURCE_REPAIR_PEER_REVIEWED'
assert qualification['source_inputs'][UI]['source_commit']=='f0d9d76ef886e86eb4e367319ecd4cd878623f16'
for p,h in EXPECTED.items():assert sha((R/p).read_bytes())==h
assert sha((E/'audit1/mirror.json').read_bytes())=='e6c2fcd2d74c4949a7f23641f7168e4381a9bdb36cf4dfb5caa8019e0a252815'
mirror=json.loads((E/'audit1/mirror.json').read_bytes());assert mirror['status']=='PASS_BYTE_EXACT_READBACK' and len(mirror['files'])==59
for row in mirror['files']:
 b=(E/'audit1'/row['name']).read_bytes();assert len(b)==row['bytes'] and sha(b)==row['sha256']
audit=(E/'audit1/v2/audit-result.json').read_bytes();assert sha(audit)=='689859142658a2d306a253ae327feab46fdceb69ed61d8b2a0cfa697735ff7f2'
a=json.loads(audit);assert a['status']=='PASS_ORIGINAL_FAILURE_AUDIT' and a['actual_results']['ui']['fail']==1
assert len(a['commands'])==25 and a['unavailable_original_command_stream']['status']=='NOT_INCLUDED_IN_PUBLISHED_ARTIFACT'
binding=(E/'git-input-bindings.json').read_bytes();assert sha(binding)=='fc307d64866b7f1181cd9512b9585584be75e1b4a113d4c9961601802a4e1892'
files=[('original-failure-audit.json',audit),('first-audit-failure.json',(E/'audit1/v1/audit-result.json').read_bytes()),('original-git-bindings.json',binding),('original-custody-index.json',(E/'audit1/mirror.json').read_bytes()),('audit-original.py',(E/'audit-original.py').read_bytes()),('audit-original-continuation.py',(E/'audit-original-continuation.py').read_bytes()),('integrate-page-menuitem.py',pathlib.Path(__file__).read_bytes())]
copied={}
for name,b in files:copied[name]=save(R/DOC/name,b)
summary={'schema':'page154-menuitem-integration-evidence-v1','status':'QUALIFIED_SOURCE_WITH_ORIGINAL_FAILURE_RETAINED','reviewed_donor':DONOR,'candidate_runtime_source_commit':'f0d9d76ef886e86eb4e367319ecd4cd878623f16','source_qualification_sha256':sha(q),'original_audit_sha256':sha(audit),'original_mirror_files':59,'original_mirror_bytes':mirror['bytes'],'original_mirror_sha256':sha((E/'audit1/mirror.json').read_bytes()),'independent_git_binding_sha256':sha(binding),'runtime_paths':EXPECTED,'copied_evidence':copied,'retained_failures':['Original UI journey: menu-action-ambiguous, zero menu taps.','First audit guard omitted the actual UITargetAppPath; failed receipt preserved.','First source metadata named the base for the candidate UI hash; corrected in a separate evidence-only commit.'],'limitations':['One original download progress stream was not included in the published artifact; command/kernel record remains.','No current UI acceptance has yet run.','Physical iPad acceptance has not run.'],'new_tests':0,'new_builds':0}
dump(R/DOC/'integration-evidence.json',summary)
git(R,'add','--',DOC);git(R,'commit','-m','docs(page154): retain original menu failure and integration evidence')
head=git(R,'rev-parse','HEAD').decode().strip();assert git(R,'status','--porcelain')==b''
changed=git(W,'diff','--name-only',BASE,head).decode().splitlines()
assert set(p for p in changed if not p.startswith(DOC+'/'))==set(EXPECTED)
git(W,'merge','--ff-only',head)
assert git(W,'rev-parse','HEAD').decode().strip()==head and git(W,'status','--porcelain')==b''
for p,h in EXPECTED.items():assert sha((W/p).read_bytes())==h and (W/p).read_bytes()==git(W,'show',head+':'+p)
sdk='Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json'
raw=(W/sdk).read_bytes();assert sha(raw)=='8d3045bc1dbe2f943b73b26e5d92c57f5523a9d3771d0800b6689040df889987'
contract=json.loads(raw);assert len(contract['inputs'])==82 and not set(EXPECTED)&set(contract['inputs'])
ls=git(W,'ls-tree','-r',head,'--',*contract['inputs']).decode().splitlines()
tree={line.split('\t',1)[1]:line.split('\t',1)[0] for line in ls}
for p,row in contract['inputs'].items():
 assert set(row)=={'git_mode','sha256'}
 b=(W/p).read_bytes();assert sha(b)==row['sha256'] and b==git(W,'show',head+':'+p)
 assert tree[p].split()[0]==row['git_mode']
 assert bool((W/p).stat().st_mode&0o111)==(row['git_mode']=='100755')
gate={'protocol':'page154-menuitem-root-source-gate-v1','status':'PASS_SOURCE_GATE','base':BASE,'reviewed_donor':DONOR,'publishedCandidate':head,'runtime_paths':EXPECTED,'changed_paths':changed,'original_failure_audit_sha256':sha(audit),'source_qualification_sha256':sha(q),'original_git_bindings_sha256':sha(binding),'sdk_contract_sha256':sha(raw),'sdk_inputs_unchanged':82,'heavy_execution_gates_changed':False,'tests_replayed':0,'new_builds':0,'current_product_acceptance':'NOT_RUN','physical_ipad':'NOT_RUN','free_final':shutil.disk_usage(W).free,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
receipt=dump(D/'source-retention-before-dispatch.json',gate)
dump(D/'source-gate-seal.json',{'status':'PASS_SOURCE_GATE','publishedCandidate':head,'sourceGateSHA256':receipt['sha256']})
print(json.dumps({'status':'PASS_SOURCE_GATE','head':head,'gate':receipt,'changed_paths':len(changed),'sdk_inputs_unchanged':82,'free_final':gate['free_final']}))
