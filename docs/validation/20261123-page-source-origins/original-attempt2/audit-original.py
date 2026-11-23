#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,stat,subprocess,time,shutil
D=Path('/mnt/development/projects/diagnostics/semantic-page-mounted-451627-attempt2-original-result-20261123')
R=D/'originals/evidence'
OLD=Path('/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit/native-selected')
REPO=Path('/mnt/development/projects/worktrees/anytype-wave15-page-mounted-kernel-20261123')
CURRENT='c0c1f851f80322c9f532e86505047498dfaf1adf'
ORIGIN='68148339c275268795360d71d519a5baf003adf8'
def need(v,m):
 if not v:raise ValueError(m)
def load(p,sha=None):
 b=p.read_bytes()
 if sha:need(hashlib.sha256(b).hexdigest()==sha,'Source/receipt changed: '+str(p))
 return json.loads(b),{'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def save(p,v):
 b=(json.dumps(v,sort_keys=True,indent=2)+'\n').encode()
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 p.chmod(0o400)
 return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def tree(sha):
 out={}
 for row in subprocess.check_output(['git','-C',str(REPO),'ls-tree','-rz',sha],timeout=30).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode('ascii').split()
  need(kind=='blob' and mode in ('100644','100755','120000'),'Unexpected Git input')
  out[path.decode()]={'mode':mode,'oid':oid}
 return out
def kernel(c):
 q=c['owned_group_quiescence'];k=q['kernel_group_observation'];pid=c['worker_pid']
 need(c['status']=='COMPLETE' and c['return_code']==0 and type(pid) is int and pid>1,'Owned command result')
 need(q['status']=='PASS' and q['live_members']==0 and q['pgid']==pid and q['budget_seconds']==10
      and q['absence_source']=='KERNEL_ESRCH' and q['observations']==0 and q['timeout_observations']==[],'Owned absence receipt')
 need(k['operation']=='os.killpg' and k['signal']==0 and k['pgid']==pid and k['errno']==3
      and k['error_type']=='ProcessLookupError' and k['outcome']=='ABSENT_ESRCH'
      and k['before_monotonic']<=k['after_monotonic']<k['deadline_monotonic'],'Timely original ESRCH')
 return {'name':c['name'],'worker_pid':pid,'return_code':0,'absence':'ORIGINAL_RECORDED_TIMELY_KERNEL_ESRCH','budget_seconds':10,
         'query_elapsed_seconds':k['after_monotonic']-k['before_monotonic']}
def main():
 need(shutil.disk_usage(D).free>=2500000000,'Reserve insufficient')
 start=time.monotonic()
 execution,ex=load(R/'execution.json','e55b6e16c0c219b203f6ca9f54c90e2ec3a9e26e89ee0f850940caf3b3eb81dd')
 before,be=load(R/'controller-source-before.json','2f5e83659315c2fe7a720fa0c9cb681c0f0ce2398b98b725f041a1b397f10f69')
 after,af=load(R/'controller-source-after.json',be['sha256']);need(before==after,'Current source maps differ')
 original,oe=load(OLD/'source-before.json','533bb8ad8eed3607521bef3517ff3a7cd53728956872180209cd9280d48e365d')
 original_after,oa=load(OLD/'source-after.json',oe['sha256']);need(original==original_after,'Original maps differ')
 original_execution,ox=load(OLD/'execution.json','93fb0440f786fb68a3fd93b370edd02aad522040d694e2d5e20564c3e236502b')
 need(execution['controller_source_sha']==CURRENT and execution['compiled_app_source_sha']==ORIGIN
      and execution['binding']['runID']=='45162736256' and execution['binding']['runAttempt']=='2','Current origin')
 need(execution['status']=='FAIL' and execution['phase']=='EXACT_ORIGINAL_PRODUCTS'
      and execution['error_type']=='ValueError' and execution['error']=='Reused App/Module/UI/project source differs','Exact original failure')
 need(execution['source_and_descriptors_unchanged'] is True and execution['restored_products_unchanged']==[]
      and 'owned_simulator' not in execution and 'integrity_failure' not in execution,'Exact pre-simulator final state')
 need(all(execution[k]==0 for k in ('app_builds','native_builds','ui_builds','new_preparation_methods_passed','new_ui_methods_passed','previous_native_or_boundary_methods_rerun')),'Unexpected executed scope')
 need(execution['original_artifacts']['source-before.json']==oe['sha256']
      and execution['original_artifacts']['source-after.json']==oa['sha256']
      and execution['original_artifacts']['execution.json']==ox['sha256'],'Prior original bindings')
 commands=execution['commands'];need(len(commands)==3,'Unexpected current commands')
 names=['consumer-run-api','consumer-artifact-api','download-original-consumer']
 argv=[['gh','api','repos/davidpovarsky/anytype-swift/actions/runs/45116855451/attempts/1'],
       ['gh','api','repos/davidpovarsky/anytype-swift/actions/artifacts/14794983588'],
       ['gh','api','repos/davidpovarsky/anytype-swift/actions/artifacts/14794983588/zip']]
 command_checks=[];original_command_receipts=[]
 for i,c in enumerate(commands):
  need(c['name']==names[i] and c['argv']==argv[i],'Command identity/order')
  command_checks.append(kernel(c))
  if i<2:
   raw,record=load(R/(c['name']+'.command.json'))
   need(all(c.get(k)==v for k,v in raw.items()),'Raw original command differs')
   log=(R/(c['name']+'.log')).read_bytes();need(hashlib.sha256(log).hexdigest()==c['log_sha256'],'Raw command log mismatch')
   original_command_receipts.append(record)
 need(len({c['worker_pid'] for c in commands})==3,'Command process identity collision')
 need(commands[2]['log_sha256']=='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46','Original downloaded carrier identity')
 snapshots={CURRENT:before,ORIGIN:original};trees={sha:tree(sha) for sha in snapshots}
 for sha,m in snapshots.items():need(set(m)==set(trees[sha]),'Git/source map membership differs')
 oids=sorted({r['oid'] for t in trees.values() for r in t.values()})
 hashes={};sizes={}
 child=subprocess.Popen(['git','-C',str(REPO),'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 try:
  for oid in oids:
   need(time.monotonic()-start<150,'Bounded read-only Git audit exceeded')
   child.stdin.write((oid+'\n').encode());child.stdin.flush()
   fields=child.stdout.readline().decode().split();need(len(fields)==3 and fields[0]==oid and fields[1]=='blob','Unexpected Git batch header')
   size=int(fields[2]);need(0<=size<=16*1024*1024,'Unexpected Git blob bound')
   remaining=size;h=hashlib.sha256()
   while remaining:
    b=child.stdout.read(min(1048576,remaining));need(bool(b),'Truncated Git blob');h.update(b);remaining-=len(b)
   need(child.stdout.read(1)==b'\n','Unexpected Git protocol delimiter')
   hashes[oid]=h.hexdigest();sizes[oid]=size
  child.stdin.close();need(child.wait(timeout=10)==0,'Git reader failed')
 finally:
  if child.poll() is None:child.kill();child.wait(timeout=10)
 for sha,m in snapshots.items():
  need(all(hashes[trees[sha][path]['oid']]==digest for path,digest in m.items()),'Actual source map does not equal exact Git bytes')
 product=lambda m:{k:v for k,v in m.items() if not k.startswith(('Tools/','.github/','docs/'))}
 oldp,newp=product(original),product(before)
 differences=[{'path':p,'original_sha256':oldp.get(p),'current_sha256':newp.get(p),
               'original_git':trees[ORIGIN].get(p),'current_git':trees[CURRENT].get(p)}
              for p in sorted(set(oldp)|set(newp)) if oldp.get(p)!=newp.get(p)]
 need(len(differences)==7,'Expected exact seven protected differences')
 same=sum(oldp.get(p)==newp.get(p) for p in set(oldp)&set(newp))
 source_pins={}
 for p in ('Tools/PinkhaSemanticAnchorWire/apple_mounted/run.py','Tools/PinkhaSemanticAnchorWire/apple_consumer/run.py',
           'Tools/PinkhaSemanticAnchorWire/apple_mounted/mounted_contract.py','Tools/PinkhaSimulatorGate/run_owned_single_lane.py',
           '.github/workflows/pinkha-semantic-page-apple-mounted.yml'):
  source_pins[p]={'git':trees[CURRENT][p],'sha256':before[p]}
 result={'protocol':'page451627-attempt2-independent-original-audit-v1','status':'PASS_AUDIT_OF_ORIGINAL_FAILURE',
  'actual_status':'FAIL','run_id':45162736256,'attempt':2,'controller_source_sha':CURRENT,'compiled_app_origin':ORIGIN,
  'source':{'current_entries':len(before),'original_entries':len(original),'all_original_and_current_source_hashes_equal_exact_git_bytes':True,
            'unique_git_blobs_read':len(oids),'unique_git_blob_bytes':sum(sizes.values()),'current_before_after_equal':True,'original_before_after_equal':True,
            'current_protected_entries':len(newp),'original_protected_entries':len(oldp),'unchanged_protected_entries':same,'protected_differences':differences,
            'inputs':[be,af,oe,oa,ox],'relevant_current_controller_pins':source_pins},
  'failure':{'phase':execution['phase'],'type':execution['error_type'],'message':execution['error'],
             'demonstrated_cause':'Current controller checkout product source is compared against immutable original681 Products source; exactly seven protected paths differ.',
             'original_source_maps_equal':True,'failed_predicate':'product_inputs(original681) == product_inputs(currentc0)'},
  'commands':command_checks,'raw_command_receipts':original_command_receipts,
  'original_download_command_raw_receipt':'INLINE_EXECUTION_ONLY; downloaded carrier and its separate raw command file are not present in this small artifact',
  'actual_app_native_ui_builds':0,'actual_xctest_or_enumeration_commands':0,'actual_preparation_or_ui_methods':0,'original_methods_replayed':0,
  'simulator_cleanup':'NOT_APPLICABLE_NO_CREATE_OR_SIMULATOR_COMMAND_REACHED','owned_subprocess_cleanup':'THREE_ORIGINAL_RECORDED_TIMELY_ESRCH_PASSES',
  'restored_products':'NOT_REACHED; empty final restored-products list is not a restoration PASS',
  'descriptor_integrity':'NO_DESCRIPTOR_COPIES_REGISTERED; final true field covers current source and empty descriptor lists',
  'original_execution':ex,'reader_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
  'elapsed_seconds':time.monotonic()-start,'new_api_queries':0,'new_downloads':0,'tests_or_builds_run_by_audit':0}
 receipt=save(D/'independent-audit.json',result)
 print(json.dumps({'status':result['status'],'receipt':receipt,'actual_failure':result['failure'],'source_counts':{'current':len(before),'original':len(original),'protected_differences':len(differences)},'commands':command_checks,'executed_product_commands':0,'free_bytes':shutil.disk_usage(D).free}))
if __name__=='__main__':main()
