import pathlib,json,hashlib,zipfile,subprocess,ast,uuid,datetime
D=pathlib.Path('/mnt/development/projects/diagnostics/native-ui-boot-order-actual-result-20261123')
W=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave15-shared-20261123')
S='a36c31542671f4bb94405855bd94c1ef8eb5464b'
def sha(b):return hashlib.sha256(b).hexdigest()
def blob(p):return subprocess.check_output(['git','show',S+':'+p],cwd=W,timeout=30)
def regular(n):return (D/n).read_bytes()
assert sha(regular('artifact.zip'))=='1f5fc52eb1dbb6dd03d14e998d43054ce3a7b528fb99a14b46effc53e357d639'
assert sha(regular('job.log'))=='1a379f1b00c48bcf43a4058f9990cc8b832592114f6fcd505a625de3602466d9'
run=json.loads(regular('run.json'));jobs=json.loads(regular('jobs.json'));artifact=json.loads(regular('artifacts.json'))
assert run['id']==45131959492 and run['head_sha']==S and run['run_attempt']==1 and run['status']=='completed' and run['conclusion']=='failure'
job=next(j for j in jobs['jobs'] if j['id']==137549291924)
assert job['conclusion']=='failure'
with zipfile.ZipFile(D/'artifact.zip') as z:files={i.filename:z.read(i) for i in z.infolist() if not i.is_dir()}
inventory=json.loads(regular('archive-inventory.json'))
assert len(files)==len(inventory)
for r in inventory:assert len(files[r['path']])==r['size'] and sha(files[r['path']])==r['sha256']
def data(p):return json.loads(files[p])
assert files['control-source-sha.txt'].decode().strip()==S
assert files['application-source-sha.txt'].decode().strip()=='4b09cc5478c60c1c6728a54f2a27a115637a835b'
failure=data('native-ui-original-products-restore.json')
assert failure['status']=='FAIL' and failure['action']=='admit' and failure['fullAcceptance'] is False
assert failure['failure']=={'kind':'TimeoutExpired','reason':"Command '['git', 'rev-parse', 'HEAD']' timed out after 30 seconds"}
assert not any(p.startswith('native-ui-original-commands/admit/') for p in files)
boot=data('hanlin-provider/boot.json');sim=data('simulator.json');udid=sim['ownedUDID']
assert str(uuid.UUID(udid)).upper()==udid and boot['ownedSimulatorUDID']==udid
assert boot['status']=='OWNED_SIMULATOR_BOOT_REQUESTED_READINESS_PENDING' and boot['simulatorInitialState']=='Shutdown' and boot['simulatorBootRequested'] is True
assert boot['githubRunID']=='45131959492' and boot['sourceCommit']==S
assert data('hanlin-provider/cleanup.json')['status']=='NO_FIXTURE_DIRECTORY_WAS_CREATED'
runtime=data('native-ui-original-runtime.json')
assert runtime['status']=='EXACT_INSTALLED_ORIGINAL_RUNTIME_PAIR' and runtime['ownedSimulatorUDID']==udid and runtime['testsExecuted']==0 and runtime['readiness']=='NOT_RUN'
cleanup=data('native-ui-original-simulator-cleanup.json')
assert cleanup['status']=='OWNED_SIMULATOR_REMOVAL_OBSERVED' and cleanup['ownedSimulatorUDID']==udid and cleanup['absenceProof'] is True and cleanup['foreignSimulatorsTouched'] is False
assert cleanup['controllerSourceInputs']==runtime['controllerSourceInputs']
inputs={**cleanup['controllerSourceInputs'],**cleanup['qualifiedProvider']['inputs']}
for p,h in inputs.items():assert sha(blob(p))==h
assert len(inputs)==13
deps=cleanup['qualifiedProvider']['runtimeDependencies']
assert sha(blob('Tools/PinkhaSimulatorGate/simulator_selection.py'))==deps['simulatorSelectionSHA256']
raw=blob('Tools/PinkhaSimulatorGate/sdk06_enumeration_probe.py');tree=ast.parse(raw.decode());lines=raw.splitlines(keepends=True)
for name,h in deps['normalizerFunctions'].items():
 nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name];assert len(nodes)==1
 n=nodes[0];start=min([n.lineno]+[v.lineno for v in n.decorator_list])
 assert sha(b''.join(lines[start-1:n.end_lineno]))==h
