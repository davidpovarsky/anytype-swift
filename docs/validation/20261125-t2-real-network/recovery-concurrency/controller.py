import pathlib,os,subprocess,json,hashlib,shutil,socket,time,signal
base=pathlib.Path('/Users/m1/builds/pinkha-t2-network-20261125')
source=base/'source-any548-sdk195';out=base/'original-recovery-concurrency-attempt1'
out.mkdir(exist_ok=False);os.chmod(out,0o700)
receipt=json.loads((base/'source-receipt.json').read_text())
def verify_source():
 for item in receipt['source']:
  root=source if item['commit'].startswith('548f5c') else source/'.runtime-artifacts/sdk-source'
  for file in item['files']:
   p=root/file['path'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==file['sha256'],str(p)
 assert hashlib.sha256((source/'staging.yml').read_bytes()).hexdigest()==receipt['staging_sha256']
verify_source()
for port in range(21001,21007):socket.create_connection(('127.0.0.1',port),3).close()
free=shutil.disk_usage('/').free
assert free>=4*1024**3,'Insufficient initial measured headroom'
for n in ('tmp','gotmp'):(out/n).mkdir()
env=os.environ.copy();env.update({'PATH':'/Users/m1/toolchains/anytapy-go1.27.4/go/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin','GOWORK':'off','GOTOOLCHAIN':'local','GOCACHE':'/Users/m1/caches/anytapy-go1.27.4-build','GOMODCACHE':'/Users/m1/caches/anytapy-go-mod','GOPROXY':'file:///Users/m1/caches/go-mod/cache/download,https://proxy.golang.org,direct','GOMEMLIMIT':'2GiB','GOMAXPROCS':'2','GOFLAGS':'-mod=readonly -p=2','CGO_ENABLED':'1','TMPDIR':str(out/'tmp'),'GOTMPDIR':str(out/'gotmp'),'ANY_E2E_KEEP':'1','ANY_E2E_P2P':'1'})
methods=['TestE2E_MultipeerInviteRefusals','TestE2E_MultipeerCancelJoin','TestE2E_MultipeerOverviewConcurrentEdits','TestE2E_MultipeerP2P','TestE2E_MultipeerP2PColdRestore','TestE2E_MultipeerJoinerMarkdownWrite','TestE2E_MultipeerJoinerDeletePropagation','TestE2E_MultipeerRealtimeSync']
cmd=['/Users/m1/toolchains/anytapy-go1.27.4/go/bin/go','test','-mod=readonly','-count=1','-p=2','-timeout=1500s','-json','-run','^('+ '|'.join(methods)+')$','./internal/e2e']
(out/'command.json').write_text(json.dumps({'argv':cmd,'cwd':str(source),'source_commit':'548f5cd0430a723bd26ea724daeb99991f68b9c9','sdk_commit':'e195f6c07a053c6588e39ffe72ee4fc44cf3d953','original_tests_unchanged':True,'test_environment_flags':{'ANY_E2E_P2P':'1'},'network_config_sha256':receipt['staging_sha256'],'scope':'real independent native processes/accounts against private live AnySync network','admission_bytes':4*1024**3,'emergency_bytes':2*1024**3},indent=2)+'\n')
start=time.monotonic();stop=None;minimum=free
log=out/'original-go-test.jsonl'
with log.open('wb') as stream:
 os.chmod(log,0o600)
 proc=subprocess.Popen(cmd,cwd=source,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
 (out/'ownership.json').write_text(json.dumps({'pid':proc.pid,'pgid':proc.pid,'started':time.time(),'source':str(source)},indent=2)+'\n')
 while proc.poll() is None:
  minimum=min(minimum,shutil.disk_usage('/').free)
  if minimum<2*1024**3 or time.monotonic()-start>1620:
   stop='disk_emergency' if minimum<2*1024**3 else 'finite_timeout'
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=8)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   break
  time.sleep(2)
 code=proc.returncode
# Original fixtures stop their own peers; residual descendants in the owned group are retired.
try:os.killpg(proc.pid,0)
except ProcessLookupError:pass
else:
 os.killpg(proc.pid,signal.SIGTERM);time.sleep(1)
 try:os.killpg(proc.pid,0)
 except ProcessLookupError:pass
 else:os.killpg(proc.pid,signal.SIGKILL)
verify_source()
events=[]
for line in log.read_text(errors='replace').splitlines():
 try:v=json.loads(line)
 except ValueError:continue
 if v.get('Action') in ('pass','fail','skip','run') and v.get('Test'):events.append({k:v[k] for k in ('Action','Test','Elapsed','Time') if k in v})
passed=[v['Test'] for v in events if v['Action']=='pass'];failed=[v['Test'] for v in events if v['Action']=='fail'];skipped=[v['Test'] for v in events if v['Action']=='skip']
result={'exit_code':code,'stop_reason':stop,'seconds':time.monotonic()-start,'minimum_free_bytes':minimum,'source_unchanged':True,'selected_methods':methods,'passed':passed,'failed':failed,'skipped':skipped,'all_original_methods_passed':code==0 and set(methods)<=set(passed) and not failed and not skipped,'original_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'events':events,'full_T2_acceptance':False}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='events'}),flush=True)
