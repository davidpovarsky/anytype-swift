import pathlib,json,hashlib,subprocess,os,shutil,time,signal,re,tarfile,io
base=pathlib.Path('/Users/m1/builds/pinkha-hanlin-sdk97ffa-20261125')
source=base/'source'; original=base/'component-proof1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def summaries(text):return [{'methods':int(n),'suites':int(s) if s else None,'status':state} for n,s,state in re.findall(r'Test run with (\d+) tests?(?: in (\d+) suites?)? (passed|failed)',text)]
oldrec=json.loads((source/'source-receipt.json').read_text())
assert oldrec['sdk_commit']=='97ffa585d4a4507e6f0c07fbb043291d832b042d'
for item in oldrec['source']:assert sha(source/item['path'])==item['sha256'],item['path']
assert sha(original/'original-test.log')=='adb975407aba2569fdf521f40afdd2f24c4e78a95f21bf81f8a6bca105bfe3f9'
oldresult=json.loads((original/'result.json').read_text());assert oldresult['exit_code']==0 and oldresult['source_unchanged']
oldsummary=summaries((original/'original-test.log').read_text())
assert sum(s['methods'] for s in oldsummary)==49 and all(s['status']=='passed' for s in oldsummary),oldsummary
qualification={'actual_test_exit':0,'methods_passed':49,'original_summaries':oldsummary,'original_log_sha256':sha(original/'original-test.log'),'original_result_sha256':sha(original/'result.json'),'original_controller_result_preserved':True,'controller_failure':'Original parser did not accept the actual in-N-suites wording after successful tests. No test rerun or result replacement.','source_commit':oldrec['sdk_commit'],'original_source_files':len(oldrec['source']),'full_app_acceptance':False}
q=original/'followup-qualification.json';assert not q.exists();q.write_text(json.dumps(qualification,indent=2)+'\n')
frozen=base/'source97-retained';assert not frozen.exists();shutil.copytree(source,frozen)
archive=base/'component-source-44bce-v2.tar.gz'
assert sha(archive)=='02d8162073ae694131b98da64d87e3e0a8cb9990e220529ea55c8036585bbf61'
with tarfile.open(archive) as tf:tf.extractall(base,filter='data')
incoming=base/'source44';rec=json.loads((incoming/'source-receipt.json').read_text())
assert rec['sdk_commit']=='44bcebf687206a37893cb584cf72c6aafbc5ca48' and rec['previous_729_source_files_identical']
for item in oldrec['source']:assert sha(incoming/item['path'])==item['sha256'],item['path']
rec['external_sources']=[]
for name,commit in rec['external_packages_required'].items():
 donor=pathlib.Path('/Users/m1/builds/hanlin-ai-cache-native-20261125/build/SourcePackages/checkouts')/name
 assert subprocess.check_output(['git','-C',str(donor),'rev-parse','HEAD'],text=True).strip()==commit
 raw=subprocess.check_output(['git','-C',str(donor),'archive',commit,'Package.swift','Sources'])
 dest=incoming/'External'/name;dest.mkdir(parents=True,exist_ok=False)
 with tarfile.open(fileobj=io.BytesIO(raw)) as tf:tf.extractall(dest,filter='data')
 for p in dest.rglob('*'):
  if p.is_file():rec['external_sources'].append({'package':name,'commit':commit,'path':str(p.relative_to(incoming)),'sha256':sha(p),'bytes':p.stat().st_size})
