import pathlib,subprocess,json,hashlib,datetime,plistlib,collections
B=pathlib.Path('/mnt/development/projects')
W=B/'worktrees/anytype-wave15-shared-20261123'
P=B/'worktrees/anytype-wave15-page154-success-audit-20261123/docs/validation/20261123-page154-app-success'
M=B/'worktrees/anytype-wave15-page154-mounted-admission-20261123/docs/validation/20261123-semantic-page-mounted-admission'
O=B/'diagnostics/page154-success-and-products-root-review-20261123'
O.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=W)
def tree(ref):
 out={}
 for row in git('ls-tree','-rz','--full-tree',ref).split(b'\0'):
  if not row:continue
  meta,path=row.split(b'\t',1);mode,kind,oid=meta.decode().split();assert kind=='blob'
  out[path.decode()]={'mode':mode,'oid':oid}
 return out
manifest=read(P/'COPIED_ORIGINALS.json');copies={}
assert manifest['count']==len(manifest['copied_files'])==121
for row in manifest['copied_files']:
 raw=(P/row['path']).read_bytes();original=pathlib.Path(row['source']).read_bytes()
 assert raw==original and sha(raw)==row['sha256'] and len(raw)==row['bytes'],row['path']
 copies[row['path']]={'sha256':sha(raw),'bytes':len(raw)}
assert sum(x['bytes'] for x in copies.values())==manifest['bytes']==5403415
audit=read(P/'originals/INDEPENDENT_NATIVE_AUDIT.json')
assert sha((P/'originals/INDEPENDENT_NATIVE_AUDIT.json').read_bytes())=='348d6e1f93b02fcd1d8d52e460115c64dd5ad49274e0c7375256de50f6bad938'
ref='68148339c275268795360d71d519a5baf003adf8';assert audit['source_sha']==ref
qualified=audit['source']['independently_read_git_sources'];assert len(qualified)==47
for p,x in qualified.items():
 raw=git('show',ref+':'+p)
 assert sha(raw)==x['sha256'] and len(raw)==x['bytes'] and raw==(P/'qualified-source'/p).read_bytes(),p
d=P/'originals/native-selected'
s=read(d/'actual-summary.json');assert [s[k] for k in ['totalTestCount','passedTests','failedTests','skippedTests']]==[1,1,0,0]
nodes=[]
def walk(x):
 if isinstance(x,dict):
  if x.get('nodeType')=='Test Case':nodes.append((x['nodeIdentifier'],x['result']))
  for v in x.values():walk(v)
 elif isinstance(x,list):
  for v in x:walk(v)
walk(read(d/'actual-tests.json'))
case='SemanticAnchorPage154NativeAcceptanceTests/testActualPage154FactoryPublishesNativeAnchorIntoOpenedDocument()'
assert nodes==[(case,'Passed')]
ex=read(d/'execution.json')
assert ex['actual_execution']['actual_cases']==[[case,'Passed']]
assert ex['actual_product_methods_passed']==ex['actual_xctest_commands_started']==ex['app_builds_started']==1
assert ex['existing_product_methods_rerun']==ex['native_methods_rerun']==ex['native_builds']==0
assert ex['status']=='PASS_ACTUAL_APP_FACTORY_EVENT_AND_READBACK'
assert ex['binding']==audit['binding'] and ex['binding']['sourceSHA']==ref and ex['binding']['runID']=='45116855451'
commands=ex['commands'];assert len(commands)==23
for c in commands:
 q=c['owned_group_quiescence']
 assert c['return_code']==0 and q['status']=='PASS' and q['live_members']==0 and q['timeout_observations']==[]
 assert q['pgid']==c['worker_pid'] and isinstance(c['worker_pid'],int) and c['worker_pid']>1
