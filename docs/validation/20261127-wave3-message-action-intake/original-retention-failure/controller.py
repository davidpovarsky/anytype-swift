import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='96f5711e43561711fc24fcf4af417992b61bb90d'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-message-action-integration.json')
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
DONOR='8932c43f59f9976efd9930e4f8c5ba0b0fee72dd'
DP='docs/validation/20261127-hanlin-message-save-action/'
fetch(DONOR)
assert t('rev-parse',DONOR+'^')=='53c468e72f261e00e4bebb5e7b7deda9b2e4b5a9'
assert t('rev-parse',DONOR+'^{tree}')=='7370f4943a50fc60549b6689eef3caf3f9f540ee'
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',DONOR).splitlines()]
assert len(rows)==8
for mode,path in rows:
 assert mode in {'A','M'}
 if mode=='M':assert b('show','HEAD:'+path)==b('show',DONOR+'^:'+path),path
 else:assert not (ROOT/path).exists(),path
proofraw=b('show',DONOR+':'+DP+'message-action-source-intake.json')
assert h(proofraw)=='6f7ef4295a1e42c643d02470e5de3b55c0e2bb196886a4c6490ee509710324b9'
proof=json.loads(proofraw);assert proof['status']=='SOURCE_ONLY_NOT_COMPILED'
assert proof['apple_compile']==proof['native_body_acceptance']==proof['tests']['status']=='NOT_RUN'
assert len(proof['tests']['methods'])==5 and proof['canonical_hanlin']=='45d5d90512c304d3457774b185741b7ef7d801db'
verified=[];n=0
for row in proof['files']:
 path=row['path'];raw=b('show',DONOR+':'+path)
 assert h(raw)==row['after_sha256'] and len(raw)==row['after_bytes'] and t('rev-parse',DONOR+':'+path)==row['after_blob'],path
 if row.get('before_blob'):
  original=b('show','HEAD:'+path);assert t('rev-parse','HEAD:'+path)==row['before_blob'] and h(original)==row['before_sha256'] and len(original)==row['before_bytes'],path
  restored=raw
  for op in reversed(row['inverse_operations']):
   pos=op['after_utf8_offset'];after=op['after'].encode();before=op['before'].encode()
   assert restored[pos:pos+len(after)]==after,path
   restored=restored[:pos]+before+restored[pos+len(after):];n+=1
  assert restored==original,path
 else:assert row['new_file'] and not (ROOT/path).exists(),path
 verified.append({'path':path,'afterBlob':row['after_blob'],'sha256':h(raw),'inverseOperations':len(row.get('inverse_operations',[]))})
assert n==17
strings='Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/Resources/PinkhaHanlin.xcstrings'
old_strings=json.loads(b('show','HEAD:'+strings));new_strings=json.loads(b('show',DONOR+':'+strings))
assert len(old_strings['strings'])==26 and all(new_strings['strings'][k]==v for k,v in old_strings['strings'].items())
assert set(new_strings['strings'])-set(old_strings['strings'])=={'pinkha.hanlin.savedMessageTitle'}
preview=t('merge-tree','--write-tree',START,DONOR);assert len(preview)==40
assert t('diff','--name-only',START,preview).splitlines()==sorted(p for _,p in rows)
for path,data in PINNED.items():assert b('show',preview+':'+path)==data,path
original_map=b('show','HEAD:'+MAP);mapping=json.loads(original_map);assert len(mapping['changes'])==129
updates={
 'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinChatPresentation.swift':('30477d2770d2fee1869d8cd55fbf5657f876cc69','a4de05fbe3afb7b5b4f11a97b08563c79e45c7d7'),
 'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinStrings.swift':('dbca7d93f63c97cfe94b84c6053938926be5f072','f0db777a31170df03cb016acb338003d89c92eea')}
changed=[]
for row in mapping['changes']:
 matched=False
 for shared in row.get('sharedSources',[]):
  if shared['path'] in updates:
   before,after=updates[shared['path']];assert shared['gitBlob']==before and t('rev-parse',DONOR+':'+shared['path'])==after
   shared['gitBlob']=after;matched=True
 if matched:
  row['reason']+=' Reviewed2026-11-27 Wave3 original message-Save action: retain one canonical AgentSession and completed-live-run provenance; shared original Save menu calls executePresentationTool with exact complete body/request identity and original host confirmation/journal/worker. A bounded256-attempt ledger survives row deletion. Stop cancels and joins an early caller; no model-text receipt or automatic retry. Ordinary catalogs remain unchanged.'
  row['validation'].append('Root read all8932source changes and actual canonical45HanlinAgentSession27d430b8. Seventeen exact inverses and26original localization entries retained. Five intent component methods and Apple/native/UI remain NOT_RUN. See docs/validation/20261127-wave3-message-action-intake/root-source-review.json.')
  changed.append(row['to'])
