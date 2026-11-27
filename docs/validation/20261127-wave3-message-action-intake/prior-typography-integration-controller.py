import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='e320b43d50f994579c327e9cb53038e4187b125b'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-typography-integration.json')
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


import base64, gzip
DONOR='33e31c64ca9e35e258a4d64cfe8690b08a6cbc39'
DP='docs/validation/20261127-wave2-native-typography/'
fetch(DONOR)
assert t('rev-parse',DONOR+'^')=='dc582ba3239d6dcb66dbe1f7098b95349e4289f9'
assert t('rev-parse',DONOR+'^{tree}')=='79eb9ea557a7f3f89ef778bd9ff9be723b8d060f'
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',DONOR).splitlines()]
assert len(rows)==14
for mode,path in rows:
 assert mode in {'A','M'}
 if mode=='M':assert b('show','HEAD:'+path)==b('show',DONOR+'^:'+path),path
 else:assert not (ROOT/path).exists(),path
proofraw=b('show',DONOR+':'+DP+'source-proof.json')
assert h(proofraw)=='447e8548c3760226b32b8b72a8ad31e3547e1d5b5d3f9fb9b48dc3d5703ab0d8'
proof=json.loads(proofraw)
assert proof['AppleCompilation']==proof['UIKitTests']=='NOT_RUN' and not proof['HanlinFunctionChanged']
for row in proof['files']:
 raw=b('show',DONOR+':'+row['path']);assert h(raw)==row['sha256'] and len(raw)==row['bytes'] and t('rev-parse',DONOR+':'+row['path'])==row['gitBlob'],row['path']
editor='Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift'
invraw=b('show',DONOR+':'+DP+'editor-source-inverse.json')
assert h(invraw)==proof['editorInverseSHA256']=='1afd3086821d10a73536716bfd6f3807addf39deac63518ed761076cccc090f5'
inv=json.loads(invraw);candidate=b('show',DONOR+':'+editor).decode();original=b('show','HEAD:'+editor).decode()
ops=inv['exactChanges']+inv['reviewCorrectionChanges']+inv['bodyWeightCorrectionChanges'];assert len(ops)==15
s=original
for op in ops:
 assert s.count(op['old'])==1,op;s=s.replace(op['old'],op['new'],1)
assert s==candidate
for op in reversed(ops):
 assert s.count(op['new'])==1,op;s=s.replace(op['new'],op['old'],1)
assert s==original
hanlin=json.loads(b('show',DONOR+':'+DP+'hanlin-present-preimage.json'))
f=hanlin['function'];assert h(f.encode())==hanlin['functionSHA256']=='350a4b1c22e61427b7cccd1c347a9df5e77df5304e4564cee46a9c60a4e5a3cc' and len(f.encode())==1262
assert original.count(f)==candidate.count(f)==1 and not hanlin['hookImplemented']
references=json.loads(b('show',DONOR+':'+DP+'source-references.json'))
for row in references['sourceReferences']:
 assert t('rev-parse','HEAD:'+row['path'])==row['gitBlob'] and h(b('show','HEAD:'+row['path']))==row['sha256'],row['path']
for row in json.loads(b('show',DONOR+':'+DP+'binary-evidence-index.json'))['files']:
 encoded=b('show',DONOR+':'+DP+row['encodedName']);decoded=gzip.decompress(encoded)
 assert h(encoded)==row['encodedSHA256'] and len(encoded)==row['encodedBytes'] and h(decoded)==row['originalSHA256'] and len(decoded)==row['originalBytes']
