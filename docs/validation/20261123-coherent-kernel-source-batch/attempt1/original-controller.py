from pathlib import Path
import ast,contextlib,datetime,hashlib,importlib,json,os,platform,subprocess,sys,threading,time,traceback,unittest
W=Path('/mnt/development/projects/worktrees/anytype-wave15-coherent-kernel-20261123')
SOURCE='1c4b690b7776e8330a4b3bfb34dcc37b0f76d65d'
E=Path('/mnt/development/projects/evidence/coherent-kernel-source-batch-20261123')
OUT=E/'attempt1'
CONES=['.github/workflows','Tools/Hanlin','Tools/PinkhaArchitecture','Tools/PinkhaNativeDerived','Tools/PinkhaSimulatorGate']
REVIEW='docs/validation/20261123-coherent-kernel-source-batch/source-review.json'
DESIGN='docs/validation/20261123-coherent-kernel-source-batch/DESIGN.md'
METHODS=[
 'CoherentKernelAndSourceControls.test_coherent_owned_readiness_and_nested_cleanup_use_exact_kernel_absence',
 'CoherentKernelAndSourceControls.test_single_git_batch_preserves_exact_loaded_closure_and_rejects_corruption']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b):return hashlib.sha256(b).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=True)+'\n')
def git(*args):return subprocess.check_output(['git',*args],cwd=W,timeout=30)
def snapshot():
 assert git('rev-parse','HEAD').decode().strip()==SOURCE,'Frozen HEAD changed'
 raw=git('ls-tree','-rz',SOURCE,'--',*CONES,REVIEW,DESIGN)
 result={};counts={c:0 for c in CONES}
 for row in raw.split(b'\0'):
  if not row:continue
  meta,name=row.split(b'\t',1);mode,typ,oid=meta.decode().split();rel=name.decode();p=W/rel
  assert mode in ('100644','100755') and typ=='blob' and p.is_file() and not p.is_symlink(),rel
  b=p.read_bytes()
  actual_oid=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
  assert actual_oid==oid,'Physical bytes differ from frozen Git:'+rel
  result[rel]={'sha256':sha(b),'gitBlobSHA1':oid,'gitMode':mode,'bytes':len(b)}
  for cone in CONES:
   if rel.startswith(cone+'/'):counts[cone]+=1
 assert not git('status','--porcelain','--untracked-files=no').decode().strip(),'Tracked source dirty'
 return result,counts
def loaded():
 result={}
 for mod in tuple(sys.modules.values()):
  f=getattr(mod,'__file__',None)
  if not f:continue
  p=Path(f).resolve()
  if not p.is_relative_to(W) or p.suffix!='.py':continue
  rel=p.relative_to(W).as_posix();b=p.read_bytes()
  original=git('show',SOURCE+':'+rel)
  result[rel]={'sha256':sha(b),'gitSHA256':sha(original),'matchesFrozenGit':b==original,'modulePath':str(p)}
 return dict(sorted(result.items()))
assert threading.current_thread() is threading.main_thread()
assert not OUT.exists(),'Refuse existing attempt; no implicit rerun'
assert not git('status','--porcelain').decode().strip(),'Writer must be clean before controls'
assert sha((W/REVIEW).read_bytes())=='f8fa746c88f366256b02822843d291cb208cf52d0c86d94f8272e4cb116bf345'
review=json.loads((W/REVIEW).read_bytes())
assert review['newControls']==METHODS
for rel,proof in review['sourceChanges'].items():
 b=(W/rel).read_bytes();s=b.decode()
 assert sha(b)==proof['afterSHA256'] and s.count(proof['new'])==1
 assert s.replace(proof['new'],proof['old'],1).encode()==git('show',review['base']+':'+rel)
for rel,h in review['newFiles'].items():assert sha((W/rel).read_bytes())==h
before,counts=snapshot()
OUT.mkdir(parents=True,mode=0o700)
ORIGINALS=OUT/'owned-command-originals';ORIGINALS.mkdir(mode=0o700)
os.environ['PINKHA_COHERENT_CONTROL_ORIGINALS']=str(ORIGINALS)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
os.chdir(W)
sys.path.insert(0,str(W/'Tools/PinkhaSimulatorGate'))
(OUT/'original-controller.py').write_bytes(Path(__file__).read_bytes())
dump(OUT/'source-before.json',before)
started=now()
dump(OUT/'intent.json',{'sourceCommit':SOURCE,'reviewSHA256':sha((W/REVIEW).read_bytes()),'methods':METHODS,
 'mainThread':True,'startedAt':started,'sourceCones':counts,'snapshotInputs':len(before),
 'ownedOriginalsPath':str(ORIGINALS),'oldControllerMethodsRequested':0,'productMethodsRequested':0,'newBuildsRequested':0})
events=[]
def event(kind,test,**extra):
 events.append({'event':kind,'method':test.id(),'at':now(),**extra});dump(OUT/'events.json',events)
class Result(unittest.TextTestResult):
 def startTest(self,t):event('START',t);super().startTest(t)
 def addSuccess(self,t):event('PASS',t);super().addSuccess(t)
 def addFailure(self,t,err):event('FAIL',t,kind=err[0].__name__);super().addFailure(t,err)
 def addError(self,t,err):event('ERROR',t,kind=err[0].__name__);super().addError(t,err)
 def addSkip(self,t,reason):event('SKIP',t,reason=reason);super().addSkip(t,reason)
 def addSubTest(self,test,subtest,err):
  if err is not None:event('SUBTEST_FAIL',test,subtest=str(subtest),kind=err[0].__name__)
  super().addSubTest(test,subtest,err)
