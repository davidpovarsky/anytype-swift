"""Normal exact source merges and two reviewed original Kit pin promotions."""
import gzip, hashlib, json, os, pathlib, subprocess, time, traceback

ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='db7b1c8cc5be5950912b91b8cae4f6e5f19f3a16'
START_TREE='177ace40fb161a7a1863e14ab73511f017084521'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-t5-kit-attachment-intake'
OUT=pathlib.Path('/tmp/pinkha-root-t5-kit-source-integration-20261127.json')
PAYLOAD=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-t5-kit-source-payload.json.gz')
GATE='Tools/AnyEnginePort/verify_source_retention.py'

def h(raw):return hashlib.sha256(raw).hexdigest()
def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args):return b(*args).decode().strip()
def match(raw,row):assert len(raw)==row['bytes'] and h(raw)==row['sha256'] and blob(raw)==row['gitBlob']
def resources():
    rows={}
    for name,path,floor in [('root','/',2147483648),('development',str(ROOT),536870912)]:
        s=os.statvfs(path);free=s.f_bavail*s.f_frsize
        assert free>=floor+67108864,(name,free,floor,'fixed64MiB source allowance')
        rows[name]={'freeBytes':free,'floorBytes':floor,'sourceAllowanceBytes':67108864}
    return rows
def owned(path,raw,replace=False):
    code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);assert not p.is_symlink();p.open(sys.argv[2]).write(sys.stdin.buffer.read())'
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'wb' if replace else 'xb'],input=raw,capture_output=True,check=True)
def diff_check(args,expected):
    p=subprocess.run(G+args,capture_output=True)
    receipt.setdefault('diffChecks',[]).append({'argv':args,'exit':p.returncode,'stdout':p.stdout.decode(),'stderr':p.stderr.decode()})
    assert p.returncode==expected['exit'] and p.stdout.decode()==expected['stdout'] and p.stderr.decode()==expected['stderr']
def pins(expectedKit,manifestSHA,lockSHA):
    sdk=json.loads(b('show',':Tools/Hanlin/source.json'))
    assert sdk['revision']=='0ae1920d316b9592cbad0462bea96a07fd1ca351'
    common=b('show',':Tools/MiniApps/receipt_admission.py');assert h(common)=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    stage=b('show',':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift');assert h(stage)=='c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    manifest=b('show',':Modules/PinkhaTorahPresentation/Package.swift');assert h(manifest)==manifestSHA and expectedKit.encode() in manifest
    lock=b('show',':Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved');assert h(lock)==lockSHA
    values=json.loads(lock)['pins'];assert len(values)==56
    p={x['identity']:x['state'] for x in values}
    assert p['torahinspectorkit']=={'revision':expectedKit}
    assert p['swift-collections']=={'revision':'7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e','version':'1.3.0'}
    return {'sdk':sdk['revision'],'kit':expectedKit,'kitManifestSHA256':h(manifest),'packageResolvedSHA256':h(lock),'collections':p['swift-collections'],'common57SHA256':h(common),'stage1SHA256':h(stage)}

