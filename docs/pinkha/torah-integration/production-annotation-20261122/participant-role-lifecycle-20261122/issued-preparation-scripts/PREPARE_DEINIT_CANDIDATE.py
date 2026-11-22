import pathlib,json,hashlib,difflib,datetime
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-original-annotation-authority-20261122')
path='Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift'
p=out/'candidate'/path
before=p.read_bytes()
def sha(b):return hashlib.sha256(b).hexdigest()
assert sha(before)=='0f5120fefcafb5763913114142f5ed467a178114d656ca2c01fa40db7c3855ca'
test=out/'role-lifecycle-controls-await'
receipt=json.loads((test/'EXECUTION.json').read_text(encoding='utf-8'));assert receipt['result']=='PASS' and receipt['source_after_exact']
frozen=test/'PRODUCTION_CANDIDATE.swift';assert not frozen.exists();frozen.write_bytes(before)
(out/'PARTICIPANT_ROLE_BEFORE_DEINIT.swift').write_bytes(before)
old=b'    private let subscriptionBuilder = AcountParticipantSubscriptionBuilder()\n'
new=old+b'\n    deinit {\n        for permission in channelPinPermissions.value.values { permission.retire() }\n        for permission in participantEditPermissions.value.values { permission.retire() }\n        subscription?.cancel()\n    }\n'
assert before.count(old)==1
after=before.replace(old,new,1);p.write_bytes(after)
patch=''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),after.decode().splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path)).encode()
(out/'PARTICIPANT_DEINIT.patch').write_bytes(patch)
m={'base_candidate_sha256':sha(before),'candidate_sha256':sha(after),'patch_sha256':sha(patch),'prior_16_case_receipt_sha256':sha((test/'EXECUTION.json').read_bytes()),'prior_assertions_not_rerun':True,'worktree_changed':False,'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Retire already minted role snapshots and cancel original consumer on actual actor deallocation; no RPC.'}
(out/'PARTICIPANT_DEINIT_MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(m))
