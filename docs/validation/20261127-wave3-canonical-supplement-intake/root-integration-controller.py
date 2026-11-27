import ast, base64, gzip, hashlib, json, os, pathlib, subprocess, time
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='71e586ff6e46ef758e8d6f264f7c49476e86a136'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-canonical-g02-integration.json')
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

assert not OUT.exists()
assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
STATUS=t('status','--porcelain=v1','--untracked-files=all')
pins=['Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json',GATE,MAP,'NativeApp/UITests/NativeLaunchTests.swift']
pins += [p for p in t('ls-tree','-r','--name-only','HEAD').splitlines() if p.endswith('/Package.resolved')]
PINNED={p:b('show','HEAD:'+p) for p in pins}
raw=PAYLOAD.read_bytes();assert len(raw)==407766 and h(raw)=='068f045e219045c5da7a7880af8a159f1f34fa09d2b17a8704b064493a8344dd'
raw=gzip.decompress(raw);assert h(raw)=='1bd89e32c6178aab2973d0eac98eca330229d219401eedc2229fc1c78b1af11c'
files={}
for row in json.loads(raw)['files']:
    name=row['name'];p=pathlib.PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts and name not in files
    data=base64.b64decode(row['base64'],validate=True)
    assert h(data)==row['sha256'] and len(data)==row['bytes']
    files[name]=data
assert len(files)==43
state={'schema':'pinkha-canonical-g02-root-integration-v1','start':START,'integrations':[],
       'controllerSHA256':h(pathlib.Path(__file__).read_bytes()),'payloadSHA256':h(raw),'startedAt':time.time()}
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
         'pinsLocksSourceMapAndNativeLaunchUnchanged':True,'newProductTestInvocations':0,'publication':'LOCAL_CHECKPOINT'}
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

# Canonical mapping: the root file is byte-identical to the original5235 donor
# preimage. The add/add conflict is ancestry only, resolved by the exact source.
DONOR='0925ff79df8f70be288f96ea117dbd7059e24219'
BASE='5235bf902f8820fdc41fe802265ff5444407b363'
assert t('rev-parse',DONOR+'^')==BASE
paths=delta(BASE,DONOR);production='Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeImportedDefinitionDirectory.swift'
assert len(paths)==57 and [(s,p) for s,p in paths if s!='A']==[('M',production)]
metadata=json.loads(files['canonical/commit-compare.json'])
assert sorted(p for _,p in paths)==sorted(x['filename'] for x in metadata['files'])
assert b('show','HEAD:'+production)==b('show',BASE+':'+production)
for s,p in paths:
    if s=='A':assert not (ROOT/p).exists(),p
