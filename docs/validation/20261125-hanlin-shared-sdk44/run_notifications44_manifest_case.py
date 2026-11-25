import pathlib,json,hashlib,subprocess,os,shutil,time,signal,re
base=pathlib.Path('/Users/m1/builds/pinkha-hanlin-sdk97ffa-20261125');source=base/'source'
prior=base/'component-proof44';out=base/'component-proof44-notifications2';out.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((source/'source-receipt.json').read_text())
assert receipt['sdk_commit']=='44bcebf687206a37893cb584cf72c6aafbc5ca48'
old=(source/'Package.swift').read_text();assert sha(source/'Package.swift')==receipt['generated_manifest_sha256']
assert old.count('.when(platforms: [.ios, .macos])')==1
(out/'generated-manifest-before.swift').write_text(old)
fixed=old.replace('.when(platforms: [.ios, .macos])','.when(platforms: [.iOS, .macOS])')
(source/'Package.swift').write_text(fixed)
receipt['projection_correction']={'reason':'Map canonical dump-package lowercase platform identifiers to PackageDescription iOS/macOS case; preserve original platform condition, modules, dependencies, resource rules and test bodies.','previous_manifest_sha256':receipt['generated_manifest_sha256'],'original_failure':str(prior/'notifications-swift-test/result.json')}
receipt['generated_manifest_sha256']=sha(source/'Package.swift')
(source/'source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
(out/'source-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def verify():
 assert sha(source/'Package.swift')==receipt['generated_manifest_sha256']
 for item in receipt['source']+receipt['external_sources']+receipt['support_files']:assert sha(source/item['path'])==item['sha256'],item['path']
verify()
free=shutil.disk_usage('/').free;assert free>800*1024**2+2*1024**3
command=['xcrun','swift','test','--package-path',str(source),'--scratch-path',str(base/'component-proof1/build'),'--jobs','2','--filter','HanlinNotificationInvocationTests|HanlinInvocationQueueTests|HanlinShareInvocationTests|HanlinMiniAppSurfaceRoutingTests']
(out/'command.json').write_text(json.dumps({'argv':command,'source_commit':receipt['sdk_commit'],'free_before':free,'estimated_incremental_bytes':800*1024**2,'original_sources_and_tests_unchanged':True,'previous49_not_repeated':True,'successful_oauth_and_lifetime_not_repeated':True},indent=2)+'\n')
env=os.environ.copy();env['PATH']='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin';env['SWIFTPM_MODULECACHE_OVERRIDE']=str(base/'component-proof1/module-cache')
log=out/'original.log';start=time.monotonic();minimum=free;stop=None
with log.open('wb') as stream:
 p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,cwd=base,env=env,start_new_session=True)
 (out/'ownership.json').write_text(json.dumps({'pid':p.pid,'pgid':p.pid,'started':time.time()})+'\n')
 while p.poll() is None:
  minimum=min(minimum,shutil.disk_usage('/').free)
  if minimum<2*1024**3 or time.monotonic()-start>900:
   stop='disk_emergency' if minimum<2*1024**3 else 'finite_timeout';os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
   break
  time.sleep(1)
verify();text=log.read_text(errors='replace')
summary=[{'methods':int(n),'suites':int(s) if s else None,'status':state} for n,s,state in re.findall(r'Test run with (\d+) tests?(?: in (\d+) suites?)? (passed|failed)',text)]
result={'exit':p.returncode,'seconds':time.monotonic()-start,'stop_reason':stop,'minimum_free_bytes':minimum,'log_sha256':sha(log),'summaries':summary,'source_unchanged':True,'passed':p.returncode==0 and bool(summary) and all(s['status']=='passed' for s in summary),'full_app_acceptance':False}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
if not result['passed']:print(text[-12000:],flush=True)
raise SystemExit(0 if result['passed'] else 1)
