from pathlib import Path
import ast,datetime,hashlib,json,os,stat,subprocess,time
ROOT=Path('/mnt/development/projects/worktrees/anytype-wave15-page-source-origins-20261123')
OUT=Path('/mnt/development/projects/diagnostics/page-source-origins-root-review-20261123')
D=ROOT/'docs/validation/20261123-page-source-origins'
HEAD='a513821699ff0ed5fc032b71ff91f56027bdef8b'
BASE='c0c1f851f80322c9f532e86505047498dfaf1adf'
APP='68148339c275268795360d71d519a5baf003adf8'
def req(v,s):
 if not v:raise RuntimeError(s)
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(ROOT),*a],timeout=30)
def blob(ref,p):return git('show',ref+':'+p)
def data(p):return json.loads(p.read_bytes())
t=time.monotonic();s=os.statvfs(ROOT);free=s.f_bavail*s.f_frsize;req(free>=2516777216,'reserve')
req(git('rev-parse','HEAD').decode().strip()==HEAD and not git('status','--porcelain'),'clean_frozen_head')
pins={'docs/validation/20261123-page-source-origins/control-inputs.json':'8667972b46994b1cc4d49241bbc53cc0755e2d4adbdeb8a681c3e8c7bad6ab41','docs/validation/20261123-page-source-origins/final-source-review.json':'c135af339ed5da290fc1ea7ff632775f992c7ee32191be1027481309735c08b3','docs/validation/20261123-page-source-origins/source-review.json':'03518192ad21db2208079d42e9635a1d7b0d95174401603646fa21535508d7ac','Tools/PinkhaSemanticAnchorWire/apple_mounted/run_source_origin_controls.py':'34adfa0f6afb7b30dc13a8846301e73136fde1942c3a7d9d283622c2dbfd064f'}
for p,h in pins.items():
 b=(ROOT/p).read_bytes();req(sha(b)==h and b==blob(HEAD,p),'fixed_metadata:'+p)
man=data(D/'control-inputs.json');req(man['input_count']==len(man['inputs'])==39 and man['eager_python_count']==33,'fixed_scope')
for row in man['inputs']:
 p=ROOT/row['path'];s=p.lstat();b=p.read_bytes()
 req(p.resolve()==p and stat.S_ISREG(s.st_mode) and s.st_nlink==1,'regular_input')
 req(len(b)==row['bytes'] and sha(b)==row['sha256'] and format(stat.S_IMODE(s.st_mode),'04o')==row['physical_mode'],'physical_input:'+row['path'])
 req(b==blob(HEAD,row['path']),'Git_input:'+row['path'])
 if p.suffix=='.py':ast.parse(b)
review=data(D/'source-review.json');inverses=[]
for p in review['patch']['patches']:
 b=(ROOT/p['path']).read_bytes();text=b.decode();req(sha(b)==p['after'],'after_hash')
 for h in reversed(p['hunks']):
  req(text.count(h['after'])==h['count'],'unique_inverse')
  text=text.replace(h['after'],h['before'])
 req(text.encode()==blob(BASE,p['path']) and sha(text.encode())==p['before'],'whole_inverse')
 inverses.append({'path':p['path'],'hunks':len(p['hunks']),'beforeSHA256':p['before'],'afterSHA256':p['after']})
for p in review['patch']['newfiles']:req((ROOT/p['path']).read_bytes()==p['content'].encode(),'new_helper_source')
run='Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py'
def functions(b):
 text=b.decode();return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
before=functions(blob(BASE,run));after=functions((ROOT/run).read_bytes())
unchanged=['copy_original_fixture','download_originals','enumerate_and_run','product_inputs','ui_attachments']
req(all(before[n]==after[n] for n in unchanged),'unchanged_five_functions')
req({n for n in before if before[n]!=after.get(n)}=={'execute','main'},'only_execute_main_changed')
plan=json.loads(blob(HEAD,'Tools/PinkhaSemanticAnchorWire/apple_mounted/source-plan.json'))
for p,row in plan['files'].items():req(sha(blob(HEAD,p))==sha(blob(APP,p))==row['sha256'],'frozen_app_plan:'+p)
for p in ['Tools/PinkhaSimulatorGate/run_owned_single_lane.py','Tools/PinkhaSimulatorGate/wave15_batch.py','.github/workflows/torah-inspector-ipados27.yml']:
 req(blob(HEAD,p)==blob(BASE,p),'unchanged_supervisor_or_central:'+p)
test='Tools/PinkhaSemanticAnchorWire/apple_mounted/test_mounted_source_origins.py'
tree=ast.parse((ROOT/test).read_bytes());methods=[n.name for c in tree.body if isinstance(c,ast.ClassDef) for n in c.body if isinstance(n,ast.FunctionDef) and n.name.startswith('test_')]
req(methods==['test_real_current_controller_and_original_app_have_separate_complete_source_admission','test_actual_origin_adapter_refuses_wrong_roots_heads_foreign_imports_and_postflight_drift'],'two_new_methods')
req(not git('status','--porcelain'),'after_clean')
report={'schema':'page-source-origin-root-source-review/v1','status':'PASS','reviewedHead':HEAD,'base':BASE,'immutableApp':APP,'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'fixedMetadata':pins,'verifiedPhysicalGitInputs':39,'declaredEagerPython':33,'wholeFileInverses':inverses,'unchangedFiveFunctions':unchanged,'protectedAppPlanFiles':len(plan['files']),'supervisorAndCentralUnchanged':True,'exactNewMethods':methods,'manualReview':['actual complete consumer checkout_inputs checks both real Git roots','loaded current modules retain current controller origin; compiled App checkout cannot supply controller modules','strict whole product_inputs equality uses original681 App; seven differences never excluded','current controller dispatch binding and admission tracked path remain enforced','two real synthetic Git fixtures and eight exact-reason refusals; owned child cleanup and before/after proofs','only execute and main origin plumbing changed; original product/UI assertions and restore comparison retained'],'testsExecuted':0,'builds':0,'oldKernelControlReplay':0,'freeBytes':free,'elapsedSeconds':round(time.monotonic()-t,4),'scopeLimit':'This review authorizes two new source-origin host controls only; actual Apple/runtime/product acceptance remains unproved.'}
dest=OUT/'source-review-a513821.json'
with dest.open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':'PASS','path':str(dest),'sha256':sha(dest.read_bytes()),'readerSHA256':sha(Path(__file__).read_bytes()),'elapsed':report['elapsedSeconds'],'free':free}))
