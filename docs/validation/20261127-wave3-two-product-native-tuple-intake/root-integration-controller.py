import hashlib, json, os, pathlib, subprocess, tempfile, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='2cb6c678adcb283f3f5d6953dc8bdbe5812265a2'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-two-product-native-tuple-intake'
OUT=pathlib.Path('/tmp/pinkha-root-native9eb-integration-20261127.json')
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-native9eb-source-payload.json')
GATE='Tools/AnyEnginePort/verify_source_retention.py'

def h(data):return hashlib.sha256(data).hexdigest()
def blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args):return b(*args).decode().strip()
def owned(path,data):
    code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)

assert not OUT.exists()
receipt={'schema':'pinkha-root-native9eb-source-integration/v1','startedAt':time.time(),'parent':START,'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
    payload=json.loads(PAYLOAD.read_bytes())
    assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
    assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
    assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
    status=t('status','--porcelain=v1','--untracked-files=all')
    assert t('ls-remote','origin',REF).split()[0]==START
    original_paths=set(t('ls-tree','-r','--name-only',START).splitlines())
    files={};donors=[]
    for donor in payload['donors']:
        sha,parent=donor['sha'],donor['parent']
        b('-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',sha)
        assert t('rev-parse',sha+'^')==parent
        diff_base=donor.get('diffBase',parent)
        subprocess.run(G+['merge-base','--is-ancestor',diff_base,START],capture_output=True,check=True)
        paths=sorted(row['path'] for row in donor['files'])
        assert t('diff','--name-only',diff_base,sha).splitlines()==paths
        for row in donor['files']:
            path=row['path'];assert path not in files
            if row['status']=='A':assert path not in original_paths
            else:
                assert row['status']=='M' and path in original_paths
                assert blob(b('show',START+':'+path))==row['beforeGitBlob']
            data=b('show',sha+':'+path)
            assert len(data)==row['bytes'] and h(data)==row['sha256'] and blob(data)==row['gitBlob'],path
            assert t('ls-tree',sha,'--',path).split()[0]=='100644'
            files[path]=row
        donors.append({'sha':sha,'parent':parent,'tree':t('rev-parse',sha+'^{tree}'),'files':len(paths)})
    assert len(files)==42
    dep=json.loads(b('show',payload['dependencyRef']+':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json'))
    assert len(dep['files'])==15
    for path,row in dep['files'].items():
        data=b('show',START+':'+path)
        assert len(data)==row['bytes'] and h(data)==row['sha256'] and blob(data)==row['gitBlob'],path
    assert h(payload['rootReview'].encode())==payload['rootReviewSHA256']
    assert json.loads(b('show',START+':Tools/Hanlin/source.json'))['revision']=='0ae1920d316b9592cbad0462bea96a07fd1ca351'
    assert h(b('show',START+':Tools/MiniApps/receipt_admission.py'))=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    assert h(b('show',START+':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift'))=='c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    # Build the expected complete merge tree in a disposable owned index.
    code='''import os,pathlib,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-native9eb-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview=subprocess.run(PRE+['python3','-B','-c',code],input=json.dumps([str(ROOT),START,files]).encode(),capture_output=True,check=True).stdout.decode().strip()
    assert t('diff','--name-only',START,preview).splitlines()==sorted(files)
    assert dict(line.split('\t')[::-1] for line in t('diff','--name-status',START,preview).splitlines())=={p:r['status'] for p,r in files.items()}
    b('merge','--no-ff','--no-commit',*[d['sha'] for d in donors])
    assert t('write-tree')==preview and t('diff','--cached','--name-only').splitlines()==sorted(files)
    review={'schema':'pinkha-root-native9eb-intake/v1','sourceParent':START,'donors':donors,'expectedCompleteMergeTree':preview,
            'allNonChangedTrackedBytesPreserved':True,'exactModifiedControls':0,'exactNewDonorEvidence':42,
            'originalDependencyFilesVerified':15,'sourceFiles':files,'sourceReviewSHA256':payload['rootReviewSHA256'],
            'baseNativeSourceFiles':4868,'futureHeartSourceFiles':4900,'futureSharedSourceFiles':4905,
            'testsExecuted':0,'runtimeAccepted':False,'sdkRevision':'0ae1920d316b9592cbad0462bea96a07fd1ca351',
            'scope':['Preserve W1 complete two-product tuple maps and exact historical custody records as42 additions.',
                     'Any0796/versionedSync and proposedshared4905/localSync are explicitly distinct; fullnewruntimeidentity andactualApplebuild remain separate.',
                     'No activeApp/Native/SDK product source, lockfile, PBX membership or source-retention map changes.',
                     'Original raw Go metadata output retains four exact trailing-tab records; ordinary diff-check observation is retained, never reported asPASS.']}
    evidence={'root-source-intake.json':(json.dumps(review,indent=2,sort_keys=True)+'\n').encode(),
              'root-independent-source-review.json':payload['rootReview'].encode(),
              'root-integration-controller.py':pathlib.Path(__file__).read_bytes()}
    for name,row in payload['evidence'].items():
        data=row['text'].encode();assert h(data)==row['sha256'];evidence[name]=data
    prior=pathlib.Path('/tmp/pinkha-root-core22-integration-20261127.json').read_bytes()
    assert h(prior)=='73e57ca5d3a2b0c2f86f95441fb93ee7c0c37737f51fd9904fce830d408623bf'
    evidence['prior-core22-integration.original.json']=prior
    for name,data in evidence.items():owned(PREFIX+'/'+name,data)
    b('add','--',PREFIX)
    check=subprocess.run(G+['diff','--cached','--check'],capture_output=True)
    assert check.returncode==2 and not check.stderr and len(check.stdout)==667 and h(check.stdout)=='4ffa0b3aff54dea06446b68b0416c7e31596d28459e5f27c66c3ccca5ca6274c'
    receipt['ordinaryDiffCheck']={'exit':check.returncode,'stdoutSHA256':h(check.stdout),'stdout':check.stdout.decode(),'reviewedScope':'Only exact original Go metadata output trailing tabs, no product/executable source finding','passed':False}
    expected=sorted(list(files)+[PREFIX+'/'+name for name in evidence])
    assert t('diff','--cached','--name-only').splitlines()==expected
    expected_status={p:r['status'] for p,r in files.items()};expected_status.update({PREFIX+'/'+name:'A' for name in evidence})
    assert dict(line.split('\t')[::-1] for line in t('diff','--cached','--name-status').splitlines())==expected_status
    tree=t('write-tree')
    gate=pathlib.Path('/tmp/pinkha-root-native9eb-retention-20261127.json');assert not gate.exists()
    run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr)
    result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
    message='Merge W1 complete native source tuple and original custody evidence\n\nPreserve exact4868/4900/4905 source maps with ordered40core/11RPC/7SDK preimages and explicit standaloneversusshared Sync identity. Retain all original custody results and failures without rerunning their controllers. Exact raw Go metadata tabs remain bound to the original receipt; no product or runtime acceptance is added.\n'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START]+[d['sha'] for d in donors]
    assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,donors=donors,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,
                   retentionSHA256=h(gate.read_bytes()),intakeSHA256=h(evidence['root-source-intake.json']),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(PAYLOAD.read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
    if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['state']='NATIVE_TUPLE_SOURCE_PUBLISHED_NEW_NATIVE_PENDING'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
