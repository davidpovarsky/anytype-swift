#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,stat,shutil,subprocess,os
D=Path('/mnt/development/projects/evidence/page-source-origins-20261123')
W=Path('/mnt/development/projects/worktrees/anytype-wave15-page-source-origins-20261123')
HEAD='a513821699ff0ed5fc032b71ff91f56027bdef8b'
PIN_BYTES=(D/"seal-inputs.json").read_bytes()
assert hashlib.sha256(PIN_BYTES).hexdigest()=="e26dbdaf6c4ef8f36a288f8da87640d299af31bf745999d1aa7248e7d6baeed2"
PINS=json.loads(PIN_BYTES)
def need(v,m):
 if not v:raise ValueError(m)
def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def save(p,b):
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {'path':str(p),'bytes':len(b),'sha256':digest(b)}
def main():
 need(shutil.disk_usage(D).free>=2500000000,'Capacity reserve')
 need(subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD']).decode().strip()==HEAD,'Frozen source')
 need(subprocess.check_output(['git','-C',str(W),'status','--porcelain'])==b'','Clean source')
 for pin in PINS:
  p=D/pin['path'];b=p.read_bytes()
  need(p.is_file() and not p.is_symlink() and len(b)==pin['bytes'] and digest(b)==pin['sha256'],'Original evidence changed')
 a=D/'attempt1';before=read(a/'source-before.json');after=read(a/'source-after.json')
 need(before==after and len(before)==39,'Original source snapshots')
 manifest=read(W/'docs/validation/20261123-page-source-origins/control-inputs.json')
 expected_sources={row['path']:row['sha256'] for row in manifest['inputs']}
 need(set(expected_sources)==set(before),'Frozen input membership')
 for row in manifest['inputs']:
  p=W/row['path'];b=p.read_bytes()
  need(digest(b)==row['sha256']==before[row['path']]['sha256'],'Current frozen source bytes')
  need(format(stat.S_IMODE(p.stat().st_mode),'04o')==row['physical_mode']==before[row['path']]['physical_mode'],'Current frozen modes')
 outer_before=read(a/'loaded-outer-before.json');outer_after=read(a/'loaded-outer-after.json')
 need(outer_before==outer_after and len(outer_before)==2,'Outer loaded sources')
 need(all(expected_sources[v['path']]==v['sha256'] for v in outer_before.values()),'Outer source binding')
 methods=[
 'page_source_origin_controls.PageSourceOriginControls.test_real_current_controller_and_original_app_have_separate_complete_source_admission',
 'page_source_origin_controls.PageSourceOriginControls.test_actual_origin_adapter_refuses_wrong_roots_heads_foreign_imports_and_postflight_drift']
 events=read(a/'events.json')
 need([(r['event'],r['method']) for r in events]==[('START',methods[0]),('PASS',methods[0]),('START',methods[1]),('PASS',methods[1])],'Exact named outcomes')
 need(all(events[i]['monotonic']<=events[i+1]['monotonic'] for i in range(3)),'Original event order')
 receipt=read(a/'receipt.json')
 need(receipt['status']=='PASS' and receipt['frozen_head']==HEAD and receipt['tests_run']==receipt['actual_named_passes']==2
      and receipt['outer_failure'] is None and receipt['older_controller_methods']==receipt['product_methods']==receipt['new_builds']==0,'Original terminal')
 children=[]
 expected_cases=['same-root','nested-root','wrong-controller-head','wrong-app-head','foreign-consumer-helper','loaded-app-module','app-source-postflight-drift','controller-source-postflight-drift']
 for mode in ('success','refusals'):
  childroot=a/'owned-child-originals'
  value=read(childroot/('real-origin-'+mode+'.stdout.json'))
  command=read(childroot/('real-origin-'+mode+'.command.json'))
  need(value['status']=='PASS_NEW_SOURCE_ORIGIN_CONTROL' and value['mode']==mode,'Child original')
  need(command['return_code']==0 and command['new_session'] is True and command['owned_group_absent'] is True
       and command['owned_pid']==command['owned_pgid'] and command['primary_error'] is None
       and command['separate_cleanup_error'] is None,'Owned child result and cleanup')
  need(command['stdout_sha256']==digest((childroot/('real-origin-'+mode+'.stdout.json')).read_bytes())
       and command['stderr_sha256']==digest((childroot/('real-origin-'+mode+'.stderr')).read_bytes()),'Child stream binding')
  need(value['source_before']==value['source_after']==expected_sources,'Child frozen source')
  previous=value['before'];final=value['after']
  need(previous==final and len(final['loaded_controller_modules'])==33,'Complete actual current imports')
  need(all(expected_sources[v['path']]==v['sha256'] for v in final['loaded_controller_modules'].values()),'Actual imported source identity')
  need(final['controller_input_count']==35 and final['compiled_app_input_count']==3
       and final['current_controller_is_compiled_app_source'] is False and final['product_acceptance'] is False,'Explicit two synthetic Git origins')
  for field,key in [('controller_input_map_sha256','independent_expected_current_inputs'),('compiled_app_input_map_sha256','independent_expected_app_inputs')]:
   need(final[field]==digest(json.dumps(value[key],sort_keys=True,separators=(',',':')).encode()),'Independent expected map')
  cases=[r['case'] for r in value.get('refusals',[])]
  need(cases==(expected_cases if mode=='refusals' else []),'Exact negative scope')
  need(value['owned_temporary_fixtures_removed'] is True,'Owned fixture lifecycle')
  children.append({'mode':mode,'owned_pid':command['owned_pid'],'owned_pgid':command['owned_pgid'],'return_code':0,
    'owned_group_absent':True,'source_inputs':39,'actual_loaded_current_modules':33,
    'source_maps_before_after_unchanged':True,'synthetic_current_git_inputs':35,'synthetic_original_app_git_inputs':3,'refusals':value.get('refusals',[])})
 need(children[0]['owned_pid']!=children[1]['owned_pid'],'Distinct original child identities')
 out=W/'docs/validation/20261123-page-source-origins/controls-attempt1'
 need(not out.exists(),'No reseal overwrite');out.mkdir()
 copied=[]
 for pin in PINS:
  target=out/pin['path'];target.parent.mkdir(parents=True,exist_ok=True)
  raw=(D/pin['path']).read_bytes();saved=save(target,raw)
  copied.append({**pin,'original':str(D/pin['path']),'committed_copy':target.relative_to(W).as_posix()})
 reader=Path(__file__).read_bytes();save(out/'seal-passed-originals.py',reader)
 save(out/'seal-inputs.json',PIN_BYTES)
 result={'protocol':'page-source-origin-qualified-two-controls-v1','status':'PASS','tested_source':HEAD,
   'baseline_controller':'c0c1f851f80322c9f532e86505047498dfaf1adf','immutable_compiled_app':'68148339c275268795360d71d519a5baf003adf8',
   'original_failure_audit_sha256':'f5bde718fab421229cb4d8326d52d096760dbd5179827aba1b3f977e39e9927a',
   'manifest_sha256':digest((W/'docs/validation/20261123-page-source-origins/control-inputs.json').read_bytes()),
   'original_receipt_sha256':digest((a/'receipt.json').read_bytes()),'actual_methods':methods,'distinct_new_passes':2,
   'actual_named_events':events,'physical_frozen_source_inputs':39,'loaded_outer_before_after':outer_before,
   'actual_children':children,'source_and_loaded_before_after_unchanged':True,'original_files':copied,
   'root_review_sha256':'966d36fc804735b730caed3f6122a63cd25af2ae11f1f12a28a5484bb3b15bcb',
   'seal_reader_sha256':digest(reader),'old_controller_replays':0,'old_kernel_replays':0,'product_or_Apple_methods':0,'new_builds':0,
   'actual_original_App681_or_Product_restoration_acceptance':False,
   'scope':'Only the new source-origin adapter/current-import composition is qualified using real synthetic Git fixtures. Actual unchanged Apple scopes remain unexecuted.'}
 q=save(out/'qualification.json',(json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
 save(D/'qualification.json',(json.dumps(result,sort_keys=True,indent=2)+'\n').encode())
 (D/'qualification.json').chmod(0o400)
 subprocess.run(['git','-C',str(W),'add','--',str(out.relative_to(W))],check=True)
 staged=subprocess.check_output(['git','-C',str(W),'diff','--cached','--name-only']).decode().splitlines()
 need(staged and all(p.startswith(str(out.relative_to(W))+'/') for p in staged),'Evidence-only index')
 subprocess.run(['git','-C',str(W),'-c','user.name=davidpovarsky','-c','user.email=your-email@example.com','commit','-m','test: seal two Page source-origin controls and owned originals'],check=True,timeout=60)
 final=subprocess.check_output(['git','-C',str(W),'rev-parse','HEAD']).decode().strip()
 need(subprocess.check_output(['git','-C',str(W),'status','--porcelain'])==b'','Final writer clean')
 print(json.dumps({'final_head':final,'tested_source':HEAD,'qualification':q,'original_files':len(PINS),'source_inputs':39,'actual_new_passes':2,'actual_children':children,'free':shutil.disk_usage(D).free}))
if __name__=='__main__':main()
