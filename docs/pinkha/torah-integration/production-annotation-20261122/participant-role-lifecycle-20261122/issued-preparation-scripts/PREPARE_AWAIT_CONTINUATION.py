import pathlib,json,hashlib,shutil,difflib,datetime
out=pathlib.Path(r'C:\Users\DAVID\AppData\Local\Temp\otzaria-original-annotation-authority-20261122')
oldtest=out/'role-lifecycle-controls';test=out/'role-lifecycle-controls-await'
r=json.loads((oldtest/'EXECUTION.json').read_text(encoding='utf-8'))
assert r['result']=='FAIL' and all(not c['timed_out'] for c in r['commands'])
assert r['commands'][-1]['label']=='compile' and r['commands'][-1]['exit_code']==1
assert not (oldtest/'participant-role-lifecycle-controls.exe').exists()
assert not test.exists();test.mkdir()
def sha(b):return hashlib.sha256(b).hexdigest()
path='Anytype/Sources/ServiceLayer/ParticipantStorage/ParticipantsStorage.swift'
candidate=out/'candidate'/path;before=candidate.read_bytes()
assert sha(before)=='75428a575873caac9a592c18954c6b476c859381a27111c5ae650fd9447d74ed'
(out/'PARTICIPANT_ROLE_BEFORE_AWAIT.swift').write_bytes(before)
old=b'                self?.publishParticipants(\n'
new=b'                await self?.publishParticipants(\n'
assert before.count(old)==1;after=before.replace(old,new,1)
candidate.write_bytes(after)
m=json.loads((oldtest/'INPUTS.json').read_text(encoding='utf-8'))
for item in m['swift_inputs']:
 b=(oldtest/item['name']).read_bytes();assert sha(b)==item['sha256']
 if item['name']=='ParticipantRoleLifecycleControls.swift':
  assert b.count(old)==1
  b=b.replace(old,new,1)
 (test/item['name']).write_bytes(b)
 item['sha256']=sha(b)
(test/'CONTROLS.swift').write_bytes((oldtest/'CONTROLS.swift').read_bytes())
shutil.copytree(oldtest/'original',test/'original')
text=after.decode();actor=text[text.index('actor ParticipantsStorage:'):]
m.update({'candidate_sha256':sha(after),'actor_bytes_sha256':sha(actor.encode()),'continuation_of':'role-lifecycle-controls','reason':'Actual Apple52e and first portable semantic compile independently diagnosed the missing actor hop; exactly await added to production call and exact actor copy. No control assertions changed or cases previously executed.','raw_previous_execution_sha256':sha((oldtest/'EXECUTION.json').read_bytes()),'prepared_at':datetime.datetime.now(datetime.timezone.utc).isoformat()})
(test/'INPUTS.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
patch=''.join(difflib.unified_diff(before.decode().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path)).encode()
(out/'PARTICIPANT_LIFECYCLE_AWAIT.patch').write_bytes(patch)
original=(out/'PARTICIPANT_BASE.swift').read_bytes()
full=''.join(difflib.unified_diff(original.decode().splitlines(keepends=True),text.splitlines(keepends=True),fromfile='a/'+path,tofile='b/'+path)).encode()
(out/'PARTICIPANT_FINAL.patch').write_bytes(full)
receipt={'before_candidate':sha(before),'candidate_sha256':sha(after),'await_patch_sha256':sha(patch),'final_patch_sha256':sha(full),'controls_unchanged_sha256':sha((test/'CONTROLS.swift').read_bytes()),'worktree_changed':False,'native_calls':0}
(out/'PARTICIPANT_FINAL_MANIFEST.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(receipt))