result=None;runner_error=None;after=None;modules={};evidence_error=None
begin=time.monotonic()
with (OUT/'controls.log').open('x') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
 try:
  module=importlib.import_module('test_coherent_kernel_sources')
  suite=unittest.TestSuite()
  for name in METHODS:
   cls,method=name.split('.')
   suite.addTest(getattr(module,cls)(method))
  assert suite.countTestCases()==2
  result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
 except BaseException as error:
  runner_error={'kind':type(error).__name__,'message':str(error)}
  traceback.print_exc()
 finally:
  try:
   after,after_counts=snapshot()
   modules=loaded()
   assert after_counts==counts
   dump(OUT/'source-after.json',after)
  except BaseException as error:
   evidence_error={'kind':type(error).__name__,'message':str(error)}
   traceback.print_exc()
elapsed=time.monotonic()-begin
dump(OUT/'events.json',events)
dump(OUT/'loaded-source-map.json',modules)
original_files={p.name:sha(p.read_bytes()) for p in sorted(ORIGINALS.iterdir()) if p.is_file()}
original_proof={}
if original_files:
 try:
  names=['new-coherent-command.log','new-coherent-command.command.json','new-coherent-command.owned.command.json']
  assert set(original_files)==set(names),'Unexpected owned evidence membership'
  projection=json.loads((ORIGINALS/names[1]).read_bytes())
  original=json.loads((ORIGINALS/names[2]).read_bytes())
  assert projection['original_owned_command']==names[2]
  assert projection['original_owned_command_sha256']==original_files[names[2]]
  assert projection['controller_process_id']==original['worker_pid']>1
  assert projection['return_code']==original['return_code']==0
  assert projection['argv']==original['argv'] and projection['cwd']==original['cwd']
  assert projection['owned_group_termination']==original['owned_group_cleanup']=='TERM_THEN_KILL'
  q=projection['owned_group_quiescence']
  assert q['status']=='PASS' and q['absence_source']=='KERNEL_ESRCH' and q['budget_seconds']==10
  assert q['kernel_group_observation']['outcome']=='ABSENT_ESRCH'
  assert (ORIGINALS/names[0]).read_text().strip()=='COHERENT_NEW_SCOPE'
  original_proof={'status':'PASS','ownedPID':original['worker_pid'],'exitCode':0,
   'actualCWD':original['cwd'],'exactProjectedIdentity':True,'kernelQuiescence':q,
   'originalFiles':original_files}
 except BaseException as error:
  original_proof={'status':'FAIL','kind':type(error).__name__,'message':str(error),'originalFiles':original_files}
else:original_proof={'status':'MISSING','originalFiles':original_files}
passed=bool(result and result.wasSuccessful() and result.testsRun==2
 and not result.skipped and runner_error is None and evidence_error is None
 and before==after and all(v['matchesFrozenGit'] for v in modules.values())
 and original_proof['status']=='PASS'
 and [(x['event'],x['method']) for x in events]==[(kind,'test_coherent_kernel_sources.'+m) for m in METHODS for kind in ['START','PASS']])
receipt={'sourceCommit':SOURCE,'passed':passed,'testsRun':result.testsRun if result else 0,
 'failures':len(result.failures) if result else 0,'errors':len(result.errors) if result else 0,
 'skips':len(result.skipped) if result else 0,'runnerError':runner_error,'evidenceError':evidence_error,
 'elapsedSeconds':elapsed,'mainThread':threading.current_thread() is threading.main_thread(),
 'python':sys.version,'platform':platform.platform(),'sourceInputs':len(before),
 'sourceUnchanged':before==after,'loadedRepositoryModules':modules,
 'loadedSourceMatchesFrozenGit':bool(modules) and all(v['matchesFrozenGit'] for v in modules.values()),
 'ownedCommandProof':original_proof,'oldControllerMethodsExecuted':0,'AppleMethodsExecuted':0,'newBuilds':0}
dump(OUT/'result.json',receipt)
originals={p.relative_to(OUT).as_posix():sha(p.read_bytes()) for p in sorted(OUT.rglob('*')) if p.is_file()}
audit={'schemaVersion':1,'status':'PASS' if passed else 'FAIL','sourceCommit':SOURCE,
 'startedAt':started,'finishedAt':now(),'actualNamedEvents':events,'originals':originals,
 'sourceUnchanged':before==after,'snapshotInputs':len(before),'actualLoadedSourceInputs':len(modules),
 'actualOwnedCommandReceipts':original_files,'oldControllerMethodsExecuted':0,'AppleMethodsExecuted':0,'newBuilds':0}
dump(OUT/'audit.json',audit)
print(json.dumps({'status':audit['status'],'sourceCommit':SOURCE,'testsRun':receipt['testsRun'],
 'failures':receipt['failures'],'errors':receipt['errors'],'sourceInputs':len(before),
 'loadedInputs':len(modules),'ownedPID':original_proof.get('ownedPID'),
 'auditSHA256':sha((OUT/'audit.json').read_bytes()),'directory':str(OUT)}))
sys.exit(0 if passed else 1)
