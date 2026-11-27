import base64, gzip, hashlib, json, pathlib, subprocess, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='2fbb11845e8b058c1ca54d42c95cce47a38adfb6'
DONOR='60d32628f44f334063b756bad29b8861201287b7'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-styles-quota-intake'
CREATOR='Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeBlockCreator.swift'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-w1-styles-quota-intake.json.gz')
OUT=pathlib.Path('/tmp/pinkha-wave3-styles-quota-source-integration.json')

def h(b):return hashlib.sha256(b).hexdigest()
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE)
def t(*a):return b(*a).decode().strip()
def owned(path,data):
    code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)

assert not OUT.exists()
receipt={'schema':'pinkha-wave3-original-styles-quota-intake/v1','parent':START,'donor':DONOR,'startedAt':time.time(),'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
    packed=PAYLOAD.read_bytes();assert h(packed)=='021f580ac75f7bd948e1953ba9412395364ff5d82bcfeef4ef080b9478a62b93'
    payload=json.loads(gzip.decompress(packed));retained={}
    for row in payload['files']:
        data=base64.b64decode(row['base64'],validate=True)
        assert h(data)==row['sha256'] and len(data)==row['bytes']
        assert row['name'] in ['independent-review.json','independent-byte-semantic-proof.json','complete-primary-source-index.json','oracle-original-hash-probe.json','oracle-original-hash-result.json','verify_original_evidence.py']
        assert row['name'] not in retained;retained[row['name']]=data
    assert h(retained['independent-review.json'])=='9f9aa61b94f933b2e3901e1949cb93b6bf872caefa0ac334c3ebf15fc476fc33'
    assert h(retained['independent-byte-semantic-proof.json'])=='8df371873673695cd1abb2a0b5024cdab19f63c90d3091bf529179623aeb9a37'
    review=json.loads(retained['independent-review.json']);index=json.loads(retained['complete-primary-source-index.json'])
    assert review['status']=='SOURCE_AND_ORIGINAL_EVIDENCE_READY_NO_NEW_BLOCKER' and index['ref']==DONOR
    assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
    assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
    assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
    status=t('status','--porcelain=v1','--untracked-files=all')
    assert t('ls-remote','origin',REF).split()[0]==START
    for c in review['commits']:
        assert t('rev-parse',c['sha']+'^{tree}')==c['tree'] and t('rev-parse',c['sha']+'^')==c['parent']
    assert len(index['files'])==41
    for row in index['files']:assert t('rev-parse',DONOR+':'+row['path'])==row['gitBlob'],row['path']
    before,after=b('show',START+':'+CREATOR),b('show',DONOR+':'+CREATOR)
    assert h(before)=='58a3ce0653a8973a07dce7e7dde80e1cb66a8bcce692652a47a8c8c60db684bc'
    assert h(after)=='6bea1d2f1108cf737d68f91cf891c901e0140212b574aaf9e42fa63b392fd652'
    new=b'              parentID.utf8.count <= 256,\n';assert after.count(new)==1
    restored=after.replace(new,b'',1)
    new=b'              !position.isEmpty, position.utf8.count <= 256,\n';old=b'              !position.isEmpty, position.utf8.count <= 1024,\n'
    assert restored.count(new)==1 and restored.replace(new,old,1)==before
    native_result=b('show',DONOR+':docs/validation/20261127-wave1-native-block-styles/original/result.json')
    quota_result=b('show',DONOR+':docs/validation/20261127-wave1-cloud-quota-observation/original/result.json')
    assert h(native_result)==review['nativeEvidence']['originalResultSHA256']=='dc3d09497f0f247447d0394407c2b34a1b2cbf8dd357150244d849c5b89926d5'
    assert h(quota_result)==review['cloudObservation']['originalResultSHA256']=='aa61aadca348b2c89bc0321f6239a299c4d2fb3d62014366e1c4b707defef100'
    preview=subprocess.run(G+['merge-tree','--write-tree',START,DONOR],capture_output=True,text=True)
    assert preview.returncode==0 and preview.stdout.strip()=='96b1570ba5d4fde561b95f466f17439ce52a82e2'
    changes=t('diff','--name-status',START,preview.stdout.strip()).splitlines()
    assert sorted(x.split('\t')[1] for x in changes)==sorted(r['path'] for r in index['files'])
    assert [x for x in changes if x.startswith('M\t')]==['M\t'+CREATOR]
    for x in changes:
        state,path=x.split('\t')
        if state=='A':assert not (ROOT/path).exists()
        else:assert state=='M' and path==CREATOR
    preserved_paths=[MAP,GATE,'Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json','NativeApp/UITests/NativeLaunchTests.swift','Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift']
    preserved_paths += [p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
    preserved={p:b('show',START+':'+p) for p in preserved_paths}
    assert len(json.loads(preserved[MAP])['changes'])==129
    merged=subprocess.run(G+['merge','--no-ff','--no-commit',DONOR],capture_output=True,text=True)
    assert merged.returncode==0 and not t('ls-files','-u')
    assert t('write-tree')==preview.stdout.strip()
    for row in index['files']:assert (ROOT/row['path']).read_bytes()==b('show',DONOR+':'+row['path'])
    prior=pathlib.Path('/tmp/pinkha-wave3-styled-ui-source-integration-resume1.json').read_bytes()
    assert h(prior)=='47983dc957b2e234ebb6882b323ec09436a2df3cc2cef1f4806712bf7851fab3' and json.loads(prior)['head']==START
    retained['prior-styled-ui-integration.json']=prior
    retained['root-integration-controller.py']=pathlib.Path(__file__).read_bytes()
    note={'schema':'pinkha-root-styles-quota-review/v1','parent':START,'donor':DONOR,'exactImmutablePrimaryFiles':41,'creatorLiteralInverseOperations':2,
      'creatorBeforeSHA256':h(before),'creatorAfterSHA256':h(after),'sourceRetentionMapUnchanged':True,
      'nativeOriginalResultSHA256':h(native_result),'quotaOriginalResultSHA256':h(quota_result),
      'independentReviewSHA256':h(retained['independent-review.json']),'originalEvidenceNotRerun':True,
      'review':[
        'Root read the exact original creation intent and two tests. Only parent UTF8 length<=256 and position length1024→256 change; both match the actual original native blocks.go limits. Empty root parent, ASCII position, validated Codable path, identity, native mutation/dispatch/journal and worker semantics remain intact.',
        'The exact41 candidate blobs are the entire merge delta; earlier graph prerequisites cause no additional source change. Every added original artifact and controller matches the independent primary-source index. SDK/native pins, locks, PBX, retained W2editor/NativeLaunch23 and all129 source-map rows remain byte-identical.',
        'Original12 native201 creates, actual nonempty change/version IDs, typed styles, nested parent, empty kinds and65536 HebrewUTF8 bytes passed. Real SIGKILL then fresh PID cold reopening retained exact200540-byte rows with zero cold writes. This is original Linux1594-source/1dc native scope, not current Apple or Host execution.',
        'Original cloud read observes0-byte account limit and21070-byte use; two files remain limited while two smaller files are durable. Four original CAR inventories unchanged and no explicit retry. Broader quota recovery/four-file cloud custody stay false; prior failed quota evidence is retained.',
        'Both new SwiftTesting methods and native256-boundary execution remain NOT_RUN. This intake executes no account/native/HTTP/controller test and does not replay original182 suite or accepted migration evidence.'
      ],'newTestsExecuted':0,'SwiftHostBoundaryMethods':'NOT_RUN','AppleNativeUnion':'NOT_RUN','quotaRecovery':'NOT_ACCEPTED','ReleaseArchive':'NOT_RUN','TestFlight':'NOT_RUN'}
    retained['root-source-review.json']=(json.dumps(note,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
    for name,data in retained.items():owned(PREFIX+'/'+name,data)
    b('add','--',PREFIX)
    b('diff','--cached','--check','--',CREATOR,'Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyNativeBlockLocationLimitTests.swift','Tools/AnyEngineValidation/native_block_creation/run_native_styles1.py','Tools/AnyEngineValidation/native_file_durability/read_cloud_account_limits1.py',PREFIX)
    for p,v in preserved.items():assert (ROOT/p).read_bytes()==v,p
    expected=sorted([r['path'] for r in index['files']]+[PREFIX+'/'+n for n in retained]);assert t('diff','--cached','--name-only').splitlines()==expected
    tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-wave3-styles-quota-retention.json');assert not gate.exists()
    r=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(r.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(r.stderr)
    result=json.loads(gate.read_bytes());assert r.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
    msg='Integrate original native styled-block and cloud quota evidence\n\nAlign creation-only parent and position limits with the original native contract. Preserve actual12-create SIGKILL/cold and failed quota scope without replay. Two authored Host boundary methods and current Apple acceptance remain open.\n\nIntegrated from '+DONOR+'\n'
    subprocess.run(G+['commit','-F','-'],input=msg.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START,DONOR]
    assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,retentionSHA256=h(gate.read_bytes()),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),payloadSHA256=h(packed),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0,sourceMapUnchanged=True)
    if push.returncode==0:
        assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['state']='SOURCE_AND_ORIGINAL_EVIDENCE_INTEGRATED_AND_PUBLISHED'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
