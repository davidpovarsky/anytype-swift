import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='65715e98b501d6fc751ffd4f7f2ba02abb91cad3'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-pure-message-integration.json')
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

donor='53c468e72f261e00e4bebb5e7b7deda9b2e4b5a9'
parent,rows,proof,verified,preview=prepare(donor,'docs/validation/20261127-hanlin-save-message/pure-message-support-source-intake.json','1636a039af6f1d41b8ee9c7133b7ee9d285d49c7435283c39d5a503f5c98d94a',7)
assert proof['testsExecuted']==proof['nativeWrites']==proof['swiftCompilerInvocations']==0
assert proof['productionSaveBindingInstalled'] is False and proof['inverseOperations']==10
assert proof['authoredTests']['newMethods']==4 and proof['authoredTests']['previousMethods']==15
assert proof['sourceMethodInventory']['methods']==101 and proof['sourceMethodInventory']['previousMethods']==97
inventory=b('show',donor+':docs/validation/20261127-hanlin-save-message/pure-message-support-selected-source-methods.json')
assert h(inventory)==proof['sourceMethodInventory']['sha256']=='90c198cfce6b7cc539e542c2a410b0836d5b64075030230b1f8539c80170b71b'
original_map=b('show','HEAD:'+MAP)
mapped={r['to'] for r in json.loads(original_map)['changes']}
assert all(path not in mapped for mode,path in rows if mode=='M')
publisher=pathlib.Path('/tmp/pinkha-pure-message-support-published.json').read_bytes()
assert h(publisher)=='a3c739b52feb102562fe79b425982b67830c9dc6f18fdd7ca7be847d8f2f2957'
published=json.loads(publisher)
assert published['head']==published['remoteHead']==donor and published['tree']==t('rev-parse',donor+'^{tree}')
assert published['testsExecuted']==published['nativeWrites']==published['swiftCompilerInvocations']==0
prior=pathlib.Path('/tmp/pinkha-wave3-resource512-integration.json').read_bytes()
assert h(prior)=='4384a81853f9542a50146eeca335fea49ba6a2eebdd9f50644d0911f6d239500' and json.loads(prior)['head']==parent
prior_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-resource512-integration-905aa3713dff.py').read_bytes()
assert h(prior_controller)=='905aa3713dff9bf9a6311348b9245a0ba1b91d279b8fd770c7bf5932e3465803'
t5=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-t5-scope-review-efe6affbf80c.json').read_bytes()
assert h(t5)=='efe6affbf80c7586f014e4186f36e69f393befc8e3acaa200c9d7727406e2423'
t5review=json.loads(t5);assert t5review['macCalls']==t5review['runtimeTests']==t5review['builds']==0
merge_checked(parent,donor,rows,preview)
assert (ROOT/MAP).read_bytes()==original_map
prefix='docs/validation/20261127-wave3-pure-message-intake';extras=[]
for name,data in [('original-publication-receipt.json',publisher),('prior-resource-integration-receipt.json',prior),('prior-resource-integration-controller.py',prior_controller),('t5-local-readiness-scope-review.json',t5)]:
    path=prefix+'/'+name;owned(path,data);extras.append(path)
note=prefix+'/root-source-review.json'
owned(note,(json.dumps({'rootParent':parent,'candidate':donor,'verifiedSources':verified,'rootReadAllFourSwiftDiffs':True,'review':'Pure presentation eligibility uses the same original completed parser, exact source bytes, strict semantic builder and bounded sorted-key native serialization. Content validation grants no scope or identity. Only the real plan initializer binds a write manifest. Original SDK envelope/deadline/namespace gates, builder/convert tails, cancellation and15existing conversion tests remain. Caller must recheck original session and completed origin after awaiting eligibility.','fourNewTests':'NOT_RUN','sourceMethodInventory':101,'compiledEnumeration':False,'newAppleCompilerOrNativeRuns':0,'productionSaveInstalled':False,'macFrozenSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe','t5Review':'Native1dc local-readiness proof does not change current8ac retainedfixture coverage/indexFreshnessUnverified; no36+9 replay or unsupported wholeSpace claim.'},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix);finish(parent,donor,'pure-completed-message-save-eligibility',[path for _,path in rows]+extras)
