import pathlib,json,subprocess,hashlib,os,socket,signal,time,shutil,urllib.request,sys
r=pathlib.Path(sys.argv[1])
r.mkdir(mode=0o700,exist_ok=False);os.umask(0o077)
original=r.parent/'attempt2';runtime=json.loads((original/'runtime.json').read_text())
binary=pathlib.Path('/Users/m1/builds/pinkha-c-native-file-peer-20261125/any548')
source=pathlib.Path('/Users/m1/builds/pinkha-t2-network-20261125/source-any548-sdk195')
profile=original/'offline.sb';data=original/'private-account'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(binary)==runtime['binarySHA256']
assert sha(profile)=='e210de323e5d671bb6b63b79ce1481f8314b5ac2fd65d65a180d381294ee2fa1'
sources=json.loads((source.parent/'source-receipt.json').read_text())
def check():
 out=[]
 for entry in sources['source']:
  root=source if entry['commit']=='548f5cd0430a723bd26ea724daeb99991f68b9c9' else source/'.runtime-artifacts/sdk-source'
  for f in entry['files']:assert sha(root/f['path'])==f['sha256']
  out.append({'commit':entry['commit'],'files':len(entry['files']),'unchanged':True})
 return out
result={'scope':'retained target native default and description phase','result':'RUNNING','originalControllerResult':'FAIL retained separately','sourceBefore':check(),'binarySHA256':sha(binary),'offlineProfileSHA256':sha(profile),'privateSourceReused':True,'wholeSpaceMigration':False,'cloudCustody':False,'forcedKill':False}
start=time.monotonic();minfree=shutil.disk_usage(r).free
assert minfree>2*1024**3+64*1024**2
result['resourcePolicy']={'estimatedNewBytes':64*1024**2,'emergencyFreeBytes':2*1024**3,'reason':'Reused original warmed native account/binary; five prepared operations or their cold current-state readback; no compilation/download.'}
with socket.socket() as s:
 s.bind(('127.0.0.1',0));port=s.getsockname()[1]
env={k:v for k,v in os.environ.items() if not k.startswith('ANY_')}
env.update(ANY_DATA_DIR=str(data),GOMAXPROCS='2',GOMEMLIMIT='2GiB')
cmd=['/usr/bin/sandbox-exec','-f',str(profile),str(binary),'run','--config',str(data/'config.yaml'),'--data-dir',str(data),'--addr','127.0.0.1:'+str(port)]
(r/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
log=(r/'private-native.log').open('wb')
p=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result['processID']=p.pid
base='http://127.0.0.1:'+str(port)
def get(path):
 with urllib.request.urlopen(base+path,timeout=2) as reply:return json.load(reply)
def guard():
 global minfree
 minfree=min(minfree,shutil.disk_usage(r).free)
 assert minfree>=2*1024**3,'disk emergency'
 assert time.monotonic()-start<900,'bounded continuation deadline'
 assert p.poll() is None,'native process stopped unexpectedly'
try:
 deadline=time.monotonic()+60
 while True:
  guard()
  try:
   get('/v1/health');break
  except OSError:assert time.monotonic()<deadline;time.sleep(.25)
 assert get('/v1/account')['id']==runtime['accountID']
 sync=get('/v1/spaces/'+runtime['spaceID']+'/sync-status')
 result['syncStatus']={k:sync.get(k) for k in ('state','networkPeers','localPeers','globalPeers','p2p')}
 assert all(sync[k]==0 for k in ('networkPeers','localPeers','globalPeers'))
 runtime.update(baseURL=base,processID=p.pid,phase='retained-offline-default')
 (r/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
 while not (r/'finish').exists():guard();time.sleep(.25)
 result['result']='PROCESS_CONTINUATION_PASS'
except Exception as e:
 result.update(result='FAIL',errorType=type(e).__name__,error=str(e))
finally:
 if p.poll() is None:
  os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=20)
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=5);result['forcedKill']=True
 result['exitCode']=p.returncode;log.close()
 try:result['sourceAfter']=check()
 except Exception as e:result.update(result='FAIL',sourceAfterError=type(e).__name__)
 if p.returncode!=0 or result['forcedKill']:result['result']='FAIL'
 result.update(seconds=round(time.monotonic()-start,3),minimumFreeBytes=minfree,privateNativeLogSHA256=sha(r/'private-native.log'))
 (r/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if result['result']=='PROCESS_CONTINUATION_PASS' else 1)
