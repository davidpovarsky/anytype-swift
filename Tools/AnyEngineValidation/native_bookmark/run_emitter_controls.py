from pathlib import Path
import hashlib, importlib.util, json, os, re, shutil, signal, subprocess, time

ROOT=Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
CACHE=Path('/tmp/pinkha-c-swift-cache-20261125')
OUT=Path('/var/lib/pinkha-c-native-preservation-20261126/bookmark-emitter-controls1')
EVIDENCE=ROOT/'docs/validation/20261126-original-source-compiled-definitions/actual-original-go-export'
EXPECTED=[]
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
r={'protocol':'pinkha-bookmark-emitter-controls-v1','status':'RUNNING','actualNativeCalls':0,'sourceAdmission':False,'destinationWrites':False,'testsInvoked':0,'errors':[]}
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
 expected_dependencies=json.loads(json.dumps(dependencies))
 expected_revisions={'swift-asn1':'917b472dbe53ba699cbb0495f9a95a084bc6364d','swift-crypto':'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed','torahinspectorkit':'9058b489e9acc271b4f8ef69e2ed24648f93b4ed'}
 expected_local={'pinkhaanyengine':'PinkhaAnyEngine','pinkhaanyintegration':'PinkhaAnyIntegration','pinkhakit':'PinkhaKit'}
 assert len(dependencies)==6
 for row in expected_dependencies:
  identity=row['packageRef']['identity']
  if identity in expected_local:
   target=str(ROOT/'Modules'/expected_local[identity])
   old='/mnt/development/projects/evidence/migration-final-20261125/recovered-definition-controls/combined-root523/source/Modules/'+expected_local[identity]
   assert row['packageRef']['kind']=='fileSystem' and row['state']['name']=='fileSystem'
   assert row['packageRef']['location']==row['state']['path'] and row['state']['path'] in [old,target]
   row['packageRef']['location']=target;row['state']['path']=target
  else:
   assert identity in expected_revisions
   assert row['packageRef']['kind']=='remoteSourceControl' and row['state']['checkoutState']['revision']==expected_revisions[identity]
   checkout=CACHE/'checkouts'/row['subpath']
   g=['git','-c','safe.directory='+str(checkout),'-C',str(checkout)]
   assert subprocess.check_output(g+['rev-parse','HEAD'],text=True).strip()==expected_revisions[identity]
   assert not subprocess.check_output(g+['status','--porcelain','--untracked-files=no'],text=True)
 write(OUT/'dependencies-expected.json',expected_dependencies)
 writers=[]
 for process in Path('/proc').iterdir():
  if not process.name.isdigit():continue
  try:
   executable=Path(os.readlink(process/'exe')).name
   if not (executable.startswith('swift') or executable.startswith('clang') or executable.endswith('.xctest')):continue
   command_bytes=(process/'cmdline').read_bytes()
   if str(CACHE).encode() in command_bytes:writers.append({'pid':int(process.name),'executable':executable})
  except (FileNotFoundError,ProcessLookupError):continue
 assert not writers,'C cache has an actual compiler/test writer: '+json.dumps(writers)
 r['cacheWriterAdmission']={'actualCompilerOrTestWriters':writers,'pythonControllerArgumentsDoNotIdentifyACompiler':True}
 r['sourceFiles']=len(before);r['freeCacheBefore']=shutil.disk_usage(CACHE).free;r['freeEvidenceBefore']=shutil.disk_usage(OUT).free
 r['resourceEstimate']={'incrementalCompilerAndLogBytes':512*1024*1024,'ownEmergencyFloorBytes':2*1024**3,'nativeOrAppleBuilds':0,'packageWorkers':2}
 assert r['freeCacheBefore']>=2*1024**3+512*1024**2 and r['freeEvidenceBefore']>=32*1024*1024

 retained=Path('/var/lib/pinkha-c-native-preservation-20261126/retained-preservation-products-d3f')
 retained.mkdir(mode=0o700,exist_ok=False)
 retained_products={}
 original_products=CACHE/'out/Products/Debug-linux-aarch64'
 expected_products={
  'PinkhaAnyHostTests-test-runner':'28c2cd2c4935bd59a8de614539115d1d5f54c573abf1dac5f9df43c4db426083',
  'PinkhaAnyHostTests.so':'2c86b12a7d9eff7b2f2011f6a1117b25ecfb9a19eb78b3196b8fe698e704578a'}
 for name,digest in expected_products.items():
  original=original_products/name
  before_stat=original.stat();assert original.resolve()==original and original.is_file() and sha(original)==digest
  shutil.copy2(original,retained/name)
  assert sha(original)==sha(retained/name)==digest
  assert (original.stat().st_dev,original.stat().st_ino,original.stat().st_mode,original.stat().st_size)==(before_stat.st_dev,before_stat.st_ino,before_stat.st_mode,before_stat.st_size)
  assert (retained/name).stat().st_mode==before_stat.st_mode
  retained_products[name]={'sha256':digest,'bytes':before_stat.st_size,'mode':before_stat.st_mode&0o7777}
 original_build=Path('/var/lib/pinkha-c-native-preservation-20261126/native-shared-build-linux1')
 for name in ['result.json','source-before.json','source-after.json','dependencies-after.json','command.json','original.log']:
  shutil.copy2(original_build/name,retained/name)
  assert sha(original_build/name)==sha(retained/name)
 write(retained/'retention.json',{'status':'PASS_EXACT_EXECUTED_SHARED_PRODUCTS_RETAINED','productionCommit':'1e715c3afa3e42611fb454112fba1b8efde17d40','compiledCommit':'d3f03d2a1e9b1bd31cfe82d4d3aa895df78c72ea','nativeExecutionSHA256':'f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b','products':retained_products})
 r['previousExecutedProductsRetentionSHA256']=sha(retained/'retention.json')
 command=['/usr/local/bin/swift','build','--build-tests','--package-path',str(ROOT/'Modules/PinkhaAnyHost'),'--scratch-path',str(CACHE),'--jobs','2']
 write(OUT/'command.json',command)
 env=os.environ.copy()
 with (OUT/'original.log').open('wb') as log:
  child=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  r['pid']=child.pid;save();deadline=time.monotonic()+900
  while child.poll() is None:
   assert time.monotonic()<deadline,'actual shared build bound'
   assert shutil.disk_usage(CACHE).free>=2*1024**3,'own compiler emergency floor'
   time.sleep(.5)
  r['exitCode']=child.wait();r['ownedGroupAbsent']=gone();save()
 after=sources();write(OUT/'source-after.json',after)
 dep_after=json.loads((CACHE/'workspace-state.json').read_bytes())['object']['dependencies']
 write(OUT/'dependencies-after.json',dep_after)
 r['sourceUnchanged']=before==after;r['dependenciesUnchanged']=dependencies==dep_after;r['dependenciesMatchExactRelocation']=expected_dependencies==dep_after
 r['originalAfter']=m.verify_original();r['originalUnchanged']=r['originalBefore']==r['originalAfter']
 log=(OUT/'original.log').read_text(errors='replace')
 r['logSHA256']=sha(OUT/'original.log')
 assert r['exitCode']==0 and r['ownedGroupAbsent']
 assert r['sourceUnchanged'] and r['dependenciesUnchanged'] and r['originalUnchanged']
 assert 'Build complete!' in log and 'Test Suite ' not in log
 products=CACHE/'out/Products/Debug-linux-aarch64'
 r['compiledProducts']={name:{'bytes':(products/name).stat().st_size,'sha256':sha(products/name)} for name in ['PinkhaAnyHostTests-test-runner','PinkhaAnyHostTests.so']}

 r['buildExitCode']=r['exitCode'];r['buildPID']=child.pid
 methods=[
  'testBookmarkDefinitionEmitsItsDistinctNativeLayoutAndExactMappedURLRole',
  'testBookmarkDefinitionRefusesWrongSourceRoleFormatAndReadOnlyAuthority',
  'testBookmarkDefinitionRequiresVisibleRoleAndKeepsBasicAndOtherLayoutsSeparate',
  'testBookmarkDefinitionRetainsSourceURLValuesWithoutMakingURLActionsOrSourceObjectAliases']
 test_command=['/usr/local/bin/swift','test','--skip-build','--package-path',str(ROOT/'Modules/PinkhaAnyHost'),'--scratch-path',str(CACHE),'--jobs','2','--filter','NativeDefinitionPlanTests/testBookmarkDefinition']
 write(OUT/'test-command.json',test_command)
 known_absent=False
 with (OUT/'tests.log').open('wb') as log:
  child=subprocess.Popen(test_command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  r['testPID']=child.pid;r['testsInvoked']=True;save();deadline=time.monotonic()+180
  while child.poll() is None:
   assert time.monotonic()<deadline,'bounded four emitter controls'
   assert shutil.disk_usage(CACHE).free>=2*1024**3,'own test emergency floor'
   time.sleep(.25)
  r['testExitCode']=child.wait();r['testOwnedGroupAbsent']=gone();save()
 test_log=(OUT/'tests.log').read_text(errors='replace')
 r['testLogSHA256']=sha(OUT/'tests.log')
 actual=re.findall(r"Test Case 'NativeDefinitionPlanTests[.]([^']+)' passed",test_log)
 r['passedMethods']=actual;r['expectedMethods']=methods
 r['sourceAfterTests']=sources()==before
 final_dependencies=json.loads((CACHE/'workspace-state.json').read_bytes())['object']['dependencies']
 r['dependenciesAfterTests']=final_dependencies==expected_dependencies
 assert r['testExitCode']==0 and r['testOwnedGroupAbsent'] and sorted(actual)==sorted(methods)
 assert 'Executed 4 tests, with 0 failures' in test_log and 'skipped' not in test_log.lower()
 assert r['sourceAfterTests'] and r['dependenciesAfterTests']
 r['status']='PASS_FOUR_BOOKMARK_EMITTER_CONTROLS'
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
raise SystemExit(0 if r['status']=='PASS_FOUR_BOOKMARK_EMITTER_CONTROLS' else 1)
