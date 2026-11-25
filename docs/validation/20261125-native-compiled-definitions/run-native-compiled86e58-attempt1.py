from pathlib import Path
import subprocess,os,json,time,hashlib,datetime,signal,shutil
root=Path('/Users/m1/builds/anytapy-migration-default-final-20261125')
out=root/'evidence-native-compiled86e58-attempt1';out.mkdir(mode=0o700,exist_ok=False);meta=json.loads((root/'incoming/heart-compiled86e58-source.json').read_text())
go='/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def source_changes():
 changed=[]
 for row in meta['files']:
  p=root/'heart-current'/row['path']
  if not p.exists() and not p.is_symlink():changed.append(row['path']);continue
  raw=os.readlink(p).encode() if p.is_symlink() else p.read_bytes()
  if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=row['gitBlob']:changed.append(row['path'])
 return changed
assert not source_changes()
assert shutil.disk_usage(root).free > (2<<30)+(528<<20)
env=os.environ.copy()
env.update({'PATH':'/Users/m1/toolchains/anytapy-go1.27.4/go/bin:/usr/bin:/bin:/usr/sbin:/sbin','GOWORK':'off','GOTOOLCHAIN':'local',
 'GOCACHE':'/Users/m1/caches/anytapy-go1.27.4-build','GOMODCACHE':'/Users/m1/caches/anytapy-go-mod',
 'GOPROXY':'file:///Users/m1/caches/go-mod/cache/download,https://proxy.golang.org,direct','GOSUMDB':'sum.golang.org',
 'GOMAXPROCS':'2','GOMEMLIMIT':'2GiB','CGO_ENABLED':'1'})
temp=root/'private-temporary-native-compiled86e58-attempt1';temp.mkdir(mode=0o700,exist_ok=False);env['TMPDIR']=str(temp)
private=root/'private-source-capture-native-compiled86e58-attempt1';private.mkdir(mode=0o700,exist_ok=False);env['PINKHA_LOADED_ACCOUNT_PRIVATE_ROOT']=str(private)
methods=['TestCapturedBundledDefinitionRetainsActualNativeDescriptorBytes','TestCapturedBundledDefinitionReceiptsRefuseChangedOrAmbiguousIdentity','TestCapturedBundledDefinitionFallbackRetainsCensusAndCapturedOverridePriority','TestLoadedAccountSourceCheckpointRequiresCurrentNativeSessionAndUnchangedRows']
cmd=[go,'test','-mod=readonly','-count=1','-p=2','-timeout=480s','-json','-run','^('+'|'.join(methods)+')$',
 '-tags','pinkha_loaded_account_witness,pinkha_loaded_account_witness_acceptance',
 '-modfile='+str(root/'candidate-heart-current-native-sync.mod'),'./pkg/lib/anyblockjson/storeresolver','./core/application']
launch={'source':meta['source'],'sourceTree':meta['tree'],'nativeProductSource':meta['productSource'],'methods':methods,'command':cmd,'cwd':str(root/'heart-current'),
 'nativeConfiguration':json.loads((root/'native-configuration-admission.json').read_text()),
 'nativeLibrary':json.loads((root/'incoming/tantivy-v1.0.6-darwin-arm64/native-complete-verification.json').read_text()),
 'environment':{k:env[k] for k in ['GOWORK','GOTOOLCHAIN','GOCACHE','GOMODCACHE','GOPROXY','GOSUMDB','GOMAXPROCS','GOMEMLIMIT','CGO_ENABLED','TMPDIR']},
 'startedAt':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wholeSpaceMigration':False,'freshProcessReopen':False,
 'priorNativeSource':meta['base'],'unaffectedDefaultAndFilePassesReused':True,'resourceAdmission':{'initialFreeBytes':shutil.disk_usage(root).free,'estimatedNewBytes':528<<20,'minimumInitialBytes':(2<<30)+(528<<20),'emergencyFreeBytes':2<<30,'buildParallelism':2,'goMemoryLimit':'2GiB','warmGoCache':True,'combinedProducerOverlap':False,'rationale':'Root authorized 3 descriptor controls plus the affected real checkpoint method; warmed packages/dependencies, at most512MiB compiler/test products plus16MiB fixture; D confirmed no native producer overlap.'}}
(out/'launch.json').write_text(json.dumps(launch,indent=2)+'\n')
started=time.monotonic();stop=None
logpath=out/'original-native-go-test.jsonl'
with logpath.open('wb') as log:
 os.chmod(logpath,0o600)
 p=subprocess.Popen(cmd,cwd=root/'heart-current',env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
 (out/'process.json').write_text(json.dumps({'pid':p.pid,'pgid':p.pid})+'\n')
 minimum_free=shutil.disk_usage(root).free
 while p.poll() is None:
  current_free=shutil.disk_usage(root).free
  minimum_free=min(minimum_free,current_free)
  if current_free<2<<30:
   stop='owned workload emergency disk floor2GiB';break
  if time.monotonic()-started>900:
   stop='controller deadline';break
  time.sleep(2)
 if stop is not None and p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=10)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
 rc=p.wait()
events=[]
for line in logpath.read_text(errors='replace').splitlines():
 try:
  e=json.loads(line)
  if e.get('Action') in ['pass','fail','skip']:events.append({k:e[k] for k in ['Action','Package','Test','Elapsed'] if k in e})
 except json.JSONDecodeError:pass
result={'source':meta['source'],'returncode':rc,'stopReason':stop,'minimumFreeBytes':minimum_free,'seconds':round(time.monotonic()-started,3),'sourceUnchanged':not source_changes(),
 'logSHA256':digest(logpath),'logBytes':logpath.stat().st_size,'events':events,'wholeSpaceMigration':False,'freshProcessReopen':False,
 'compiledDefinitionSemanticCompleteness':False,'finishedAt':datetime.datetime.now(datetime.timezone.utc).isoformat()}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
raise SystemExit(0 if rc==0 and result['sourceUnchanged'] and not stop else 1)
