import base64,gzip,hashlib,json,pathlib,subprocess,time,traceback
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125');PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent'];G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='a25b243a4db595010e9aa11b0fc3aed57a4be2a3';DONOR='1f8a19ab4ec87490d6a17ae8470224f39bc48596';BASE='7380a797d13b279b6d19e43ade7af1929089b8ef';REF='refs/heads/codex/chatgpt-wave15-final-20261125';PREFIX='docs/validation/20261127-wave3-styled51-intake';GATE='Tools/AnyEnginePort/verify_source_retention.py';OUT=pathlib.Path('/tmp/pinkha-root-styled51-integration-20261127.json')
def h(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE)
def t(*a):return b(*a).decode().strip()
def owned(path,data):
 code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())';subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path)],input=data,capture_output=True,check=True)
assert not OUT.exists();receipt={'schema':'pinkha-root-styled51-integration/v1','startedAt':time.time(),'parent':START,'donor':DONOR,'state':'PREFLIGHT'};OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
 assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
 assert not t('diff','--name-only') and not t('diff','--cached','--name-only') and not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
 status=t('status','--porcelain=v1','--untracked-files=all');assert t('ls-remote','origin',REF).split()[0]==START
 payload=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-styled51-review-payload.json.gz').read_bytes();assert h(payload)=='f4f0c11494498545f14365a5628d52d95bccc6aae971fb511bc95e6353b1c00c';entries=json.loads(gzip.decompress(payload));evidence={}
 for n,v in entries.items():
  assert pathlib.PurePosixPath(n).name==n;data=base64.b64decode(v['base64']);assert len(data)==v['bytes'] and h(data)==v['sha256'];evidence[n]=data
 ids=json.loads(evidence['primary-source-identities.json']);source27=json.loads(evidence['source27-pins.json']);assert len(ids)==51 and len(source27)==27
 if subprocess.run(G+['cat-file','-e',DONOR+'^{commit}'],capture_output=True).returncode:subprocess.run(G+['-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',DONOR],capture_output=True,check=True)
 assert t('rev-parse',DONOR+'^')==BASE and t('rev-parse',DONOR+'^{tree}')=='27098290e369ec0a89fcb4a2626f5010f5021752';subprocess.run(G+['merge-base','--is-ancestor',BASE,START],capture_output=True,check=True)
 paths=sorted(row['path'] for row in ids);assert t('diff','--name-only',BASE,DONOR).splitlines()==paths
 for row in ids:
  data=b('show',DONOR+':'+row['path']);assert len(data)==row['bytes'] and h(data)==row['sha256'] and blob(data)==row['gitBlob'];assert t('ls-tree',DONOR,'--',row['path']).startswith('100644 blob '+row['gitBlob']+'\t')
  assert not (ROOT/row['path']).exists(),row['path']
 closure=[]
 for p,sha in source27.items():
  data=b('show',START+':'+p);assert h(data)==sha,p;closure.append({'path':p,'bytes':len(data),'sha256':sha,'gitBlob':blob(data)})
 protected=['Tools/Hanlin/source.json','Tools/Hanlin/prepare_sdk.py','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json','Tools/MiniApps/receipt_admission.py','docs/any-engine-port/SOURCE_REFACTOR_MAP.json',GATE]
 protected+=[p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
 preserved={p:b('show',START+':'+p) for p in set(protected)}
 assert json.loads(preserved['Tools/Hanlin/source.json'])['revision']=='35d26911f70794a41361cee710b1fed24a35e269';assert h(preserved['Tools/MiniApps/receipt_admission.py'])=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
 preview=b('merge-tree','--write-tree',START,DONOR);preview_tree=preview.decode().splitlines()[0];assert t('diff','--name-only',START,preview_tree).splitlines()==paths
 for row in ids:assert t('rev-parse',preview_tree+':'+row['path'])==row['gitBlob']
 receipt['previewTree']=preview_tree
 prior=pathlib.Path('/tmp/pinkha-root-sdk35d-common57-integration-20261127.json').read_bytes();assert h(prior)=='c7888c683aa4bc90383663e37182a75548ecb26f1ed7db9bc26d8eab7f6349bd' and json.loads(prior)['head']==START
 evidence['prior-root-integration.original.json']=prior;evidence['actual-current27-source-closure.json']=(json.dumps(closure,indent=2,sort_keys=True)+'\n').encode();evidence['root-integration-controller.py']=pathlib.Path(__file__).read_bytes()
 b('merge','--no-ff','--no-commit',DONOR);assert t('write-tree')==preview_tree and t('diff','--cached','--name-only').splitlines()==paths
 for n,data in evidence.items():owned(PREFIX+'/'+n,data)
 b('add','--',PREFIX);b('diff','--cached','--check');expected=sorted(paths+[PREFIX+'/'+n for n in evidence]);assert t('diff','--cached','--name-only').splitlines()==expected
 for p,data in preserved.items():assert (ROOT/p).read_bytes()==data,p
 for p,sha in source27.items():assert h((ROOT/p).read_bytes())==sha,p
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-styled51-retention-20261127.json');assert not gate.exists();run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
 pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr);result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
 message='Merge original styled NativeUI control preparation\n\nIntegrate Wave2 exact51 Tools/docs paths with original bounded selectors, observations and all-command process custody. Preserve complete original controller inverses and prior failures. All27 actual current source dependencies match; SDK35d/native8ac/common57, all production and source-retention mappings are unchanged. Runtime gate remains closed pending actual shared App/UI and native runner compiler proof.\n'
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True);head=t('rev-parse','HEAD');assert t('rev-parse','HEAD^1')==START and t('rev-parse','HEAD^2')==DONOR
 assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
 receipt.update(head=head,tree=tree,files=expected,sourceClosure27Matched=True,sourceRetentionPassed=True,reviewedRefactors=129,retentionSHA256=h(gate.read_bytes()),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
 if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
 assert push.returncode==0;receipt['state']='STYLED51_SOURCE_PUBLISHED_RUNTIME_CLOSED'
except BaseException:
 receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
 receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