original_map=b('show','HEAD:'+MAP);mapped={r['to'] for r in json.loads(original_map)['changes']}
assert editor not in mapped
assert subprocess.run(G+['cat-file','-e','586c98bcc17dee425664224e508fc0e8df277678:'+editor],capture_output=True).returncode!=0
preview=t('merge-tree','--write-tree',START,DONOR);assert len(preview)==40
assert t('diff','--name-only',START,preview).splitlines()==sorted(p for _,p in rows)
for path,data in PINNED.items():assert b('show',preview+':'+path)==data,path
publisher=pathlib.Path('/tmp/pinkha-wave2-native-typography-publication-20261127.json').read_bytes()
assert h(publisher)=='a0035d22d038c2a1e0adb61116aa1571bbf6d9c3a5ced08c3eb49962b0648a58'
pub=json.loads(publisher);assert pub['head']==DONOR and pub['tree']==t('rev-parse',DONOR+'^{tree}')
assert pub['status']=='PUBLISHED_SOURCE_ONLY_APPLE_UI_PENDING'
prior=pathlib.Path('/tmp/pinkha-wave3-pure-message-integration.json').read_bytes()
assert h(prior)=='1b4fc6cc2f3ca18ecf31877542bda396b8508de1a008e4d9a3df6c5df1e72d17' and json.loads(prior)['head']==START
prior_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-pure-message-f7fcce0b6a9a.py').read_bytes()
assert h(prior_controller)=='f7fcce0b6a9a040cc8c8595d676d2f4980794f78f52d0d914748244899d83614'
rawpayload=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-typography-review-payload.json').read_bytes()
assert h(rawpayload)=='ba300837a7a57d59d0f2aa537c33d7a1cbc1ab4c51c81ac423d5a427f6ca2ca4'
payload=json.loads(rawpayload);verified=[];names=set()
for row in payload['files']:
 assert pathlib.Path(row['name']).name==row['name'] and row['name'] not in names;names.add(row['name'])
 data=base64.b64decode(row['base64'],validate=True);assert len(data)==row['bytes'] and h(data)==row['sha256'];verified.append((row['name'],data))
ind=json.loads(dict(verified)['independent-typography-review.json'])
assert ind['sourceCommit']==DONOR and ind['execution']['swiftCompilerRuns']==ind['execution']['UIKitRuns']==ind['execution']['nativeServiceCalls']==ind['execution']['MacOperations']==0
assert h(dict(verified)['independent-typography-review.json'])=='ec4a34087c07b7e1d75ebbb5eeffed613638d103f561c23c63809dbf12cc57a0'
assert h(dict(verified)['g02-independent-source-review.json'])=='048b57fbb7ca2418607e5661b3a6d4b5fb4bb1046ca0ce66c6d85261455db30e'
b('merge','--no-ff','--no-commit',DONOR);assert t('write-tree')==preview
for _,path in rows:assert (ROOT/path).read_bytes()==b('show',DONOR+':'+path),path
assert (ROOT/MAP).read_bytes()==original_map
prefix='docs/validation/20261127-wave3-native-typography-intake';extras=[]
for name,data in verified+[('original-publication-receipt.json',publisher),('prior-pure-message-integration-receipt.json',prior),('prior-pure-message-integration-controller.py',prior_controller)]:
 path=prefix+'/'+name;owned(path,data);extras.append(path)
note=prefix+'/root-source-review.json'
owned(note,(json.dumps({'rootParent':START,'candidate':DONOR,'review':'Four complete Swift diffs and original font policy reviewed. Exactly15 literal editor changes restore the full original, package/reference files and separate independent27-file audit verified. Native heading/body/code use original registered DesignKit faces; nominal font scales once. Inline body semibold, heading bold, marked composition, type/category cache invalidation and original render/mutation paths retained.','originalReferencesVerified':len(references['sourceReferences']),'sourceMap':'129 original586c entries unchanged; downstream editor is absent from that baseline, so 8f2-relative supplied mapping remains review evidence only.','hanlinPresentationUnchangedSHA256':hanlin['functionSHA256'],'UIKitMethods':{'count':2,'status':'NOT_RUN','hosted43SourceBinding':False},'newAppleCompilerOrNativeRuns':0,'macFrozenSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe','separateG02':'HOLD; original8ac derived cache seal changes with unlink, and attached property presentation is added after sealing. Native/UI/control successors require a narrow reviewed correction; none merged here.','AppleObservation':'Original05:00 live read and05:03 single capabilities correction retained. Candidate app exists, complete build list empty; active main profile has no multicast. Portal request status and owner final Bundle decision unknown. No Apple writes or distribution.'},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix);b('diff','--cached','--check');finish(START,DONOR,'native-original-typography',[path for _,path in rows]+extras)
