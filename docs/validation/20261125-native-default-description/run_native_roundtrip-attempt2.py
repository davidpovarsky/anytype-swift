from pathlib import Path
import os,json,subprocess,hashlib,time,socket,signal,base64
root=Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
e=Path('/mnt/development/projects/evidence/migration-final-20261125/default-metadata/native-attempt2')
e.mkdir(mode=0o700,exist_ok=False);os.umask(0o077)
work=e/'private-work';work.mkdir(mode=0o700)
base=Path('/mnt/development/projects/evidence/migration-final-20261125/native-destination-content/native_refusal_continuation.py').read_text()
assert hashlib.sha256(base.encode()).hexdigest()=='bfcd9bd70a16ea126267a9bea1e3b95254d4cfa9e640c5b11aa5c7b019482f50'
base=base.replace("import pathlib,json,subprocess,hashlib,os,socket,signal,time,shutil,urllib.request","import pathlib,json,subprocess,hashlib,os,socket,signal,time,shutil,urllib.request,sys")
base=base.replace("r=pathlib.Path('/Users/m1/builds/pinkha-c-destination-content-20261125/refusal-continuation')","r=pathlib.Path(sys.argv[1])")
base=base.replace("retained target current-content refusal continuation","retained target native default and description phase")
base=base.replace("retained-offline-refusal","retained-offline-default")
base=base.replace("readback and one ordinary property mutation","five prepared operations or their cold current-state readback")
base=base.replace("assert minfree>2*1024**3+64*1024**2","(r/'preflight.json').write_text(json.dumps({'freeBytes':minfree,'estimatedNewBytes':64*1024**2,'emergencyFreeBytes':2*1024**3})+'\\n')\nassert minfree>2*1024**3+64*1024**2")
macRoot='/Users/m1/builds/pinkha-c-destination-content-20261125'
macScript=macRoot+'/native_default_phase-v2.py'
(e/'native_default_phase.py').write_text(base)
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','scaleway-mac']
def remote(code):
 p=subprocess.run(ssh+['python3','-'],input=code,text=True,capture_output=True,timeout=30)
 assert p.returncode==0,p.stderr[-500:]
 return p.stdout
remote("from pathlib import Path\np=Path("+repr(macScript)+")\nassert not p.exists()\np.write_text("+repr(base)+")\n")
relative=['Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/'+f for f in ['AnyNativeImportedDefaultMetadata.swift','AnyHeartNativeDefinitionPlan.swift','AnyNativePropertyStore.swift','AnyDestinationDefinitionCoverage.swift','AnyDestinationMigrationVerifier.swift','AnyDestinationContentProjection.swift','AnyDestinationMigrationExecutor.swift']]
relative+=['Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeDefaultTests.swift','Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyHTTPClient.swift']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p:sha(root/p) for p in relative};(e/'source.json').write_text(json.dumps(before,indent=2)+'\n')
command=['/usr/local/bin/swift','test','--package-path',str(root/'Modules/PinkhaAnyHost'),'--scratch-path','/tmp/pinkha-c-swift-cache-20261125','--skip-update','--jobs','2','--filter','AnyDestinationNativeDefaultTests.testActualNativeDefaultMetadataAndDescriptionColdReopen']
(e/'command.json').write_text(json.dumps(command,indent=2)+'\n')
started=time.monotonic();result={'scope':'five-operation explicit component default/description actual-native roundtrip','result':'RUNNING','phases':[],'wholeSpaceMigration':False}
def save():
 result['seconds']=round(time.monotonic()-started,3);(e/'result.json').write_text(json.dumps(result,indent=2)+'\n')
