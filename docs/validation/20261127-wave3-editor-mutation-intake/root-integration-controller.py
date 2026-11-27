import hashlib,json,pathlib,subprocess,time,traceback
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125');PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent'];G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='a953df842e5c686d5058e3c3b3000c7b6424e70c';DONOR='a892500cfc552c9b975a49440fcf2f19fc1a6659';BASE='c95395aec96214dfabd73d55755baa95689cc6d3';REF='refs/heads/codex/chatgpt-wave15-final-20261125';PREFIX='docs/validation/20261127-wave3-editor-mutation-intake';GATE='Tools/AnyEnginePort/verify_source_retention.py';OUT=pathlib.Path('/tmp/pinkha-root-editor-a892-integration-20261127.json');SOURCE='PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift';DP='docs/validation/20261127-wave2-editor-mutations/'
IDENTITIES={SOURCE:(103720,'c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906','9e1766d81529f1716f13ffb8a5f146dc4ade8e43'),DP+'README.md':(4608,'7e3bdd8037071de8ed0b7f8132c897057210909a9383e323f5db4221bd60cbe7','249a7a8bee8a767efbb7d438149756444b509d59'),DP+'independent-review.json':(1142,'9d4575d3aa0de968a3e3f7ca71109774b42d05e8aa775fe6b6c2e46eb25e47c1','a9a4ed768314734cb394eab58a4c5fe8614f99e8'),DP+'source-proof.json':(3042,'2cd96c0ad7a2ca02708920fd85259a8429175b25ab26aa460c022e0e49572fa8','f27d622ee94c72a7584b460a3134b3cb101524f7')}
def h(x):return hashlib.sha256(x).hexdigest()
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE)
def t(*a):return b(*a).decode().strip()
def owned(path,data):
 code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())';subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)
