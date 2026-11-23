from pathlib import Path
import ast,hashlib,json,os,stat,subprocess,time,datetime
ROOT=Path('/mnt/development/projects/worktrees/anytype-wave15-sdk06-original-native-20261123')
D='docs/validation/20261123-sdk06-original-native-continuation'
OUT=Path('/mnt/development/projects/diagnostics/sdk06-original-native-root-review-20261123')
HEAD='44aa9d3c64275917a79e6392ef619554d1af2990'
OLD='46c03ec8692bee4ffe6304b041a4a4425d08e2dc'
SEALED='cf70fdf165586baffd257fdb135cea06f64e745d'
def req(v,s):
 if not v: raise RuntimeError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(ROOT),*a],timeout=30)
def blob(ref,p):return git('show',ref+':'+p)
def read(p):
 f=ROOT/p;s=f.lstat();req(stat.S_ISREG(s.st_mode) and f.resolve()==f,'regular_path')
 return f.read_bytes()
t=time.monotonic();s=os.statvfs(ROOT);free=s.f_bavail*s.f_frsize;req(free>=2516777216,'reserve')
req(git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain=v1'),'clean_frozen')
pinned={'failed-method-review.json':'cca2ac1240f27bec27878237c6ff0decb5c322100c55dc013cb1baa44e27c48e','failed-control-inputs.json':'a93c55f232b6c21b72645810e91c40e6e3cf3d0eb4a00382a20b2c4b9e8b2c74','run-failed-lane-control.py':'4cf990027474f23cf6d7899ebbb76bb445ecce9f3d84ae61d072ea6a46f326e5'}
for p,h in pinned.items():req(sha(read(D+'/'+p))==h and read(D+'/'+p)==blob(HEAD,D+'/'+p),'metadata_sha')
review=json.loads(read(D+'/failed-method-review.json'));manifest=json.loads(read(D+'/failed-control-inputs.json'))
wrapper=read(D+'/run-failed-lane-control.py').decode();tree=ast.parse(wrapper)
assign={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='METHODS'}
req(assign['METHODS']==(('test_sdk06_original_native','OriginalNativeContinuationControls','test_actual_lane_stops_on_original30_and_ui_builder_cannot_rebuild_native'),),'one_failed_method')
metadata=['control-inputs.json','run-controls.py','source-review.json','source-plan.json','exact-source-inverses.json','selection-copy-inverse.json','current-static-closure.json',*pinned]
names=set(manifest['inputs'])|{D+'/'+p for p in metadata};req(len(manifest['inputs'])==150 and len(names)==160,'fixed160')
observed={}
for p in sorted(names):
 b=read(p);req(b==blob(HEAD,p),'physical_git:'+p)
 mode=git('ls-tree',HEAD,'--',p).decode().split()[0]
 req(bool((ROOT/p).stat().st_mode&0o111)==(mode=='100755'),'mode')
 row={'sha256':sha(b),'bytes':len(b),'git_mode':mode}
 if p in manifest['inputs']:req(row==manifest['inputs'][p],'fixed_hash:'+p)
 observed[p]=row
test=read(review['test_path']).decode()
for h in reversed(review['test_inverse']):
 req(test.count(h['after'])==1,'unique_test_inverse')
 test=test.replace(h['after'],h['before'],1)
req(test.encode()==blob(OLD,review['test_path'])==blob(SEALED,review['test_path']),'test_whole_inverse')
for h in reversed(review['wrapper_inverse']):
 req(wrapper.count(h['after'])==1,'unique_wrapper_inverse')
 wrapper=wrapper.replace(h['after'],h['before'],1)
a=review['wrapper_input_hash_substitution'];req(wrapper.count(a['after'])==1,'unique_wrapper_hash')
wrapper=wrapper.replace(a['after'],a['before'],1)
req(wrapper.encode()==blob(OLD,D+'/run-controls.py'),'wrapper_whole_inverse')
contract=review['runtime_contract_delta']['path']
old_contract=json.loads(blob(OLD,contract));new_contract=json.loads(read(contract))
def changes(a,b,path=()):
 if type(a)!=type(b):return [list(path)]
 if isinstance(a,dict):
  out=[]
  for k in sorted(set(a)|set(b)):
   if k not in a or k not in b:out.append(list(path+(k,)))
   else:out+=changes(a[k],b[k],path+(k,))
  return out
 if isinstance(a,list):
  if len(a)!=len(b):return [list(path)]
  return [p for i,(x,y) in enumerate(zip(a,b)) for p in changes(x,y,path+(str(i),))]
 return [] if a==b else [list(path)]
delta=changes(old_contract,new_contract)
req(len(delta)==1 and review['test_path'] in delta[0],'only_test_contract_row')
old_inputs=json.loads(blob(OLD,D+'/control-inputs.json'))['inputs']
kept=0
for p,row in old_inputs.items():
 if p in {review['test_path'],contract}:continue
 req(manifest['inputs'][p]==row and read(p)==blob(OLD,p),'retained_original_input:'+p);kept+=1
req(kept==98,'retained98')
expected={review['test_path'],contract,D+'/failed-control-inputs.json',D+'/run-failed-lane-control.py',D+'/failed-method-review.json'}
changed=set(git('diff','--name-only',SEALED,HEAD).decode().splitlines());req(changed==expected,'exact_five_path_delta')
req(not git('status','--porcelain=v1'),'after_clean')
report={'schema':'sdk06-failed-third-root-review/v1','status':'PASS','reviewedHead':HEAD,'originalAttemptSource':OLD,'originalEvidenceCommit':SEALED,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixedMetadata':pinned,'verifiedPhysicalGitInputs':len(names),'fixedInputs':len(manifest['inputs']),'unchangedOriginalInputs':kept,'testInverseHunks':len(review['test_inverse']),'wrapperInverseHunks':len(review['wrapper_inverse']),'runtimeContractDelta':delta,'changedPaths':sorted(changed),'onlyMethod':manifest['methods'],'branchObservation':'SYNTHETIC only for exact branch --show-current argv; actual HEAD and all other Git calls retained; no allowlist or branch changes','manualReview':['all original failure and two passes preserved','third-method fixture intercept before original lane','actual identity and source guard path preserved','one-method outside-repository wrapper and source-before/after gates'],'oldOrPassingMethodsReplayed':0,'testsExecuted':0,'builds':0,'freeBytes':free,'elapsedSeconds':round(time.monotonic()-t,4)}
out=OUT/'source-review-44aa9d3.json'
with out.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':'PASS','output':str(out),'sha256':sha(out.read_bytes()),'readerSHA256':sha(Path(__file__).read_bytes()),'elapsed':report['elapsedSeconds'],'free':free}))
