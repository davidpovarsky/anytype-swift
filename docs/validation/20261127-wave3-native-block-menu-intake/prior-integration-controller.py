import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='ba1bf2c2cb5cab20efe5edb2d5522ee48f3a88fb'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-local-readiness-integration.json')
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

donor='2cdc1c99783cc90d8e867350c23587fcdc74a2ad';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==25 and all(mode=='A' and not (ROOT/p).exists() for mode,p in rows)
audit_path=pathlib.Path('/tmp/pinkha-wave3-local-readiness-intake.json');audit=audit_path.read_bytes()
assert h(audit)=='b85f484b8a020a1f68c517fd4ee93f6309de48797dbff46e438638eb3bf57540'
review=json.loads(audit);assert review['status']=='PASS_ROOT_ORIGINAL_LOCAL_READINESS_EVIDENCE_AND_SOURCE_INTAKE_NO_RERUN'
assert review['candidate']==donor and review['newTestsOrBuilds']==0
for row in review['sourceClosure']:assert h(b('show','HEAD:'+row['path']))==row['sha256']
original_receipt=pathlib.Path('/tmp/pinkha-wave3-any-body-composition-integrations.json').read_bytes()
assert h(original_receipt)=='4b8e519ecb3fe246a8909083b9f117cd0f6f05e19b23a007b8623afec1d527f4'
assert json.loads(original_receipt)['head']==parent
proofs={
 'original-evidence-intake.json':(audit,'b85f484b8a020a1f68c517fd4ee93f6309de48797dbff46e438638eb3bf57540'),
 'read-only-intake.py':(pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-local-readiness-intake-014cf4f0bee1.py').read_bytes(),'014cf4f0bee145413ea6a554d94ddee6ed5f4f999985df4594283f5692a8b700'),
 'prior-hanlin-integration-receipt.json':(original_receipt,'4b8e519ecb3fe246a8909083b9f117cd0f6f05e19b23a007b8623afec1d527f4'),
 'prior-hanlin-integration-controller.py':(pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-any-body-composition-50fda726a4ff.py').read_bytes(),'50fda726a4ffa5fd61f3dbbf24a43847d30d4ef0acabbfc8127f222a02fa9513'),
 'independent-c511-source-review.json':(pathlib.Path('/var/lib/sentinelx/uploads/pinkha-mini-independent-c511-0512fc5e1b4e.json').read_bytes(),'0512fc5e1b4e8ff232d97e7df983e32110386f42ae384fb3049a624d471588ee')}
for name,(data,expected) in proofs.items():assert h(data)==expected,name
b('cherry-pick','-x','--no-commit',donor)
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
prefix='docs/validation/20261127-wave3-local-readiness-intake';extras=[]
for name,(data,expected) in proofs.items():
    p=prefix+'/'+name;owned(p,data);extras.append(p)
note=prefix+'/root-contract-review.json'
owned(note,(json.dumps({'rootParent':parent,'candidate':donor,'fullBothControllersAndContractReviewed':True,'actualOriginalEvidenceReused':{'originalReceiptSHA256':'9e26b39507fcaf32fed97cc10f9ad8ff23e0c7a6f35fcde993ae831d6ea59f9c','nativeProcesses':2,'probeProcesses':6,'originalResponseProofs':19,'sourceClosureFiles':51,'allSourceFilesExactAtCurrentRoot':True,'actualSIGKILL':1,'newPages':2,'newSignedAppends':2,'explicitProbeBundleEnsures':2},'review':'Native local raw signed-claims completeness is distinct from semantic related completeness. Opaque history remains in full dataset and globally denies complete related coverage. Bounds return409 without a truncated success. Original object-logical-closure stays narrower than Space. Opaque generation may survive cold reopen; it is not account identity, process lease, peer convergence or fresh mutation authorization. Composite UI still needs related-before/metadata/related-after stable generation/targets and post-await active scope fence.','notTransferred':['peer convergence','Heart authoritative-head/index projection','Swift related UI adapter execution','Apple native8ac ABI/runtime','UI visual acceptance','full migration source-history authority'],'newCompilerOrRuntime':0,'sourceProductionDelta':False,'macFrozenSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe'},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix);finish(parent,donor,'current-local-space-readiness-evidence',[p for _,p in rows]+extras)
