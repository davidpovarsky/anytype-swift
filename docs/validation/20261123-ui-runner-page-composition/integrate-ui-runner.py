import pathlib,subprocess,json,hashlib,shutil
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/ui-runner-page-composition-20261123')
BASE='0037ce76f02d7b659a5a655129e0e1331526bd29'
DONOR='83e2c28a71a6e073f0c1062f4da2f88f25e8159a'
DONOR_BASE='f9bc59c0dae72103fbf13525c7adf8d0c4bceb1f'
DOC='docs/validation/20261123-ui-runner-page-composition'
CENTRAL='.github/workflows/torah-inspector-ipados27.yml'
CHAIN=['86de1704c4bf40528de10f6d2a80e6f852a1d0bb','63a6d28f1ceba3758910ca8a46654ce70ebffb0d','9519b240ec658a10aefff69d44a434b379b929d7',DONOR]
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
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain=v1')
assert git('rev-list','--reverse',DONOR_BASE+'..'+DONOR).decode().splitlines()==CHAIN
qname='docs/validation/20261123-native-ui-runner-continuation/qualification.json'
raw=git('show',DONOR+':'+qname)
assert hashlib.sha256(raw).hexdigest()=='d7a2cd0643c94f7e9da738e1b2ff28c90cc09e8716e837d94843cd9a2c45dd1b'
q=json.loads(raw)
assert q['counts']['distinctNewMethodsQualified']==2 and q['counts']['distinctQualifiedSubcases']==25
assert q['counts']['previousPassedNewMethodReplays']==0 and q['sourceProof']['beforeAfterExact']
for row in q['originals']:
 b=git('show',DONOR+':'+row['copy'])
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
before=tree(BASE);donor=tree(DONOR);db=tree(DONOR_BASE)
changed={p for p in set(donor)|set(db) if donor.get(p)!=db.get(p)}
assert all(p.startswith(('docs/validation/20261123-native-ui-runner-continuation/','Tools/AnyEnginePort/')) or p in {CENTRAL,'.github/workflows/pinkha-any-native-ui-runner-continuation.yml'} for p in changed)
expected=(W/CENTRAL).read_text()
edits=[
('          - native-ui-transition-candidate\n','          - native-ui-transition-candidate\n          - native-ui-runner-continuation\n'),
('  coherent-original-products:\n','  native-ui-runner-continuation:\n    if: '+chr(36)+"{{ inputs.route == 'native-ui-runner-continuation' }}\n    uses: ./.github/workflows/pinkha-any-native-ui-runner-continuation.yml\n\n  coherent-original-products:\n")]
for a,b in edits:
 assert expected.count(a)==1
 expected=expected.replace(a,b,1)
save(D/'intent.json',{'base':BASE,'donor':DONOR,'commits':CHAIN,'excluded_baseline':DONOR_BASE,'changed_paths':sorted(changed),'central_literal_edits':edits,'tests_replayed':0,'builds':0})
git('cherry-pick',*CHAIN)
composed=git('rev-parse','HEAD').decode().strip();current=tree('HEAD')
assert (W/CENTRAL).read_text()==expected
assert all(current.get(p)==donor.get(p) for p in changed if p!=CENTRAL)
assert all(current.get(p)==row for p,row in before.items() if p not in changed)
doc=W/DOC;doc.mkdir(parents=True)
record={'status':'QUALIFIED_UI_CONTROLS_COMPOSED_WITH_PAGE_APPLE_EXECUTION_PENDING','base':BASE,'donor':DONOR,'donor_commits':CHAIN,'excluded_baseline':DONOR_BASE,'composed_donor_head':composed,'qualification_sha256':hashlib.sha256(raw).hexdigest(),'source_paths_preserved':len(changed)-1,'all_other_page_and_release_baseline_paths_unchanged':True,'central_literal_edits':edits,'retained_distinct_new_controls':2,'retained_distinct_subcases':25,'original_first_aggregate_failure_preserved':True,'tests_replayed_now':0,'builds_now':0,'ui_route':'native-ui-runner-continuation','ui_apple_builds':0,'ui_failed_methods_to_execute':5,'page_route':'semantic-page-startup-warning','page_new_ui_builds':1,'page_original_app_native_builds':0,'page_fresh_preparation_setup':1,'page_new_preparation_credit':0,'page_failed_journey_to_execute':1,'integrator_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()}
save(doc/'qualification.json',record)
(doc/'integrate-ui-runner.py').write_bytes(pathlib.Path(__file__).read_bytes())
git('add','--',DOC)
git('commit','-m','Seal retained UI runner continuation with qualified Page route')
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
allowed=changed|{p for p in after if p.startswith(DOC+'/')}
assert all(after.get(p)==row for p,row in before.items() if p not in allowed)
assert all(p in allowed for p in set(after)-set(before))
assert not git('status','--porcelain=v1')
gate={'status':'PASS_SOURCE_RETENTION_BEFORE_DISPATCH','head':head,'base':BASE,'remote_before':'5f21049dc223d70a8408c84ca9a1e45fe6ea3f78','donor':DONOR,'routes':['semantic-page-startup-warning','native-ui-runner-continuation'],'changed_paths':sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p)),'prior_page_gate_sha256':'862ae85a0ecaea91cb12835ae1b613a1eda1893aedafafa3d85ecf117e4a5448','all_donor_bytes_and_original_receipts_preserved':True,'all_other_baseline_paths_unchanged':True,'tests_replayed_now':0,'builds_now':0,'free_bytes':shutil.disk_usage(W).free}
assert gate['free_bytes']>=2500000000
save(D/'source-retention-before-dispatch.json',gate)
gate_sha=hashlib.sha256((D/'source-retention-before-dispatch.json').read_bytes()).hexdigest()
save(D/'source-gate-seal.json',{'status':'PASS_SOURCE_GATE','publishedCandidate':head,'sourceGateSHA256':gate_sha})
print(json.dumps({'head':head,'gate_sha256':gate_sha,'changed_count':len(gate['changed_paths']),'status':gate['status'],'free_bytes':gate['free_bytes']}))
