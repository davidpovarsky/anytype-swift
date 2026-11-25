from pathlib import Path
import os,json,hashlib,subprocess,shutil,time,signal,sys,resource
root=Path('/Users/m1/builds/anytype-original-network-acceptance-20261125/revision-cas-50426b50-d4360923')
attempt=root/'attempt-1';attempt.mkdir(mode=0o700)
evidence=attempt/'evidence';evidence.mkdir(mode=0o700)
work=attempt/'work';work.mkdir(mode=0o700);(work/'tmp').mkdir(mode=0o700)
donor=Path('/Users/m1/builds/anytype-c7e9935eb36a-native-import/build/Heart-Owned-Annotation-Import')
fixture=Path('/Users/m1/builds/anytype-original-network-acceptance-20261125/run-1-private')
manifest=root/'transfer/SOURCE_INPUTS.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,obj):
 p=evidence/name
 with p.open('x') as f:json.dump(obj,f,sort_keys=True,indent=2);f.write('\n')
def ownbytes(p):
 return sum(x.stat().st_size for x in p.rglob('*') if x.is_file() and not x.is_symlink())
expected_manifest='6c2efa18821e47a342c9e0720d8060bd05dfd773993ed84bc8b59e36dc119b38'
assert sha(manifest)==expected_manifest
m=json.loads(manifest.read_text())
for p,x in m['files'].items():assert sha(root/'source'/p)==x['sha256'],p
for p,h in m['native_donor_required_sha256'].items():assert sha(donor/p)==h,p
assert sha(root/'overlay.json')=='dc0add55a6d944bb1c6dd57142e439104a6f1c5c3aedd87988c757d0e67d7c0b'
def available():
 return int(subprocess.check_output(['df','-k','/System/Volumes/Data'],text=True).splitlines()[-1].split()[3])*1024
def verify_donor():
 composition=m['native_composition_manifest']
 p=Path(composition['path']);assert sha(p)==composition['sha256']
 source=json.loads(p.read_text())
 assert source['canonical_union_tree']==composition['canonical_union_tree']
 rows=source['actual_union_file_rows'];assert len(rows)==composition['actual_union_files']
 for x in rows:assert sha(donor/x['path'])==x['sha256'],x['path']
 approved=m['native_approved_input_manifest']
 p=Path(approved['path']);assert sha(p)==approved['sha256']
 original=json.loads(p.read_text());assert original['source_commit']==m['native_source_commit']
 for x in original['files']:
  current=donor/x['path'];actual=sha(current) if current.is_file() else None
  assert actual==x['before_sha256'],x['path']
  assert m['files']['native/'+x['path']]['sha256']==x['sha256']
 for p,h in m['native_donor_required_sha256'].items():assert sha(donor/p)==h,p
 return {'composition_files_checked':len(rows),'overlay_preimages_checked':len(original['files']),'composition_manifest_sha256':composition['sha256'],'native_approved_manifest_sha256':approved['sha256'],'canonical_union_tree':source['canonical_union_tree'],'upstream_git_head':subprocess.check_output(['git','-C',str(donor),'rev-parse','HEAD'],text=True).strip(),'git_head_is_not_the_composed_tree':True}

reserve=768*1024**2;other=4*1024**3
free=available()
result={'status':'ADMISSION_PENDING','phase_budget':{'owned_growth_bytes':reserve,'external_growth_bytes':2*1024**3,'os_margin_bytes':2*1024**3,'other_native_growth_bytes':0,'required_before_compile':other+reserve},'free_before':free,'fixture_bytes_before':ownbytes(fixture),'records':[],'source_manifest_sha256':sha(manifest)}
result['historical_failed_attempt']={'job_id':'job_09fe7fb07354','old_native_contract':'878f1cbd82d0e0ded5739acfeb2832e61b96952d','old_comparator_failed':True,'old_reverse_and_cold_not_qualified':True}
result['source_change']='Current native504 Archive CAS +d436 genuine read baseline and original Base.Diff restrictions controls'
result['donor_before']=verify_donor()
save('admission.json',result)
if free<other+reserve:
 result['status']='BLOCKED_BEFORE_COMPILE';save('result.json',result);print(json.dumps(result));sys.exit(2)
