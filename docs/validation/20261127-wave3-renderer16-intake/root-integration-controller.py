import hashlib, json, os, pathlib, subprocess, tempfile, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='edde2fd5058f86c4dc611e44dd5491bffb6b22e0'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-renderer16-intake'
OUT=pathlib.Path('/tmp/pinkha-root-renderer16-integration-20261127.json')
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-renderer16-source-payload.json')
GATE='Tools/AnyEnginePort/verify_source_retention.py'

def h(data):return hashlib.sha256(data).hexdigest()
def blob(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args):return b(*args).decode().strip()
def owned(path,data):
    code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)

assert not OUT.exists()
receipt={'schema':'pinkha-root-renderer16-source-integration/v1','startedAt':time.time(),'parent':START,'state':'PREFLIGHT'}
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
            path=row['path'];assert path not in files and path not in original_paths
            data=b('show',sha+':'+path)
            assert len(data)==row['bytes'] and h(data)==row['sha256'] and blob(data)==row['gitBlob'],path
            assert t('ls-tree',sha,'--',path).split()[0]=='100644'
            files[path]=row
        donors.append({'sha':sha,'parent':parent,'tree':t('rev-parse',sha+'^{tree}'),'files':len(paths)})
    assert len(files)==16
    core='Tools/PinkhaDualEngineRuntime/hosted_core13/'
    dep=json.loads(b('show',START+':'+core+'original_sources.json'))
    assert len(dep['files'])==15
    for path,row in dep['files'].items():
        data=b('show',START+':'+path)
        assert len(data)==row['bytes'] and h(data)==row['sha256'] and blob(data)==row['gitBlob'],path
    rtl_review=json.loads(payload['rtlReview'])
    assert h(payload['rtlReview'].encode())=='71011d3014c30a7b2842d8f2f19b36d97ab69043ed5e9a4082aa0736d84a5557'
    for row in rtl_review['sourceFiles']:
        data=b('show',START+':'+row['path'])
        assert len(data)==row['bytes'] and h(data)==row['sha256'] and blob(data)==row['gitBlob'],row['path']
    renderer=b('show',START+':Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativeTextRendererTests.swift')
    assert len(renderer)==3269 and h(renderer)=='695c89e5c8d5ad8e41f8ec525486836e42338bcc063d13f0945080c169fd7eaa'
    assert h(payload['rendererReview'].encode())=='6fe8bc1b5a1c369c0f0bbedc738fb41d93439c831664ea2f60841b8994a389f4'
    assert h(payload['rendererByteProof'].encode())=='bb351457a7f48f0071b66fee41572aa95e8135d4e2d52c5256588b4565f46eef'
    assert json.loads(b('show',START+':Tools/Hanlin/source.json'))['revision']=='0ae1920d316b9592cbad0462bea96a07fd1ca351'
    assert h(b('show',START+':Tools/MiniApps/receipt_admission.py'))=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    assert h(b('show',START+':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift'))=='c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    # Build the expected complete merge tree in a disposable owned index.
    code='''import os,pathlib,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-renderer16-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview=subprocess.run(PRE+['python3','-B','-c',code],input=json.dumps([str(ROOT),START,files]).encode(),capture_output=True,check=True).stdout.decode().strip()
    assert t('diff','--name-only',START,preview).splitlines()==sorted(files)
    assert all(line.startswith('A\t') for line in t('diff','--name-status',START,preview).splitlines())
    b('merge','--no-ff','--no-commit',*[d['sha'] for d in donors])
    assert t('write-tree')==preview and t('diff','--cached','--name-only').splitlines()==sorted(files)
    review={'schema':'pinkha-root-renderer16-intake/v1','sourceParent':START,'donors':donors,'expectedCompleteMergeTree':preview,
            'allExistingTrackedBytesPreserved':True,'originalDependencyFilesVerified':15,'rtlCurrentSourcesVerified':5,
            'sourceFiles':files,'sourceReviewSHA256':'3ec94af9e875698cd6ec60ac264f5199eb6488c6ff44ea6d1da8b39a4d2871a6',
            'rtlReviewSHA256':h(payload['rtlReview'].encode()),'core13MethodsInExistingAdapter':13,'renderer16MethodsInNewOriginalProfile':16,'rtlMethods':6,'rtlCases':10,
            'testsExecuted':0,'runtimeAccepted':False,'sdkRevision':'0ae1920d316b9592cbad0462bea96a07fd1ca351',
            'scope':['Original Renderer3/Core16 closed profile is now integrated; the existing same-job adapter remains13 methods until a separately reviewed22/26 successor.',
                     'RTL is an exact source-only original profile successor. A separately reviewed adapter successor must explicitly select it for actual runtime.',
                     'All existing App, Native, SDK, lockfiles, PBX targets, original helper declarations and source-retention map are unchanged.',
                     'Original failed publication receipt and exact original inverse patch bytes are preserved; full ordinary diff check remains enabled.']}
    evidence={'root-source-intake.json':(json.dumps(review,indent=2,sort_keys=True)+'\n').encode(),
              'root-rtl-independent-review.json':payload['rtlReview'].encode(),
              'root-integration-controller.py':pathlib.Path(__file__).read_bytes(),
              'independent-renderer16-review.json':payload['rendererReview'].encode(),
              'independent-renderer16-byte-proof.json':payload['rendererByteProof'].encode()}
    prior=pathlib.Path('/tmp/pinkha-root-core13-rtl-integration-20261127.json').read_bytes()
    assert h(prior)=='1180a598258bdb9ccd50c6a1f5d77853064f8a37f159372877a902e316c98de9'
    evidence['prior-core13-rtl-integration.original.json']=prior
    for name,data in evidence.items():owned(PREFIX+'/'+name,data)
    b('add','--',PREFIX);b('diff','--cached','--check')
    expected=sorted(list(files)+[PREFIX+'/'+name for name in evidence])
    assert t('diff','--cached','--name-only').splitlines()==expected
    assert all(line.startswith('A\t') for line in t('diff','--cached','--name-status').splitlines())
    tree=t('write-tree')
    gate=pathlib.Path('/tmp/pinkha-root-renderer16-retention-20261127.json');assert not gate.exists()
    run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr)
    result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
    message='Merge exact original Renderer3 and closed Core16 acceptance profile\n\nAdd the independently reviewed finite renderer suite while preserving all13 original methods, original source/compiler/result validators and owned lifecycle. Retain source-only closed readiness; the existing same-job runtime adapter remains13 until its explicit successor is reviewed. Product source, SDK, native, locks and targets remain unchanged.\n'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START]+[d['sha'] for d in donors]
    assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,donors=donors,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,
                   retentionSHA256=h(gate.read_bytes()),intakeSHA256=h(evidence['root-source-intake.json']),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(PAYLOAD.read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
    if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['state']='RENDERER16_SOURCE_PUBLISHED_RUNTIME_PENDING'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
