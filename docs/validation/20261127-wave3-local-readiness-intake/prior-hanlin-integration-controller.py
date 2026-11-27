import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='1cb23cee4488b7d604426df6c0bd4042f33026ba'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-any-body-composition-integrations.json')
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

def verify_sources(donor, proof):
    verified=[]
    for row in proof['sources']:
        path=row['path']; after=b('show',donor+':'+path)
        assert h(after)==row.get('afterSHA256',row.get('sha256')) and len(after)==row['bytes'],path
        assert t('rev-parse',donor+':'+path)==row['afterBlob'],path
        if row.get('beforeBlob'):
            before=b('show','HEAD:'+path)
            assert t('rev-parse','HEAD:'+path)==row['beforeBlob'],path
            lines=after.splitlines(keepends=True)
            for op in reversed(row['inverseOperations']):
                if 'afterLineEndExclusive' in op:
                    start,end=op['afterLineStart'],op['afterLineEndExclusive']; replacement=op['originalBase64']
                else:
                    start,end=op['afterLineStart']-1,op['afterLineEnd'];replacement=op['replacementOriginalBase64']
                assert h(b''.join(lines[start:end]))==op['expectedAfterSHA256'],path
                lines[start:end]=base64.b64decode(replacement).splitlines(keepends=True)
            assert b''.join(lines)==before,path
        else: assert not (ROOT/path).exists(),path
        verified.append({'path':path,'afterBlob':row['afterBlob'],'sha256':h(after),'inverseOperations':len(row.get('inverseOperations',[]))})
    return verified

def prepare(donor,proofpath,proofsha,count):
    fetch(donor); parent=t('rev-parse','HEAD')
    rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
    assert len(rows)==count
    for mode,path in rows:
        assert mode in {'A','M'}
        if mode=='M':assert b('show','HEAD:'+path)==b('show',donor+'^:'+path),path
        else:assert not (ROOT/path).exists(),path
    raw=b('show',donor+':'+proofpath);assert h(raw)==proofsha
    proof=json.loads(raw);assert proof['status']=='SOURCE_ONLY_NOT_COMPILED_OR_EXECUTED'
    verified=verify_sources(donor,proof)
    preview=t('merge-tree','--write-tree',parent,donor);assert len(preview)==40
    assert t('diff','--name-only',parent,preview).splitlines()==sorted(p for _,p in rows)
    for path,data in PINNED.items():assert b('show',preview+':'+path)==data,path
    return parent,rows,proof,verified,preview

def merge_checked(parent,donor,rows,preview):
    b('merge','--no-ff','--no-commit',donor);assert t('write-tree')==preview
    for _,path in rows:assert (ROOT/path).read_bytes()==b('show',donor+':'+path),path

donor='c5117ccfc031493d7fd32e30d5fb1c00be8acd2a'
parent,rows,proof,verified,preview=prepare(donor,'docs/validation/20261127-hanlin-any-body/any-host-context-source.json','dabe2574e22e83e6b2bf8448cbe5ea6802f58d15925ffcbd4b92a5f4f4a6e400',9)
assert proof['newCompilerOrNativeRuns']==0 and proof['pinsChanged'] is False
assert len(proof['sourceMapUpdates'])==1
update=proof['sourceMapUpdates'][0]
assert update['replacementBlobBefore']=='d68bdbe4fe1915fbc56a8e7422cd3d6f886ab7d5' and update['replacementBlobAfter']=='dc3d1110e42022723433010f190d984427061a0e'
original_dir=pathlib.Path('/tmp/hanlin-any-context-retention-20261127')
originals={p.name:p.read_bytes() for p in original_dir.iterdir() if p.is_file()}
assert set(originals)=={'source-retention.json','verify_source_retention.py','stdout.log','receipt.json','stderr.log','SOURCE_REFACTOR_MAP.json'}
assert h(originals['receipt.json'])=='aea214c38a040e1b20472b89e87d514abca993c09d3ef3435c85ab0acf877527'
original_receipt=json.loads(originals['receipt.json'])
assert original_receipt['head']==donor and original_receipt['tree']==t('rev-parse',donor+'^{tree}')
assert original_receipt['sourceRetentionExitCode']==1 and original_receipt['compilerRuns']==0
for item in original_receipt['files']:
    data=originals[pathlib.Path(item['path']).name];assert h(data)==item['sha256'] and len(data)==item['bytes']
assert originals['verify_source_retention.py']==b('show','HEAD:'+GATE)
assert originals['SOURCE_REFACTOR_MAP.json']==b('show','HEAD:'+MAP)
assert h(originals['source-retention.json'])=='f9097a9c718583ddac5c8195fc10dd994c594a7c8cdd559bda269baf66b432d1'
preview_result=json.loads(originals['source-retention.json'])
assert preview_result['sourceRetentionPassed'] is False
assert preview_result['inventoryErrors']==['Replacement blob mismatch: Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaHanlinWriteJournal.swift']
assert not preview_result['unreviewedChangedExistingFiles']
oldmap=json.loads(b('show','HEAD:'+MAP));newmap=copy.deepcopy(oldmap)
assert len(oldmap['changes'])==129
selected=[r for r in newmap['changes'] if r['to']==update['to']];assert len(selected)==1
row=selected[0]
for key in ['from','to','kind','baselineBlob']:assert row[key]==update[key]
assert row['replacementBlob']==update['replacementBlobBefore']
row['replacementBlob']=update['replacementBlobAfter']
prefix='docs/validation/20261127-wave3-any-body-composition'
row['reason']+=' Root reviewed c511: retain original v1 journal, exclusive ownership and total64MiB bound; typed original atomic ACK may occupy64KiB and conditional-Markdown mode reserves one additional64KiB event before effects. Ordered-mode budget remains unchanged.'
row['validation'].append('Full root and independent SDK/Mini source review with exact literal inverse. Original one-mismatch preview is retained in '+prefix+'/original-map-preview. New Apple compile, protected reopen and mounted original Any/Heart write/drain acceptance remain NOT_RUN.')
for old,new in zip(oldmap['changes'],newmap['changes']):
    for key in ['from','to','kind','baselineBlob']:assert old[key]==new[key]
    if old['to']!=update['to']:assert old==new
