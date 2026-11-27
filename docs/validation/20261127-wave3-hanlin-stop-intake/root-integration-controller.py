import copy, hashlib, json, pathlib, subprocess, time

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='cf3737835a8a926ba0b720e976fb9b7a686fadad'
DONOR='026ed0c3e6cce6af3824233798e73c0f28024e56'
BASE='eee40593bf2088fbf6168106f9d2c49248d3ce1f'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
DP='docs/validation/20261127-hanlin-message-save-action/'
PREFIX='docs/validation/20261127-wave3-hanlin-stop-intake'
OUT=pathlib.Path('/tmp/pinkha-wave3-hanlin-stop-source-integration.json')
PUBLICATION=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-hanlin-stop-publication-2083ea357222.json')

def h(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def b(*args): return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args): return b(*args).decode().strip()
def owned(path,data,exclusive=True):
    code="import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);f=p.open(sys.argv[2]);f.write(sys.stdin.buffer.read());f.close()"
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'xb' if exclusive else 'wb'],input=data,capture_output=True,check=True)
def ident(data): return {'bytes':len(data),'sha256':h(data),'blob':blob(data)}

assert not OUT.exists()
publication=PUBLICATION.read_bytes()
assert h(publication)=='2083ea3572225f70d1b2b0e4512971b0816dc1871384d6eefe2b4f8825c44423'
pub=json.loads(publication)
assert pub['sha']==DONOR and pub['parent']==BASE and pub['tree']=='1abb0b65366be04bc971f75d288def8c10739ca7'
assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
status=t('status','--porcelain=v1','--untracked-files=all')
assert t('ls-remote','origin',REF).split()[0]==START
assert t('rev-parse',DONOR+'^')==BASE
assert t('rev-parse',DONOR+'^{tree}')==pub['tree']
subprocess.run(G+['merge-base','--is-ancestor',BASE,START],capture_output=True,check=True)
paths=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','--no-renames','-r',DONOR).splitlines()]
assert len(paths)==21 and sum(s=='M' for s,p in paths)==9 and sum(p.endswith('.swift') for s,p in paths)==11
intake_bytes=b('show',DONOR+':'+DP+'native-stop-after-root-source-intake.json')
assert h(intake_bytes)=='9cb2381418435037878971c35c59fab58e1c62a973aa4d77fe8024b23056bec8'
intake=json.loads(intake_bytes)
assert intake['base']==BASE and len(intake['files'])==11 and intake['literalInverseOperations']==45
source_rows=[]
inverse_count=0
for row in intake['files']:
    path=row['path']; after=b('show',DONOR+':'+path)
    assert ident(after)==row['after'],path
    assert (path.endswith('.swift') and ['A' if row['before'] is None else 'M',path] in paths)
    if row['before'] is None:
        assert not (ROOT/path).exists(),path
        assert subprocess.run(G+['cat-file','-e',START+':'+path],capture_output=True).returncode!=0,path
        assert not row['literalInverse']
    else:
        before=b('show',START+':'+path)
        assert before==b('show',BASE+':'+path) and ident(before)==row['before'],path
        restored=after
        for op in sorted(row['literalInverse'],key=lambda x:x['after_start_byte'],reverse=True):
            start,end=op['after_start_byte'],op['after_end_byte']
            assert restored[start:end]==op['after'].encode(),path
            restored=restored[:start]+op['before'].encode()+restored[end:]
            inverse_count+=1
        assert restored==before,path
    source_rows.append({'path':path,'before':row['before'],'after':row['after'],'literalInverseOperations':len(row['literalInverse'])})
assert inverse_count==45
for state,path in paths:
    if not path.endswith('.swift'):
        assert state=='A' and path.startswith(DP) and not (ROOT/path).exists(),path
review=b('show',DONOR+':'+DP+'native-stop-independent-review/independent-review.json')
assert h(review)=='adc86d9b679c1ca1231d3a4d0713e0724c449bc73c19590e75a814f6d4e1b2e4'
assert json.loads(review)['status']=='READY_FOR_SOURCE_INTAKE_AFTER_TWO_CORRECTIONS_COMPILE_AND_RUNTIME_NOT_RUN'
proof=b('show',DONOR+':'+DP+'native-stop-independent-review/independent-source-byte-proof.json')
assert h(proof)=='83a1f5020fcbb6f6a1f4b58f94b1159d55a633f04519b309e83a847e077b06a8'

pins=['Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json',GATE,
      'NativeApp/UITests/NativeLaunchTests.swift','Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift']
