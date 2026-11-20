from pathlib import Path
import hashlib,json,shutil
r=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
sdk=Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119\.runtime-artifacts\sdk-source')
b=r/'build/any-engine-port'
t=r/'Tools/AnyEngineValidation/evidence/native-v8-commutative-witness-v2'
assert not t.exists()
p=b/'native-noop-v8-commutative-witness-v2'; result=json.loads((p/'result.json').read_text())
assert result['status']=='PASS' and result['testCases']==1 and result['skippedEvents']==0 and result['sourceStable']
shutil.copytree(p,t)
shutil.copytree(b/'native-noop-v8-commutative-witness-v1',t/'setup-failure-v1')
def sha(x): return hashlib.sha256(x.read_bytes()).hexdigest()
before=json.loads((p/'source-before.json').read_text())
paths=['internal/properties/conditional_membership_version_test.go','internal/properties/system.go','internal/crdt/apply.go','internal/crdt/controller.go','internal/crdt/op.go']
for name in paths:
 f=sdk/name
 assert sha(f)==before['files'][name]
 q=t/'executed-source'/name;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,q)
(t/'scope.json').write_text(json.dumps({'status':'PASS_ACTUAL_NATIVE_PROPERTIES_PROJECTION_WITNESS','test':'TestNativeConditionalMembershipLateOperationLeavesFullVersionUnchanged','cases':1,'failed':0,'skipped':0,'witness':'Actual native properties handler and allocator: v1 collections, newer unrelated v3, then late v2 add-to-set; full _ver remains equal while memberships change and _applySeq advances.','scopeLimit':'Controller/handler regression, not an execution of the old Any executable or successful fixed HTTP CAS. The watchdog historical before/after metadata was not captured.','initialSetupFailureRetained':True,'sourceStable':True},indent=2)+'\n',encoding='utf8')
shutil.copyfile(__file__,t/'executed-archive.py')
files={x.relative_to(t).as_posix():{'sha256':sha(x),'bytes':x.stat().st_size} for x in sorted(t.rglob('*')) if x.is_file()}
(t/'archive.json').write_text(json.dumps({'status':'FROZEN','files':files},indent=2)+'\n',encoding='utf8')
print(json.dumps({'status':'FROZEN','files':len(files),'archiveSHA256':sha(t/'archive.json'),'receiptSHA256':sha(t/'result.json'),'path':t.relative_to(r).as_posix()}))
