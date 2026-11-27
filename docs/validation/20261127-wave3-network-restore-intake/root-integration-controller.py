import hashlib,json,pathlib,subprocess,time,traceback
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='9414885fb7ac1c6619f82a5397a4d04d49c19c3e';DONOR='7db7c7e143b26dbb9c4a87474607c76409ecc141';REF='refs/heads/codex/chatgpt-wave15-final-20261125'
BASE='4a381db674fa1f011bff5d02d1a1e9badf253c1e';P='Tools/AnyEngineValidation/native_file_peer_comparison/native_product_custody/'
DP='docs/validation/20261127-wave3-restore-receipt/';PREFIX='docs/validation/20261127-wave3-network-restore-intake'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json';GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-root-network-restore-source-integration.json')
def h(x):return hashlib.sha256(x).hexdigest()
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE)
def t(*a):return b(*a).decode().strip()
def owned(path,data):
 c='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
 subprocess.run(PRE+['python3','-B','-c',c,str(ROOT/path)],input=data,capture_output=True,check=True)
assert not OUT.exists()
receipt={'schema':'pinkha-root-network-restore-source-intake/v1','parent':START,'donor':DONOR,'startedAt':time.time(),'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
 plan_bytes=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-network-restore-intake-plan.json').read_bytes();assert h(plan_bytes)=='5813f661e8a2231865e4a5e766b0414102f41b7442b08e6b0b9b44ae2da68202';plan=json.loads(plan_bytes)
 assert plan['parent']==START and plan['donor']==DONOR and plan['previewTree']=='ea543dbdd080da9598ccb46b077a5dceb1908cb1'
 assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
 assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
 assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
 status=t('status','--porcelain=v1','--untracked-files=all');assert t('ls-remote','origin',REF).split()[0]==START
 subprocess.run(G+['merge-base','--is-ancestor',BASE,START],capture_output=True,check=True)
 assert t('rev-parse',DONOR+'^')=='a70e94f9647df16ce8962894b1973ba5a5a35163' and t('rev-parse',DONOR+'^{tree}')=='5fab3b752f689f181da400f409ab96b8888171f1'
 assert len(plan['files'])==20
 for row in plan['files']:
  p=row['path'];data=b('show',DONOR+':'+p)
  assert len(data)==row['bytes'] and h(data)==row['sha256'] and t('rev-parse',DONOR+':'+p)==row['blob']
  assert p.startswith('Tools/AnyEngineValidation/native_file_peer_comparison/') or p.startswith(DP)
  if row['status']=='A':assert not (ROOT/p).exists()
  else:assert row['status']=='M' and p in [P+'README.md',P+'restore.py']
 inv=json.loads(b('show',DONOR+':'+DP+'literal-inverse.json'));current=b('show',DONOR+':'+inv['path']);restored=current
 assert h(current)==inv['afterSHA256']=='e2b025dc9a48f547b4e87fcceb39b9d9185c3c6b8f8920946369979fe3e379e5'
 for op in reversed(inv['changes']):
  new,old=op['new'].encode(),op['old'].encode();assert restored.count(new)==1;restored=restored.replace(new,old,1)
 assert restored==b('show',DONOR+'^:'+inv['path']) and h(restored)==inv['beforeSHA256']
 original_restore=b('show',START+':'+P+'restore.py');assert h(original_restore)=='f4b368bdf8280caa52967585fd55be03a99b9c8ecf4aa9c50421bfd814f6b481'
 assert original_restore==b('show',DONOR+':'+P+'restore-v1-before-exclusive.py')
 review=b('show',DONOR+':'+DP+'independent-review.json');assert h(review)=='ff329081bd2206701962869f0e4222ebb4b81b5e6784881fb592221f3f812ad9'
 control=b('show',DONOR+':'+DP+'existing-result-control.json');assert h(control)=='64c4ca5785da2ea7630f1195d65fc42457bae947eb9cc0e94fae9e6134c66c28'
 original_control=b('show',DONOR+':'+P+'exclusive-restore-controls.json');assert h(original_control)=='f8ccfc8e7b4ecb7a641ef904eb51d2502ed45406db352b6e6ee2eaa398f89be7'
 assert b('show',START+':'+P+'receipt.json')==b('show',DONOR+':'+P+'receipt.json')
 preserved_paths=[MAP,GATE,'Tools/Hanlin/source.json','Tools/Hanlin/prepare_sdk.py','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json','NativeApp/UITests/NativeLaunchTests.swift']
 preserved_paths += [p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or p.endswith('.pbxproj')]
 preserved={p:b('show',START+':'+p) for p in preserved_paths}
 preview=subprocess.run(G+['merge-tree','--write-tree',START,DONOR],capture_output=True,text=True)
 assert preview.returncode==0 and preview.stdout.strip()==plan['previewTree']
 expected_delta=[r['status']+'\t'+r['path'] for r in plan['files']];assert t('diff','--name-status',START,plan['previewTree']).splitlines()==expected_delta
 merged=subprocess.run(G+['merge','--no-ff','--no-commit',DONOR],capture_output=True,text=True)
 assert merged.returncode==0 and not t('ls-files','-u') and t('write-tree')==plan['previewTree']
 for row in plan['files']:assert (ROOT/row['path']).read_bytes()==b('show',DONOR+':'+row['path'])
 prior=pathlib.Path('/tmp/pinkha-root-original-sdk-consumer-pin.json').read_bytes();assert h(prior)=='026e12a506e0a5c99711946802e0b7ce429328f590ccedd0eee8281b5d486229' and json.loads(prior)['head']==START
 publication=pathlib.Path('/tmp/pinkha-wave3-restore-receipt-publication-20261127.json').read_bytes();assert h(publication)=='90f03ff32b386ef0c36829c4dbcf97a6b50dd0df8393317a06879eb2ff23c98d'
 note={'schema':'pinkha-root-network-restore-review/v1','parent':START,'donor':DONOR,'originalReviewedBlobs':plan['files'],'reviewedQualifierLiteralInverse':True,'originalNativeRestoreSourceRetained':True,
  'review':[
   'Root read the exact two-step file installation change and complete qualifier/test. os.link installs only at an absent destination, including dangling-link rejection; fsync brackets retiring only the owned temporary link. Full original native copy/hash/metadata/headroom guards remain in main, not module import.',
   'A concrete original qualifier defect was repaired: its unconditional finally save could overwrite an existing result even after assert-not-exists failed. The new exclusive0600 O_CREAT|O_EXCL claim occurs before try/finally and before native custody reads. One literal inverse restores the entirea70 qualifier. Root independently reviewed the child-authored change and actual focused test.',
   'The actual one local disposable existing-result control passed once with bytes/inode/mode/owner/mtime/ctime/nlink unchanged, no extra files, no native reads or tests. Original four-case f8cc receipt and helper/controller remain historical original evidence; neither they nor native792 restoration was replayed.',
   'a935 original read-only archive ledger retains12 network,2 object-authority and2 LinuxP2P methods under their original source/platform scopes. Original collector/role failures remain failed, including the2-pass2-fail run. Exact1594→1599 seven-file SDKdelta is explicit; no historical pass is relabeled current0796.',
   'All20 changed paths are downstream custody/evidence controls/docs. No current App, engine, SDK, locks, native binary/source pins, NativeLaunch23, source map or build gates change. Current FilesV2 revoked/cold plaintext acceptance, mixed Heart/Any and Apple/runtime/distribution remain open.'
  ],'newTestsRunByRoot':0,'actualNativeRestore':'NOT_RUN','currentRevocationAcceptance':'OPEN','AppleAcceptance':'NOT_RUN','TestFlight':'NOT_RUN'}
 extra={'root-source-review.json':(json.dumps(note,ensure_ascii=False,indent=2,sort_keys=True)+'\n').encode(),'root-integration-controller.py':pathlib.Path(__file__).read_bytes(),'approved-source-plan.json':plan_bytes,'prior-sdk-pin-integration.json':prior,'owner-publication-receipt.json':publication}
 for n,data in extra.items():owned(PREFIX+'/'+n,data)
 b('add','--',PREFIX);b('diff','--cached','--check','--',*(r['path'] for r in plan['files'] if r['path'].endswith('.py')),PREFIX)
 for p,v in preserved.items():assert (ROOT/p).read_bytes()==v,p
 expected=sorted([r['path'] for r in plan['files']]+[PREFIX+'/'+n for n in extra]);assert t('diff','--cached','--name-only').splitlines()==expected
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-network-restore-retention.json');assert not gate.exists()
 r=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
 pathlib.Path(str(gate)+'.stdout').open('xb').write(r.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(r.stderr)
 v=json.loads(gate.read_bytes());assert r.returncode==0 and v['sourceRetentionPassed'] and len(v['reviewedRefactors'])==129
 message='Integrate original network evidence and exclusive restore custody\n\nPreserve historical network and failure scope. Install retained files without replacement and protect original qualification receipts before cleanup. No native restoration, account activity or test replay is performed by this source intake.\n\nIntegrated from '+DONOR+'\n'
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True)
 head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START,DONOR]
 assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
 receipt.update(head=head,tree=tree,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,retentionSHA256=h(gate.read_bytes()),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),planSHA256=h(plan_bytes),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
 if push.returncode==0:
  assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
 assert push.returncode==0;receipt['state']='SOURCE_AND_ORIGINAL_EVIDENCE_INTEGRATED_AND_PUBLISHED'
except BaseException:
 receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
 receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