for state in ex['owned_simulator_cleanup'].values():assert state['status']=='PASS' and state['return_code']==0
raw=(d/'actual-single-xctest.log').read_text()
assert raw.count(audit['raw_terminal']['text'])==1
en=read(d/'enumeration.json');assert en['errors']==[] and len(en['values'])==1
en=en['values'][0];assert len(en['enabledTests'])==1 and len(en['disabledTests'])==940
assert en['enabledTests'][0]['identifier']=='AnytypeTests/'+case
attachment=P/'originals'/audit['actual_attachment']['path']
assert sha(attachment.read_bytes())==ex['observation_sha256']==audit['actual_attachment']['sha256']
sb=(d/'source-before.json').read_bytes();assert sb==(d/'source-after.json').read_bytes()
src=json.loads(sb);originaltree=tree(ref);assert len(src)==12033 and set(src)==set(originaltree)
for p,x in qualified.items():assert src[p]==x['sha256'],p
jobs=read(P/'originals/original-attempt1-jobs-api.json')['jobs']
job=[j for j in jobs if j['id']==137501560037];assert len(job)==1 and job[0]['conclusion']=='success'
api=read(P/'originals/original-artifacts-api.json')['artifacts'];assert len(api)==1
a=api[0];assert a['id']==14794983588 and a['size_in_bytes']==703289417 and a['digest']=='sha256:082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46'
ma=read(M/'original-artifacts.json');mcopies={}
assert len(ma['copied_originals'])==24
for row in ma['copied_originals']:
 raw=(M/row['copy_path']).read_bytes();orig=pathlib.Path(row['original_path']).read_bytes()
 assert raw==orig and len(raw)==row['bytes'] and sha(raw)==row['sha256'],row['copy_path']
 mcopies[row['copy_path']]={'bytes':len(raw),'sha256':sha(raw)}
for name,row in ma['external_originals'].items():
 raw=pathlib.Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and sha(raw)==row['sha256'],name
v=M/'originals';inventories={}
for scope,prefix in [('native',''),('ui','ui-runner/')]:
 inv=read(v/(scope+'-inventory.json'));entries=read(v/(scope+'-verified-entries.json'))
 pm=read(v/(prefix+'semantic-page154-early-products/manifest.json'))
 assert entries==pm['products'] and len(entries)==inv['entries']
 assert inv['manifest_sha256']==sha((v/(prefix+'semantic-page154-early-products/manifest.json')).read_bytes())
 assert inv['entry_proof_sha256']==sha((v/(scope+'-verified-entries.json')).read_bytes())
 kinds=dict(collections.Counter(x['kind'] for x in entries.values()));assert kinds==inv['kinds']
 assert sum(x.get('bytes',0) for x in entries.values())==inv['file_bytes_hashed']
 assert inv['links']==inv['outside_members']==inv['case_collisions']==0
 assert inv['archive_sha256']==pm['archive_sha256'] and inv['compressed_bytes']==pm['archive_bytes']
 assert not pm['build_reuse_enabled'] and pm['capture_phase']=='AFTER_BUILD_BEFORE_ADMISSION'
 inventories[scope]={'entries':len(entries),'kinds':kinds,'archiveSHA256':inv['archive_sha256'],'originalManifestSHA256':inv['manifest_sha256'],'reStreamedByRoot':False}
