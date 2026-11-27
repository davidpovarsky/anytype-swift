#!/usr/bin/env python3
"""Build the retained native source with the qualified node/LAN progress overlay."""
import hashlib,importlib.util,json,os,shutil,signal,subprocess,time
from pathlib import Path
ROOT=Path('/var/lib/pinkha-c-filesv2-20261126')
BASE=ROOT/'acl-refresh-native1'
QUAL=ROOT/'lan-progress-unit2'
OUT=ROOT/'lan-progress-native1'
QUAL_SHA='5e9df7a7e9a3039938996d68108fab934f6b4fe1888ba3d34097843c0277a64c'
TEMP=Path('/mnt/development/projects/caches/pinkha-w1-lan-native-temp-20261127')
CACHE=Path('/var/lib/pinkha-root-t2-linux-20261126/go-cache')
REPO=Path('/mnt/development/projects/worktrees/anytype-network-final-20261127/Tools/AnyEngineValidation/native_file_peer_comparison')
spec=importlib.util.spec_from_file_location('fv2',REPO/'resume_linux_filesv2_invite.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
os.umask(0o077);OUT.mkdir(mode=0o700,exist_ok=False)
FLOORS={'root':2*1024**3,'development':512*1024**2}
RESERVES={'root':128*1024**2,'development':384*1024**2}
result={'protocol':'pinkha-bounded-node-lan-qualified-native-build-v1','status':'RUNNING','nativeAccountRuns':0,'actualFilesV2Acceptance':False,'processes':[],'errors':[],'resourcePolicy':{'floors':FLOORS,'reserves':RESERVES,'temporaryWorkPath':str(TEMP),'cachePath':str(CACHE)}}
started=time.monotonic();before=None;baseExpected=None;sdkExpected=None
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def inventory(path):
 out={}
 for p in sorted(path.rglob('*')):
  assert not p.is_symlink(),str(p)
  if p.is_file():
   assert p.stat().st_nlink==1,str(p)
   out[str(p.relative_to(path))]={'sha256':sha(p),'bytes':p.stat().st_size}
 return out
def sdk_inventory(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}
def save():
 result['seconds']=round(time.monotonic()-started,3);m.atomic(OUT/'result.json',result)
def guard(admission=False):
 values={'root':shutil.disk_usage(OUT).free,'development':shutil.disk_usage('/mnt/development').free}
 for k,v in values.items():
  result.setdefault('minimumFreeBytes',{})[k]=min(result.get('minimumFreeBytes',{}).get(k,v),v)
  assert v>=FLOORS[k]+(RESERVES[k] if admission else 0),'resource reserve: '+k
 assert not (OUT/'abort').exists(),'owned abort'
 return values
def absent(pid):
 try:os.killpg(pid,0)
 except ProcessLookupError:return True
 return False
def interrupt(*_):raise RuntimeError('owned native build interrupted')
signal.signal(signal.SIGTERM,interrupt);signal.signal(signal.SIGINT,interrupt)
signal.pthread_sigmask(signal.SIG_UNBLOCK,{signal.SIGTERM,signal.SIGINT})
try:
 result['sourceBefore']=m.source_admission();result['controllerSHA256']=sha(__file__)
 qualified=json.loads(m.pinned(QUAL/'result.json',QUAL_SHA,4*1024**2))
 assert qualified['status']=='PASS_BASELINE_FIVE_FAILURES_CORRECTED_SEVENTEEN_PASSES'
 assert qualified['baselineFailureReproduced'] and qualified['allOwnedGroupsPositivelyAbsent'] and qualified['originalOverlayUnchanged'] and qualified['baselineTestSourcesUnchanged'] and qualified['aclAndSignatureSourcesUnchanged']
 assert len(qualified['baseline'])==7 and sum(x['action']=='fail' for x in qualified['baseline'])==5
 assert len(qualified['corrected'])==17 and all(x['action']=='pass' for x in qualified['corrected'])
 sdkExpected=json.loads(m.pinned(QUAL/'corrected-source-manifest.json',qualified['correctedManifestSHA256'],4*1024**2))
 assert sdk_inventory(QUAL/'sdk-source')==sdkExpected and len(sdkExpected)==718
 result['focusedTestReceiptSHA256']=QUAL_SHA
 result['sdkManifestSHA256']=qualified['correctedManifestSHA256']
 baseReceipt=json.loads(m.pinned(BASE/'result.json','bfafdf6d7304786726235fd1d2f3065dbf5782091123f03fbd6bb54b09328380',4*1024**2))
 assert baseReceipt['status']=='PASS_BUILD_ONLY' and baseReceipt['allOwnedGroupsPositivelyAbsent']
 baseManifest=json.loads(m.pinned(BASE/'source-manifest.json','44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68',8*1024**2))
 baseExpected=baseManifest['files'];assert inventory(BASE/'source')==baseExpected and len(baseExpected)==1597
 assert sha(BASE/'any')=='79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857'
 assert CACHE.is_symlink() and str(CACHE.resolve())=='/mnt/development/projects/caches/pinkha-w1-t2-go-cache-20261127'
 assert OUT.stat().st_dev!=CACHE.resolve().stat().st_dev
 result['resourcePolicy']['cacheResolvedPath']=str(CACHE.resolve());result['resourcePolicy']['admissionFreeBytes']=guard(True)
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 assert mem>=3*1024**3,'native compile requires3GiB MemAvailable admission'
 result['resourcePolicy']['memAvailableBefore']=mem
 assert sum(v['bytes'] for v in baseExpected.values())+(BASE/'any').stat().st_size<128*1024**2
 result['resourceEstimateEvidence']={'previousQualifiedNativeBytes':(BASE/'any').stat().st_size,'copiedSourceBytes':sum(v['bytes'] for v in baseExpected.values()),'previousNativeBuildSeconds':86.205,'cacheAndTempAreEstimatedNotMeasuredPeak':True}
 source=OUT/'source';shutil.copytree(BASE/'source',source,copy_function=shutil.copy2);assert inventory(source)==baseExpected
 for name in qualified['sourceDelta']:
  src=QUAL/'sdk-source'/name;dst=source/'.runtime-artifacts/sdk-source'/name
  assert sha(src)==sdkExpected[name]
  dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
 before=inventory(source)
 delta={k for k in before.keys()|baseExpected.keys() if before.get(k)!=baseExpected.get(k)}
 assert delta=={'.runtime-artifacts/sdk-source/'+k for k in qualified['sourceDelta']}
 assert len(before)==1599
 result['sourceChanges']=sorted(delta);result['sourceFiles']=len(before)
 m.atomic(OUT/'source-manifest.json',{'protocol':'qualified-native-any-with-signed-acl-and-bounded-lan-progress-v1','baseAnyCommit':'8fbd1e819fb132ac0e0a848d2ddf5c5714189b81','baseSDKCommit':'c1fd59bd8f0ed62471234ec1a65a402d22eab6a9','baseNativeSourceManifestSHA256':'44abb44523e01b4631c8eff5f3ff183aca17f58b472fbb041e7a1e501028ca68','focusedTestReceiptSHA256':QUAL_SHA,'files':before})
 result['sourceManifestSHA256']=sha(OUT/'source-manifest.json')
 TEMP.mkdir(mode=0o700,exist_ok=False);assert TEMP.resolve()==TEMP and TEMP.stat().st_dev==CACHE.resolve().stat().st_dev
 env=os.environ.copy();env.update(GOTOOLCHAIN='local',GOMAXPROCS='2',GOMEMLIMIT='1GiB',GOCACHE=str(CACHE),GOMODCACHE='/root/go/pkg/mod',GOTMPDIR=str(TEMP),TMPDIR=str(TEMP),CGO_ENABLED='1',GOWORK='off',GOFLAGS='-mod=readonly',GOPROXY='off',GOSUMDB='off')
 result['environment']={k:env[k] for k in ('GOTOOLCHAIN','GOMAXPROCS','GOMEMLIMIT','GOCACHE','GOMODCACHE','GOTMPDIR','TMPDIR','CGO_ENABLED','GOWORK','GOFLAGS','GOPROXY','GOSUMDB')}
 command=['/usr/local/bin/go','build','-p','2','-o',str(OUT/'any'),'./cmd/any']
 row={'label':'native-build','command':command,'forcedKill':False,'resourceStopped':False};result['processes'].append(row)
 begin=time.monotonic();guard()
 with (OUT/'build.log').open('xb') as stream:
  proc=subprocess.Popen(command,cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True);row.update(pid=proc.pid,pgid=proc.pid);save()
  try:
   while proc.poll() is None:
    guard();assert time.monotonic()-begin<360,'bounded native build deadline';time.sleep(.5)
  except BaseException:
   row['resourceStopped']=True;raise
  finally:
   if proc.poll() is None:
    if not absent(proc.pid):os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
     if not absent(proc.pid):os.killpg(proc.pid,signal.SIGKILL);row['forcedKill']=True
     proc.wait(timeout=5)
   row.update(exitCode=proc.returncode,seconds=round(time.monotonic()-begin,3),groupPositivelyAbsent=absent(proc.pid))
 row['logSHA256']=sha(OUT/'build.log')
 assert row['exitCode']==0 and row['groupPositivelyAbsent'] and not row['forcedKill'] and not row['resourceStopped'],'native build lifecycle failure'
 result['binary']={'path':str(OUT/'any'),'sha256':sha(OUT/'any'),'bytes':(OUT/'any').stat().st_size}
 result['status']='PASS_BUILD_ONLY'
except BaseException as error:
 result['status']='FAIL_NATIVE_BUILD';result['errors'].append({'type':type(error).__name__,'message':str(error)})
finally:
 try:
  result['sourceAfter']=m.source_admission();assert result['sourceAfter']==result['sourceBefore']
  result['baseNativeSourceUnchanged']=baseExpected is not None and inventory(BASE/'source')==baseExpected;assert result['baseNativeSourceUnchanged']
  result['qualifiedSDKUnchanged']=sdkExpected is not None and sdk_inventory(QUAL/'sdk-source')==sdkExpected;assert result['qualifiedSDKUnchanged']
  result['isolatedSourceUnchanged']=before is not None and inventory(OUT/'source')==before
  result['allOwnedGroupsPositivelyAbsent']=all(p.get('groupPositivelyAbsent') and not p.get('forcedKill') and not p.get('resourceStopped') for p in result['processes'])
  if result['status']=='PASS_BUILD_ONLY':assert result['allOwnedGroupsPositivelyAbsent'] and result['isolatedSourceUnchanged']
 except BaseException as error:
  result['status']='FAIL_NATIVE_BUILD';result['errors'].append({'finalization':type(error).__name__,'message':str(error)})
 result['freeBytesAfter']={'root':shutil.disk_usage(OUT).free,'development':shutil.disk_usage('/mnt/development').free};save()
 print(json.dumps({'status':result['status'],'result':str(OUT/'result.json'),'sha256':sha(OUT/'result.json'),'seconds':result['seconds'],'errors':result['errors']}))
raise SystemExit(0 if result['status']=='PASS_BUILD_ONLY' else 1)