assert not OUT.exists();receipt={'schema':'pinkha-root-editor-a892-integration/v1','startedAt':time.time(),'parent':START,'donor':DONOR,'state':'PREFLIGHT'};OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
 assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
 assert not t('diff','--name-only') and not t('diff','--cached','--name-only') and not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
 status=t('status','--porcelain=v1','--untracked-files=all');assert t('ls-remote','origin',REF).split()[0]==START
 assert t('rev-parse',DONOR+'^')==BASE and t('rev-parse',DONOR+'^{tree}')=='6edf4baab315f21f3236c3230020b9883d5662be';subprocess.run(G+['merge-base','--is-ancestor',BASE,START],capture_output=True,check=True)
 paths=sorted(IDENTITIES);assert t('diff','--name-only',BASE,DONOR).splitlines()==paths
 for p,(size,sha,gitblob) in IDENTITIES.items():
  data=b('show',DONOR+':'+p);assert len(data)==size and h(data)==sha and blob(data)==gitblob
 old=b('show',START+':'+SOURCE);new=b('show',DONOR+':'+SOURCE)
 assert len(old)==86201 and h(old)=='d4ffc25ee659e03bd4dd76b7847faf4fecf343630edf094c0bc02fe060f00850'
 assert new[:len(old)]==old and len(new[len(old):])==17519 and h(new[len(old):])=='68ad800228afbbb8520151fd9991cd68f52dd3442a5b6984e1e9c5012adc7332'
 methods=['testMiddleSplitMergeUndoRedoAndColdReopen','testPartialRangeReplacementUndoRedoAndColdReopen']
 assert all(new[len(old):].count(('func '+method+'()').encode())==1 for method in methods)
 protected=['Tools/Hanlin/source.json','Tools/Hanlin/prepare_sdk.py','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json','Tools/MiniApps/receipt_admission.py','docs/any-engine-port/SOURCE_REFACTOR_MAP.json',GATE]
 protected += [p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
 preserved={p:b('show',START+':'+p) for p in set(protected)}
 assert json.loads(preserved['Tools/Hanlin/source.json'])['revision']=='0ae1920d316b9592cbad0462bea96a07fd1ca351';assert h(preserved['Tools/MiniApps/receipt_admission.py'])=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
 preview=b('merge-tree','--write-tree',START,DONOR);preview_tree=preview.decode().splitlines()[0];assert preview_tree=='4538378455b188d746f46d0da857afae86d8ea85' and t('diff','--name-only',START,preview_tree).splitlines()==paths
 for p,(_,_,gitblob) in IDENTITIES.items():assert t('rev-parse',preview_tree+':'+p)==gitblob
 review={'schema':'pinkha-root-editor-mutation-source-review/v1','parent':START,'donor':DONOR,'donorParent':BASE,'sourcePath':SOURCE,'sourceBeforeBytes':len(old),'sourceBeforeSHA256':h(old),'sourceAfterBytes':len(new),'sourceAfterSHA256':h(new),'appendBytes':17519,'appendSHA256':h(new[len(old):]),'entireOriginalPrefixAndInverseVerified':True,'sourceFiles':{p:{'bytes':v[0],'sha256':v[1],'gitBlob':v[2]} for p,v in IDENTITIES.items()},'exactNewMethods':methods,'documentFlows':6,'newMethodAllowanceSeconds':1200,'review':['All original source bytes, 10 original methods, existing startup warning and preparation helpers remain exact; only a same-file extension is appended.','Real keyboard middle Return split, Command-A/left/backspace merge and Shift-arrow range replacement use original UI paths, distinct block IDs and unchanged neighboring guard. No programmatic selection setter.','Every history action requires exact observed IDs/text/count and current unobscured original Space/object. Intermediate UI state is not counted as persistence.','Actual process termination and different observed App PID precede separate exact cold readback. Observation attachments retain both expected and actual block states, original binding hash, AX and PNG.','No source-level MainActor/import/lifecycle/history blocker found after full append review. Actual UIKit caret/keyboard/history behavior and compilation remain unproved.','The finite future runtime must explicitly select these two methods, all six document flows, real matched App/UI compiler evidence and unchanged native preparation; old products cannot qualify the append.'],'applicationChanges':0,'nativeChanges':0,'sdkChanges':0,'newTestsExecuted':0,'scopeOpen':['Apple UI compilation','Original native fixture and exact selectors','Real history and cold persisted readback','Visual and physical-device acceptance']}
 evidence={'root-independent-review.json':(json.dumps(review,indent=2,sort_keys=True)+'\n').encode(),'root-integration-controller.py':pathlib.Path(__file__).read_bytes()}
 for n,p,sha in [('prior-sdk0ae-integration.original.json','/tmp/pinkha-root-sdk0ae-integration-20261127.json','4adeb15c66cb08c1f9012f374eb84000e38dd6e342103c6223920a23d32e9d92'),('merge-preview.original.json','/tmp/pinkha-root-editor-mutation-a892-intake-20261127/receipt.json','606fc087875484059a601daa5c66f45bef9e8e22301500ed956657ba5bca2e68')]:
  data=pathlib.Path(p).read_bytes();assert h(data)==sha;evidence[n]=data
 b('merge','--no-ff','--no-commit',DONOR);assert t('write-tree')==preview_tree and t('diff','--cached','--name-only').splitlines()==paths
 for n,data in evidence.items():owned(PREFIX+'/'+n,data)
 b('add','--',PREFIX);b('diff','--cached','--check');expected=sorted(paths+[PREFIX+'/'+n for n in evidence]);assert t('diff','--cached','--name-only').splitlines()==expected
 for p,data in preserved.items():assert (ROOT/p).read_bytes()==data,p
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-editor-a892-retention-20261127.json');assert not gate.exists();run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
 pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr);result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
 message='Merge real editor split merge and range history acceptance source\n\nPreserve the complete original Stage1 UI file and append the two reviewed original keyboard/history journeys across three document kinds. Keep interim UI observations distinct from different-process persisted readback. All production, SDK0ae, native8ac, locks and project membership remain unchanged. Actual Apple compilation and execution remain required.\n'
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True);head=t('rev-parse','HEAD');assert t('rev-parse','HEAD^1')==START and t('rev-parse','HEAD^2')==DONOR
 assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
 receipt.update(head=head,tree=tree,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,retentionSHA256=h(gate.read_bytes()),rootReviewSHA256=h(evidence['root-independent-review.json']),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
 if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
 assert push.returncode==0;receipt['state']='EDITOR_MUTATION_SOURCE_PUBLISHED_RUNTIME_PENDING'
except BaseException:
 receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
 receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