go='/Users/m1/toolchains/go1.26.5/bin/go'
bounded={'GOCACHE':'/Users/m1/Library/Caches/go-build','GOMODCACHE':'/Users/m1/go/pkg/mod','CGO_ENABLED':'1','GOMAXPROCS':'2','GOTOOLCHAIN':'local','GOWORK':'off','GOENV':'off','GOFLAGS':'-mod=readonly','CGO_LDFLAGS':'-L'+str(donor/'deps/libs/darwin-arm64'),'TMPDIR':str(work/'tmp'),'GOTMPDIR':str(work/'tmp')}
env=os.environ.copy();env.update(bounded)
binary=work/'original-network-revision.test'
def run(label,argv,timeout,cwd,phase=None):
 save(label+'-command.json',{'argv':argv,'cwd':str(cwd),'bounded_env':bounded})
 output=evidence/(label+'.log')
 started=time.monotonic();minimum=shutil.disk_usage(root).free;reason='';stop_at=None;forced=False
 with output.open('xb') as out:
  proc=subprocess.Popen(argv,cwd=cwd,env=env,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
  (evidence/(label+'-pid.json')).write_text(json.dumps({'pid':proc.pid,'process_group':proc.pid})+'\n')
  while proc.poll() is None:
   current=shutil.disk_usage(root).free;minimum=min(minimum,current)
   if not reason and (current<other or time.monotonic()-started>timeout):
    reason='phase_growth_budget_exhausted' if current<other else 'controller_deadline'
    stop_at=time.monotonic()
    if phase is not None and phase.is_dir():
     marker=phase/'abort.json'
     try:
      with marker.open('x') as f:json.dump({'reason':reason,'request':'cancel contexts and perform actual AccountStop'},f)
     except FileExistsError:pass
    else:os.killpg(proc.pid,signal.SIGTERM);forced=True
   if reason and stop_at and time.monotonic()-stop_at>45:
    try:os.killpg(proc.pid,signal.SIGTERM);forced=True
    except ProcessLookupError:pass
   if reason and stop_at and time.monotonic()-stop_at>60:
    try:os.killpg(proc.pid,signal.SIGKILL);forced=True
    except ProcessLookupError:pass
   time.sleep(1)
  code=proc.wait()
 item={'label':label,'pid':proc.pid,'exit':code,'elapsed_seconds':round(time.monotonic()-started,3),'minimum_sampled_global_free_bytes':minimum,'free_after':shutil.disk_usage(root).free,'stop_reason':reason,'forced_termination':forced,'log_sha256':sha(output)}
 result['records'].append(item);save(label+'-result.json',item)
 return code==0 and not reason
try:
 with (evidence/'compiler-version.txt').open('x') as f:subprocess.run([go,'version'],text=True,stdout=f,stderr=subprocess.STDOUT,check=True)
 with (evidence/'process-census-before.txt').open('x') as f:subprocess.run(['ps','-axo','pid,ppid,rss,comm'],text=True,stdout=f,stderr=subprocess.STDOUT,check=True)
 compiled=run('compile',[go,'test','-overlay',str(root/'overlay.json'),'-c','-p','2','-o',str(binary),'./core/application'],240,donor)
 if not compiled:result['status']='FAILED_COMPILE_OR_PHASE_BUDGET'
 else:
  result['binary_sha256']=sha(binary);result['binary_bytes']=binary.stat().st_size
  controls=run('canonical-restrictions-control',[str(binary),'-test.run=^TestOtzariaOriginalNetworkRevisionCanonicalRestrictions$','-test.v'],60,root)
  control_log=(evidence/'canonical-restrictions-control.log').read_text()
  names=['TestOtzariaOriginalNetworkRevisionCanonicalRestrictions']+['TestOtzariaOriginalNetworkRevisionCanonicalRestrictions/'+x for x in ['read','edit','remove','drag','drop_on']]
  assert controls and all('--- PASS: '+name+' (' in control_log for name in names), 'all six actual restriction controls required'
  result['canonical_restriction_controls_passed']=len(names)
  phase=attempt/'peers'
  ran=run('original-remote-cas',[sys.executable,str(root/'source/harness/run_revision_peers.py'),'--binary',str(binary),'--binary-sha256',result['binary_sha256'],'--source-manifest',str(manifest),'--fixture',str(fixture),'--phase',str(phase),'--timeout','420'],960,root,phase)
  proof=json.loads((phase/'result.json').read_text()) if (phase/'result.json').is_file() else None
  result['peer_result']=proof
  result['status']='PASS_ACTUAL_REMOTE_CAS' if ran and proof and proof['status']=='PASS' else 'FAILED_REMOTE_CAS'
except BaseException as e:
 result['status']='FAILED_CONTROLLER';result['error_type']=type(e).__name__;result['error']=str(e)
finally:
 result['source_unchanged']=sha(manifest)==expected_manifest and all(sha(root/'source'/p)==x['sha256'] for p,x in m['files'].items())
 try:
  result['donor_after']=verify_donor()
  result['donor_required_unchanged']=result['donor_after']==result['donor_before']
 except BaseException as input_error:
  result['donor_required_unchanged']=False
  result['donor_verification_error']=str(input_error)
 result['owned_attempt_bytes']=ownbytes(attempt)
 result['max_child_rss_bytes']=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
 result['raw_peer_artifacts_private']=True
 result['fixture_bytes_after']=ownbytes(fixture)
 result['free_after']=available()
 if not result['source_unchanged'] or not result['donor_required_unchanged']:result['status']='FAILED_INPUT_DRIFT'
 save('result.json',result)
 print(json.dumps({'status':result['status'],'evidence':str(evidence),'records':result['records'],'source_unchanged':result['source_unchanged'],'owned_attempt_bytes':result['owned_attempt_bytes'],'free_after':result['free_after']}))
sys.exit(0 if result['status']=='PASS_ACTUAL_REMOTE_CAS' else 1)
