import hashlib, json, pathlib, subprocess, time
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='654e7d835994c030f650b967c4ab10bb9ed0b639'
DONOR='dfbb481102226e5484b5b8e4dd730661f9b03d14'
BASE='33e31c64ca9e35e258a4d64cfe8690b08a6cbc39'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
EDITOR='Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeEditor.swift'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
DP='docs/validation/20261127-wave2-native-hanlin-hook/'
PREFIX='docs/validation/20261127-wave3-native-hanlin-hook-intake'
OUT=pathlib.Path('/tmp/pinkha-wave3-native-hanlin-hook-integration.json')
def h(b):return hashlib.sha256(b).hexdigest()
def b(*args):return subprocess.check_output(G+list(args),stderr=subprocess.PIPE)
def t(*args):return b(*args).decode().strip()
def owned(path,data):
    code="import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);f=p.open('xb');f.write(sys.stdin.buffer.read());f.close()"
    subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)
assert not OUT.exists()
assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
status=t('status','--porcelain=v1','--untracked-files=all')
if subprocess.run(G+['cat-file','-e',DONOR+'^{commit}'],capture_output=True).returncode:
    b('-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',DONOR)
assert t('rev-parse',DONOR+'^')==BASE
assert t('rev-parse',DONOR+'^{tree}')=='6652397271d7648652da563b5225ca8ef1b15cb5'
paths=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','--no-renames','-r',DONOR).splitlines()]
assert len(paths)==8 and [(s,p) for s,p in paths if s!='A']==[('M',EDITOR)]
for s,p in paths:
    if s=='A':assert p.startswith(DP) and not (ROOT/p).exists(),p
before=b('show','HEAD:'+EDITOR);after=b('show',DONOR+':'+EDITOR)
assert before==b('show',BASE+':'+EDITOR)
assert t('rev-parse','HEAD:'+EDITOR)=='29407373ed3ed0fe6e36ecc6365db0d6918b702d'
assert h(before)=='4b7a6feaa4557a63183789549ae9fe498ef2d988f0b7516f39947891a3c1dd3a'
assert len(after)==61193 and h(after)=='c0c045570318f03ac38633e3b48dd6602506b748e0866594ba2f434a523bd4f8'
inverse=json.loads(b('show',DONOR+':'+DP+'source-inverse.json'))
old=inverse['oldCall'].encode();new=inverse['newCall'].encode()
assert before.count(old)==1 and after.count(new)==1 and after.replace(new,old,1)==before
assert before.replace(old,new,1)==after
proof=json.loads(b('show',DONOR+':'+DP+'source-proof.json'))
assert proof['functionBeforeBytes']==1262 and proof['functionAfterBytes']==1333
assert proof['compilerInvocations']==proof['MacCommands']==0 and not proof['productionSaveActivated']
assert proof['functionOutsideCallBytesUnchanged'] and proof['outsideFunctionBytesUnchanged']
assert proof['requiredSDKHelperCommit']=='680364279e08dc69d7d7eee8f6f13169ea8d0be4'
for row in proof['sourceInputs']:
    data=b('show','HEAD:'+row['path'])
    assert len(data)==row['bytes'] and h(data)==row['sha256']
    assert t('rev-parse','HEAD:'+row['path'])==row['gitBlob']
projections=json.loads(b('show',DONOR+':'+DP+'conditional-source-projections.json'))
assert projections['publicHelperIsAsyncInAllUIKitBuilds'] and not projections['releaseMachineCodeIdentityClaimed']
assert projections['releaseAndDebugDeviceSourceEqual'] and h(projections['releaseUIKitProjection'].encode())==projections['releaseUIKitSHA256']
pins=['Tools/Hanlin/source.json','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json',GATE,MAP,'NativeApp/UITests/NativeLaunchTests.swift']
pins += [p for p in t('ls-tree','-r','--name-only','HEAD').splitlines() if p.endswith('/Package.resolved')]
preserved={p:b('show','HEAD:'+p) for p in pins}
assert not any(x.get('from')==EDITOR for x in json.loads(preserved[MAP])['changes'])
assert subprocess.run(G+['cat-file','-e','586c98bcc17dee425664224e508fc0e8df277678:'+EDITOR],capture_output=True).returncode!=0
preview=subprocess.run(G+['merge-tree','--write-tree',START,DONOR],capture_output=True,text=True)
assert preview.returncode==0,preview.stdout
tree=preview.stdout.strip();assert len(tree)==40
assert t('diff','--name-only',START,tree).splitlines()==sorted(p for _,p in paths)
merged=subprocess.run(G+['merge','--no-ff','--no-commit',DONOR],capture_output=True,text=True)
assert merged.returncode==0 and not t('ls-files','-u')
assert t('write-tree')==tree
for _,path in paths:assert (ROOT/path).read_bytes()==b('show',DONOR+':'+path),path
extras=[]
prior=pathlib.Path('/tmp/pinkha-wave3-g02-retention-resume-integration.json').read_bytes()
assert h(prior)=='a76049e3c066c12f8a685cf0295eb703c017a16f997db17c85fc32da82f7e70a' and json.loads(prior)['head']==START
for name,data in [('prior-g02-final-receipt.json',prior),('root-integration-controller.py',pathlib.Path(__file__).read_bytes())]:
    path=PREFIX+'/'+name;owned(path,data);extras.append(path)
