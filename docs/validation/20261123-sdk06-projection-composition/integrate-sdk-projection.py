import pathlib,subprocess,json,hashlib,shutil
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/sdk06-projection-composition-20261123')
BASE='fa50f627889cd01a73dcdb1762973577e3aebb2b'
DONOR='8ebeda993843835098c7fe3168bde9e99dfec3fe'
DONOR_BASE='5f21049dc223d70a8408c84ca9a1e45fe6ea3f78'
DOC='docs/validation/20261123-sdk06-projection-composition'
QDOC='docs/validation/20261123-sdk06-component-projection'
CHAIN=['4d5f5b36a2db58b906df40a2eec2fd296baf9338',DONOR]
CENTRAL='.github/workflows/torah-inspector-ipados27.yml'
def git(*args):
 return subprocess.check_output(['git','-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','-C',str(W),*args],stderr=subprocess.PIPE,timeout=80)
def save(p,v):
 with p.open('xb') as f:f.write((json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def tree(ref):
 result={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   m,n=row.split(b'\t',1);result[n.decode()]=m.decode()
 return result
assert shutil.disk_usage(W).free>=2520000000
assert git('rev-parse','HEAD').decode().strip()==BASE
assert git('rev-parse','CHERRY_PICK_HEAD').decode().strip()==CHAIN[0]
assert set(git('diff','--name-only','--diff-filter=U').decode().splitlines())=={CENTRAL}
assert hashlib.sha256((W/CENTRAL).read_bytes()).hexdigest()=='7d8f9d5ed6d7a649713aa643284048c34567ce1c46d0c775d3a2a0eb9050c280'
assert git('rev-list','--reverse',DONOR_BASE+'..'+DONOR).decode().splitlines()==CHAIN
raw=git('show',DONOR+':'+QDOC+'/qualification.json')
assert hashlib.sha256(raw).hexdigest()=='1b91a14404e87b17e20eed5cf6637d9f804cd6cff8449daf280710a320847572'
q=json.loads(raw)
assert q['status']=='PASS_PURE_CONTROL_ONLY' and q['control']['actualMethods']==q['control']['actualPasses']==1 and q['control']['actualSubcasesPassed']==24
assert q['counts']=={'builds':0,'oldControlMethodsExecuted':0,'productMethodsExecuted':0,'productionPlanImports':0}
assert q['sourceAdmission']['beforeAfterIdentical'] and q['ownedExecution']['ownedGroupAbsent']
sealraw=git('show',DONOR+':'+q['proof']['originalSeal'])
assert hashlib.sha256(sealraw).hexdigest()==q['proof']['originalSealSHA256']
seal=json.loads(sealraw);assert seal['originalCount']==13 and seal['byteExact']
for row in seal['copies']:
 b=git('show',DONOR+':'+row['copy'])
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
before=tree(BASE);donor=tree(DONOR);db=tree(DONOR_BASE)
changed={p for p in set(donor)|set(db) if donor.get(p)!=db.get(p)}
assert all(p.startswith(('Tools/PinkhaSimulatorGate/',QDOC+'/')) or p in {CENTRAL,'.github/workflows/pinkha-sdk06-projected-components.yml'} for p in changed)
composition=json.loads(git('show',DONOR+':'+QDOC+'/final-source-closure.json'))
expected=git('show',BASE+':'+CENTRAL).decode()
for a,b in composition['central_literal_edits']:
 assert expected.count(a)==1;expected=expected.replace(a,b,1)
assert expected==git('show',DONOR+':'+CENTRAL).decode()
save(D/'recovery-intent.json',{'base':BASE,'donor':DONOR,'commits':CHAIN,'changed_paths':sorted(changed),'verified_original_copies':13,'tests_replayed':0,'builds':0})
(W/CENTRAL).write_text(expected)
git('add','--',CENTRAL)
recovered=subprocess.run(['git','-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','-c','core.editor=true','-C',str(W),'cherry-pick','--continue'],capture_output=True,timeout=100)
(D/'cherry-continue.stdout').write_bytes(recovered.stdout)
(D/'cherry-continue.stderr').write_bytes(recovered.stderr)
assert recovered.returncode==0,recovered.stderr.decode()
assert git('rev-list','--count',BASE+'..HEAD').decode().strip()=='2'
current=tree('HEAD')
assert all(current.get(p)==donor.get(p) for p in changed)
assert all(current.get(p)==row for p,row in before.items() if p not in changed)
contract=json.loads((W/'Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json').read_bytes())
for name,row in contract['inputs'].items():
 b=(W/name).read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'] and git('show','HEAD:'+name)==b
 assert ('100755' if (W/name).stat().st_mode&0o111 else '100644')==row['git_mode']
doc=W/DOC;doc.mkdir(parents=True)
record={'status':'SDK_NEW_PURE_CONTROL_QUALIFIED_APPLE_PENDING','base':BASE,'donor':DONOR,'donor_commits':CHAIN,'qualification_sha256':hashlib.sha256(raw).hexdigest(),'retained_new_control_methods':1,'retained_new_subcases':24,'original_controls_source':q['source'],'verified_original_copies':13,'current_source_contract_sha256':hashlib.sha256((W/'Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json').read_bytes()).hexdigest(),'current_source_inputs_verified':len(contract['inputs']),'production_preloads':len(contract['preload_modules']),'all_other_prior_c_page_ui_release_paths_unchanged':True,'central_exact_donor_and_two_hunk_composition':True,'tests_replayed_now':0,'builds_now':0,'route':'sdk06-projected-components','original_app_native_builds_to_execute':0,'new_component_bundle_builds_to_execute':1,'actual23_32_and_following_sdk_gates':'NOT_RUN','integrator_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
record['first_attempt_failure']={'kind':'one central workflow merge conflict','original_failure_preserved':True,'resolved_from':'exact current baseline plus two reviewed SDK route additions','all_existing_Page_UI_routes_preserved':True}
(doc/'first-cherry-pick-conflict.json').write_bytes((D/'first-cherry-pick-conflict.json').read_bytes())
(doc/'first-integration.stderr').write_bytes((D/'integration.stderr').read_bytes())
save(doc/'qualification.json',record)
(doc/'integrate-sdk-projection.py').write_bytes(pathlib.Path(__file__).read_bytes())
git('add','--',DOC)
git('commit','-m','Compose qualified SDK component projection over retained native lifetime and Apple routes')
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
assert all(after.get(p)==row for p,row in before.items() if p not in changed)
assert all(p in changed or p.startswith(DOC+'/') for p in set(after)-set(before))
assert not git('status','--porcelain=v1')
gate={'status':'PASS_SOURCE_RETENTION_BEFORE_DISPATCH','head':head,'base':BASE,'remote_before':'5fc0a95dc1f8573ff55dfcae1f4ae04c1a7cee33','donor':DONOR,'route':'sdk06-projected-components','changed_paths':sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p)),'new_host_control_retained_methods':1,'new_host_control_retained_subcases':24,'current_source_inputs':82,'all_original_receipts_preserved':True,'other_prior_sources_unchanged':True,'tests_replayed_now':0,'builds_now':0,'free_bytes':shutil.disk_usage(W).free}
assert gate['free_bytes']>=2500000000
save(D/'source-retention-before-dispatch.json',gate)
gate_sha=hashlib.sha256((D/'source-retention-before-dispatch.json').read_bytes()).hexdigest()
save(D/'source-gate-seal.json',{'status':'PASS_SOURCE_GATE','publishedCandidate':head,'sourceGateSHA256':gate_sha})
print(json.dumps({'status':gate['status'],'head':head,'gate_sha256':gate_sha,'changed_paths':len(gate['changed_paths']),'free_bytes':gate['free_bytes']}))
