from pathlib import Path
import ast,copy,datetime,hashlib,json,os,subprocess
import yaml
base=Path('/mnt/development/projects');root=base/'worktrees/anytype-wave15-shared-20261123';diag=base/'diagnostics/sdk-ui-page-composition-20261123'
HEAD='64ffab92a48c61956816890b9206271c3ea909a5';BASE='c0c1f851f80322c9f532e86505047498dfaf1adf';PAGE='a513821699ff0ed5fc032b71ff91f56027bdef8b'
doc=root/'docs/validation/20261123-sdk-ui-page-composition'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(root),*a],timeout=30)
def blob(ref,p):return git('show',ref+':'+p)
def save(path,value):
 with path.open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
assert git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain')
s=os.statvfs(base);assert s.f_bavail*s.f_frsize>=2_500_000_000+16*1024**2
receipt=base/'evidence/page-source-origins-20261123/attempt1/receipt.json'
b=receipt.read_bytes();assert sha(b)=='77988c8ceb40604051788c0ead492059e5f0a152f558d5def4b99f8eb8e3231c'
r=json.loads(b);assert r['status']=='PASS' and r['frozen_head']==PAGE and r['tests_run']==r['actual_named_passes']==2
cmd=['git','-c','gc.auto=0','-C',str(root),'cherry-pick','--no-commit','aa82f2dced586274fa2e02f8eb5736e0ef7e6619',PAGE]
p=subprocess.run(cmd,capture_output=True,timeout=120)
for n,b in [('page-cherry-pick.stdout',p.stdout),('page-cherry-pick.stderr',p.stderr)]:
 with (diag/n).open('xb') as f:f.write(b)
save(diag/'page-cherry-pick-command.json',{'argv':cmd,'exit':p.returncode})
assert p.returncode==0,p.stderr.decode()
central='.github/workflows/torah-inspector-ipados27.yml';pin='Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json'
before=(root/central).read_bytes();original_pin=(root/pin).read_bytes()
assert sha(before)=='5f6e22ff33548aa098499ed8428f7b4ff0581347930c076b71a06155da971d1f'
assert sha(original_pin)=='cffb659acfc7758ec268d76edc0cf4f28e5c179fecdc3c58107cc590a4331917'
patch=root/'docs/validation/20261123-native-ui-transition-candidate/central-route.patch'
assert sha(patch.read_bytes())=='b8db6fa42ff1c9002b9cf785b891d0d87ad7cb566a568f93e23858fb92aa2870'
subprocess.run(['git','apply','--check',str(patch)],cwd=root,check=True,capture_output=True)
subprocess.run(['git','apply',str(patch)],cwd=root,check=True,capture_output=True)
after=(root/central).read_bytes()
addition1=b'          - native-ui-transition-candidate\n'
addition2=b"\n  native-ui-transition-candidate:\n    if: "+b"$"+b"{{ inputs.route == 'native-ui-transition-candidate' }}\n    uses: ./.github/workflows/pinkha-any-native-ui-transition-candidate.yml\n"
assert after.count(addition1)==after.count(addition2)==1
assert after.replace(addition1,b'',1).replace(addition2,b'',1)==before
old=yaml.load(blob(BASE,central),Loader=yaml.BaseLoader);new=yaml.load(after,Loader=yaml.BaseLoader)
new_routes={'sdk06-original-native-continuation','native-ui-transition-candidate'}
assert set(new['jobs'])-set(old['jobs'])==new_routes
assert all(new['jobs'][k]==v for k,v in old['jobs'].items())
old_options=old['on']['workflow_dispatch']['inputs']['route']['options']
new_options=new['on']['workflow_dispatch']['inputs']['route']['options']
assert [x for x in new_options if x not in new_routes]==old_options
assert set(new_options)-set(old_options)==new_routes and len(new_options)==len(set(new_options))
for name in new_routes:
 j=new['jobs'][name];assert j['if']=="$"+"{{ inputs.route == '"+name+"' }}"
 assert (root/j['uses'].removeprefix('./')).is_file()
changed=original_pin.replace(sha(before).encode(),sha(after).encode())
assert original_pin.count(sha(before).encode())==1
x=json.loads(original_pin);y=json.loads(changed);assert y['inputs'][central]['sha256']==sha(after)
back=copy.deepcopy(y);back['inputs'][central]['sha256']=sha(before);assert back==x
assert changed.replace(sha(after).encode(),sha(before).encode(),1)==original_pin
(root/pin).write_bytes(changed)
for path,row in y['inputs'].items():
 raw=(root/path).read_bytes();assert sha(raw)==row['sha256'],path
 assert bool((root/path).stat().st_mode&0o111)==(row['git_mode']=='100755')
