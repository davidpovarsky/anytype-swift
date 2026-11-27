import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='ff6836a6d4db7f1a19b94280d3b2f548e8d7d622'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-helper680-integration.json')
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE)
def t(*a):return b(*a).decode().strip()
def h(x):return hashlib.sha256(x).hexdigest()
def owned(path,data,exclusive=True):
 code="import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);f=p.open(sys.argv[2]);f.write(sys.stdin.buffer.read());f.close()"
 subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'xb' if exclusive else 'wb'],input=data,check=True,capture_output=True)
def fetch(sha):
 if subprocess.run(G+['cat-file','-e',sha+'^{commit}'],capture_output=True).returncode:b('fetch','--no-tags','--refmap=','origin',sha)
def preserved():
 paths=['Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json',GATE,'NativeApp/UITests/NativeLaunchTests.swift']
 paths += [p for p in t('ls-tree','-r','--name-only','HEAD').splitlines() if p.endswith('/Package.resolved')]
 return {p:b('show','HEAD:'+p) for p in paths}
assert not OUT.exists()
assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
STATUS=t('status','--porcelain');ROWS=[]
PINNED=preserved()

def finish(parent,donor,label,expected_paths=None):
 for p,data in PINNED.items():assert (ROOT/p).read_bytes()==data,p
 paths=t('diff','--cached','--name-only').splitlines()
 if expected_paths is not None:assert paths==sorted(expected_paths),(paths,expected_paths)
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-wave3-'+label+'-retention.json');assert not gate.exists()
 r=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
 pathlib.Path(str(gate)+'.stdout').write_bytes(r.stdout);pathlib.Path(str(gate)+'.stderr').write_bytes(r.stderr)
 result=json.loads(gate.read_bytes());assert r.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
 message=('Integrate reviewed '+label+' source into Wave3\n\nOriginal native and SDK pins, lockfiles and historical evidence preserved. New Apple compilation/runtime remain NOT_RUN. Mac8f2 source is unchanged.\n\nIntegrated from '+donor+'\n')
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
 head=t('rev-parse','HEAD');assert t('status','--porcelain')==STATUS
 assert t('ls-remote','origin',REF).split()[0]==parent
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
 row={'label':label,'parent':parent,'donor':donor,'head':head,'tree':tree,'files':paths,'sourceRetentionPassed':True,'reviewedRefactors':129,'retentionSHA256':h(gate.read_bytes()),'pinsAndLocksUnchanged':True,'nativeLaunchSHA256':h((ROOT/'NativeApp/UITests/NativeLaunchTests.swift').read_bytes()),'newAppleTestsExecuted':0,'pushExitCode':push.returncode,'pushStdout':push.stdout,'pushStderr':push.stderr}
 if push.returncode==0:
  assert t('ls-remote','origin',REF).split()[0]==head
  row['normalPushReadback']=head
 ROWS.append(row);OUT.write_text(json.dumps({'start':START,'head':head,'integrations':ROWS},indent=2,sort_keys=True)+'\n')
 print(json.dumps({'progress':row,'receiptPath':str(OUT),'receiptSHA256':h(OUT.read_bytes())}),flush=True)
 assert push.returncode==0


import base64
DONOR='680364279e08dc69d7d7eee8f6f13169ea8d0be4'
DP='docs/validation/20261127-hanlin-message-save-action/'
fetch(DONOR)
assert t('rev-parse',DONOR+'^')=='8932c43f59f9976efd9930e4f8c5ba0b0fee72dd'
assert t('rev-parse',DONOR+'^{tree}')=='1cbff430d880a46470d0f252f4b2c9cf8e761d20'
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',DONOR).splitlines()]
assert len(rows)==13
for mode,path in rows:
 assert mode in {'A','M'}
 if mode=='M':assert b('show','HEAD:'+path)==b('show',DONOR+'^:'+path),path
 else:assert not (ROOT/path).exists(),path