assert len(changed)==2
original_mapping=json.loads(original_map)
for old,new in zip(original_mapping['changes'],mapping['changes']):
 assert all(old[k]==new[k] for k in ['from','to','kind','baselineBlob','replacementBlob'])
 if old['to'] not in changed:assert old==new
prior=pathlib.Path('/tmp/pinkha-wave3-typography-integration.json').read_bytes()
assert h(prior)=='5ec464ff5b86c6de2699fc64d7e3f7e6969c55438f260e15d328e1ba594195d5' and json.loads(prior)['head']==START
prior_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-typography-integration-874f9141aa34.py').read_bytes()
assert h(prior_controller)=='874f9141aa34345c6627bcffb94ec95d4260eed3dfb65d3ec3a55d2bd52d3636'
rawpayload=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-message-action-review-payload.json').read_bytes();assert h(rawpayload)=='e21250c5b8716d06125557a471236f8bacbbe163aba56f5d0fe01b48a559845c'
verified_files=[];names=set()
for row in json.loads(rawpayload)['files']:
 assert pathlib.Path(row['name']).name==row['name'] and row['name'] not in names;names.add(row['name'])
 data=base64.b64decode(row['base64'],validate=True);assert len(data)==row['bytes'] and h(data)==row['sha256'];verified_files.append((row['name'],data))
assert h(dict(verified_files)['original-action-publication.json'])=='a25aa1b31376a089ffdeb84aa52bd1ca790a550deaba01543674031ea24a437e'
cache=json.loads(dict(verified_files)['owned-cache-receipt.json']);assert cache['status']=='PASS_THREE_OWNED_COMPILER_CACHE_LEAVES_REMOVED_ORIGINALS_PRESERVED'
assert h(dict(verified_files)['owned-cache-receipt.json'])=='827e599ef3bc1065a7a2579a68d50cf8456f65ac6206d45d8b04ff8f03d7c8b4'
assert dict(verified_files)['owned-cache-protected-before.json']==dict(verified_files)['owned-cache-protected-after.json']
b('merge','--no-ff','--no-commit',DONOR);assert t('write-tree')==preview
for _,path in rows:assert (ROOT/path).read_bytes()==b('show',DONOR+':'+path),path
owned(MAP,(json.dumps(mapping,indent=2,ensure_ascii=False)+'\n').encode(),exclusive=False)
prefix='docs/validation/20261127-wave3-message-action-intake';extras=[]
for name,data in verified_files+[('prior-typography-integration-receipt.json',prior),('prior-typography-integration-controller.py',prior_controller)]:
 path=prefix+'/'+name;owned(path,data);extras.append(path)
note=prefix+'/root-source-review.json'
owned(note,(json.dumps({'rootParent':START,'candidate':DONOR,'verifiedSources':verified,'literalInverses':17,'originalLocalizationEntries':26,'canonicalAgentSession':{'revision':proof['canonical_hanlin'],'gitBlob':'27d430b8b3ad8c159c3874cd96cd29694321cf13','bytes':41688,'sha256':'b535b7e362b2b8c84b75fe9bfa6367c6905cc259efb1dc3dc2700c568f4dc775'},'review':'Original completed SDK run/text + supported whole Markdown + current body-capable catalog are required before Save origin admission. Save reaches original executePresentationTool, current session/context/catalog, normalized argument guard, durable pending-before-dispatch, native consent/one-use approval/journal/worker and durable original host result callback. Request identity is stable and exact full UTF8 hashes checked, per-message execution/result identity rejects cross-account/run/tool/duplicates. Only actual confirmedCommitted+completed marks Saved.256attempt ledger survives transcript deletion; pending/cancelled/uncertain/noReceipt cannot remint attempt. Stop cancels early caller and joins canonical drain; close revokes then drains original SDK/host. No ordinary catalog or production body binding activated.','mapChanges':changed,'mapBaselineAndReplacementIdentityUnchanged':True,'newTests':{'methods':5,'status':'NOT_RUN'},'AppleCompilation':'NOT_RUN','nativeBodyAcceptance':'NOT_RUN','macFrozenSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe','cacheRetirement':'Actual3ownedinactiveleaves removed; originals exact; global455045120Bdelta,8473333760free belowAppadmission; no newApp/consumer run.'},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix,MAP);b('diff','--cached','--check');finish(START,DONOR,'original-message-save-action',[path for _,path in rows]+extras+[MAP])