helper='Tools/PinkhaSimulatorGate/shared_editor_existing_build.py'
def functions(raw):
 text=raw.decode();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)}
a=functions(blob(PAGE,helper));z=functions((root/helper).read_bytes())
assert set(a)==set(z) and {n for n in a if a[n]!=z[n]}=={'execute'}
page_consumer=blob(PAGE,'Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py').decode()
assert 'shared_editor_existing_build.execute' not in page_consumer
ui_comp=json.loads((root/'docs/validation/20261123-native-ui-transition-candidate/runtime-composition.json').read_bytes())
for path,row in ui_comp['retained_direct_runtime_helpers'].items():assert sha((root/path).read_bytes())==row['sha256'],path
doc.mkdir()
with (doc/'sdk-runtime-contract-tested-original.json').open('xb') as f:f.write(original_pin)
with (doc/'central-workflow-before-ui-route.yml').open('xb') as f:f.write(before)
report={'schema':'sdk-ui-page-current-source-composition/v1','createdAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'priorMain':HEAD,'pageSource':PAGE,'pageControlReceiptSHA256':sha(receipt.read_bytes()),'central':{'path':central,'sdkQualifiedSHA256':sha(before),'composedSHA256':sha(after),'uiAdditiveWholeInverse':True,'newRoutes':sorted(new_routes),'originalJobsPreserved':len(old['jobs']),'currentJobs':len(new['jobs']),'allOriginalOptionsRetainedInOrder':True},'sdkContract':{'path':pin,'testedSHA256':sha(original_pin),'composedSHA256':sha(changed),'onlyJSONChange':['inputs',central,'sha256'],'exactWholeInverse':True,'verifiedActualComposedInputs':len(y['inputs']),'fixedOriginalApp':y['fixed_original_app_source'],'originalAppInputs':y['original_app_members_are_separately_bound']},'pageComposition':{'sharedHelper':helper,'qualifiedBeforeSHA256':sha(blob(PAGE,helper)),'composedSHA256':sha((root/helper).read_bytes()),'onlyChangedFunction':'execute','unchangedOtherFunctions':len(a)-1,'pageUsesChangedFunction':False,'meaning':'Existing reviewed nine SDK-context hunks are inactive on Page caller paths; this is explicit source composition, not a claim of whole-file identity.'},'uiComposition':{'retainedDirectHelpersUnchanged':len(ui_comp['retained_direct_runtime_helpers']),'originalApp':ui_comp['original_app'],'candidateSwiftSHA256':'1d0b0f4a66d4ebfe1af522ef38372525c3ec8c452cc82963fe346e77d0608d72','newHostControlModulesUnchanged':True},'sourceAndEvidenceIntegrationOnly':True,'passingOrOldTestsReplayed':0,'productTestsExecuted':0,'AppOrNativeBuilds':0,'actualCIMacAcceptance':'NOT_RUN_FOR_THIS_COMPOSITION'}
save(doc/'composition.json',report)
subprocess.run(['git','-c','gc.auto=0','add','--',central,pin,doc.relative_to(root).as_posix()],cwd=root,check=True)
assert not git('diff','--name-only')
p=subprocess.run(['git','-c','gc.auto=0','-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','commit','-m','Compose separate Page origin with qualified SDK and UI dispatch routes'],cwd=root,capture_output=True,timeout=60)
for n,b in [('page-route-commit.stdout',p.stdout),('page-route-commit.stderr',p.stderr)]:
 with (diag/n).open('xb') as f:f.write(b)
assert p.returncode==0,p.stderr.decode()
assert not git('status','--porcelain')
result={'status':'PASS','head':git('rev-parse','HEAD').decode().strip(),'compositionSHA256':sha((doc/'composition.json').read_bytes()),'centralSHA256':sha(after),'sdkContractSHA256':sha(changed),'sourceGate':'PENDING_FINAL_EVIDENCE_SEAL','testsExecuted':0,'freeBytes':os.statvfs(base).f_bavail*os.statvfs(base).f_frsize}
save(diag/'page-route-composition-result.json',result);print(json.dumps(result))