proofraw=b('show',DONOR+':'+DP+'native-acceptance-source-intake.json')
assert h(proofraw)=='0f0759cb5ebaa814588d46f7879d99cc5d0331c68e446b7d5c1c0c536225e7ef'
proof=json.loads(proofraw)
assert proof['status']=='SOURCE_ONLY_NOT_COMPILED' and proof['apple_compile']==proof['native_acceptance']==proof['tests']['status']=='NOT_RUN'
assert proof['canonical_hanlin']=='45d5d90512c304d3457774b185741b7ef7d801db'
assert proof['tests']['methods']==['testOriginalSDKMessageSaveConsentAndNativeReadback']
verified=[];n=0
for row in proof['files']:
 path=row['path'];raw=b('show',DONOR+':'+path)
 assert h(raw)==row['after_sha256'] and len(raw)==row['after_bytes'] and t('rev-parse',DONOR+':'+path)==row['after_blob'],path
 if row.get('before_blob'):
  original=b('show','HEAD:'+path)
  assert t('rev-parse','HEAD:'+path)==row['before_blob'] and h(original)==row['before_sha256'] and len(original)==row['before_bytes'],path
  restored=raw
  for op in reversed(row['inverse_operations']):
   pos=op['after_utf8_offset'];after=op['after'].encode();before=op['before'].encode()
   assert restored[pos:pos+len(after)]==after,path
   restored=restored[:pos]+before+restored[pos+len(after):];n+=1
  assert restored==original,path
 else:assert row['new_file'] and not (ROOT/path).exists(),path
 verified.append({'path':path,'afterBlob':row['after_blob'],'sha256':h(raw),'inverseOperations':len(row.get('inverse_operations',[]))})
assert n==20 and len(verified)==10
preview=t('merge-tree','--write-tree',START,DONOR);assert len(preview)==40
assert t('diff','--name-only',START,preview).splitlines()==sorted(p for _,p in rows)
for path,data in PINNED.items():assert b('show',preview+':'+path)==data,path
original_map=b('show','HEAD:'+MAP);mapping=json.loads(original_map);assert len(mapping['changes'])==129
updates={
 'Anytype/Sources/Pinkha/AI/PinkhaHanlinChatPresentation.swift':('35f5857ca3de7c98c3e33358a3af2f7138364ba3','49acb7d07bd8d93a8750d481d9c9873caa77067d'),
 'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinChatPresentation.swift':('a4de05fbe3afb7b5b4f11a97b08563c79e45c7d7','11cfab1994884d40b8a6cc0a21a6e9bb2538e17d'),
 'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaHanlinWriteJournal.swift':('dc3d1110e42022723433010f190d984427061a0e','c4578ca5e67ee1f8338a8b5c6f287989fb2d7d2a')}
changed=[];changed_hashes=[]
for row in mapping['changes']:
 matched=False
 if row['to'] in updates:
  before,after=updates[row['to']]
  assert row['replacementBlob']==before and t('rev-parse',DONOR+':'+row['to'])==after
  row['replacementBlob']=after;matched=True;changed_hashes.append(row['to'])
 for shared in row.get('sharedSources',[]):
  if shared['path'] in updates:
   before,after=updates[shared['path']]
   assert shared['gitBlob']==before and t('rev-parse',DONOR+':'+shared['path'])==after
   shared['gitBlob']=after;matched=True;changed_hashes.append(shared['path'])
 if matched:
  row['reason']+=' Reviewed2026-11-27 Wave3 native message-Save acceptance source: DEBUG Simulator hooks retain the original mounted host, protected journal actor, account/context fences and cancellation drain. The fixture is qualified from an actual same-process mounted native read; only model HTTP input is controlled. Original Send/Save and native Cancel/Allow produce original SDK/native results; independent postflight reads original native body and complete ACK. Release shared/Heart projection remains unchanged. No ordinary production Save capability is enabled.'
  row['validation'].append('Root read680 source and retained native-acceptance publication;20 literal inverse operations reconstruct all four modified sources. Exact baseline/from/to/kind are retained; only three reviewed replacement/shared hashes changed. New UI file awaits separate explicit Stage1 PBX registration successor and Wave2 editor hook. Apple compile and native/UI acceptance NOT_RUN; no fixture provisioned. See docs/validation/20261127-wave3-native-save-acceptance-intake/root-source-review.json.')
  changed.append(row['to'])
assert len(changed)==2 and sorted(changed_hashes)==sorted(updates)
original_mapping=json.loads(original_map)
for old,new in zip(original_mapping['changes'],mapping['changes']):
 assert all(old[k]==new[k] for k in ['from','to','kind','baselineBlob'])
 if old['to'] not in changed:assert old==new
for mode,path in rows:
 if mode=='M':
  for row in mapping['changes']:
   if row['to']==path:assert row['replacementBlob']==t('rev-parse',DONOR+':'+path),path
   for shared in row.get('sharedSources',[]):
    if shared['path']==path:assert shared['gitBlob']==t('rev-parse',DONOR+':'+path),path
