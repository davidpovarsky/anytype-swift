import pathlib,subprocess,json,hashlib,ast,datetime
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
G=['sudo','-n','-u','ubuntu','-g','chatgpt-agent','git','-c','gc.auto=0','-C',str(ROOT)]
OUT=pathlib.Path('/tmp/pinkha-wave3-definitions-warm-intake-audit.json')
def h(b):return hashlib.sha256(b).hexdigest()
def git(ref,path):return subprocess.check_output(G+['show',ref+':'+path],stderr=subprocess.PIPE)
def exact(path,digest):
 b=path.read_bytes();assert h(b)==digest,(str(path),h(b),digest);return b
def fetch(ref):
 if subprocess.run(G+['cat-file','-e',ref+'^{commit}'],capture_output=True).returncode:
  subprocess.run(G+['fetch','--no-tags','--refmap=','origin',ref],capture_output=True,check=True)
assert not OUT.exists()
result={'timeUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'testsExecuted':0,'appBuilds':0,'nativeAccountStoresOpened':0}
ref='5235bf902f8820fdc41fe802265ff5444407b363';fetch(ref)
prefix='docs/validation/20261127-wave1-functional-migration/native-definition-directory/'
qbytes=git(ref,prefix+'qualification.json');assert h(qbytes)=='d4a3e363d4d1bfd0f1f63c969d58d12615a5fdb6c80b4dcfc9aa386605e91dda';q=json.loads(qbytes)
for item in q['files']:
 b=git(ref,prefix+item['path']);assert len(b)==item['bytes'] and h(b)==item['sha256'],item['path']
for path,digest in q['code'].items():assert h(git(ref,path))==digest,path
base=pathlib.Path('/var/lib/pinkha-w1-functional-migration-20261127')
component=base/'definition-directory-components-attempt3';native=base/'definition-directory-native-attempt1'
craw=exact(component/'result.json',q['componentResultSHA256']);assert craw==git(ref,prefix+'components/result.json');c=json.loads(craw)
nraw=exact(native/'result.json',q['nativeResultSHA256']);assert nraw==git(ref,prefix+'native/result.json');n=json.loads(nraw)
assert c['status']=='PASS' and c['exitCode']==0 and c['ownedGroupAbsent'] and not c['errors']
clog=exact(component/'test.log',c['logSHA256']);assert clog==git(ref,prefix+'components/test.log')
assert len(c['passLines'])==4 and all(v in clog.decode() for v in c['passLines']) and not c['failLines']
assert n['status']=='PASS' and not n['errors'] and n['allOwnedGroupsPositivelyAbsent']
assert n['actualNativeDefinitionPatchWrites']==6 and n['actualPreparedOperations']==0 and n['intentionalNativeSIGKILLCount']==1
assert n['testInvocations']==3 and n['uniqueTestMethods']==1
assert not n['sourceAdmissionPromoted'] and not n['wholeSpaceMigration'] and not n['originalAccountOpenedByController']
assert n['nativeBefore']==n['nativeAfter'] and n['sourceDefinitionMembersBefore']==n['sourceDefinitionMembersAfter']
for name in ['edit-test.log','edited-reopen-test.log','restored-reopen-test.log']:
 assert (native/name).read_bytes()==git(ref,prefix+'native/'+name),name
for row in n['privateLogReceipts']:
 raw=exact(native/'private-logs'/row['name'],row['sha256']);assert len(raw)==row['bytes']
for name,digest in n['proofSHA256'].items():exact(native/'component'/name,digest)
source=git(ref,prefix+'components/source-before.json');assert source==git(ref,prefix+'components/source-after.json')
assert source==git(ref,prefix+'native/swift-sources-before.json')==git(ref,prefix+'native/swift-sources-after.json')
manifest=json.loads(source);diffs=[]
for path,digest in manifest.items():
 assert h(git(ref,path))==digest,('candidate receipt source mismatch',path)
 try:actual=h(git('HEAD',path))
 except subprocess.CalledProcessError:actual=None
 if actual!=digest:diffs.append({'path':path,'testedSHA256':digest,'currentRootSHA256':actual,'addedByCandidate':path in q['code']})
for file in ['source-before.json','source-after.json']:
 assert (component/file).read_bytes()==source
for file in ['swift-sources-before.json','swift-sources-after.json']:
 assert (native/file).read_bytes()==source
result['definitions']={'commit':ref,'qualificationSHA256':h(qbytes),'publicFilesVerified':len(q['files']),'sourceClosureFilesVerifiedAgainstCommit':len(manifest),'sourceClosureDifferencesAtRoot':diffs,'originalComponentMethods':4,'originalNativeMethodInvocations':3,'actualNativeDefinitionPatchWrites':6,'actualSIGKILLCount':1,'originalsVerified':['components/result.json','components/test.log','native/result.json','three native XCTest logs','three original native logs','ten native proof files','four complete source manifests'],'newTestsExecuted':0,'scope':'13 original native definition entries;137 unresolved remain explicit. No full migration/history/Apple or global schema concurrency admission.'}
ref='a89635ab5d911af37719d23adefa161d864c91f8';fetch(ref)
tools='Tools/CurrentAppleValidation/combined_heart_semantics/wave2/wave3-warm-staged/'
docs='docs/validation/20261127-wave2-warm-stage-intake/'
fragment=git(ref,tools+'wave3_intake.py');assert h(fragment)=='f097cdb1a12087475cda0728d34d7a7dcb2ef0d62ad67810fd9724d11d096bfa'
inverse=json.loads(git(ref,docs+'stage-schema-inverse.json'));restored=fragment.decode()
for op in reversed(inverse['changes']):
 i=op['candidateStart'];assert restored[i:i+len(op['new'])]==op['new'];restored=restored[:i]+op['old']+restored[i+len(op['new']):]
assert h(restored.encode())==inverse['originalSHA256']=='7ff8af54801d089fe6abad52fdd3c6fbec957c8f205be1d2299556a75d227ad5'
def defs(text):return {n.name:ast.get_source_segment(text,n) for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
old,new=defs(restored),defs(fragment.decode());assert set(new)-set(old)=={'w3_stage_control_references'}
changed=[k for k in old if old[k]!=new[k]];assert changed==['w3_stage_proof']
profile=json.loads(git(ref,tools+'frozen-profile.staged.closed.json'));assert profile['readyForRuntimeAdmission'] is False
assert 'W3_BUILD_ADMISSION_SHA = None' in fragment.decode() and 'W3_EXECUTED_PRODUCER_SHA = None' in fragment.decode() and 'W3_EXECUTED_DELTA_SHA = None' in fragment.decode()
handoff=json.loads(git(ref,docs+'handoff.json'))
for item in handoff['files']:
 parent=tools if item['file'] in ['wave3_intake.py','materialize_wave3_intake.py','frozen-profile.staged.closed.json','test_staged_warm_intake.py'] else docs
 b=git(ref,parent+item['file']);assert len(b)==item['bytes'] and h(b)==item['sha256']
for rel,digest in [('source-staging1/receipt.json','506620e9c9cb2aafe0c89076269c2a7d3a4cb6fa7334924a18dda4dff1b2f6bb'),('cache-requalification1/receipt.json','cf181ce88ac84618868a4c1c9faed69288bcb191599e8015271d629bcd0be00a'),('source-staging.proposed-ready.preview.txt','d22db29bd444895e0152cc9234b3631cfb085684d23bd5ac9c074b64e51e5f3d'),('build-admission.draft.json','cf48a0fa5e5a3acdabff9a9e6df77c6abd9098b1b446af107ebf8c397541c640')]:
 assert h(git(ref,docs+'actual-inputs/'+rel))==digest,rel
result['warmIntake']={'commit':ref,'candidateSHA256':h(fragment),'inverseRestoresEveryOriginalByte':True,'inverseOperations':len(inverse['changes']),'originalDeclarationsUnchanged':len(old)-len(changed),'changedOriginalDeclarations':changed,'addedDeclarations':list(set(new)-set(old)),'actualStageAndCachePinsMatchRootPreviouslyVerifiedOriginals':True,'readyForRuntimeAdmission':False,'reportedOriginalPortableMethods':3,'reportedOriginalNegativeCases':7,'newTestsExecuted':0,'currentMacSourceUnchanged':True}
result['status']='PASS_SOURCE_AND_ORIGINAL_EVIDENCE_REVIEW_NO_RERUN'
OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps({'path':str(OUT),'sha256':h(OUT.read_bytes()),'status':result['status'],'definitionSourceClosureFiles':len(manifest),'rootSourceDifferences':diffs,'warmIntakeInverseOperations':len(inverse['changes'])}))
