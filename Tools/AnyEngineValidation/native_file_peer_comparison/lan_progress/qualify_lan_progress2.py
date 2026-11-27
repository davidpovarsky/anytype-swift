#!/usr/bin/env python3
"""Qualify bounded node discovery against the original shared-worker starvation."""
import hashlib,importlib.util,json,os,shutil,signal,subprocess,time
from pathlib import Path
ROOT=Path('/var/lib/pinkha-c-filesv2-20261126')
OUT=ROOT/'lan-progress-unit2'
BASE=ROOT/'acl-refresh-overlay1/sdk-source'
SDK=OUT/'sdk-source'
INPUT=ROOT/'lan-progress-inputs2.json'
INPUT_SHA='26dfe9c5dfff380af0e584f6094ffbcc0952565d2c12e91be631aca6928d9d29'
TEMP=Path('/mnt/development/projects/caches/pinkha-w1-lan-progress-temp2-20261127')
REPO=Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec=importlib.util.spec_from_file_location('fv2',REPO/'resume_linux_filesv2_invite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.umask(0o077)
OUT.mkdir(mode=0o700,exist_ok=False)
FLOORS={'root':2*1024**3,'development':512*1024**2}
RESERVES={'root':64*1024**2,'development':256*1024**2}
result={'protocol':'pinkha-lan-node-progress-baseline-and-corrected-v1','status':'RUNNING','nativeAccountProcesses':0,'accountWrites':0,'processes':[],'errors':[],'resourcePolicy':{'floors':FLOORS,'reserves':RESERVES}}
started=time.monotonic();expected=None;fixed=None;process=None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inv(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}
def save():
 result['seconds']=round(time.monotonic()-started,3)
 m.atomic(OUT/'result.json',result)
def free():return {'root':shutil.disk_usage(OUT).free,'development':shutil.disk_usage('/mnt/development').free}
def guard(admission=False):
 values=free()
 for key,value in values.items():
  result.setdefault('minimumFreeBytes',{})[key]=min(result.get('minimumFreeBytes',{}).get(key,value),value)
  assert value>=FLOORS[key]+(RESERVES[key] if admission else 0),'resource reserve: '+key
 assert not (OUT/'abort').exists(),'owned abort'
 return values
def absent(pid):
 try:os.killpg(pid,0)
 except ProcessLookupError:return True
 return False
def interrupt(*_):raise RuntimeError('owned controller interrupted')
signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
def run(label,pattern,expected_code):
 global process
 guard(True)
 command=['/usr/local/bin/go','test','-json','-count=1','-p=2','-timeout=90s','-run',pattern,'./internal/anysyncx']
 log=OUT/(label+'.log');row={'label':label,'command':command,'forcedKill':False,'resourceStopped':False};result['processes'].append(row)
 began=time.monotonic()
 with log.open('xb') as stream:
  process=subprocess.Popen(command,cwd=SDK,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
  row.update(pid=process.pid,pgid=process.pid);save()
  try:
   while process.poll() is None:
    guard();assert time.monotonic()-began<300,'bounded compile and test deadline'
    time.sleep(.5)
  except BaseException:
   row['resourceStopped']=True
   raise
  finally:
   if process.poll() is None:
    if not absent(process.pid):os.killpg(process.pid,signal.SIGTERM)
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
     if not absent(process.pid):os.killpg(process.pid,signal.SIGKILL);row['forcedKill']=True
     process.wait(timeout=5)
   row.update(exitCode=process.returncode,seconds=round(time.monotonic()-began,3),groupPositivelyAbsent=absent(process.pid))
   process=None
 row['logSHA256']=sha(log);save()
 assert row['exitCode']==expected_code and row['groupPositivelyAbsent'] and not row['forcedKill'] and not row['resourceStopped'],label+' process outcome'
 events=[]
 for line in log.read_text().splitlines():
  try:v=json.loads(line)
  except json.JSONDecodeError:continue
  if isinstance(v,dict) and v.get('Test') and v.get('Action') in ('pass','fail','skip'):events.append({'name':v['Test'],'action':v['Action'],'seconds':v.get('Elapsed')})
 result[label]=events;save();return events
try:
 result['controllerSHA256']=sha(__file__)
 prior=json.loads(m.pinned(ROOT/'lan-progress-unit1/result.json','77e1d1ebc5f8c19c0427fdad78f88aa912659f56882f05323522ce17ce58b984',4*1024**2))
 assert prior['status']=='FAIL_QUALIFICATION' and prior['allOwnedGroupsPositivelyAbsent'] and len(prior['baseline'])==7
 result['priorFixtureFailureReceiptSHA256']=sha(ROOT/'lan-progress-unit1/result.json')
 result['fixtureCorrection']='Explicit empty fakeLocalPeers instead of typed nil pointer; all acceptance assertions unchanged.'
 result['sourceBefore']=m.source_admission()
 expected=json.loads(m.pinned(ROOT/'acl-refresh-overlay1/sdk-overlay-manifest.json','81fb6bf29c672010f7fe98554ae562b7e75b6154f10e933ac5682fe3916c4a4a',4*1024**2))
 assert inv(BASE)==expected and len(expected)==716
 inputs=json.loads(m.pinned(INPUT,INPUT_SHA,128*1024))
 assert set(inputs)=={'internal/anysyncx/peermanager.go','internal/anysyncx/peerprogress.go','internal/anysyncx/peerprogress_test.go'}
 result['inputSHA256']=INPUT_SHA
 result['admissionFreeBytes']=guard(True)
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 assert mem>=2*1024**3,'2GiB available memory required'
 result['resourcePolicy']['memAvailableBefore']=mem
 TEMP.mkdir(mode=0o700,exist_ok=False)
 shutil.copytree(BASE,SDK,copy_function=shutil.copy2)
 assert inv(SDK)==expected
 test_path=SDK/'internal/anysyncx/peerprogress_test.go';test_path.write_text(inputs['internal/anysyncx/peerprogress_test.go'])
 gofmt=Path('/usr/local/bin/go').resolve().parent/'gofmt'
 assert gofmt.is_file()
 subprocess.run([str(gofmt),'-w',str(test_path)],check=True,timeout=10)
 baseline=inv(SDK);m.atomic(OUT/'baseline-source-manifest.json',baseline)
 assert set(baseline)-set(expected)=={'internal/anysyncx/peerprogress_test.go'} and all(baseline[k]==v for k,v in expected.items())
 result['baselineManifestSHA256']=sha(OUT/'baseline-source-manifest.json')
 env=os.environ.copy();env.update(GOTOOLCHAIN='local',GOMAXPROCS='2',GOMEMLIMIT='1GiB',GOCACHE='/var/lib/pinkha-root-t2-linux-20261126/go-cache',GOMODCACHE='/root/go/pkg/mod',GOTMPDIR=str(TEMP),TMPDIR=str(TEMP),CGO_ENABLED='1',GOWORK='off',GOFLAGS='-mod=readonly',GOPROXY='off',GOSUMDB='off')
 result['environment']={k:env[k] for k in ('GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','TMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB')}
 names={'TestLANProgressResponsiblePeersBoundNodeWait','TestLANProgressBroadcastPeersBoundNodeWait','TestLANProgressKeepAliveCoalescesQueuedSubscription','TestLANProgressKeepAliveQueueRejectionAllowsRetry','TestLANProgressKeepAliveBoundsConcurrentNodeLookup','TestLANProgressKeepAliveLeavesSharedWorkersAvailable','TestLANProgressNodeOnlyFailureStillSurfaces'}
 fails=names-{'TestLANProgressKeepAliveQueueRejectionAllowsRetry','TestLANProgressNodeOnlyFailureStillSurfaces'}
 original=run('baseline','^TestLANProgress',1)
 assert {v['name'] for v in original}==names and len(original)==7
 assert {v['name'] for v in original if v['action']=='fail'}==fails and not any(v['action']=='skip' for v in original)
 assert inv(SDK)==baseline
 result['baselineFailureReproduced']=True;save()
 for name in ('internal/anysyncx/peermanager.go','internal/anysyncx/peerprogress.go'):
  (SDK/name).write_text(inputs[name])
  subprocess.run([str(gofmt),'-w',str(SDK/name)],check=True,timeout=10)
 fixed=inv(SDK);assert fixed['internal/anysyncx/peerprogress_test.go']==baseline['internal/anysyncx/peerprogress_test.go']
 changed={k for k in set(fixed)|set(expected) if fixed.get(k)!=expected.get(k)}
 assert changed==set(inputs)
 m.atomic(OUT/'corrected-source-manifest.json',fixed);result['correctedManifestSHA256']=sha(OUT/'corrected-source-manifest.json')
 old={'TestGetResponsiblePeersFoldsLocalPeers','TestGetResponsiblePeersLocalOnlyWhenNodesDown','TestGetResponsiblePeersNodeErrorWhenNobodyReachable','TestGetLocalPeersRemovesUnreachableAfterStrikes','TestGetLocalPeersStrikeResetsOnSuccess','TestGetLocalPeersKeepsPeerOnCancelledContext','TestGetBroadcastPeersIsNodesPlusLocal','TestNoteNodeStateWakesOnTransition','TestBroadcastPark_OverflowParksAndReportsSuccess','TestBroadcastPark_RetriesUntilDelivered'}
 corrected=run('corrected','^('+'|'.join(sorted(names|old))+')$',0)
 assert len(corrected)==len(names|old) and {v['name'] for v in corrected}==names|old and all(v['action']=='pass' for v in corrected)
 assert inv(SDK)==fixed
 result.update(status='PASS_BASELINE_FIVE_FAILURES_CORRECTED_SEVENTEEN_PASSES',sourceDelta=sorted(changed),baselineTestSourcesUnchanged=True,aclAndSignatureSourcesUnchanged=True)
except BaseException as error:
 result['status']='FAIL_QUALIFICATION';result['errors'].append({'type':type(error).__name__,'message':str(error)})
finally:
 try:
  result['sourceAfter']=m.source_admission()
  result['originalOverlayUnchanged']=expected is not None and inv(BASE)==expected
  assert result['originalOverlayUnchanged']
  result['allOwnedGroupsPositivelyAbsent']=all(p.get('groupPositivelyAbsent') and not p.get('forcedKill') and not p.get('resourceStopped') for p in result['processes'])
  if result['status'].startswith('PASS'):assert result['allOwnedGroupsPositivelyAbsent'] and fixed is not None and inv(SDK)==fixed
 except BaseException as error:
  result['status']='FAIL_QUALIFICATION';result['errors'].append({'finalization':type(error).__name__,'message':str(error)})
 result['freeBytesAfter']=free();save()
 print(json.dumps({'status':result['status'],'result':str(OUT/'result.json'),'sha256':sha(OUT/'result.json'),'seconds':result['seconds'],'errors':result['errors']}))
raise SystemExit(0 if result['status'].startswith('PASS_') else 1)