commands={}
for p,b in files.items():
 if p.startswith('native-ui-original-commands/') and p.endswith('.json'):
  o=json.loads(b);assert o['status']=='PASS' and o['returncode']==0
  for stream in ('stdout','stderr'):
   f=str(pathlib.PurePosixPath(p).parent/o[stream]['path'])
   assert len(files[f])==o[stream]['bytes'] and sha(files[f])==o[stream]['sha256']
  commands[p]=o
assert len(commands)==8
for kind in ('shutdown','delete'):
 assert commands['native-ui-original-commands/cleanup/'+kind+'.json']['command']==['xcrun','simctl',kind,udid]
before=data('native-ui-original-commands/create/devices-before.stdout')
after=data('native-ui-original-commands/cleanup/devices-after.stdout')
def ids(value):
 assert isinstance(value,dict) and isinstance(value['devices'],dict)
 out=[]
 for key,rows in value['devices'].items():
  assert isinstance(key,str) and isinstance(rows,list)
  for row in rows:
   assert isinstance(row,dict) and isinstance(row['udid'],str)
   out.append(str(uuid.UUID(row['udid'])).upper())
 assert len(out)==len(set(out))
 return out
old=ids(before);new=ids(after);assert udid not in old and udid not in new and len(new)==40
steps={x['name']:x['conclusion'] for x in job['steps']}
assert steps['Request owned cold boot before original Products admission']=='success'
assert steps['Admit and restore original Products without any build']=='failure'
assert steps['Prepare the qualified owned Hanlin HTTPS provider']=='skipped'
for p in ('native-ui-continuation','archive-roundtrip','custom-type','native-history'):
 assert steps['Execute and verify original Products '+p]=='skipped'
assert steps['Preserve final original Products and source integrity']=='skipped'
out={'status':'INDEPENDENT_ACTUAL_FAILURE_REVIEW_COMPLETE','reviewed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run_id':45131959492,'source_sha':S,'conclusion':'failure','job_id':137549291924,'runner_id':job['runner_id'],'original_archive_sha256':sha(regular('artifact.zip')),'original_job_log_sha256':sha(regular('job.log')),'all_original_archive_members_verified':len(files),'actual_original_command_receipts_verified':len(commands),'current_controller_provider_inputs_equal_frozen_git':13,'normalizer_function_pins_unchanged':3,'simulator_selector_pin_unchanged':True,'fresh_owned_uuid':udid,'boot_request':'PASS_READINESS_PENDING','admission_failure':failure['failure'],'last_boundary':'Current source/context verification before the first original App worktree command. Current control_context and provider github_context both use git rev-parse; the exception does not identify which of these same-argv calls timed out.','original_app_checkout':'NOT_REACHED_BY_CONTROL_FLOW_AND_COMPLETE_ARTIFACT_COMMAND_SET','product_restore':'NOT_REACHED','provider_prepare':'NOT_REACHED','provider_fixture':'NO_FIXTURE_DIRECTORY_WAS_CREATED','provider_transcript':'NOT_REACHED','new_builds':0,'new_product_methods_started':0,'retained_22_methods_rerun':0,'owned_shutdown_and_delete_returned_zero':True,'complete_after_inventory_devices':40,'owned_uuid_absent_before_and_after':True,'overall_provider_or_product_acceptance':False,'final_product_integrity_step':'SKIPPED_NOT_CLAIMED','likely_boot_resource_contention':'INFERENCE_ONLY_NOT_ESTABLISHED_BY_HOST_RESOURCE_TELEMETRY','script_sha256':sha(pathlib.Path(__file__).read_bytes())}
(D/'root-review.json').write_text(json.dumps(out,sort_keys=True,indent=2)+'\n')
print(json.dumps({'status':out['status'],'root_sha256':sha(regular('root-review.json')),'members':len(files),'new_tests':0,'cleanup':'OWNED_ABSENCE_VERIFIED'}))
