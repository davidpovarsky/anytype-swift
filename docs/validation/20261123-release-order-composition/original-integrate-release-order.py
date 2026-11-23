import ast,datetime,hashlib,json,os,pathlib,shutil,subprocess
R=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
D=pathlib.Path('/mnt/development/projects/diagnostics/release-selection-order-composition-20261123')
BASE='856130b141ce29e5095effe80a04e6108b7995f3'
COMMITS=['c853f6b68860f037d014c17cb2d268b8e9c1631a','97563de533579b0705eed0ad0028bdaa944ff470','c9b8d0a8aa784faad389f7a4bf5a702fa7e06ba5','24e3fdaffaf8ad6152a13cc6ca4c7bd8be3d820d']
CALLER='Tools/PinkhaSimulatorGate/run_wave15_acceptance.py'
CONTRACT='Tools/PinkhaSimulatorGate/sdk06-original-native-controller-source.json'
OLD='1d08140358381855e3c143fd48e8b392bc15aeb9fc07a08d51d5390c3afd21d0'
NEW='423bb279972950fc3118c99af948ad846f5507a93823219fd75fb38b1efee2d8'
sha=lambda b:hashlib.sha256(b).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def save(path,value):
 data=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode() if not isinstance(value,bytes) else value
 with path.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
 return {'path':str(path),'sha256':sha(data),'bytes':len(data)}
def git(*args,check=True):
 p=subprocess.run(['git','-c','gc.auto=0','-C',str(R),*args],capture_output=True,timeout=180)
 if check and p.returncode:raise RuntimeError('git failed: '+repr(args)+' '+p.stderr.decode(errors='replace'))
 return p.stdout
def tree(ref):
 out={}
 for line in git('ls-tree','-rz',ref).split(b'\0'):
  if not line:continue
  meta,path=line.split(b'\t',1);mode,kind,oid=meta.decode().split();out[path.decode()]={'mode':mode,'kind':kind,'oid':oid}
 return out
def free():return shutil.disk_usage(R).free
assert free()>=2516777216
assert git('rev-parse','HEAD').decode().strip()==BASE and not git('status','--porcelain')
b_tree=tree(BASE);donor_base=git('rev-parse',COMMITS[0]+'^').decode().strip()
a_tree,z_tree=tree(donor_base),tree(COMMITS[-1])
changed={n for n in set(a_tree)|set(z_tree) if a_tree.get(n)!=z_tree.get(n)}
assert changed and all(n.startswith('docs/validation/20261123-release-selection-order/') or n in {CALLER,'Tools/PinkhaSimulatorGate/test_coherent_selection_order.py'} for n in changed)
assert all(n in z_tree for n in changed)
assert all(b_tree.get(n)==a_tree.get(n) for n in changed)
inverse_bytes=git('show',COMMITS[-1]+':docs/validation/20261123-release-selection-order/source-inverse.json')
assert sha(inverse_bytes)=='adab8960c348d0c2241622eae58e01322612de8bdaa675f0f31b16c53e8916fd'
inverse=json.loads(inverse_bytes);candidate=git('show',COMMITS[-1]+':'+CALLER)
assert sha(candidate)==NEW and sha((R/CALLER).read_bytes())==OLD
recovered=candidate
for h in reversed(inverse['two_exact_substitutions']):
 before,after=h['before'].encode(),h['after'].encode();assert recovered.count(after)==1;recovered=recovered.replace(after,before,1)
assert sha(recovered)==OLD and recovered==(R/CALLER).read_bytes()
ast.parse(candidate)
original_contract=(R/CONTRACT).read_bytes()
assert sha(original_contract)=='aded7fbbe277ecbb56cf4648e862505002dadc72cca963ea43377c2d439fe35b'
c=json.loads(original_contract);assert len(c['inputs'])==78 and c['inputs'][CALLER]=={'git_mode':'100644','sha256':OLD}
q_path='docs/validation/20261123-release-selection-order/qualification.json'
q_bytes=git('show',COMMITS[-1]+':'+q_path)
assert sha(q_bytes)=='1f3f2c1ac92fa5c77f99c0340fa917835fb0b0edf8916b14979e4a183c72bd6a'
q=json.loads(q_bytes);assert q['status']=='QUALIFIED_RETAINED_CONTROL_WITH_CURRENT_IMPORT_ADMISSION'
assert q['original_control']['overall_status']=='FAIL' and q['current_admission']['status']=='PASS' and q['passing_methods_replayed']==0
save(D/'intent.json',{'protocol':'release-order-exact-composition-v1','baseline':BASE,'donor_commits':COMMITS,'donor_base':donor_base,'changed_paths':sorted(changed),'exact_source_inverse':sha(inverse_bytes),'qualification':sha(q_bytes),'started_at':now(),'free_bytes':free(),'new_tests':0})
p=subprocess.run(['git','-c','gc.auto=0','-C',str(R),'cherry-pick','--no-edit',*COMMITS],capture_output=True,timeout=180)
save(D/'cherry-pick.stdout',p.stdout);save(D/'cherry-pick.stderr',p.stderr)
assert p.returncode==0,p.stderr.decode(errors='replace')
integrated=git('rev-parse','HEAD').decode().strip();integrated_tree=tree(integrated)
assert not git('status','--porcelain')
assert all(integrated_tree[n]==z_tree[n] for n in changed)
assert {n:v for n,v in integrated_tree.items() if n not in changed}=={n:v for n,v in b_tree.items() if n not in changed}
assert (R/CALLER).read_bytes()==candidate and (R/CONTRACT).read_bytes()==original_contract
rebound=original_contract.replace(OLD.encode(),NEW.encode())
assert original_contract.count(OLD.encode())==1
parsed=json.loads(rebound);expect=json.loads(original_contract);expect['inputs'][CALLER]['sha256']=NEW
assert parsed==expect
with (R/CONTRACT).open('wb') as f:f.write(rebound);f.flush();os.fsync(f.fileno())
for name,row in parsed['inputs'].items():
 path=R/name
 assert path.is_file() and not path.is_symlink(),name
 assert sha(path.read_bytes())==row['sha256'],name
 mode='100755' if path.stat().st_mode&0o111 else '100644'
 assert mode==row['git_mode'],name
