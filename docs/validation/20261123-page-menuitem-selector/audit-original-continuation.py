import pathlib,zipfile,tarfile,io,json,hashlib,os,stat,time,copy,plistlib,sys
ZIP=pathlib.Path(r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\page-menu-selector-original-45222136118-1\original-14842632494.zip')
OUT=ZIP.parent/'audit-menuitem-v2'
EXPECTED_SHA='4d4b9c837846a4ceb900ddaee1ad9637be3746160f65e76768f47bc50d2e84a0'
PLAN={"app_commit":"68148339c275268795360d71d519a5baf003adf8","candidate_ui_sha256":"ad527c3082a29932af15ddc5a0bcaca7da5585845960cdebbdab65b4f50a78e2","files":{"PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj/project.pbxproj":{"bytes":12598,"origin":"app","original_sha256":"38219484965210d09a25d6a68f2e46c71ae7682028a55f1e27834075a73acef2","sha256":"38219484965210d09a25d6a68f2e46c71ae7682028a55f1e27834075a73acef2"},"PinkhaStage1Acceptance/PinkhaStage1Acceptance.xcodeproj/xcshareddata/xcschemes/PinkhaStage1Acceptance.xcscheme":{"bytes":3429,"origin":"app","original_sha256":"43660974b215776ef4539c961a4ef75a7da8e1a21a08c4f0b1a12538e33fb845","sha256":"43660974b215776ef4539c961a4ef75a7da8e1a21a08c4f0b1a12538e33fb845"},"PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift":{"bytes":28184,"origin":"app","original_sha256":"c07f549a39ea3069098353776bb7bb78766cdc0136b3b25257e591ae6d586579","sha256":"c07f549a39ea3069098353776bb7bb78766cdc0136b3b25257e591ae6d586579"},"PinkhaStage1Acceptance/Tests/HanlinNativeAcceptanceUITests.swift":{"bytes":26662,"origin":"app","original_sha256":"8af3eea788ab5383d754bd8fdd8ca8443e9cbf44cde34eb5ae2323bd90849824","sha256":"8af3eea788ab5383d754bd8fdd8ca8443e9cbf44cde34eb5ae2323bd90849824"},"PinkhaStage1Acceptance/Tests/HanlinSelectionAcceptanceUITests.swift":{"bytes":13939,"origin":"app","original_sha256":"5136113b10452d86ed5befcf46cb35b7262fc123268b6249421441aa6209cb61","sha256":"5136113b10452d86ed5befcf46cb35b7262fc123268b6249421441aa6209cb61"},"PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift":{"bytes":67409,"origin":"app","original_sha256":"14f825b44c562d6e12e83f86b95531f040759584e8b5b4ad1286bf415ea70621","sha256":"14f825b44c562d6e12e83f86b95531f040759584e8b5b4ad1286bf415ea70621"},"PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift":{"bytes":29193,"origin":"app","original_sha256":"a2244cf16250ab64e4827ef25feec76c62a581df842a64f93810620b72ae75d0","sha256":"a2244cf16250ab64e4827ef25feec76c62a581df842a64f93810620b72ae75d0"},"PinkhaStage1Acceptance/Tests/PinkhaTorahQuoteAcceptanceUITests.swift":{"bytes":18677,"origin":"app","original_sha256":"84ce38f69f4eac25e19a768f1fc63cfd4bde0b7c6f78e46a7bc7f23f33d1f477","sha256":"84ce38f69f4eac25e19a768f1fc63cfd4bde0b7c6f78e46a7bc7f23f33d1f477"},"PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift":{"bytes":22649,"origin":"controller","original_sha256":"468139db53be7dac0570ea16c7fec918332f44107927d6043a9bcc4469773c8b","sha256":"ad527c3082a29932af15ddc5a0bcaca7da5585845960cdebbdab65b4f50a78e2"}},"fresh_setup_new_acceptance_credit":0,"generator_path":"Tools/PinkhaNativeDerived/rerun_original_ui.py","generator_sha256":"ec5688909921942e94f792cdde0a02baa7b5f9b2f9e0b3bde3df3a877f299279","original_mounted_source_plan_sha256":"19806530ea3f492ff221efac5a5430ec46893fb7066bf5294afaa06a390ad42f","original_ui_sha256":"468139db53be7dac0570ea16c7fec918332f44107927d6043a9bcc4469773c8b","preparation_selector":"AnytypeTests/SemanticAnchorPage154MountedPreparationTests/testPrepareOwnedPage154MountedFixture","retained_preparation":{"artifact_id":14822310800,"artifact_sha256":"e7ac823612bc9474b282f2cbe69e0fc5bb8fd8e55900456af0696571e9161441","attempt":"2","audit_diagnosis_sha256":"cb88af9a01fd7429ad77967790fb2cd3a2ebcd386fdc0262b2d3f113493e4f8e","result":"PASS","run":"45174292731","summary_sha256":"61e23ff2ae69d35623de887a6a30d2c4649cf194fc6eba404c994f7d5401338d"},"schema":"pinkha-page154-startup-warning-ui-v1","ui_path":"PinkhaStage1Acceptance/Tests/SemanticAnchorPage154MountedUITests.swift","ui_selector":"PinkhaStage1AcceptanceUITests/SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen"}
START=time.monotonic();LIMIT=4*1024*1024
def need(c,m):
 if not c:raise RuntimeError(m)
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,b):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 need(not p.exists(),'preserve_existing_'+name)
 need(sum(x.stat().st_size for x in OUT.rglob('*') if x.is_file())+len(b)<=LIMIT,'audit_output_bound')
 with p.open('xb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 need(p.read_bytes()==b,'saved_readback_'+name)
 return {'path':str(p),'bytes':len(b),'sha256':sha(b)}
def dump(name,v):return save(name,(json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def safe(n):
 p=pathlib.PurePosixPath(n)
 return bool(n) and not n.startswith(('/','\\')) and '\\' not in n and ':' not in n and '..' not in p.parts
def delta(a,b,p=''):
 if isinstance(a,dict) and isinstance(b,dict):
  return sum([delta(a.get(k,{'ABSENT':True}),b.get(k,{'ABSENT':True}),p+'/'+k) for k in sorted(set(a)|set(b))],[])
 if a==b:return []
 return [{'path':p,'before':a,'after':b}]
need(not OUT.exists(),'fresh_audit_output');OUT.mkdir()
result={'schema':'page154-original-menuitem-audit-v1','status':'FAIL_AUDIT','product_status':'FAIL','source':'9178f18736244851657279761ad492618fab53c1','run':45222136118,'attempt':1,'artifact_id':14842632494,'new_test_executions':0,'new_builds':0}
try:
 priorp=ZIP.parent/'audit-menuitem-v1/audit-result.json';priorb=priorp.read_bytes()
 need(sha(priorb)=='e0495df73cdfecadd06a090c07f2def6eb59df1f05fe73439bbb3f559b20928b','original_failed_audit_changed')
 prior=json.loads(priorb);need(prior['status']=='FAIL_AUDIT' and prior['error']['message']=='unreviewed_ui_descriptor_field','original_audit_failure')
 for k in ['original_zip','zip_inventory','zip_crc_all_members_verified','app_source','controller_source','loaded_modules','ui_build','new_ui_products']:result[k]=prior[k]
 result['prior_failed_audit']={'path':str(priorp),'sha256':sha(priorb),'status':'FAIL_AUDIT','completed_scopes_reused':['full ZIP member CRC/digests','identical before/after source maps','36 module bindings','nine build input bindings','31 Products path/mode/digests'],'observed_guard':'The original allowed-field audit omitted the actual bound UITargetAppPath. This continuation binds that field to the exact restored original native App path.'}
 need(ZIP.stat().st_size==32650234 and sha(ZIP.read_bytes())==EXPECTED_SHA,'original_zip_identity')
 invb=pathlib.Path(prior['zip_inventory']['path']).read_bytes();need(sha(invb)=='ccf9d5dcae68d4e149f7bf3e1509f31af6a6c1d9230e77eed8b8382b8d691a27','retained_full_inventory_changed')
 inventory=json.loads(invb);index={x['path']:x for x in inventory};names=set(index)
 need(len(inventory)==1448 and len(index)==1448,'retained_inventory_members')
 with zipfile.ZipFile(ZIP) as z:
  ex=json.loads(z.read('evidence/execution.json'))
  original=plistlib.loads(z.read('evidence/ui-runner/original.xctestrun'));bound=plistlib.loads(z.read('evidence/ui-bound.xctestrun'))
  descriptor=json.loads(z.read('evidence/ui-descriptor.json'))
  need(sha(z.read('evidence/ui-bound.xctestrun'))==descriptor['copied_sha256'] and sha(z.read('evidence/ui-runner/original.xctestrun'))==descriptor['original_sha256'],'ui_descriptor_digests')
  changes=delta(original,bound)
  allowed={'EnvironmentVariables','OnlyTestIdentifiers','SkipTestIdentifiers','TestingEnvironmentVariables','UITargetAppPath'}
  need(all(len(x['path'].split('/'))>2 and x['path'].split('/')[2] in allowed for x in changes),'unreviewed_ui_descriptor_field')
  blueprint='PinkhaStage1AcceptanceUITests';a=original[blueprint];b=bound[blueprint];inverse=copy.deepcopy(bound)
  need(b['UITargetAppPath']=='/Users/runner/work/anytype-swift/anytype-swift/build/page154-mounted-45222136118-1/work/native-products/Build/Products/Debug-Anytype-iphonesimulator/Anytype.app','original_native_target_app_path')
  need(b['OnlyTestIdentifiers']==['SemanticAnchorPage154MountedUITests/testActualTextSelectionCancelThenCreateAndColdReopen'],'exact_ui_selection')
  newenv=b.get('EnvironmentVariables',{});oldenv=a.get('EnvironmentVariables',{})
  need(set(newenv)-set(oldenv)==set(descriptor['environment_keys']),'owned_ui_environment_keys')
  need(all(newenv[k]==v for k,v in oldenv.items()),'original_ui_environment_changed')
  for k in allowed:
   if k in a:inverse[blueprint][k]=copy.deepcopy(a[k])
   else:inverse[blueprint].pop(k,None)
  need(inverse==original,'ui_descriptor_inverse')
  injection=descriptor['runtime_injection'];oldtesting=a.get('TestingEnvironmentVariables',{});newtesting=b.get('TestingEnvironmentVariables',{})
  repaired=copy.deepcopy(newtesting)
  for k,v in repaired.items():
   if isinstance(v,str):repaired[k]=v.replace(injection['replacement_token'],injection['original_token'])
  need(repaired==oldtesting,'testing_environment_token_inverse')
  result['ui_descriptor']={'inverse':True,'changed_paths':[x['path'] for x in changes],'details':dump('ui-descriptor-delta.json',changes)}
  commands=[]
  for c in ex['commands']:
   q=c.get('owned_group_quiescence');need(q and q['status']=='PASS' and q['live_members']==0,'owned_group_quiescence')
   o=q['kernel_group_observation']
   need(o['outcome']=='ABSENT_ESRCH' and o['errno']==3 and o['signal']==0 and o['pgid']==q['pgid']==c['worker_pid'],'kernel_group_identity')
   need(o['after_monotonic']<=o['deadline_monotonic'],'kernel_group_deadline')
   matches=[x for x in inventory if x['sha256']==c['log_sha256']]
   if not matches:
    need(c['name']=='download-original-consumer' and c['log_sha256']=='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46','unexpected_missing_command_stream')
    result['unavailable_original_command_stream']={'name':c['name'],'recorded_sha256':c['log_sha256'],'status':'NOT_INCLUDED_IN_PUBLISHED_ARTIFACT','scope':'Kernel PGID and command result are preserved in execution.json; the raw download progress stream cannot be independently rechecked from this artifact.'}
   commands.append({'name':c['name'],'status':c['status'],'return_code':c['return_code'],'log_sha256':c['log_sha256'],'pgid':q['pgid'],'kernel_absent_within_budget':True,'original_stream_members':[x['path'] for x in matches]})
  need(len(commands)==25,'exact_command_count');result['commands']=commands
  need(ex['owned_simulator_cleanup_status']=='COMPLETE' and ex['owned_simulator_cleanup']['delete']['status']=='PASS_EXIT_0' and ex['owned_simulator_cleanup']['shutdown']['status']=='PASS_EXIT_0','simulator_cleanup')
  result['owned_simulator_cleanup']={'udid':ex['owned_simulator']['udid'],'shutdown_and_delete_exit_zero':True,'scope':'Recorded exact owned commands and kernel PGID evidence; no added remote simulator query.'}
  summary=json.loads(z.read('evidence/ui/actual-summary.json'));prep=json.loads(z.read('evidence/preparation/actual-summary.json'))
  need(summary['passedTests']==0 and summary['failedTests']==1 and summary['skippedTests']==0,'actual_ui_counts')
  need(prep['passedTests']==1 and prep['failedTests']==0 and prep['skippedTests']==0,'actual_preparation_counts')
  trn='evidence/ui/actual-attachments/836D8566-F99B-430D-B50B-7706B6E4C50D.json';trace=json.loads(z.read(trn))
  need(sha(z.read(trn))=='2186ec852130dd00cb430db45241cfc46f265ea1ed5adb04a6b7b8f55422226b','trace_original')
  need(trace['tapAttempts']==0 and trace['matchingElements']==2 and trace['actionableElements']==2,'actual_menu_boundary')
  axn='evidence/ui/actual-attachments/C38BD873-F6D5-4276-BF2D-20238DA8C190.txt'
  ax=z.read(axn);need(sha(ax)=='cdfa5f07355a266081376ef9dcd6e9a1164ab42c05c469978951e98710f1c5ae','original_ax')
  lines=[l for l in ax.decode().splitlines() if "label: 'Create text anchor'" in l]
  need(len(lines)==2 and 'MenuItem' in lines[0] and 'StaticText' in lines[1],'native_menu_and_child_types')
  result['actual_results']={'ui':{'pass':0,'fail':1,'skip':0,'reason':'menu-action-ambiguous','tap_attempts':0},'fresh_setup':{'pass':1,'fail':0,'skip':0,'new_acceptance_credit':0},'downstream_cancel_create_apply_cold':'NOT_RUN','physical_ipad':'NOT_RUN'}
  selected=[x['path'] for x in inventory if x['path'].startswith('evidence/') and x['bytes']<250000 and ((x['path'].endswith('.json') and '/actual-attachments/' not in x['path']) or x['path'].endswith('.xctestrun'))]
  selected+=['evidence/ui/actual-owned-one.log',trn,axn,'evidence/build-warning-ui-runner.log','evidence/preparation/actual-owned-one.log']
  copies=[]
  for n in sorted(set(selected)):
   if n not in names:continue
   receipt=save('originals/'+n,z.read(n));need(receipt['sha256']==index[n]['sha256'],'original_copy_digest')
   copies.append({'zip_member':n,**receipt})
  result['original_copies']=dump('originals-index.json',copies)
  result['retained_original_products']={'native':ex['restored_native'],'previous_ui':ex['restored_ui'],'scope':'Existing exact restore/integrity receipts retained; original 2.37 GB native tree was not downloaded or re-executed for this failure audit.'}
  result['status']='PASS_ORIGINAL_FAILURE_AUDIT'
except BaseException as e:
 result['error']={'type':type(e).__name__,'message':str(e)}
result['elapsed_seconds']=time.monotonic()-START
receipt=dump('audit-result.json',result)
print(json.dumps({'status':result['status'],'receipt':receipt,'error':result.get('error'),'elapsed_seconds':result['elapsed_seconds']},ensure_ascii=True))
sys.exit(0 if result['status']=='PASS_ORIGINAL_FAILURE_AUDIT' else 1)
