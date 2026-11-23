import pathlib,zipfile,tarfile,io,json,hashlib,os,stat,time,copy,plistlib,sys
ZIP=pathlib.Path(r'C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\page-menu-selector-original-45222136118-1\original-14842632494.zip')
OUT=ZIP.parent/'audit-menuitem-v1'
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
 need(ZIP.stat().st_size==32650234 and sha(ZIP.read_bytes())==EXPECTED_SHA,'original_zip_identity')
 result['original_zip']={'path':str(ZIP),'bytes':32650234,'sha256':EXPECTED_SHA}
 with zipfile.ZipFile(ZIP) as z:
  entries=z.infolist();need(len(entries)==1448,'original_entry_count')
  names=set();inventory=[];total=0
  for e in entries:
   need(time.monotonic()-START<100,'audit_deadline')
   need(safe(e.filename) and e.filename not in names,'unsafe_or_duplicate_zip_member')
   names.add(e.filename);mode=e.external_attr>>16
   need(stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR),'zip_non_regular_member')
   b=z.read(e);need(len(b)==e.file_size,'zip_member_size');total+=len(b)
   inventory.append({'path':e.filename,'bytes':len(b),'sha256':sha(b),'mode':mode,'crc':e.CRC})
  need(total==40854417,'original_expanded_size')
  result['zip_inventory']=dump('zip-inventory.json',inventory)
  result['zip_crc_all_members_verified']=True
  index={r['path']:r for r in inventory}
  ex=json.loads(z.read('evidence/execution.json'))
  need(ex['status']=='FAIL' and ex['phase']=='ACTUAL_NEW_MOUNTED_JOURNEY','actual_failure_phase')
  need(ex['controller_source_sha']==result['source'] and ex['compiled_app_source_sha']==PLAN['app_commit'],'source_identity')
  sources={}
  for kind,count in [('app',12033),('controller',15017)]:
   b=z.read('evidence/'+kind+'-source-before.json');a=z.read('evidence/'+kind+'-source-after.json')
   need(a==b,'source_bytes_changed_'+kind);v=json.loads(b);need(len(v)==count,'source_count_'+kind)
   sources[kind]=v
   result[kind+'_source']={'before_after_byte_identical':True,'count':count,'sha256':sha(b)}
  origins=ex['source_origins_before']['loaded_controller_modules'];after=ex['source_origins_after']['loaded_controller_modules']
  need(len(origins)==33 and len(after)==36,'loaded_module_count')
  need(all(after[k]==v for k,v in origins.items()),'loaded_module_replaced')
  for v in after.values():need(sources['controller'][v['path']]==v['sha256'],'loaded_module_source_binding')
  result['loaded_modules']={'before':33,'after':36,'all_bound_to_original_controller_snapshot':True,'added':sorted(set(after)-set(origins))}
  build=json.loads(z.read('evidence/ui-runner/build-source-inputs.json'))
  warning=json.loads(z.read('evidence/ui-runner/warning-build.json'))
  need(build['ui_source_sha']==result['source'] and build['app_source_sha']==PLAN['app_commit'],'build_source_split')
  need(build['app_targets']==0 and build['ui_targets']==1 and build['build_implicit_dependencies'] is False and build['package_references']==0,'ui_only_build_scope')
  need(warning['ui_builds_started']==warning['ui_builds_succeeded']==1 and warning['app_builds']==warning['native_builds']==0,'build_counts')
  need(warning['ui_input_plan_sha256']=='ab399ceba07a88db6e572bccfdf00b0455a24887dcf6b6ae7a6443c4b8356bba','input_plan_binding')
  for p,v in PLAN['files'].items():
   need(build['source_inputs'][p]=={'bytes':v['bytes'],'sha256':v['sha256']},'nine_input_build_binding')
   need(sources[v['origin']][p]==v['sha256'],'nine_input_source_binding')
  need(len(build['source_inputs'])==9,'source_input_exact_count')
  result['ui_build']={'started':1,'succeeded':1,'app':0,'native':0,'nine_input_bindings':True,'build_inputs_sha256':sha(z.read('evidence/ui-runner/build-source-inputs.json'))}
  mn='evidence/ui-runner/semantic-page154-early-products/manifest.json';manifest=json.loads(z.read(mn))
  archive=z.read('evidence/ui-runner/semantic-page154-early-products/BuildProducts.tar.gz')
  need(len(archive)==manifest['archive_bytes'] and sha(archive)==manifest['archive_sha256'],'products_archive_digest')
  with tarfile.open(fileobj=io.BytesIO(archive),mode='r:gz') as tf:
   ts=tf.getmembers();need(len(ts)==len(manifest['products'])==31,'products_entry_count')
   seen=set()
   for m in ts:
    name=m.name.rstrip('/');need(safe(name) and name not in seen,'unsafe_duplicate_product');seen.add(name)
    row=manifest['products'][name]
    need((m.isdir() and row['kind']=='directory') or (m.isfile() and row['kind']=='file'),'product_kind')
    need(m.mode==row['mode'],'product_mode')
    if m.isfile():
     b=tf.extractfile(m).read();need(len(b)==row['bytes'] and sha(b)==row['sha256'],'product_bytes')
   need(seen==set(manifest['products']),'product_paths')
  need(manifest['products']['Build/PinkhaSourceInputs.json']['sha256']==result['ui_build']['build_inputs_sha256'],'products_build_input_binding')
  result['new_ui_products']={'entries':31,'archive_sha256':sha(archive),'manifest_sha256':sha(z.read(mn)),'all_file_digests_modes_paths_verified':True,'links':0,'reusable_acceptance':'NOT_GRANTED'}
  original=plistlib.loads(z.read('evidence/ui-runner/original.xctestrun'));bound=plistlib.loads(z.read('evidence/ui-bound.xctestrun'))
  descriptor=json.loads(z.read('evidence/ui-descriptor.json'))
  need(sha(z.read('evidence/ui-bound.xctestrun'))==descriptor['copied_sha256'] and sha(z.read('evidence/ui-runner/original.xctestrun'))==descriptor['original_sha256'],'ui_descriptor_digests')
  changes=delta(original,bound)
  allowed={'EnvironmentVariables','OnlyTestIdentifiers','SkipTestIdentifiers','TestingEnvironmentVariables'}
  need(all(len(x['path'].split('/'))>2 and x['path'].split('/')[2] in allowed for x in changes),'unreviewed_ui_descriptor_field')
  blueprint='PinkhaStage1AcceptanceUITests';a=original[blueprint];b=bound[blueprint];inverse=copy.deepcopy(bound)
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
   matches=[x for x in inventory if x['path'].endswith('/'+c['name']+'.log') and x['sha256']==c['log_sha256']]
   need(bool(matches),'original_command_log_digest_'+c['name'])
   commands.append({'name':c['name'],'status':c['status'],'return_code':c['return_code'],'log_sha256':c['log_sha256'],'pgid':q['pgid'],'kernel_absent_within_budget':True})
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