docs=R/'docs/validation/20261123-release-order-composition';docs.mkdir()
scope={
 'protocol':'release-order-source-composition-v1','status':'PASS_SOURCE_COMPOSITION_NO_TEST_REPLAY','baseline':BASE,'donor_chain':COMMITS,'integrated_donor_head':integrated,
 'donor_changed_path_count':len(changed),'all_donor_bytes_modes_exact':True,'all_other_baseline_tree_entries_unchanged':True,
 'release_source':{'path':CALLER,'qualified_before':OLD,'current':NEW,'inverse_manifest_sha256':sha(inverse_bytes),'exact_inverse_hunks':2,'whole_file_inverse_matches_baseline':True,'sdk_branch_exclusion':inverse['sdk_existing_context']},
 'sdk_contract':{'path':CONTRACT,'tested_before_sha256':sha(original_contract),'current_sha256':sha(rebound),'changed_rows':[CALLER],'input_rows_verified':78,'other_json_fields_byte_unchanged':True,'other_inputs_unchanged':True},
 'retained_qualification':{'path':q_path,'sha256':sha(q_bytes),'original_control_status':'FAIL','original_named_passes':1,'original_subcase_passes':3,'historical_after_available':False,'supplemental_current_import_status':'PASS','current_import_methods_executed':0,'historical_failure_not_relabelled':True},
 'prior_sdk_ui_page_gate':{'path':'/mnt/development/projects/diagnostics/sdk-ui-page-composition-20261123/source-retention-before-dispatch.json','sha256':'bb83fb04b5b14ea48482e2c44e4ab98f15994d8f694487719af097a1cbe473e4','scope':'Retained source gate; current Release delta is composed explicitly here.'},
 'tests_replayed':0,'new_tests_executed':0,'new_builds':0,'product_runtime_status':'NOT_RUN_CURRENT_RELEASE_SOURCE','recorded_at':now()
}
save(docs/'qualification.json',scope)
save(docs/'integrate-release-order.py',pathlib.Path(__file__).read_bytes())
git('diff','--check',BASE,'--','Tools','.github')
git('add','--',CONTRACT,str(docs.relative_to(R)))
git('commit','-m','Bind retained Release ordering repair into the current SDK controller source')
head=git('rev-parse','HEAD').decode().strip()
assert not git('status','--porcelain')
final_tree=tree(head)
allowed=changed|{CONTRACT}|{str(x.relative_to(R)) for x in docs.iterdir()}
assert {n:v for n,v in final_tree.items() if n not in allowed}=={n:v for n,v in b_tree.items() if n not in allowed}
assert all(final_tree[n]==z_tree[n] for n in changed)
assert sha((R/CALLER).read_bytes())==NEW and sha((R/CONTRACT).read_bytes())==sha(rebound)
assert free()>=2500000000
gate={'status':'PASS_SOURCE_GATE','baseline':BASE,'source':head,'scope':scope,'allowed_changed_paths':sorted(allowed),'protected_baseline_entries':len(b_tree)-len(set(b_tree)&allowed),'unmapped_changes':0,'source_and_git_on_oracle':True,'tests_executed_now':0,'free_bytes_after':free(),'finished_at':now()}
proof=save(D/'source-retention-before-dispatch.json',gate)
seal=save(D/'source-gate-seal.json',{'status':'PASS_SOURCE_GATE','publishedCandidate':head,'sourceGateSHA256':proof['sha256'],'baseline':BASE,'testsReplayed':0})
result={'status':'PASS_RELEASE_ORDER_INTEGRATED_AND_SOURCE_GATED','source':head,'integrated_head':integrated,'source_gate_sha256':proof['sha256'],'seal_sha256':seal['sha256'],'sdk_contract_sha256':sha(rebound),'source_changes':[CALLER,CONTRACT],'new_tests':0,'free_bytes_after':free(),'directory':str(D)}
save(D/'integration-result.json',result)
print(json.dumps(result))
