from pathlib import Path
import hashlib, importlib.util, json, os, re, shutil, signal, subprocess, time

ROOT=Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
CACHE=Path('/tmp/pinkha-c-swift-cache-20261125')
OUT=Path('/mnt/development/projects/evidence/migration-final-20261125/recovered-definition-controls/full-census1')
EVIDENCE=ROOT/'docs/validation/20261126-original-source-compiled-definitions/actual-original-go-export'
EXPECTED=['testProduceRecoveredFullSourceCensusWithoutDestinationCalls']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 q=p.with_name(p.name+'.new')
 q.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n');q.replace(p)
def sources():
 result={}
 for name in ['PinkhaAnyHost','PinkhaAnyEngine','PinkhaAnyIntegration','PinkhaKit']:
  base=ROOT/'Modules'/name
  paths=[base/'Package.swift',base/'Package.resolved']
  for leaf in ['Sources','Tests']:
   if (base/leaf).exists():paths.extend((base/leaf).rglob('*.swift'))
  for p in sorted(set(paths)):
   if not p.exists():continue
   assert p.is_file() and not p.is_symlink()
   result[p.relative_to(ROOT).as_posix()]=sha(p)
 return result
os.umask(0o077);OUT.mkdir(mode=0o700,parents=True,exist_ok=False)
start=time.monotonic();child=None;known_absent=False
r={'protocol':'pinkha-historical156-recovered-definition-controls-v1','status':'RUNNING',
   'recoveredCatalogQualificationSHA256':'1246d847895f448013b9f5abc0bd5e90fbba05d35a8dd8661683c1a82007123e','actualNativeCalls':0,'sourceAdmission':False,'destinationWrites':False,'expectedMethods':EXPECTED,'errors':[]}
def save():r['seconds']=round(time.monotonic()-start,3);write(OUT/'result.json',r)
def gone():
 global known_absent
 if known_absent:return True
 try:os.killpg(child.pid,0)
 except ProcessLookupError:known_absent=True
 return known_absent
def interrupted(*args):raise RuntimeError('owned recovery component interrupted')
signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
try:
 r['controllerSHA256']=sha(Path(__file__))
 r['sourceCommit']=subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 verifier=ROOT/'Tools/AnyEngineValidation/native_captured_content/run_native_captured_content_roundtrip.py'
 assert sha(verifier)=='da4311e3cf0af4d0d14d42fa39a799348bea29122e7fb0d313b111e47fddf299'
 spec=importlib.util.spec_from_file_location('original_custody',verifier);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 r['originalBefore']=m.verify_original()
 before=sources();write(OUT/'source-before.json',before)
 dependencies=json.loads((CACHE/'workspace-state.json').read_bytes())['object']['dependencies']
 write(OUT/'dependencies-before.json',dependencies)
 r['sourceFiles']=len(before);r['freeCacheBefore']=shutil.disk_usage(CACHE).free;r['freeEvidenceBefore']=shutil.disk_usage(OUT).free
 r['resourceEstimate']={'incrementalCompilerAndLogBytes':512*1024*1024,'ownEmergencyFloorBytes':256*1024*1024,'nativeOrAppleBuilds':0,'packageWorkers':2}
 assert r['freeCacheBefore']>=768*1024*1024 and r['freeEvidenceBefore']>=32*1024*1024
 command=['/usr/local/bin/swift','test','--package-path',str(ROOT/'Modules/PinkhaAnyHost'),'--scratch-path',str(CACHE),'--jobs','2','--filter','RecoveredCompiledDefinitionTests.testProduceRecoveredFullSourceCensusWithoutDestinationCalls']
 write(OUT/'command.json',command)
 env=os.environ.copy();env['PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE']=str(m.ORIGINAL)
 env['PINKHA_RECOVERED_DEFINITION_EVIDENCE']=str(EVIDENCE);env['PINKHA_RECOVERED_DEFINITION_REPOSITORY']=str(ROOT);env['PINKHA_RECOVERED_DEFINITION_CENSUS']=str(OUT/'full-source-census.private.json')
 with (OUT/'original.log').open('wb') as log:
  child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  r['pid']=child.pid;save();deadline=time.monotonic()+900
  while child.poll() is None:
   assert time.monotonic()<deadline,'actual component bound'
   assert shutil.disk_usage(CACHE).free>=256*1024*1024,'own compiler emergency floor'
   time.sleep(.5)
  r['exitCode']=child.wait();r['ownedGroupAbsent']=gone();save()
 after=sources();write(OUT/'source-after.json',after)
 dep_after=json.loads((CACHE/'workspace-state.json').read_bytes())['object']['dependencies']
 write(OUT/'dependencies-after.json',dep_after)
 r['sourceUnchanged']=before==after;r['dependenciesUnchanged']=dependencies==dep_after
 r['originalAfter']=m.verify_original();r['originalUnchanged']=r['originalBefore']==r['originalAfter']
 log=(OUT/'original.log').read_text(errors='replace')
 r['logSHA256']=sha(OUT/'original.log')
 passed=re.findall(r"Test Case 'RecoveredCompiledDefinitionTests\.([^']+)' passed",log)
 r['passedMethods']=passed
 assert r['exitCode']==0 and r['ownedGroupAbsent']
 assert r['sourceUnchanged'] and r['dependenciesUnchanged'] and r['originalUnchanged']
 assert len(passed)==len(EXPECTED) and set(passed)==set(EXPECTED)
 assert 'Executed 1 test, with 0 failures' in log and 'skipped' not in log.lower()
 r['status']='PASS_CENSUS_ONLY_NOT_NATIVE_ACCEPTANCE'
except BaseException as e:
 r['status']='FAIL';r['errors'].append({'type':type(e).__name__,'error':str(e)})
finally:
 if child is not None:
  try:
   if child.poll() is None and not gone():
    os.killpg(child.pid,signal.SIGTERM);child.wait(timeout=30)
   if not gone():raise RuntimeError('owned group unresolved after exit; no historical group signal')
   r['ownedGroupAbsent']=True
  except BaseException as e:r['status']='FAIL';r['errors'].append({'cleanup':type(e).__name__,'error':str(e)})
 save()
print(json.dumps({'status':r['status'],'result':str(OUT/'result.json'),'sha256':sha(OUT/'result.json'),'passed':len(r.get('passedMethods',[]))}))
raise SystemExit(0 if r['status']=='PASS_CENSUS_ONLY_NOT_NATIVE_ACCEPTANCE' else 1)