report=json.loads(files['canonical/independent-review.json'])
assert h(files['canonical/independent-review.json'])=='2af2688d47712e4229e202159eab78e19550ccce8826858e3e901db59790199d'
assert report['sourceClosure']['completeSelectedSwiftAndPackageInputs']==308 and report['sourceClosure']['missingOrAdditionalOrChanged']==0
assert report['dependencyEvidence']['retainedSourceFilesJoinedAcrossOriginalPreparationAndPostBuildCustody']==1265
assert report['nativeEvidence']['actualPasses']==2 and report['nativeEvidence']['invocations']==2 and report['nativeEvidence']['uniqueMethodCount']==1
merge(START,DONOR,[p for _,p in paths],production)
prefix='docs/validation/20261127-wave3-canonical-supplement-intake'
extra=import_group('canonical',prefix)
union_prefix='docs/validation/20261127-wave3-hanlin-original-sdk-union'
extra+=import_group('hanlin',union_prefix)
note=prefix+'/root-source-review.json'
owned(note,jsonbytes({'rootParent':START,'candidate':DONOR,'exactProductionPreimageSHA256':'7d234d38ae4ee977839d8e33193c79e0266b08bb20619c0fa646736e740634a5',
 'mergeResolution':'The one add/add conflict comes from earlier preserved source integration. Root production bytes equal original5235 before changes; choose exact0925 after independently reading its44additions/2removals and all new component/native methods. No unrelated root bytes replaced.',
 'sourceSemantics':'Eight canonical mappings preserve original provenance; description ordinary, id/spaceId/type translated, author/time destination-derived. Duplicate original IDs/canonical native addresses fail; historical source values, native authority and whole-Space admission do not change.',
 'evidence':'Actual recorded308 Swift/package inputs match0925 despite the producer honestly recording parent5235 HEAD.1265 original dependency files/modes match original clean-all preparation and retained custody. One new positive plus two unchanged negative observations retained from an overallFAIL; one native method/two normal processes/twoPASS/0skip, exact4310-byte cold descriptors. No test rerun by root.',
 'remaining':'129 unresolved definitions,17Type families, historical/current-value migration, peer synchronization and new Apple acceptance remain separate. Native1dc evidence is not Mac8ac evidence.',
 'externalHanlinCheckpoint':{'commit':'20a1e6fa33ed261ba11e83a0b84a157029822e5e','tree':'14e860ce3f7d2b8623085f16d99d34b8b347a48c','publicationReceiptSHA256':'69644eeb1deced0568c440390516404c8bbdf8bfb90510d2348d80c73e981845','consumerPinChanged':False,'sourceOnly':True},
 'sourceMapAndPinsUnchanged':True,'newAppleCompilation':'NOT_RUN'}));extra.append(note)
controller_path=prefix+'/root-integration-controller.py';owned(controller_path,pathlib.Path(__file__).read_bytes());extra.append(controller_path)
b('add','--',prefix,union_prefix)
b('diff','--cached','--check','--',production,note)
canonical=finish(START,DONOR,'canonical-supplement',[p for _,p in paths]+extra)

# Both G02 donor histories and every exact changed blob are checked before
# changing source. No original runtime gate is opened by this integration.
manifest=json.loads(files['g02/combined-intake/manifest.json'])
assert h(files['g02/combined-intake/manifest.json'])=='797f74aea4502ea11c992b094141e49adb4543e2582a61e833577f62c6b32956'
donors=json.loads(files['g02/combined-intake/donor-paths.json'])['commits']
status_codes={'added':'A','modified':'M','removed':'D'}
for row in donors:
    ref=row['commit'];assert t('show','-s','--format=%P',ref).split()==row['parents']
    assert t('rev-parse',ref+'^{tree}')==row['tree']
    observed=delta(row['parents'][0],ref)
    assert len(observed)==row['changedPathCount']
    assert sorted(observed)==sorted([status_codes[x['status']],x['path']] for x in row['changedPaths'])
    for x in row['changedPaths']:
        if x['status']!='removed':assert t('rev-parse',ref+':'+x['path'])==x['blob']
NATIVE='67e0f612fbb166cf9a80c21ae9c97f6641daef45'
NBASE='8f2c11713fb8a40ae13444104723666ffef68afe'
NP='AnyTypeTests/Pinkha/TorahNativeDerivedProductIntegrationTests.swift'
before=b('show','HEAD:'+NP);after=b('show',NATIVE+':'+NP)
assert len(before)==84286 and h(before)=='7ec7ef47c53c02e61b0cccb05ab7f4f58b3824368d84883aadee6767ff24ab85'
assert after[:len(before)]==before and h(after)=='b453fafed2e5e5737ef04524b6add7c4bf0019cf99a03c6137151039f38171ed'
assert h(after[len(before):])=='1363c0f8679dab6b4d1feeeaabac63abce7a9fe733f7e15d3b4b2f3ed857afd9'
npaths=delta(NBASE,NATIVE)
assert [(s,p) for s,p in npaths if s!='A']==[('M',NP)]
merge(canonical,NATIVE,[p for _,p in npaths])
native_head=finish(canonical,NATIVE,'g02-native-corrected-source',[p for _,p in npaths],publish=False)

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