note=PREFIX+'/root-source-review.json'
owned(note,(json.dumps({'rootParent':START,'donor':DONOR,'donorParent':BASE,'originalEditorBlob':'29407373ed3ed0fe6e36ecc6365db0d6918b702d',
 'finalEditorBlob':'fab7238a26e3af5b60c03c318106aa8d28a0d629','originalEditorSHA256':h(before),'finalEditorSHA256':h(after),
 'literalFullInverse':True,'sourceInputsVerified':proof['sourceInputs'],
 'review':['The only editor change calls the delivered original async helper with its current native session, documents, client and source owner. Original focus cancellation, Task/flush/pending-edit refusal, authority/creation services, conversation and error handling remain byte-identical.',
 'Root read both the original helper implementation and the actual editor function. Preparation/fixture admission performs original native reads under the current lease and revalidates cancellation, source owner/document revision, account/Space/engine generation after awaits. The original presentation factory is called on that current scope.',
 'The original lifecycle revoke/drain is installed on the returned controller. Release and ordinary Debug now use an async wrapper which delegates the original factory; no compiled machine-code identity or production Save activation is claimed.',
 'All four helper contract files match their published blobs/bytes. The special native UI route remains DEBUG simulator and explicitly bound to fresh preparation/runtime/source identity. Stop-after-root is a separate source successor, not accepted by this hook.',
 'AnyNativeEditor did not exist in the original586c baseline. No invented map baseline is added. Current129map, verifier, source/native/SDK pins, all package locks and original NativeLaunch source remain exact.'],
 'AppleCompilation':'NOT_RUN','UIEnumeration':'NOT_RUN','UIRuntime':'NOT_RUN','nativeSave':'NOT_RUN','visual':'NOT_RUN','physicalDevice':'NOT_RUN','newTestsExecuted':0},ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',PREFIX);b('diff','--cached','--check','--',EDITOR,note)
for path,value in preserved.items():assert (ROOT/path).read_bytes()==value,path
expected=sorted([p for _,p in paths]+extras);assert t('diff','--cached','--name-only').splitlines()==expected
tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-wave3-native-hanlin-hook-retention.json');assert not gate.exists()
r=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
pathlib.Path(str(gate)+'.stdout').open('xb').write(r.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(r.stderr)
result=json.loads(gate.read_bytes());assert r.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
message='Integrate original native Hanlin editor helper hook\n\nPreserve original focus/flush/authority/error/lifecycle behavior and exact shared helper API. New Apple/native acceptance remains open.\n\nIntegrated from '+DONOR+'\n'
subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START,DONOR]
assert t('status','--porcelain=v1','--untracked-files=all')==status
assert t('ls-remote','origin',REF).split()[0]==START
p=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
receipt={'schema':'pinkha-original-native-hanlin-hook-integration-v1','parent':START,'donor':DONOR,'head':head,'tree':tree,'files':expected,
 'controllerSHA256':h(pathlib.Path(__file__).read_bytes()),'sourceRetentionPassed':True,'reviewedRefactors':129,'retentionSHA256':h(gate.read_bytes()),
 'pinsLocksSourceMapVerifierAndNativeLaunchUnchanged':True,'sourceInputsVerified':proof['sourceInputs'],'newAppleTests':0,
 'pushExit':p.returncode,'pushStdout':p.stdout,'pushStderr':p.stderr,'completedAt':time.time()}
if p.returncode==0:
    assert t('ls-remote','origin',REF).split()[0]==head
    receipt['normalPushReadback']=head
OUT.open('x').write(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({'head':head,'tree':tree,'retentionSHA256':receipt['retentionSHA256'],'pushExit':p.returncode,'receipt':str(OUT),'receiptSHA256':h(OUT.read_bytes())}),flush=True)
assert p.returncode==0