pins += [p for p in t('ls-tree','-r','--name-only','HEAD').splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
preserved={p:b('show','HEAD:'+p) for p in pins}
map_before=b('show','HEAD:'+MAP)
map_value=json.loads(map_before)
assert len(map_value['changes'])==129
changes=[
 {'owner':'Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinCreatePageRunner.swift',
  'baseline':'8ff879e4cf8ef04cb367be3b801829a047bebc80','replacement':'e94124b26ab84596536b85f320d31c8658448e1c',
  'path':'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaHanlinCreateRunner.swift',
  'old':'12bdd93bc89c430e7c660b70e15b8e0749481944','new':'ead38c85fc62b4dd61a24c428d66c26118ae36b9'},
 {'owner':'Anytype/Sources/Pinkha/AI/PinkhaHanlinChatPresentation.swift',
  'baseline':'810af73f1ecf45b3ea40827aa7549b12f7f3d1bc','replacement':'49acb7d07bd8d93a8750d481d9c9873caa77067d',
  'path':'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinChatPresentation.swift',
  'old':'11cfab1994884d40b8a6cc0a21a6e9bb2538e17d','new':'0e27ed6a0696db35f95c30ad8249b9fa6730985e'}]
map_expected=copy.deepcopy(map_value); map_after=map_before
for c in changes:
    rows=[r for r in map_expected['changes'] if r['from']==c['owner']]
    assert len(rows)==1
    row=rows[0]
    assert row['baselineBlob']==c['baseline'] and row['replacementBlob']==c['replacement'] and row['to']==c['owner']
    ss=[r for r in row['sharedSources'] if r['path']==c['path']]
    assert len(ss)==1 and ss[0]['gitBlob']==c['old']
    assert t('rev-parse',START+':'+c['owner'])==c['replacement']==t('rev-parse',DONOR+':'+c['owner'])
    assert map_after.count(c['old'].encode())==1 and c['new'].encode() not in map_after
    map_after=map_after.replace(c['old'].encode(),c['new'].encode(),1)
    ss[0]['gitBlob']=c['new']
assert json.loads(map_after)==map_expected
map_inverse=map_after
for c in reversed(changes): map_inverse=map_inverse.replace(c['new'].encode(),c['old'].encode(),1)
assert map_inverse==map_before
preview=subprocess.run(G+['merge-tree','--write-tree',START,DONOR],capture_output=True,text=True)
assert preview.returncode==0,preview.stdout
preview_tree=preview.stdout.strip();assert preview_tree=='a5904b7d7d83707228223e3be2d29b92f50ba1df'
assert t('diff','--name-only',START,preview_tree).splitlines()==sorted(p for _,p in paths)
merged=subprocess.run(G+['merge','--no-ff','--no-commit',DONOR],capture_output=True,text=True)
assert merged.returncode==0 and not t('ls-files','-u')
assert t('write-tree')==preview_tree
for _,path in paths: assert (ROOT/path).read_bytes()==b('show',DONOR+':'+path),path
assert (ROOT/MAP).read_bytes()==map_before
owned(MAP,map_after,exclusive=False)

prior=pathlib.Path('/tmp/pinkha-wave3-native-hanlin-hook-integration.json').read_bytes()
assert h(prior)=='a3da87536ce561e6ee3f163b4c325c99907348319328ff5f3e11622d9c711f9f' and json.loads(prior)['head']==START
extras=[]
for name,data in [('prior-native-hook-receipt.json',prior),('owner-publication-receipt.json',publication),('root-integration-controller.py',pathlib.Path(__file__).read_bytes())]:
    path=PREFIX+'/'+name;owned(path,data);extras.append(path)
note={
 'schema':'pinkha-root-original-stop-source-intake-v1','rootParent':START,'donor':DONOR,'donorParent':BASE,
 'publishedSourceFilesVerified':source_rows,'originalInverseOperations':45,
 'independentReviewSHA256':h(review),'independentByteProofSHA256':h(proof),
 'sourceMapChanges':changes,'sourceMapBefore':ident(map_before),'sourceMapAfter':ident(map_after),
 'sourceMapFullLiteralInverse':True,'all129BaselinesOwnerReplacementsReasonsAndOtherFieldsPreserved':True,
 'review':[
 'Root read original shared worker/journal/chat/driver and complete Stop helper/observer, then original Any and Heart postflight and the actual new XCTest. Forty-five literal inverse operations reconstruct all nine original sources; two new DEBUG simulator files cannot overwrite earlier source.',
 'Notification follows actual protected journal persistence and canonical comparison outside actor/file lock. The same original journal is reread. Real worker identity, append-to-real-drain-waiters and original finishNativeWork are observed; no native result or ACK is injected.',
 'Passive root hold is bounded by 20 seconds and the original request deadline. Stop presses the original SDK Composer, closes dispatch and waits for the actual original worker. Release cannot authorize body effects. Success requires actual original SDK/consumer join and real zero-body native readback.',
 'Independent review found and source corrected asynchronous pre-hold revocation and failed-Stop cleanup. Abort now synchronously calls original presentation.invalidate, with the original stopping task retained before diagnostic notification. Failure cleanup preserves the failed receipt and incomplete root.',
 'Any reads through the same captured native session/lease/account client and source owner, checks two actual body versions and empty Markdown/rows/root semantics. Heart uses the existing mounted native editor and strict original objectLifecycle readback. Neither infers an object by title or substitutes account state.',
 'The unchanged baseline native Save selector remains4459 bytes SHA256cf979fd9595ba1f9d284239e90f733c05169d1fdd79b3ddf006312d3da6462f6. The new Stop selector requires separately admitted fresh Any and Heart fixtures. It does not cover account/engine replacement, lost body ACK or cold reconciliation.',
 'Release text projections are conditional source checks only, not typechecking or machine-code equivalence. Ordinary production Save remains disabled. This is source intake, not evidence of a compiled app, UI enumeration or runtime success.',
 'Only the two reviewed sharedSources gitBlob values change in the source-retention map. All original baseline and owner replacement blobs, reasons, other fields and all other127entries are retained byte for byte. Existing SDK/native pins, locks, PBX files, Wave2editor hook, original NativeLaunch and gate code remain exact.'
 ],
 'newSelector':intake['newNativeSelector'],'compiler':'NOT_RUN','AnyNativeUI':'NOT_RUN','HeartNativeUI':'NOT_RUN',
 'fixtures':'NOT_PROVISIONED_OR_QUALIFIED','physicalDevice':'NOT_RUN','releaseArchive':'NOT_RUN','TestFlight':'NOT_RUN','newTestsExecuted':0}
path=PREFIX+'/root-source-review.json';owned(path,(json.dumps(note,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode());extras.append(path)
b('add','--',MAP,PREFIX)
b('diff','--cached','--check','--',MAP,*(p for _,p in paths if p.endswith('.swift')),PREFIX)
for path,value in preserved.items(): assert (ROOT/path).read_bytes()==value,path
expected=sorted([p for _,p in paths]+[MAP]+extras)
assert t('diff','--cached','--name-only').splitlines()==expected
tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-wave3-hanlin-stop-retention.json');assert not gate.exists()
run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr)
result=json.loads(gate.read_bytes())
assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
message='Integrate original Hanlin Stop-after-root acceptance source\n\nRetain durable original journal, real worker drain and original Composer Stop. Preserve nine full original source preimages and update only two reviewed shared-source retention pins. Apple/native runtime acceptance remains open.\n\nIntegrated from '+DONOR+'\n'
subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
head=t('rev-parse','HEAD'); assert t('show','-s','--format=%P',head).split()==[START,DONOR]
assert t('status','--porcelain=v1','--untracked-files=all')==status
assert t('ls-remote','origin',REF).split()[0]==START
push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
receipt={'schema':'pinkha-original-hanlin-stop-source-integration-v1','parent':START,'donor':DONOR,'head':head,'tree':tree,
 'files':expected,'sourceRows':source_rows,'literalInverseOperations':45,'mapSharedSourcesUpdated':changes,
 'sourceRetentionPassed':True,'reviewedRefactors':129,'retentionSHA256':h(gate.read_bytes()),'mapSHA256':h(map_after),
 'controllerSHA256':h(pathlib.Path(__file__).read_bytes()),'ownerPublicationSHA256':h(publication),
 'SDKNativePinsLocksPBXNativeLaunchAndEditorHookUnchanged':True,'newAppleTests':0,
 'pushExit':push.returncode,'pushStdout':push.stdout,'pushStderr':push.stderr,'completedAt':time.time()}
if push.returncode==0:
    assert t('ls-remote','origin',REF).split()[0]==head
    receipt['normalPushReadback']=head
OUT.open('x').write(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'head':head,'tree':tree,'retentionSHA256':receipt['retentionSHA256'],'pushExit':push.returncode,
 'receipt':str(OUT),'receiptSHA256':h(OUT.read_bytes())}),flush=True)
assert push.returncode==0