assert inventories['native']['entries']==5008 and inventories['ui']['entries']==30
frozen=read(v/'frozen-git-inputs.json');ftree=tree(frozen['source_sha'])
assert frozen['source_sha']=='5a6a05d9152553b1bee661eadc7b539b25b10ae1'
assert frozen['git']==ftree and set(frozen['inputs'])==set(ftree)
product=lambda p:not p.startswith(('Tools/','.github/','docs/'))
beforeproduct={p:x for p,x in ftree.items() if product(p)}
afterproduct={p:x for p,x in originaltree.items() if product(p)}
assert beforeproduct==afterproduct and len(beforeproduct)==6321
deltas={p for p in set(ftree)|set(originaltree) if ftree.get(p)!=originaltree.get(p)}
compare=read(v/'source-comparison.json');assert deltas==set(compare['controller_documentation_only_delta']) and len(deltas)==18
embedded=read(v/'native-source-inputs-original.json');eh={p:(x['sha256'] if isinstance(x,dict) else x) for p,x in embedded['inputs'].items()}
assert len(eh)==12042 and embedded['source_sha']==ref
assert {p:eh[p] for p in src}==src
extra={p:x for p,x in eh.items() if p not in src};assert extra==compare['exact_approved_framework_extras'] and len(extra)==9
ar=git('show','8a6d64ba152ba3aa4bb4376d070f63f5c9daceca:Tools/PinkhaSemanticAnchorWire/apple_mounted/admissions/45116855451-1.json')
ad=json.loads(ar);assert sha(ar)=='17c37d842009b23d50ab2222383c1f025242aa2e61f1828cf1bc1a346b5ed7e5'
assert ad['consumer_sha']==ref and ad['consumer_run']=='45116855451' and ad['artifact_id']==a['id']
for scope,prefix in [('native',''),('ui','ui-runner/')]:
 raw=(v/(prefix+'original.xctestrun')).read_bytes();pl=plistlib.loads(raw)
 assert sha(raw)==ad[scope+'_descriptor']['sha256']
 assert pl['__xctestrun_metadata__']['FormatVersion']==(2 if scope=='native' else 1)
 if scope=='native':
  targets=[t for c in pl['TestConfigurations'] for t in c['TestTargets'] if t.get('BlueprintName')=='AnytypeTests'];assert len(targets)==1;target=targets[0]
 else:
  keys=[k for k in pl if k!='__xctestrun_metadata__'];assert keys==['PinkhaStage1AcceptanceUITests'];target=pl[keys[0]]
 tokens=target['TestingEnvironmentVariables']['DYLD_INSERT_LIBRARIES'].split(':')
 assert tokens.count(ad[scope+'_descriptor']['main_thread_checker_token'])==1
 assert ad[scope+'_manifest_sha256']==inventories[scope]['originalManifestSHA256']
q=read(M/'qualification.json')
assert q['new_product_tests']==q['builds']==q['full_restores']==0
result={'schemaVersion':1,'status':'INDEPENDENT_ROOT_NATIVE_RESULT_AND_ORIGINAL_PRODUCTS_REVIEW_PASS',
 'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runID':45116855451,'sourceCommit':ref,
 'originalNativeAuditSHA256':sha((P/'originals/INDEPENDENT_NATIVE_AUDIT.json').read_bytes()),
 'nativeCopies':{'count':len(copies),'bytes':sum(x['bytes'] for x in copies.values()),'manifestSHA256':sha((P/'COPIED_ORIGINALS.json').read_bytes())},
 'qualifiedSourceBlobsRead':47,'originalNativeTestCases':nodes,'actualCommands':23,'allActualOwnedGroupsAbsent':True,
 'sourceBeforeAfterSHA256':sha(sb),'originalTrackedPaths':len(src),'originalTrackedContentsRereadByRoot':47,
 'mountedCopies':{'count':len(mcopies),'bytes':sum(x['bytes'] for x in mcopies.values()),'manifestSHA256':sha((M/'original-artifacts.json').read_bytes())},
 'mountedAdmissionSHA256':sha(ar),'inventories':inventories,'productGitInputsIdentical':len(beforeproduct),
 'fullOriginalGitContentAuditRetainedSHA256':sha((v/'source-comparison.json').read_bytes()),
 'frozenOriginalInputsGitTreeAndModesMatch':True,'originalToMountedControllerOnlyDifferences':len(deltas),
 'frameworkExtras':len(extra),'firstInventoryAuditorFailurePreserved':True,
 'rootAuditBuilds':0,'rootAuditControllerTests':0,'rootAuditProductMethods':0,'largeArtifactRedownloads':0,'largeArchiveRestreams':0,
 'limitations':ex['limits'],'mountedActualAcceptance':'NOT_RUN','mountedPairRepair':'SEPARATE_NEW_ADAPTER_QUALIFICATION_PENDING'}
raw=(json.dumps(result,indent=2,sort_keys=True)+'\n').encode();(O/'root-review.json').write_bytes(raw)
print(json.dumps({'status':result['status'],'sha256':sha(raw),'nativeOriginalCopies':len(copies),'mountedOriginalCopies':len(mcopies),'newNativeActualPassRetained':1,'productsEntries':5038,'gitProductInputsIdentical':6321,'auditExecutions':0}))
