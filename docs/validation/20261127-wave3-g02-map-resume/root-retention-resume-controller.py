import ast, base64, gzip, hashlib, json, os, pathlib, subprocess, time
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='71e586ff6e46ef758e8d6f264f7c49476e86a136'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-g02-retention-resume-integration.json')
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-canonical-g02-hanlin-review-payload-068f045e2190.json.gz')
def h(x):return hashlib.sha256(x).hexdigest()
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE)
def t(*a):return b(*a).decode().strip()
def owned(path,data,exclusive=True):
    code="import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);f=p.open(sys.argv[2]);f.write(sys.stdin.buffer.read());f.close()"
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'xb' if exclusive else 'wb'],input=data,check=True,capture_output=True)
def jsonbytes(x):return (json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
def delta(base,head):
    return [line.split('\t') for line in t('diff','--name-status','--no-renames',base,head).splitlines()]


canonical='15180a74d3c4230bc18d519f4ea2c4fca1c67289'
NATIVE='67e0f612fbb166cf9a80c21ae9c97f6641daef45'
NBASE='8f2c11713fb8a40ae13444104723666ffef68afe'
NP='AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift'
PRIOR=pathlib.Path('/tmp/pinkha-wave3-canonical-g02-integration.json')
prior=PRIOR.read_bytes();assert h(prior)=='f6a00cae98091ff312348e8b2da5ce853b21168ec906c1fb81cc5dbd73ceccfb'
assert not OUT.exists()
assert t('rev-parse','HEAD')==canonical and t('symbolic-ref','HEAD')==REF
assert t('rev-parse','MERGE_HEAD')==NATIVE
assert t('write-tree')=='975f6fd6f04860ab1094555ab68c98739f57c0f7'
assert not t('diff','--name-only') and not t('ls-files','-u')
assert t('ls-remote','origin',REF).split()[0]==canonical
STATUS='\n'.join(x for x in t('status','--porcelain=v1','--untracked-files=all').splitlines() if x.startswith('?? '))
pins=['Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json',GATE,MAP,'NativeApp/UITests/NativeLaunchTests.swift']
pins += [p for p in t('ls-tree','-r','--name-only','HEAD').splitlines() if p.endswith('/Package.resolved')]
PINNED={p:b('show','HEAD:'+p) for p in pins}
for path,value in PINNED.items():assert (ROOT/path).read_bytes()==value,path
raw=PAYLOAD.read_bytes();assert len(raw)==407766 and h(raw)=='068f045e219045c5da7a7880af8a159f1f34fa09d2b17a8704b064493a8344dd'
raw=gzip.decompress(raw);assert h(raw)=='1bd89e32c6178aab2973d0eac98eca330229d219401eedc2229fc1c78b1af11c'
files={}
for row in json.loads(raw)['files']:
    data=base64.b64decode(row['base64'],validate=True);assert h(data)==row['sha256'] and len(data)==row['bytes'];files[row['name']]=data
assert len(files)==43
state=json.loads(prior)
state['retainedFirstAttemptReceiptSHA256']=h(prior)
state['resumeControllerSHA256']=h(pathlib.Path(__file__).read_bytes())
state['resumeStartedAt']=time.time()
out=OUT.open('x',encoding='utf-8')
def persist():
    out.seek(0);out.truncate();json.dump(state,out,ensure_ascii=False,indent=2);out.write('\n');out.flush();os.fsync(out.fileno())
persist()
def import_group(group,prefix):
    paths=[]
    for name,data in files.items():
        if name.startswith(group+'/'):
            path=prefix+'/'+name[len(group)+1:];owned(path,data);paths.append(path)
    return paths
def merge(parent,donor,expected,conflict_path=None):
    assert t('rev-parse','HEAD')==parent
    r=subprocess.run(G+['merge','--no-ff','--no-commit',donor],capture_output=True,text=True)
    observed={'donor':donor,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
    state.setdefault('mergeObservations',[]).append(observed);persist()
    unresolved=t('diff','--name-only','--diff-filter=U').splitlines()
    if conflict_path and unresolved:
        assert r.returncode==1 and unresolved==[conflict_path],observed
        # Preimage equality was proved before the merge, and the exact donor
        # preserves every root byte/required semantic delta for this path.
        owned(conflict_path,b('show',donor+':'+conflict_path),exclusive=False)
        b('add','--',conflict_path)
    else:
        assert r.returncode==0 and not unresolved,observed
    assert not t('ls-files','-u')
    assert t('diff','--cached','--name-only').splitlines()==sorted(expected)
    for path in expected:
        assert (ROOT/path).read_bytes()==b('show',donor+':'+path),path
    for path,value in PINNED.items():assert (ROOT/path).read_bytes()==value,path
def finish(parent,donor,label,expected,remote_parent=None,publish=True):
    for path,value in PINNED.items():assert (ROOT/path).read_bytes()==value,path
    assert t('diff','--cached','--name-only').splitlines()==sorted(expected)
    tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-wave3-'+label+'-retention.json');assert not gate.exists()
    r=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(r.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(r.stderr)
    result=json.loads(gate.read_bytes())
    assert r.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
    message='Integrate reviewed '+label+' source into Wave3\n\nOriginal source, native and SDK pins, locks and historical evidence preserved. Source integration only; new Apple/runtime acceptance remains open.\n\nIntegrated from '+donor+'\n'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD')
    assert t('show','-s','--format=%P',head).split()==[parent,donor]
    assert t('status','--porcelain=v1','--untracked-files=all')==STATUS
    row={'label':label,'parent':parent,'donor':donor,'head':head,'tree':tree,'files':sorted(expected),
         'retentionSHA256':h(gate.read_bytes()),'sourceRetentionPassed':True,'reviewedRefactors':129,
         'nativeSDKPinsLocksAndNativeLaunchUnchanged':True,'sourceMapChange':'one reviewed native replacement blob and explanatory reason only; all baselines and other128 entries unchanged','newProductTestInvocations':0,'publication':'LOCAL_CHECKPOINT'}
    state['integrations'].append(row);state['head']=head;persist()
    if publish:
        assert t('ls-remote','origin',REF).split()[0]==(remote_parent or parent)
        p=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
        row.update(pushExit=p.returncode,pushStdout=p.stdout,pushStderr=p.stderr);persist()
        assert p.returncode==0
        assert t('ls-remote','origin',REF).split()[0]==head
        row['publication']='NORMAL_PUSH_EXACT_READBACK';persist()
    print(json.dumps({'label':label,'head':head,'tree':tree,'retentionSHA256':row['retentionSHA256'],
                      'publication':row['publication'],'receipt':str(OUT),'receiptSHA256':h(OUT.read_bytes())}),flush=True)
    return head


npaths=delta(NBASE,NATIVE)
assert t('diff','--cached','--name-only').splitlines()==sorted(p for _,p in npaths)
for _,p in npaths:assert (ROOT/p).read_bytes()==b('show',NATIVE+':'+p),p
native=(ROOT/NP).read_bytes();original=b('show','HEAD:'+NP)
assert len(original)==84286 and h(original)=='7ec7ef47c53c02e61b0cccb05ab7f4f58b3824368d84883aadee6767ff24ab85'
assert native[:len(original)]==original and h(native)=='b453fafed2e5e5737ef04524b6add7c4bf0019cf99a03c6137151039f38171ed'
assert h(native[len(original):])=='1363c0f8679dab6b4d1feeeaabac63abce7a9fe733f7e15d3b4b2f3ed857afd9'
oldmap=PINNED[MAP];assert h(oldmap)=='8ab4a1adb263e9c76a16de74fa8fa4b4a04fed4dc76b95beb92e03e1ab24f321'
m=json.loads(oldmap);matches=[x for x in m['changes'] if x.get('from')==NP];assert len(matches)==1
row=matches[0];assert row['baselineBlob']=='cab7dcb9c0e5ca7bb08db419f9181b3e8184cec3' and row['replacementBlob']=='24135b5070aaceec764e245a033c4b14bd58d059'
newblob=t('rev-parse',NATIVE+':'+NP);assert newblob=='ccdddd03e7ebe437ee701f6127f6ae1a952b9192'
oldreason=row['reason'];newreason=oldreason+' Append the original G02 baseline/postflight reader and observed native cache-seal renewal while retaining every original preparation byte. Exact source-only inverse review is retained in docs/validation/20261127-wave3-g02-corrected-intake; Apple acceptance remains open.'
assert oldmap.count(row['replacementBlob'].encode())==1 and oldmap.count(oldreason.encode())==1
newmap=oldmap.replace(row['replacementBlob'].encode(),newblob.encode(),1).replace(oldreason.encode(),newreason.encode(),1)
reversedmap=newmap.replace(newblob.encode(),row['replacementBlob'].encode(),1).replace(newreason.encode(),oldreason.encode(),1)
assert reversedmap==oldmap
newparsed=json.loads(newmap);oldparsed=json.loads(oldmap)
newrow=next(x for x in newparsed['changes'] if x.get('from')==NP)
newrow['replacementBlob']=row['replacementBlob'];newrow['reason']=oldreason
assert newparsed==oldparsed and len(oldparsed['changes'])==129
owned(MAP,newmap,exclusive=False);PINNED[MAP]=newmap
prefix='docs/validation/20261127-wave3-g02-map-resume';extra=[MAP]
failedgate=pathlib.Path('/tmp/pinkha-wave3-g02-native-corrected-source-retention.json')
assert h(failedgate.read_bytes())=='8b83f7d2d9cea432dcf227cdfb3126150969eb66b6abe13ce36a956f70a5838c'
fg=json.loads(failedgate.read_bytes());assert fg['inventoryErrors']==['Replacement blob mismatch: '+NP] and not fg['unreviewedChangedExistingFiles']
for name,data in [('prior-integration-receipt.json',prior),('failed-source-retention.json',failedgate.read_bytes()),('failed-source-retention.stdout',pathlib.Path(str(failedgate)+'.stdout').read_bytes()),('failed-source-retention.stderr',pathlib.Path(str(failedgate)+'.stderr').read_bytes()),('root-retention-resume-controller.py',pathlib.Path(__file__).read_bytes())]:
    target=prefix+'/'+name;owned(target,data);extra.append(target)
proof=prefix+'/exact-map-successor.json'
owned(proof,jsonbytes({'previousTree':'975f6fd6f04860ab1094555ab68c98739f57c0f7','retainedFailedGateSHA256':h(failedgate.read_bytes()),'reason':'The original map correctly refused an unupdated native-test replacement blob after the independently reviewed append. Only this reviewed exact target identity and its explanation change; no baseline, verifier, inventory or other entry is relaxed.','beforeMapSHA256':h(oldmap),'afterMapSHA256':h(newmap),'originalEntry':row,'newReplacementBlob':newblob,'literalInverseRestoresEveryOriginalMapByte':True,'all129BaselinesAndOther128EntriesUnchanged':True,'nativeFullSHA256':h(native),'originalPreparationPrefixBytes':len(original),'originalPreparationPrefixSHA256':h(original),'sourceReviewSHA256':'40ad7cc379b870f75128bca952932132362fcfdea26012d0e61302df3b9f6f02','nativeBehaviorTestsExecuted':0}));extra.append(proof)
b('add','--',MAP,prefix)
b('diff','--cached','--check','--',MAP,proof)
native_head=finish(canonical,NATIVE,'g02-native-corrected-retention',[p for _,p in npaths]+extra,publish=False)
manifest=json.loads(files['g02/combined-intake/manifest.json'])
assert h(files['g02/combined-intake/manifest.json'])=='797f74aea4502ea11c992b094141e49adb4543e2582a61e833577f62c6b32956'
CONTROL='f0efc3684789882b58a0a92bc1919c49a5d320a2'
CBASE='4c3f2f24771e13a366fc4915152c5fedfc7c21e3'
UI='PinkhaStage1Acceptance/Tests/AnytypeComprehensiveAcceptanceUITests.swift'
before=b('show','HEAD:'+UI);after=b('show',CONTROL+':'+UI)
assert before==b('show',CBASE+':'+UI)
assert len(before)==43356 and h(before)=='e56a5f6839c9426bb0e70b274a3eaafbc3f850bc6343355bed92538723a28bb9'
assert after[:len(before)]==before and len(after)==78853 and h(after)=='d7e512cb695695ea88e14bf8527d0051aeb9b315e40a7a52289a8f0b0323d6f3'
assert h(after[len(before):])=='fe889e034c5ffe1a3b30e06b4915cbbc7381a8517fa4471d1dd8a3e7570c09e9'
cpaths=delta(CBASE,CONTROL)
assert [(s,p) for s,p in cpaths if s!='A']==[('M',UI)]
merge(native_head,CONTROL,[p for _,p in cpaths],UI)
assert h((ROOT/NP).read_bytes())=='b453fafed2e5e5737ef04524b6add7c4bf0019cf99a03c6137151039f38171ed'
cp='Tools/CurrentAppleValidation/combined_heart_semantics/wave2/g02/'
for name,sha in manifest['finalClosedControllerPins'].items():assert h((ROOT/(cp+name)).read_bytes())==sha
profile=json.loads((ROOT/(cp+'g02-closed-profile.json')).read_bytes());assert profile['runtimeReady'] is False
node=ast.parse((ROOT/(cp+'g02_word_consumer.py')).read_bytes())
fn=next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name=='require_runtime_ready')
assert len(fn.body)==2 and isinstance(fn.body[1],ast.Raise)
prefix='docs/validation/20261127-wave3-g02-corrected-intake'
extra=import_group('g02',prefix)
note=prefix+'/root-source-review.json'
owned(note,jsonbytes({'rootParentBeforeG02':canonical,'nativeCheckpoint':native_head,'nativeDonor':NATIVE,'UIAndClosedControlDonor':CONTROL,
 'nativePreservation':{'originalPrefixBytes':84286,'fullSHA256':'b453fafed2e5e5737ef04524b6add7c4bf0019cf99a03c6137151039f38171ed','correctedSuffixSHA256':'1363c0f8679dab6b4d1feeeaabac63abce7a9fe733f7e15d3b4b2f3ed857afd9'},
 'UIConflictResolution':'All43356 current bytes exactly equal donor28 parent4c3. Append exactly the35497-byte original G02 suffix; unchanged full donor78853bytes/d7e512. Existing G03 suffix and all original methods remain once. Closed UI pin requires no change.',
 'semanticReview':'Original native325fb4 cache seal covers canonical bytes before presentation metadata. Observe64 lowercase ASCII hex and require renewal only after exact one-Word canonical removal; do not recompute post-adapter JSON. All other unknown/native fields, canonical records, Source/Topic/Tag/type/name, account/Space, directory/source/native and distinct-process checks remain. Five literal native edits and seven literal control substitutions independently invert to original bytes.',
 'evidenceScope':'One original successor portable pin control log/receipt reused; ten earlier synthetic terminal observations remain their original scope with separate stdout limitation explicit. Swift syntax receipt is not Apple typechecking/macros. Generated F host cf1d unchanged; materialization receipt01f7 separate. No root runtime/test invocation.',
 'runtimeReady':False,'current8f2Eligible':False,'sourceAndNativePinsChanged':False,
 'remaining':'Actual shared App+completeUI compiler proof, separately reviewed runtime-opening successor, real UIseed→nativebaseline→UIunlink/cold→nativepostflight, visual and physical acceptance remain open.'}));extra.append(note)
prior=prefix+'/preceding-native-and-canonical-receipt.json';owned(prior,OUT.read_bytes());extra.append(prior)
b('add','--',prefix);b('diff','--cached','--check','--',note)
final=finish(native_head,CONTROL,'g02-ui-and-closed-controls',[p for _,p in cpaths]+extra,remote_parent=canonical)
state['status']='PASS_ALL_SOURCE_MILESTONES_PUBLISHED';state['completedAt']=time.time();persist();out.close()
print(json.dumps({'status':state['status'],'head':final,'receipt':str(OUT),'receiptSHA256':h(OUT.read_bytes())}),flush=True)
