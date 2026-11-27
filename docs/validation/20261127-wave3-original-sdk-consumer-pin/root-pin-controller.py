import copy, hashlib, io, json, pathlib, subprocess, tarfile, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
H=['sudo','-n','-u','chatgpt-agent','git','--no-optional-locks','-c','gc.auto=0','-C','/mnt/development/projects/worktrees/hanlin-pinkha-original-sdk-union-20261127']
START='d90c88cc951eea15f0bd53b0e590af6a53f7891d'
OLD='45d5d90512c304d3457774b185741b7ef7d801db'
SDK='caa0dac32afa18e58bba55fb4f0fdd262f181835'
TREE='3c1f540131152aacc87a2249e0d938cb592a852c'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PIN='Tools/Hanlin/source.json';MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json';GATE='Tools/AnyEnginePort/verify_source_retention.py'
PREFIX='docs/validation/20261127-wave3-original-sdk-consumer-pin'
OUT=pathlib.Path('/tmp/pinkha-root-original-sdk-consumer-pin.json')

def h(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def q(cmd,*args):return subprocess.check_output(cmd+list(args),stderr=subprocess.PIPE)
def b(*args):return q(G,*args)
def t(*args):return b(*args).decode().strip()
def owned(path,data,exclusive=True):
    code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open(sys.argv[2]).write(sys.stdin.buffer.read())'
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'xb' if exclusive else 'wb'],input=data,capture_output=True,check=True)