assert not OUT.exists()
receipt={'schema':'pinkha-root-t5-kit-source-integration/v1','startedAt':time.time(),'parent':START,'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
    receipt['resourceBefore']=resources()
    packed=PAYLOAD.read_bytes();assert len(packed)==79393 and h(packed)=='171b983e644a878f30cda285e7b72af149ab9fc6c437509218c0e6fc3a0d3e39'
    raw=gzip.decompress(packed);assert len(raw)==374994 and h(raw)=='b31aa907de71c7ff8456d7a100b7ab19563c0b91ab829d9c6dd9825ebdca1d86'
    payload=json.loads(raw);assert payload['requiresG07SourceComposition'] and payload['sourceRetentionRows']==132
    assert t('rev-parse','HEAD')==START and t('rev-parse','HEAD^{tree}')==START_TREE and t('symbolic-ref','HEAD')==REF
    assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
    assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
    status=t('status','--porcelain=v1','--untracked-files=all');assert t('ls-remote','origin',REF).split()[0]==START
    beforePins=pins('9058b489e9acc271b4f8ef69e2ed24648f93b4ed','7709a4b4cc13b0b76f4e884c42ffca35d1016536c1d4cb78b7ee72cf8556da71','e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd')
    prior=pathlib.Path('/tmp/pinkha-root-g07-composition-integration-20261127.json').read_bytes();assert h(prior)=='9462dc7eee69362eea30207395e7007a3193c59ee0a2701f67b2388109e6acb7'
    p=json.loads(prior);assert p['head']==START and p['tree']==START_TREE and p['normalPushReadback']==START and p['reviewedRefactors']==132
    paths=set(t('ls-tree','-r','--name-only',START).splitlines());rows=payload['files'];assert len(rows)==94 and sum(r['status']=='M' for r in rows.values())==4
    donors=[r['commit'] for r in payload['donors']];assert donors==['02910d8e7cacb90b2654a013b9b29ea4d11c5c1e','2519140dd1966cedc4403b74f0f00479e9bd289f','e96ba072887e7581ed6de20fdd81e0897c83763d']
    b('-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',*donors)
    for donor in payload['donors']:
        for link in donor['chain']:
            assert t('show','-s','--format=%P',link['commit']).split()==[link['parent']]
            assert t('rev-parse',link['commit']+'^{tree}')==link['tree']
        subprocess.run(G+['merge-base','--is-ancestor',donor['base'],START],capture_output=True,check=True)
        selected={r['path'] for r in donor['files']}
        assert t('diff','--name-only',donor['base'],donor['commit']).splitlines()==sorted(selected)
        assert dict(line.split('\t')[::-1] for line in t('diff','--name-status',donor['base'],donor['commit']).splitlines())=={p:rows[p]['status'] for p in selected}
        for path in selected:
            match(b('show',donor['commit']+':'+path),rows[path]['after'])
            assert t('ls-tree',donor['commit'],'--',path).split()[0]=='100644'
    for path,row in rows.items():
        if row['status']=='A':assert path not in paths
        else:assert path in paths;match(b('show',START+':'+path),row['before'])
    for path,row in payload['currentDependencies'].items():match(b('show',START+':'+path),row)
    core=json.loads(b('show',START+':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json'))['files'];assert len(core)==15
    for path,row in core.items():match(b('show',START+':'+path),row)
    kitFiles=payload['rootKitFiles'];assert set(kitFiles)=={'Modules/PinkhaTorahPresentation/Package.swift','Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'}
    for path,row in kitFiles.items():
        value=row['text'].encode();match(value,row['after'])
        match(value.replace(b'26beca175d64a4d34e3567f2bbb4bf308d714478',b'9058b489e9acc271b4f8ef69e2ed24648f93b4ed'),row['before'])
        actual=subprocess.run(G+['hash-object','-w','--stdin'],input=value,capture_output=True,check=True).stdout.decode().strip();assert actual==row['after']['gitBlob']
    code='''import os,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-t5-kit-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['after']['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview=subprocess.run(PRE+['python3','-B','-c',code],input=json.dumps([str(ROOT),START,rows]).encode(),capture_output=True,check=True).stdout.decode().strip()
    assert t('diff','--name-only',START,preview).splitlines()==sorted(rows)
    diff_check(['diff','--check',START,preview],payload['diffCheck']);resources()
    merge=subprocess.run(G+['merge','--no-ff','--no-commit',*donors],capture_output=True)
    receipt['merge']={'exit':merge.returncode,'stdout':merge.stdout.decode(),'stderr':merge.stderr.decode()}
    assert merge.returncode==0 and not t('diff','--name-only','--diff-filter=U')
    assert pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).read_text().split()==donors
    for path,row in kitFiles.items():owned(path,row['text'].encode(),replace=True)
    b('add','--',*sorted(kitFiles));assert t('write-tree')==preview and t('diff','--cached','--name-only').splitlines()==sorted(rows)
    afterPins=pins('26beca175d64a4d34e3567f2bbb4bf308d714478','e519cc067165f89741485fd10566b63e788f9219d11a56429b2d33fd1f21c494','4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689')
    assert {k:v for k,v in beforePins.items() if k not in ('kit','kitManifestSHA256','packageResolvedSHA256')}=={k:v for k,v in afterPins.items() if k not in ('kit','kitManifestSHA256','packageResolvedSHA256')}
    intake={'schema':'pinkha-root-t5-kit-attachment-source-intake/v1','parent':START,'donors':donors,'files':rows,
            'wholeMergeTreeEqualsReviewedInputs':True,'expectedMergeTree':preview,'currentDependencies':18,'coreDependencies':15,
            'beforePins':beforePins,'afterPins':afterPins,'sourceRetentionRows':132,'newTestsExecuted':0,
            'originalKitHelperReceipt':'bdc048352dde0e89ff922ca97fc0ab37af21cce4610d16b707bcea813c86156c',
            'originalKitHelperMethodsPassed':6,'originalKitHelperDeclaredCases':9,'knownOpenGaps':payload['knownOpenGaps'],
            'diffCheck':payload['diffCheck'],'completeDiffCheck':payload['completeDiffCheck'],'scope':'Source checkpoint only. Uploader30 and T5/UI/App/completeKit acceptance remain open; known recovery limits preserved. Original SDK/native inputs and all55 other package pins retained.'}
    evidence={'root-source-intake.json':(json.dumps(intake,sort_keys=True,indent=2)+'\n').encode(),
              'root-integration-controller.py':pathlib.Path(__file__).read_bytes(),'prior-g07-integration.original.json':prior}
    for name,row in payload['evidence'].items():
        value=row['text'].encode();match(value,row);evidence[name]=value
    for name,value in evidence.items():owned(PREFIX+'/'+name,value)
    b('add','--',PREFIX);diff_check(['diff','--cached','--check'],payload['completeDiffCheck'])
    expected=sorted(list(rows)+[PREFIX+'/'+name for name in evidence]);assert t('diff','--cached','--name-only').splitlines()==expected
    assert dict(line.split('\t')[::-1] for line in t('diff','--cached','--name-status').splitlines())=={**{p:r['status'] for p,r in rows.items()},**{PREFIX+'/'+n:'A' for n in evidence}}
    tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-t5-kit-source-retention-20261127.json');assert not gate.exists()
    p=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
    pathlib.Path(str(gate)+'.stdout').open('xb').write(p.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(p.stderr)
    result=json.loads(gate.read_bytes());assert p.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==132
    assert pins('26beca175d64a4d34e3567f2bbb4bf308d714478','e519cc067165f89741485fd10566b63e788f9219d11a56429b2d33fd1f21c494','4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689')==afterPins
    message='Merge T5 warning, ordinary attachment source and reviewed Kit lifetime pin\n\nPreserve exact W2 T5/routing/admission and W1 attachment source with all known recovery/acceptance limits. Promote only the two original Kit source pins to26beca; original Foundation helper6/9 is qualified separately, with full SwiftUI/App acceptance pending. All94 source/evidence paths, four preimages,18 uploader dependencies and complete merge tree match. Original132-row retention passes; seven literal raw patch whitespace diagnostics remain retained. SDK/native/common57/Stage1/Collections and all other package pins remain unchanged.\n'
    subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
    head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START]+donors
    assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
    push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
    receipt.update(head=head,tree=tree,donors=donors,files=expected,inputPins=afterPins,sourceRetentionPassed=True,reviewedRefactors=132,
                   retentionSHA256=h(gate.read_bytes()),intakeSHA256=h(evidence['root-source-intake.json']),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(raw),transportSHA256=h(packed),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
    if push.returncode==0:
        assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
    assert push.returncode==0;receipt['resourceAfter']=resources();receipt['state']='SOURCE_MERGED_KIT_PIN_PROMOTED_RUNTIME_PENDING'
except BaseException:
    receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
    receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