rec['support_files']=[{'path':'Scripts/Tests/verify_chatgpt_plan_contract.swift','sha256':'e9726a19dcd4f3ef1487dc5ad548d44825991011dccc1663e8c92e88076057f7'}]
(incoming/'source-receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
for p in incoming.rglob('*'):
 if p.is_file():
  dst=source/p.relative_to(incoming);dst.parent.mkdir(parents=True,exist_ok=True)
  if not dst.exists() or sha(dst)!=sha(p):shutil.copy2(p,dst)
def verify():
 assert sha(source/'Package.swift')==rec['generated_manifest_sha256']
 for item in rec['source']+rec['external_sources']+rec['support_files']:
  assert sha(source/item['path'])==item['sha256'],item['path']
 for name,digest in rec['original_manifests'].items():assert sha(source/'OriginalManifests'/name)==digest
verify()
qualification['reusable_for_sdk_commit']=rec['sdk_commit']
qualification['all_729_original_source_files_identical']=True
qualification['prior_dependency_target_graph_preserved']=True
q.write_text(json.dumps(qualification,indent=2)+'\n')
out=base/'component-proof44';out.mkdir(exist_ok=False)
(out/'source-receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
env=os.environ.copy();env['PATH']='/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin'
env['SWIFTPM_MODULECACHE_OVERRIDE']=str(original/'module-cache')
results=[]
def run(name,argv,seconds,estimate):
 phase=out/name;phase.mkdir(exist_ok=False);log=phase/'original.log';free=shutil.disk_usage('/').free
 assert free>estimate+2*1024**3,('phase growth plus emergency capacity unavailable',name,free,estimate)
 (phase/'command.json').write_text(json.dumps({'argv':argv,'sdk_commit':rec['sdk_commit'],'free_before':free,'estimated_incremental_bytes':estimate,'original_sources_and_tests':True},indent=2)+'\n')
 begin=time.monotonic();minimum=free;stop=None
 with log.open('wb') as stream:
  p=subprocess.Popen(argv,cwd=base,stdout=stream,stderr=subprocess.STDOUT,env=env,start_new_session=True)
  (phase/'ownership.json').write_text(json.dumps({'pid':p.pid,'pgid':p.pid,'started':time.time()})+'\n')
  while p.poll() is None:
   minimum=min(minimum,shutil.disk_usage('/').free)
   if minimum<2*1024**3 or time.monotonic()-begin>seconds:
    stop='disk_emergency' if minimum<2*1024**3 else 'finite_timeout'
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
    break
   time.sleep(1)
 verify()
 text=log.read_text(errors='replace');ss=summaries(text)
 result={'phase':name,'exit':p.returncode,'seconds':time.monotonic()-begin,'stop_reason':stop,'minimum_free_bytes':minimum,'log_sha256':sha(log),'summaries':ss,'source_unchanged':True,'full_app_acceptance':False}
 if 'swift-test' in name:result['passed']=p.returncode==0 and bool(ss) and all(s['status']=='passed' for s in ss) and sum(s['methods'] for s in ss)>0
 else:result['passed']=p.returncode==0
 (phase/'result.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
 print(json.dumps(result),flush=True)
 if p.returncode:print(text[-7000:],flush=True)
 return result
run('notifications-swift-test',['xcrun','swift','test','--package-path',str(source),'--scratch-path',str(original/'build'),'--jobs','2','--filter','HanlinNotificationInvocationTests|HanlinInvocationQueueTests|HanlinShareInvocationTests|HanlinMiniAppSurfaceRoutingTests'],900,800*1024**2)
oauth=out/'oauth-original-contract';oauth.mkdir(exist_ok=False)
wire=source/'Sources/HanlinChatCore'
built=run('oauth-build',['xcrun','swiftc','-parse-as-library','-swift-version','6','-module-cache-path',str(original/'module-cache'),str(wire/'HanlinChatGPTPlanWire.swift'),str(wire/'HanlinChatGPTPlanClient.swift'),str(source/'Scripts/Tests/verify_chatgpt_plan_contract.swift'),'-o',str(oauth/'verify-original-contract')],180,150*1024**2)
if built['passed']:run('oauth-execute',[str(oauth/'verify-original-contract')],120,16*1024**2)
life=pathlib.Path('/Users/m1/builds/pinkha-miniapps-lifetime-20261125');life.mkdir(exist_ok=False)
archive=base/'miniapps-lifetime-source.tar.gz'
assert sha(archive)=='8efbd63629f821fc028cf9fda9188ccdcc475842105dc9e036820369a1f40f38'
with tarfile.open(archive) as tf:tf.extractall(life,filter='data')
lifesource=life/'source'
liferec=json.loads((lifesource/'source-receipt.json').read_text())
for item in liferec['source']:
 if item['original_path'].endswith('PinkhaMiniAppsLifetime.swift'):
  assert sha(lifesource/'Sources/PinkhaHanlinCore/PinkhaMiniAppsLifetime.swift')==item['sha256']
 if item['original_path'].endswith('PinkhaMiniAppsLifetimeTests.swift'):
  assert sha(lifesource/'Tests/PinkhaHanlinCoreTests/PinkhaMiniAppsLifetimeTests.swift')==item['sha256']
run('miniapps-ownership-swift-test',['xcrun','swift','test','--package-path',str(lifesource),'--scratch-path',str(life/'build'),'--jobs','2'],240,250*1024**2)
verify()
summary={'sdk_commit':rec['sdk_commit'],'previous49':qualification,'phases':results,'all_new_phases_passed':all(r['passed'] for r in results),'not_full_app_or_testflight':True}
(out/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({'summary':str(out/'result.json'),'all_new_phases_passed':summary['all_new_phases_passed']}),flush=True)
raise SystemExit(0 if summary['all_new_phases_passed'] else 1)