try:
 for phase in ('execute','reopen'):
  phaseStart=time.monotonic();item={'phase':phase,'result':'RUNNING'};result['phases'].append(item);save()
  assert all(sha(root/k)==v for k,v in before.items()),'frozen Swift source changed'
  output=macRoot+'/default-'+phase+'-attempt2'
  nativeLog=(e/(phase+'-native-controller.log')).open('wb')
  native=subprocess.Popen(ssh+['python3',macScript,output],stdout=nativeLog,stderr=subprocess.STDOUT,start_new_session=True)
  forward=None;forwardLog=None
  try:
   deadline=time.monotonic()+70
   while True:
    assert native.poll() is None,'native controller ended before ready'
    try:
     runtime=json.loads(remote("from pathlib import Path\nprint(Path("+repr(output+'/runtime.json')+").read_text())\n"));break
    except Exception:
     assert time.monotonic()<deadline,'native fixture readiness timeout';time.sleep(.5)
   (e/(phase+'-runtime-original.json')).write_text(json.dumps(runtime,indent=2)+'\n')
   port=int(runtime['baseURL'].rsplit(':',1)[1])
   with socket.socket() as sock:sock.bind(('127.0.0.1',0));local=sock.getsockname()[1]
   forwardCommand=ssh[:-1]+['-N','-L','127.0.0.1:'+str(local)+':127.0.0.1:'+str(port),'-o','ExitOnForwardFailure=yes','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=2',ssh[-1]]
   (e/(phase+'-forward-command.json')).write_text(json.dumps(forwardCommand)+'\n')
   forwardLog=(e/(phase+'-forward.log')).open('wb')
   forward=subprocess.Popen(forwardCommand,stdout=forwardLog,stderr=subprocess.STDOUT,start_new_session=True)
   deadline=time.monotonic()+20
   while True:
    assert forward.poll() is None,'native forward exited'
    try:socket.create_connection(('127.0.0.1',local),timeout=.5).close();break
    except OSError:assert time.monotonic()<deadline;time.sleep(.2)
   runtime['baseURL']='http://127.0.0.1:'+str(local);fixture=e/(phase+'-fixture.json')
   fixture.write_text(json.dumps(runtime,indent=2)+'\n')
   env=os.environ.copy();env.update(TMPDIR='/tmp/pinkha-c-swift-control-20261125',PINKHA_DESTINATION_NATIVE_FIXTURE=str(fixture),PINKHA_DESTINATION_NATIVE_WORK=str(work),PINKHA_DESTINATION_NATIVE_PHASE=phase)
   with (e/(phase+'.log')).open('wb') as log:
    test=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    item['testPID']=test.pid;item['nativePID']=runtime['processID'];item['forwardPID']=forward.pid;save()
    try:code=test.wait(timeout=600)
    except subprocess.TimeoutExpired:
     os.killpg(test.pid,signal.SIGTERM);test.wait(timeout=20);raise
   item.update(returncode=code,logSHA256=sha(e/(phase+'.log')),sourceUnchanged=all(sha(root/k)==v for k,v in before.items()))
   log=(e/(phase+'.log')).read_text(errors='replace')
   assert code==0 and item['sourceUnchanged'] and 'Executed 1 test, with 0 failures' in log and 'skipped' not in log.lower(),'Swift native phase failed'
   item['result']='PASS'
  finally:
   try:remote("from pathlib import Path\nPath("+repr(output+'/finish')+").write_text('phase completed\\n')\n")
   except Exception as error:item['finishError']=str(error)
   if forward is not None and forward.poll() is None:os.killpg(forward.pid,signal.SIGTERM);forward.wait(timeout=20)
   if forward is not None:item['forwardExitCode']=forward.returncode
   if forwardLog:forwardLog.close()
   try:item['nativeControllerExitCode']=native.wait(timeout=30)
   except subprocess.TimeoutExpired:item['nativeControllerExitCode']=None
   nativeLog.close()
   try:
    nativeResult=json.loads(remote("from pathlib import Path\nprint(Path("+repr(output+'/result.json')+").read_text())\n"))
    (e/(phase+'-native-result.json')).write_text(json.dumps(nativeResult,indent=2)+'\n')
    item['nativeResult']=nativeResult['result'];item['nativeExitCode']=nativeResult['exitCode']
   except Exception as error:item['nativeResultError']=str(error)
   item['seconds']=round(time.monotonic()-phaseStart,3);save()
  assert item['nativeControllerExitCode']==0 and item['nativeExitCode']==0 and item['nativeResult']=='PROCESS_CONTINUATION_PASS'
 assert (work/'execute-verification.json').read_bytes()==(work/'reopen-verification.json').read_bytes(),'cold verification changed'
 assert (work/'execute-property.json').read_bytes()==(work/'reopen-property.json').read_bytes(),'cold property definition changed'
 result.update(result='PASS',verificationSHA256=sha(work/'execute-verification.json'),propertySHA256=sha(work/'execute-property.json'),sourceUnchanged=all(sha(root/k)==v for k,v in before.items()))
except Exception as error:result.update(result='FAIL',errorType=type(error).__name__,error=str(error))
finally:save()
print(json.dumps(result))
raise SystemExit(0 if result['result']=='PASS' else 1)