merge_checked(parent,donor,rows,preview)
owned(MAP,(json.dumps(newmap,indent=2,ensure_ascii=False)+'\n').encode(),exclusive=False)
extras=[MAP]
for name,data in originals.items():
    path=prefix+'/original-map-preview/'+name;owned(path,data);extras.append(path)
previous=pathlib.Path('/tmp/pinkha-wave3-definitions-warm-ack-integrations.json').read_bytes();assert h(previous)=='39397902032b392f33b21191b8fb8ed51c612adc5be1b5d25c71126d97dc873a'
previous_script=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-definitions-warm-ack-36a81eb4ce35.py').read_bytes();assert h(previous_script)=='36a81eb4ce359cbfad007f2bae9711c4ddb8ae16d053f8a69e7c48184eb41a72'
for name,data in [('prior-integration-receipt.json',previous),('prior-integration-controller.py',previous_script)]:
    path=prefix+'/'+name;owned(path,data);extras.append(path)
note=prefix+'/root-context-review.json'
owned(note,(json.dumps({'rootParent':parent,'candidate':donor,'verifiedSources':verified,'sourceReview':'Original Any creation I/O, immutable mutationID, scope/eligibility checks, mounted confirmation and cancellation drain retained. One shared context and one-use typed full invocation approval; same captured original client constructs body services. Ordinary host remains create-only; no unpublished Runner reference.','reviewedMapUpdates':[update],'originalFailedPreviewRetained':True,'originalPreviewSource':donor,'originalExpectedMappingFailureReusedWithoutRerun':True,'rootMergePreviewOnlyExactNineCandidateFiles':preview,'allBaselineMappingsPreserved':129,'authoredTests':proof['authoredTests'],'newAppleCompilationOrRuntime':0,'productionSaveInstalled':False},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',MAP,prefix);finish(parent,donor,'any-original-context-and-atomic-journal',[p for _,p in rows]+extras)

donor='646c1d9e283a79cb1e996657041ad489122d1ae2'
parent,rows,proof,verified,preview=prepare(donor,'docs/validation/20261127-hanlin-save-message/any-native-save-source-intake.json','592533ee2c434288928dfcb0470e30bc3e0590aa5fd4ef79b432fcfd9369070e',7)
assert proof['testsExecuted']==proof['nativeWrites']==proof['swiftCompilerInvocations']==0 and proof['productionSaveBindingInstalled'] is False
for row in proof['sdkContextPhase']['exactSourceClosure']:
    data=b('show','HEAD:'+row['path']);assert h(data)==row['sha256'] and len(data)==row['bytes'] and t('rev-parse','HEAD:'+row['path'])==row['blob']
merge_checked(parent,donor,rows,preview)
note=prefix+'/root-any-native-worker-review.json'
owned(note,(json.dumps({'rootParent':parent,'candidate':donor,'verifiedSources':verified,'wholeNewOperationBodyAndRunnerAndTestsReviewed':True,'sourceReview':'One original application lease, protected original root then exact empty-page/version check, one native261 conditional Markdown PUT, full actual bounded ACK and same-version normalized plus complete native semantic readback. Late ACK retained under original namespace, no automatic retries, replacement root, synthetic block writes or inference of missing ACK from equal text. Original account/Space/engine/client/cancellation checks remain.','sourceClosureVerified':proof['sdkContextPhase']['exactSourceClosure'],'authoredMethods':5,'authoredTestsStatus':'NOT_RUN','newCompilerOrNativeWrites':0,'productionSaveInstalled':False,'requiredAcceptance':proof['requiredAcceptance']},indent=2,sort_keys=True)+'\n').encode())
b('add','--',note);finish(parent,donor,'any-native-whole-body-operation',[p for _,p in rows]+[note])

donor='78ddc75fc23e39b96f75b0ed894c0b66152e5173'
parent,rows,proof,verified,preview=prepare(donor,'docs/validation/20261127-hanlin-any-body/any-native-save-composition-source.json','4f570efbb56c1cda00f4c051662cabca6d2a1834ccc07bee9e2d73bad597ca85',5)
assert proof['newTests']==proof['newCompilerOrNativeRuns']==0 and proof['sourceMapUpdates']==[]
merge_checked(parent,donor,rows,preview)
note=prefix+'/root-any-acceptance-composition-review.json'
owned(note,(json.dumps({'rootParent':parent,'candidate':donor,'verifiedSources':verified,'sourceReview':'Concrete published Any Runner composes through original generic binding and shared context. Ordinary public factory passes nil body services. DEBUG-only native acceptance constructor chooses original parser and same-client services; foreign body account or missing full-message native UI denied before provisional source-owner installation. Original shared UIKit mount/failure cleanup/account-owner/session drains preserved.','originalProductionCreateFactoryStillCreateOnly':True,'acceptanceFactoryCompiledOrCalled':False,'newCompilerOrRuntime':0,'sourceMapUpdates':0,'requiredAcceptance':proof['requiredAcceptance'],'currentMacSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe'},indent=2,sort_keys=True)+'\n').encode())
b('add','--',note);finish(parent,donor,'any-debug-native-acceptance-composition',[p for _,p in rows]+[note])