prior=pathlib.Path('/tmp/pinkha-wave3-message-action-integration-corrected.json').read_bytes()
assert h(prior)=='8ef08b4d14890117c23077cff137c597b35a1c659fad2b92583743866b912c81' and json.loads(prior)['head']==START
prior_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-message-action-map-resume-608fc8a0824c.py').read_bytes()
assert h(prior_controller)=='608fc8a0824ce5d0f1a8e287bb1eec7674599d080ba7840b0147cd94a1c39220'
rawpayload=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-helper680-review-payload.json').read_bytes()
assert h(rawpayload)=='c700e46fda7e8fd65f7302e5a2e7b788cde4c6aed7bae59fed67261269ab3b85'
verified_files=[];names=set()
for row in json.loads(rawpayload)['files']:
 assert pathlib.Path(row['name']).name==row['name'] and row['name'] not in names;names.add(row['name'])
 data=base64.b64decode(row['base64'],validate=True)
 assert len(data)==row['bytes'] and h(data)==row['sha256']
 verified_files.append((row['name'],data))
assert len(verified_files)==27
data=dict(verified_files)
assert h(data['native-acceptance-publication.json'])=='71524fcad7fac862053893ef519758d0d8be9228ce85b2ad2e1358715c93ee8f'
assert h(data['seven-actual-retirement-receipt.json'])=='77022ce355ba548c41843fb4eb8b6a036eb3e8c09baf3f689e6ef0c8e3e429f3'
assert h(data['seven-receipt-continuation1.json'])=='dea06e4824fa836332257cf5c0530b1528409f49a25609377990eb60c8e35186'
assert h(data['seven-verification1.json'])=='15b8bc6c6eee55751bbf1997d64d06b7f50be81cdce7db3a02558ead298a2c3f'
census=json.loads(data['post-seven-retirement-census.json'])
assert census['rootClaimCreated']==census['effectiveAdmissionCreated']==census['supervisorStarted']==False
b('merge','--no-ff','--no-commit',DONOR);assert t('write-tree')==preview
for _,path in rows:assert (ROOT/path).read_bytes()==b('show',DONOR+':'+path),path
owned(MAP,(json.dumps(mapping,indent=2,ensure_ascii=False)+'\n').encode(),exclusive=False)
prefix='docs/validation/20261127-wave3-native-save-acceptance-intake';extras=[]
for name,content in verified_files+[('prior-action-integration-receipt.json',prior),('prior-action-map-resume-controller.py',prior_controller)]:
 path=prefix+'/'+name;owned(path,content);extras.append(path)
note=prefix+'/root-source-review.json'
owned(note,(json.dumps({
 'rootParent':START,'candidate':DONOR,'verifiedSources':verified,'literalInverses':20,
 'mapBaselineIdentityUnchanged':True,'mapChanges':changed,'reviewedHashUpdates':updates,
 'review':[
  'Actual mounted preparation reads existing native source under original account/Space/session/lease and produces process-bound metadata. No recreated account, native application, credential source, fake generation or protected T5 reuse.',
  'One-hour fixture bound to actual source, custody, native source/binary, run and same PID, with single-use result directory. Original saved journal actor retained before operation; observer is read-only and full identity scoped. Controlled model HTTP SSE only; original SDK engine/session produces completed messages and tool runs.',
  'UI presses original Send/Save and native Cancel then distinct Allow; requires full prompt, distinct runs/calls/results, actual no-effect cancellation, committed journal progress and independent original native readback/full Any atomic ACK. Original account/page retained. No assertion substituted with expected content.',
  'Release shared/Heart source projection proven unchanged by original child checks and root inverse verification. AnyHanlinPresentation adds default hook passthrough, without changing ordinary selected factory or enabling body-save capability.',
  'New Stage1 UI source is not yet explicitly registered in its PBX target; separate successor requested and required before compilation. Actual Any editor callsite belongs to Wave2 and is still pending. This checkpoint is reviewable source, not selectable or runtime acceptance.'
 ],
 'newUISelector':{'name':'HanlinSaveMessageAcceptanceUITests.testOriginalSDKMessageSaveConsentAndNativeReadback','status':'NOT_RUN','explicitPBXRegistration':'PENDING_SEPARATE_SUCCESSOR'},
 'AppleCompilation':'NOT_RUN','nativeAcceptance':'NOT_RUN','fixtureProvisioned':False,
 'macFrozenSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe',
 'sevenArchiveEvidence':{'count':7,'originalBytes':772912909,'actualRetirementReceiptSHA256':h(data['seven-actual-retirement-receipt.json']),'restorationHelpersExecuted':False,'rootReviewedRestorationHelpers':True,'observedGlobalFreeBytesBefore':6984937472,'observedGlobalFreeBytesAfter':7758262272,'privateWindowsBackupVerified':True,'sourceProductsAccountDataUnchanged':True},
 'latestAppDispatch':{'state':'REFUSED_BEFORE_CLAIM','originalObservedAt':census['observedAt'],'reason':'Foreign HanlinG19 and free space below unchanged9126805504B','AppBuildStarted':False}
},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix,MAP);b('diff','--cached','--check')
finish(START,DONOR,'native-save-acceptance-source',[path for _,path in rows]+extras+[MAP])

