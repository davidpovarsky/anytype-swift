import pathlib,json,hashlib,subprocess,os,shutil,time,signal,re
base=pathlib.Path('/Users/m1/builds/pinkha-hanlin-sdk97ffa-20261125')
source=base/'source';out=base/'component-proof1'
out.mkdir(exist_ok=False)
receipt=json.loads((source/'source-receipt.json').read_text())
def verify():
 assert hashlib.sha256((source/'Package.swift').read_bytes()).hexdigest()==receipt['generated_manifest_sha256']
 for item in receipt['source']:
  assert hashlib.sha256((source/item['path']).read_bytes()).hexdigest()==item['sha256'],item['path']
 for name,sha in receipt['original_manifests'].items():
  assert hashlib.sha256((source/'OriginalManifests'/name).read_bytes()).hexdigest()==sha
verify()
free=shutil.disk_usage('/').free
estimated=3*1024**3
assert free>estimated+2*1024**3, 'Measured source closure build plus emergency headroom unavailable'
env=os.environ.copy();env['PATH']='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'
env['SWIFTPM_MODULECACHE_OVERRIDE']=str(out/'module-cache')
filters='HanlinTransientToolCatalogTests|HanlinCatalogReloadCancellationTests|HanlinChatGPTPlanTests|HanlinCanonicalEntrypointProjectionTests|HanlinScriptMiniAppRegistrationTests|StoreSystemPathTests|versionOneCheckpointCanBeRestoredWithoutDestructiveMigration|HanlinCapturedStreamReplayTests|HanlinNativeStructuredResponseTests|HanlinInjectedProviderTests|HanlinAppleToolInputBoundaryTests'
cmd=['xcrun','swift','test','--package-path',str(source),'--scratch-path',str(out/'build'),'--jobs','2','--filter',filters]
(out/'command.json').write_text(json.dumps({'argv':cmd,'sdk_commit':receipt['sdk_commit'],'swift_ai_commit':receipt['swift_ai_commit'],'source_files':len(receipt['source']),'source_bytes':sum(i['bytes'] for i in receipt['source']),'original_sources_and_tests_unchanged':True,'estimated_compiler_cache_bytes':estimated,'free_before':free},indent=2)+'\n')
log=out/'original-test.log';start=time.monotonic();minimum=free;stop=None
with log.open('wb') as f:
 proc=subprocess.Popen(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,cwd=base,start_new_session=True)
 (out/'ownership.json').write_text(json.dumps({'pid':proc.pid,'pgid':proc.pid,'started':time.time()},indent=2)+'\n')
 while proc.poll() is None:
  minimum=min(minimum,shutil.disk_usage('/').free)
  if minimum<2*1024**3 or time.monotonic()-start>1800:
   stop='disk_emergency' if minimum<2*1024**3 else 'finite_timeout'
   os.killpg(proc.pid,signal.SIGTERM)
   try:proc.wait(timeout=10)
   except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
   break
  time.sleep(2)
verify()
text=log.read_text(errors='replace')
summary=re.findall(r'Test run with (\d+) tests? (passed|failed).*',text)
result={'exit_code':proc.returncode,'stop_reason':stop,'seconds':time.monotonic()-start,'minimum_free_bytes':minimum,'source_unchanged':True,'original_log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),'swift_testing_summaries':summary,'full_app_acceptance':False}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
if proc.returncode!=0:
 print(text[-18000:]);raise SystemExit(proc.returncode)
assert summary and all(status=='passed' for _,status in summary) and sum(int(n) for n,_ in summary)>0
oauth=base/'oauth-proof1';oauth.mkdir(exist_ok=False)
src=source/'Sources/HanlinChatCore'
command=['xcrun','swiftc','-parse-as-library','-swift-version','6','-module-cache-path',str(out/'module-cache'),str(src/'HanlinChatGPTPlanWire.swift'),str(src/'HanlinChatGPTPlanClient.swift'),str(source/'Scripts/Tests/verify_chatgpt_plan_contract.swift'),'-o',str(oauth/'verify-original-contract')]
with (oauth/'build.log').open('w') as f:
 p=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,env=env,cwd=base,timeout=180)
proof={'build_exit':p.returncode,'argv':command,'original_source_and_fixture':True}
if p.returncode==0:
 p=subprocess.run([str(oauth/'verify-original-contract')],capture_output=True,text=True,env=env,cwd=base,timeout=120)
 (oauth/'original-contract.log').write_text(p.stdout+p.stderr)
 proof.update({'run_exit':p.returncode,'output':p.stdout,'log_sha256':hashlib.sha256((oauth/'original-contract.log').read_bytes()).hexdigest()})
else:
 proof['build_tail']=(oauth/'build.log').read_text()[-6000:]
(oauth/'result.json').write_text(json.dumps(proof,indent=2)+'\n')
verify();print(json.dumps(proof),flush=True)
raise SystemExit(p.returncode)
