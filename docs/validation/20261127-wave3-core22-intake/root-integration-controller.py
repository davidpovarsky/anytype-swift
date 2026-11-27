import hashlib, json, os, pathlib, subprocess, tempfile, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='6581508faffa748ca51d97e6ea51ecf6400fef35'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-core22-intake'
OUT=pathlib.Path('/tmp/pinkha-root-core22-integration-20261127.json')
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-core22-source-payload.json')
GATE='Tools/AnyEnginePort/verify_source_retention.py'

def h(data):return hashlib.sha256(data).hexdigest()
def blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args):return b(*args).decode().strip()
def owned(path,data):
    code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)

assert not OUT.exists()
receipt={'schema':'pinkha-root-core22-source-integration/v1','startedAt':time.time(),'parent':START,'state':'PREFLIGHT'}
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
        subprocess.run(G+['merge-base','--is-ancestor',parent,START],capture_output=True,check=True)
        paths=sorted(row['path'] for row in donor['files'])
        assert t('diff','--name-only',parent,sha).splitlines()==paths
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
    assert len(files)==29
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
with tempfile.TemporaryDirectory(prefix='pinkha-root-core22-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview=subprocess.run(PRE+['python3','-B','-c',code],input=json.dumps([str(ROOT),START,files]).encode(),capture_output=True,check=True).stdout.decode().strip()
    assert t('diff','--name-only',START,preview).splitlines()==sorted(files)
    assert dict(line.split('\t')[::-1] for line in t('diff','--name-status',START,preview).splitlines())=={p:r['status'] for p,r in files.items()}
    b('merge','--no-ff','--no-commit',*[d['sha'] for d in donors])
    assert t('write-tree')==preview and t('diff','--cached','--name-only').splitlines()==sorted(files)
    review={'schema':'pinkha-root-core22-intake/v1','sourceParent':START,'donors':donors,'expectedCompleteMergeTree':preview,
            'allNonChangedTrackedBytesPreserved':True,'exactModifiedControls':5,'exactNewDonorEvidence':24,
            'originalDependencyFilesVerified':15,'sourceFiles':files,'sourceReviewSHA256':payload['rootReviewSHA256'],
            'coreMethods':16,'rtlMethods':6,'rtlCases':10,'totalMethods':22,'totalCases':26,
            'testsExecuted':0,'runtimeAccepted':False,'sdkRevision':'0ae1920d316b9592cbad0462bea96a07fd1ca351',
            'scope':['Merge the finite original Core16 and RTL6/10 same-job adapter; retain all13 prior contracts and exact original lifecycle/admission.',
                     'No App/Native/SDK product source, lockfile, PBX membership or source-retention map changes.',
                     'Original affected two portable controls and seven unchanged control proofs reused; no root test rerun.',
                     'Downloaded original8ac transport qualification retained separately; not4905 native or application acceptance.']}
    evidence={'root-source-intake.json':(json.dumps(review,indent=2,sort_keys=True)+'\n').encode(),
              'root-independent-source-review.json':payload['rootReview'].encode(),
              'root-integration-controller.py':pathlib.Path(__file__).read_bytes()}
    for name,row in payload['evidence'].items():
        data=row['text'].encode();assert h(data)==row['sha256'];evidence[name]=data
    prior=pathlib.Path('/tmp/pinkha-root-witness-feb-integration-20261127.json').read_bytes()
    assert h(prior)=='31e8e537f69e46640617b8eceea1e64dd073c4a063b8019644d66b4e5207243e'
    evidence['prior-current-witness-integration.original.json']=prior
    for name,data in evidence.items():owned(PREFIX+'/'+name,data)
    b('add','--',PREFIX);b('diff','--cached','--check')
    expected=sorted(list(files)+[PREFIX+'/'+name for name in evidence])
    assert t('diff','--cached','--name-only').splitlines()==expected
    expected_status={p:r['status'] for p,r in files.items()};expected_status.update({PREFIX+'/'+name:'A' for name in evidence})
    assert dict(line.split('\t')[::-1] for line in t('diff','--cached','--name-status').splitlines())==expected_status
    tree=t('write-tree')
    gate=pathlib.Path('/tmp/pinkha-root-core22-retention-20261127.json');assert not gate.exists()
    run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr)
    result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
    message='Merge original Core16 and RTL26-case hosted acceptance adapter\n\nPreserve original13 contracts and unchanged process, cleanup and evidence admission. Add only original Renderer3 and current RTL6/10 using exact published witness60fbe/profilef16a. All29 donor files are independently primary-read and full literal inverses verified. Retain actual native8ac transport consumer proof without claiming current application or new4905 native acceptance.\n'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START]+[d['sha'] for d in donors]
    assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,donors=donors,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,
                   retentionSHA256=h(gate.read_bytes()),intakeSHA256=h(evidence['root-source-intake.json']),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(PAYLOAD.read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
    if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['state']='CORE22_SOURCE_PUBLISHED_RUNTIME_PENDING'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
