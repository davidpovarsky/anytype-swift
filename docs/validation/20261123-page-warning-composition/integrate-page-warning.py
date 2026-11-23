import pathlib,subprocess,json,hashlib,shutil
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/page-warning-composition-20261123')
BASE='5f21049dc223d70a8408c84ca9a1e45fe6ea3f78'
DONOR='9d5749b618b287ba9420e797fa88012bb46dd5cb'
DONOR_BASE='856130b141ce29e5095effe80a04e6108b7995f3'
DOC='docs/validation/20261123-page-warning-composition'
CHAIN=['f28c68d88d776a052522cf3f8c8b597bf4fb5ce5','e6578312b3939cf4880ca8a70c3283f3041f3e39','af4728c2d118b445d1447fbb2bf2d2a34f90236d','3bd1f5c44c60fabda849b915f81729ef5f801c66',DONOR]
def git(*args):
 return subprocess.check_output(['git','-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','-C',str(W),*args],timeout=60)
def save(p,v):
 with p.open('xb') as o:o.write((json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def tree(ref):
 result={}
 for row in git('ls-tree','-r','-z',ref).split(b'\0'):
  if row:
   m,n=row.split(b'\t',1);result[n.decode()]=m.decode()
 return result
assert shutil.disk_usage(W).free>=2520000000
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain=v1')
assert git('rev-list','--reverse',DONOR_BASE+'..'+DONOR).decode().splitlines()==CHAIN
qname='docs/validation/20261123-semantic-page-startup-warning/qualification.json'
raw=git('show',DONOR+':'+qname)
assert hashlib.sha256(raw).hexdigest()=='6e0a0975e4c83d971b9eecd4885a1b45526f496c52ba0cfa23a49d9e72f15447'
q=json.loads(raw)
assert q['actual']['methods_passed']==1 and q['actual']['subcases_passed']==7 and q['actual']['source_and_loaded_before_after_equal'] is True
for row in q['copies']:
 b=git('show',DONOR+':'+row['copy'])
 assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256']
before=tree(BASE);donor=tree(DONOR);donor_base=tree(DONOR_BASE)
changed={p for p in set(donor)|set(donor_base) if donor.get(p)!=donor_base.get(p)}
assert all(p.startswith(('docs/validation/20261123-semantic-page-startup-warning/','Tools/PinkhaSemanticAnchorWire/apple_mounted/')) or p=='PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift' for p in changed)
save(D/'intent.json',{'base':BASE,'donor':DONOR,'commits':CHAIN,'changed_paths':sorted(changed),'old_tests_replayed':0,'new_builds':0})
git('cherry-pick',*CHAIN)
composed=git('rev-parse','HEAD').decode().strip();current=tree('HEAD')
assert all(current.get(p)==donor.get(p) for p in changed)
assert all(current.get(p)==row for p,row in before.items() if p not in changed)
old_name='.github/workflows/pinkha-semantic-page-apple-mounted.yml'
new_name='.github/workflows/pinkha-semantic-page-startup-warning.yml'
workflow=(W/old_name).read_text()
substitutions=[
('name: Run mounted Page154 selection and cold reopen from original Products','name: Continue Page154 through the native startup warning with a new UI-only runner'),
('  original-products-mounted:\n','  startup-warning-mounted:\n'),
('      - name: Execute one new preparation and the actual mounted Cancel Create reopen journey','      - name: Build only the corrected UI runner and recreate the necessary fixture for the failed journey'),
('            --work "$ATTEMPT/work" --evidence "$ATTEMPT/artifact/evidence" \\\n','            --work "$ATTEMPT/work" --evidence "$ATTEMPT/artifact/evidence" --startup-warning-ui \\\n'),
('          name: Pinkha-Semantic-Page-Mounted-','          name: Pinkha-Semantic-Page-Startup-Warning-')]
for a,b in substitutions:
 assert workflow.count(a)==1
 workflow=workflow.replace(a,b,1)
assert not (W/new_name).exists()
(W/new_name).write_text(workflow)
central_name='.github/workflows/torah-inspector-ipados27.yml'
central=(W/central_name).read_text()
route_edits=[
('          - semantic-page-apple-mounted\n','          - semantic-page-apple-mounted\n          - semantic-page-startup-warning\n'),
('  semantic-page-apple-mounted:\n','  semantic-page-startup-warning:\n    if: '+chr(36)+"{{ inputs.route == 'semantic-page-startup-warning' }}\n    uses: ./.github/workflows/pinkha-semantic-page-startup-warning.yml\n\n  semantic-page-apple-mounted:\n")]
for a,b in route_edits:
 assert central.count(a)==1
 central=central.replace(a,b,1)
(W/central_name).write_text(central)
doc=W/DOC;doc.mkdir(parents=True)
record={'status':'SOURCE_COMPOSED_QUALIFIED_NEW_HOST_CONTROL_RETAINED_APPLE_NOT_RUN','base':BASE,'donor':DONOR,'composed_donor_head':composed,'qualification_sha256':hashlib.sha256(raw).hexdigest(),'preserved_donor_paths':len(changed),'all_other_baseline_paths_unchanged':True,'new_workflow':new_name,'workflow_literal_derivation':substitutions,'central_literal_edits':route_edits,'route':'semantic-page-startup-warning','actual_retained_new_host_methods':1,'actual_retained_new_host_subcases':7,'host_controls_replayed_now':0,'native_app_builds_to_execute':0,'new_ui_runner_builds_to_execute':1,'fresh_preparation_setup_invocations':1,'new_preparation_acceptance_credit':0,'failed_ui_methods_to_execute':1,'original_app_source':'68148339c275268795360d71d519a5baf003adf8','source_integrator_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'pre_authoring_template_failure':{'kind':'local JavaScript parse error before remote call','remote_mutations':0}}
save(doc/'qualification.json',record)
(doc/'integrate-page-warning.py').write_bytes(pathlib.Path(__file__).read_bytes())
git('add','--',new_name,central_name,DOC)
git('commit','-m','Compose qualified Page startup warning continuation over original App')
head=git('rev-parse','HEAD').decode().strip();after=tree(head)
newpaths={p for p in after if p not in before}
allowed=set(changed)|{new_name,central_name}|{p for p in after if p.startswith(DOC+'/')}
assert all(after.get(p)==row for p,row in before.items() if p not in allowed)
assert all(p in allowed for p in newpaths)
assert not git('status','--porcelain=v1')
gate={'status':'PASS_SOURCE_RETENTION_BEFORE_DISPATCH','head':head,'base':BASE,'donor':DONOR,'route':'semantic-page-startup-warning','changed_paths':sorted(p for p in set(before)|set(after) if before.get(p)!=after.get(p)),'reviewed_new_paths':sorted(newpaths),'original_qualified_source_and_receipts_preserved':True,'tests_executed_during_integration':0,'builds_executed_during_integration':0,'free_bytes':shutil.disk_usage(W).free}
assert gate['free_bytes']>=2500000000
save(D/'source-retention-before-dispatch.json',gate)
gate['gate_sha256']=hashlib.sha256((D/'source-retention-before-dispatch.json').read_bytes()).hexdigest()
save(D/'integration-result.json',gate)
print(json.dumps(gate))