assert not OUT.exists()
receipt={'schema':'pinkha-root-original-sdk-consumer-pin/v1','parent':START,'sdkRevision':SDK,'startedAt':time.time(),'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
    assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
    assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
    assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
    status=t('status','--porcelain=v1','--untracked-files=all')
    assert t('ls-remote','origin',REF).split()[0]==START
    assert q(H,'rev-parse','HEAD').decode().strip()==SDK and q(H,'rev-parse',SDK+'^{tree}').decode().strip()==TREE
    subprocess.run(H+['merge-base','--is-ancestor',OLD,SDK],capture_output=True,check=True)
    before=b('show','HEAD:'+PIN);assert h(before)=='e24c2c9900a028bddbd7a97b307e45440b37c341cecb8801e20bda8281388d3f'
    assert before.count(OLD.encode())==1;after=before.replace(OLD.encode(),SDK.encode(),1)
    source=json.loads(before);expected=copy.deepcopy(source);expected['revision']=SDK
    assert json.loads(after)==expected and after.replace(SDK.encode(),OLD.encode(),1)==before
    assert source['swiftAISDKRevision']=='abf0921c6e89e6521cc2b510ff11016b45a0ef08' and source['minimumIOS']=='27.0'
    trees={'Packages/HanlinAgentSDK':'bbe6a0e4387f3f33d6592e24c1927182a1aceb22','Packages/HanlinPlatform':'db6e9533242f08bb1bb7accdf6970a436aa953d1','Packages/HanlinPresentationSDK':'ae9c38acacb2da5824d0c36e1f9d3923597dd515','Packages/HanlinMiniAppsBridge':'98ef5d2b47c03f4ea98319a851abae183f500a40'}
    assert set(source['packages'])==set(trees)
    for path,tree in trees.items():assert q(H,'rev-parse',SDK+':'+path).decode().strip()==tree
    archive=q(H,'archive','--format=tar',SDK,*source['packages'])
    assert len(archive)==40673280 and h(archive)=='a9387d537fd432d91d59c7b8a6c4561a1d17e348fe4abca109ba5039b48a6779'
    files={};total=0
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        for m in bundle:
            p=pathlib.PurePosixPath(m.name.rstrip('/'))
            assert not p.is_absolute() and '..' not in p.parts and (m.isdir() or m.isfile())
            if m.isfile():
                data=bundle.extractfile(m).read();assert m.name not in files and not data.startswith(b'version https://git-lfs.github.com/spec/v1')
                files[m.name]=h(data);total+=len(data)
    assert len(files)==1009 and total==39762768
    files={p:files[p] for p in sorted(files,key=pathlib.Path)}
    marker=(json.dumps({'revision':SDK,'files':files},indent=2)+'\n').encode()
    assert len(marker)==178454 and h(marker)=='2733c88978c7a6404e31c502468b879c9451fe612d4660088ee34b597968c26f'
    map_before=b('show','HEAD:'+MAP);mv=json.loads(map_before);rows=[r for r in mv['changes'] if r['from']==PIN]
    assert len(mv['changes'])==129 and len(rows)==1
    row=rows[0];assert row['baselineBlob']=='0ac43dc444fa2234c2eb11fb9bebf129dbe4fb94' and row['replacementBlob']==blob(before)=='f4bade779b51eadcc4e5601e4d3215844831514b'
    new_blob=blob(after);assert map_before.count(blob(before).encode())==1
    map_after=map_before.replace(blob(before).encode(),new_blob.encode(),1)
    expected_map=copy.deepcopy(mv);next(r for r in expected_map['changes'] if r['from']==PIN)['replacementBlob']=new_blob
    assert json.loads(map_after)==expected_map and map_after.replace(new_blob.encode(),blob(before).encode(),1)==map_before
    preserved_paths=[GATE,'Tools/Hanlin/prepare_sdk.py','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json','NativeApp/UITests/NativeLaunchTests.swift']
    preserved_paths += [p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
    preserved={p:b('show','HEAD:'+p) for p in preserved_paths}
    prior=pathlib.Path('/tmp/pinkha-wave3-styles-quota-source-integration.json').read_bytes()
    assert h(prior)=='071bc62fe0053e831e7fc2127df68af0a21e146c7edf9b41c7f86a90f7ba5074' and json.loads(prior)['head']==START
    union=pathlib.Path('/tmp/pinkha-root-hanlin-selective-scrolling-integration-20261127.json').read_bytes()
    assert h(union)=='ac0504faf07be3f094a24749eeace46b60f1b87215f941c70a9ec3f74fcb2bde'
    owned(PIN,after,False);owned(MAP,map_after,False)
    evidence={'prior-styles-quota-integration.json':prior,'original-hanlin-union-publication.json':union,'expected-original-sdk-marker.json':marker,'root-pin-controller.py':pathlib.Path(__file__).read_bytes()}
    note={'schema':'pinkha-original-shared-sdk-consumer-pin-review/v1','rootParent':START,'originalRevision':OLD,'selectedRevision':SDK,'selectedTree':TREE,'originalRevisionIsAncestor':True,'packageTrees':trees,
      'pinBefore':{'sha256':h(before),'gitBlob':blob(before)},'pinAfter':{'sha256':h(after),'gitBlob':new_blob},'pinLiteralInverse':True,
      'mapChangedField':'replacementBlob of Tools/Hanlin/source.json only','all129OriginalBaselinesReasonsValidationAndOtherFieldsPreserved':True,
      'originalMaterialization':{'files':len(files),'sourceBytes':total,'archiveBytes':len(archive),'archiveSHA256':h(archive),'expectedMarkerBytes':len(marker),'expectedMarkerSHA256':h(marker),'actualConsumerMaterializationNow':False},
      'review':[
        'The original shared4-package source moves from canonical45 to the normal20a union plus selectivecaa0 scrolling/locale source. Root reviewed original cancellation, context/session/permission/task drain, payload bounds, original Widget/V1 functionality and exact additive scrolling tests. No wholesale divergent3657 merge was accepted; its synthetic handler regression stays excluded.',
        'The complete959-era capabilities and later additions remain in the original sharedSDK. Current materialization contains1009 exact source files. Only one immutable revision value changes in source.json; repository, package list, SwiftAIabf and minimumiOS27 remain exact. No existing Dependencies/Hanlin snapshot is overwritten; a fresh build must run the unchanged original materializer and match this full marker.',
        'NativeScript full runtime remains its original separate producer with binary/resources dependencies. The4 consumer packages do not claim to embed or execute that runtime. Original explicit-handler state/no-handler tests remain a distinct acceptance obligation.',
        'Actual hostedAgent5methods/7cases atcaa0 passed with original SwiftTesting2403 terminal on Xcode27.2/Swift6.4.2. Run45954793309/attempt1/controller35b failed only collector method counting; failed receipt/products preserved. Original log a141517e1366496b39dd43796a0611dbc292e9146052534760b8937982c1f709 and command214.558s exit0/PGabsent retain that scope. Remaining quota6, Widget2 and iOSproduct are not yet accepted.',
        'A future shared AnytypeApp build uses its own exact27.0 toolchain and source/native locks. This pin review is not App compilation, nativeSave/Stop/MiniApps/Otzaria runtime, ABI qualification, Release signing or TestFlight.'
      ],'newTestsExecuted':0,'SDKRemainingObligations':'NOT_RUN','AnytypeAppleBuild':'NOT_RUN','NativeScriptExplicitHandler':'NOT_RUN_CURRENT_UNION','ReleaseArchive':'NOT_RUN','TestFlight':'NOT_RUN'}
    evidence['root-source-review.json']=(json.dumps(note,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode()
    for n,data in evidence.items():owned(PREFIX+'/'+n,data)
    b('add','--',PIN,MAP,PREFIX);b('diff','--cached','--check')
    expected_paths=sorted([PIN,MAP]+[PREFIX+'/'+n for n in evidence]);assert t('diff','--cached','--name-only').splitlines()==expected_paths
    for p,v in preserved.items():assert (ROOT/p).read_bytes()==v,p
    tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-original-sdk-consumer-retention.json');assert not gate.exists()
    run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr)
    result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
    message='Pin both consumers to the original Hanlin SDK union\n\nPreserve canonical cancellation/context/Composer and bounded payload ownership, original Widget/V1 changes and selected scrolling/localization fixes. Bind all1009 original materialization inputs without replacing any existing snapshot. Current App and remaining native/UI acceptance stay open.\n'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');assert t('rev-parse','HEAD^')==START
    assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,files=expected_paths,pinBeforeSHA256=h(before),pinAfterSHA256=h(after),pinAfterGitBlob=new_blob,expectedSDKMarkerSHA256=h(marker),originalPackageFiles=len(files),retentionSHA256=h(gate.read_bytes()),sourceRetentionPassed=True,reviewedRefactors=129,controllerSHA256=h(pathlib.Path(__file__).read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
    if push.returncode==0:
        assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['state']='ORIGINAL_SHARED_SDK_PIN_PUBLISHED'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
