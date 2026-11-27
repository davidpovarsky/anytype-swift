import base64, copy, gzip, hashlib, io, json, os, pathlib, subprocess, tarfile, time, traceback
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
HROOT=pathlib.Path('/mnt/development/projects/worktrees/hanlin-pinkha-original-sdk-union-20261127')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
H=['sudo','-n','-u','chatgpt-agent','git','--no-optional-locks','-c','gc.auto=0','-C',str(HROOT)]
P=PRE+['git','--no-optional-locks','-c','gc.auto=0','-C','/mnt/development/projects/git-mirrors/hanlin-ai.git']
START='3559f6010d1ae837d12e4eda9fd7cbcb40870a3d'; OLD='35d26911f70794a41361cee710b1fed24a35e269'; SDK='0ae1920d316b9592cbad0462bea96a07fd1ca351'; SDK_TREE='761851ab3909f8b419a0459a2e4739afa2776f7d'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'; HREF='refs/heads/codex/pinkha-original-sdk-union-20261127'
PIN='Tools/Hanlin/source.json'; MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'; GATE='Tools/AnyEnginePort/verify_source_retention.py'; COMMON='Tools/MiniApps/receipt_admission.py'
TEST='Packages/HanlinPresentationSDK/Tests/HanlinChatUITests/ChatCodeFencePayloadRetentionTests.swift'; HPREFIX='docs/validation/20261127-original-sdk-quota-cache-lifetime'; PREFIX='docs/validation/20261127-wave3-sdk-cache-lifetime'
OUT=pathlib.Path('/tmp/pinkha-root-sdk0ae-integration-20261127.json')
def h(x):return hashlib.sha256(x).hexdigest()
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def q(cmd,*a):return subprocess.check_output(cmd+list(a),stderr=subprocess.PIPE)
def b(*a):return q(G,*a)
def t(*a):return b(*a).decode().strip()
def ht(*a):return q(H,*a).decode().strip()
def pt(*a):return q(P,*a).decode().strip()
def owned(path,data,exclusive=True):
 code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open(sys.argv[2]).write(sys.stdin.buffer.read())'
 subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'xb' if exclusive else 'wb'],input=data,capture_output=True,check=True)
assert not OUT.exists();receipt={'schema':'pinkha-root-sdk0ae-integration/v1','parent':START,'oldSDK':OLD,'selectedSDK':SDK,'startedAt':time.time(),'state':'PREFLIGHT'};OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
 assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF and t('rev-parse','HEAD^{tree}')=='85808b5ab3f9df6607661511e75df26edea344f2'
 assert not t('diff','--name-only') and not t('diff','--cached','--name-only');assert t('ls-remote','origin',REF).split()[0]==START
 status=t('status','--porcelain=v1','--untracked-files=all')
 assert ht('rev-parse','HEAD')==OLD and ht('symbolic-ref','HEAD')==HREF and not ht('diff','--name-only') and not ht('diff','--cached','--name-only')
 hstatus=ht('status','--porcelain=v1','--untracked-files=all');assert pt('ls-remote','origin',HREF).split()[0]==OLD
 assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists() and not pathlib.Path(ht('rev-parse','--git-path','MERGE_HEAD')).exists()
 if subprocess.run(H+['cat-file','-e',SDK+'^{commit}'],capture_output=True).returncode:
  subprocess.run(P+['-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',SDK],capture_output=True,check=True)
 assert ht('rev-parse',SDK+'^')==OLD and ht('rev-parse',SDK+'^{tree}')==SDK_TREE
 sdk_delta=ht('diff','--name-only',OLD,SDK).splitlines();assert len(sdk_delta)==23 and sdk_delta[0]==TEST and all(p.startswith(HPREFIX+'/') for p in sdk_delta[1:])
 oldtest=q(H,'show',OLD+':'+TEST);newtest=q(H,'show',SDK+':'+TEST)
 assert len(oldtest)==7501 and h(oldtest)=='2838bf7cd353b80cea82f72ac30851059d6998728c5ed5876cacafb0a3957d18'
 assert len(newtest)==8535 and h(newtest)=='b4504b8c1c08a6c91204a3c0521f82c64822db4c6f28561f18cdab5d4b534de6' and blob(newtest)=='506bc4a51ad2f78e668d321db139e1c2a9a5d986'
 inverse=json.loads(q(H,'show',SDK+':'+HPREFIX+'/source-inverse-proof.json'));restored=newtest
 for edit in inverse['literalInverseOperations']:
  a,z=edit['after'].encode(),edit['before'].encode();assert restored.count(a)==1;restored=restored.replace(a,z,1)
 assert restored==oldtest and inverse['originalExpectationsRetained']==37 and inverse['additiveExpectations']==2
 unchanged=json.loads(q(H,'show',SDK+':'+HPREFIX+'/unchanged-five-quota-declarations.json'));assert len(unchanged['declarations'])==5
 for row in unchanged['declarations']:
  data=row['originalDeclaration'].encode();assert oldtest.count(data)==newtest.count(data)==1 and h(data)==row['sha256'] and len(data)==row['bytes']
 review=q(H,'show',SDK+':'+HPREFIX+'/root-independent-review.json');assert h(review)=='ce25edd453182683f5eed893dba7a68f29a1ddf8b38974de12ffe1daef90a497'
 before=b('show',START+':'+PIN);source=json.loads(before);assert source['revision']==OLD and before.count(OLD.encode())==1
 after=before.replace(OLD.encode(),SDK.encode(),1);expected=copy.deepcopy(source);expected['revision']=SDK;assert json.loads(after)==expected and after.replace(SDK.encode(),OLD.encode(),1)==before
 assert source['swiftAISDKRevision']=='abf0921c6e89e6521cc2b510ff11016b45a0ef08' and source['minimumIOS']=='27.0'
 packages=source['packages'];assert ht('diff','--name-only',OLD,SDK,'--',*packages).splitlines()==[TEST]
 trees={p:ht('rev-parse',SDK+':'+p) for p in packages}
 for p in packages:
  if p!='Packages/HanlinPresentationSDK':assert ht('rev-parse',OLD+':'+p)==trees[p]
 archive=q(H,'archive','--format=tar',SDK,*packages);files={};total=0
 with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
  for m in bundle:
   p=pathlib.PurePosixPath(m.name.rstrip('/'));assert not p.is_absolute() and '..' not in p.parts and (m.isdir() or m.isfile())
   if m.isfile():
    data=bundle.extractfile(m).read();assert m.name not in files and not data.startswith(b'version https://git-lfs.github.com/spec/v1');files[m.name]=h(data);total+=len(data)
 assert len(files)==1009 and total==39764302
 files={p:files[p] for p in sorted(files,key=pathlib.Path)};marker=(json.dumps({'revision':SDK,'files':files},indent=2)+'\n').encode();assert len(marker)==178454
 oldmarker=b('show',START+':docs/validation/20261127-wave3-sdk35d-common57/expected-original-sdk-marker.json');assert h(oldmarker)=='db6916542999e9f0044479627edd2e2a9c79809dbdbdfe2a8e04d4cfc83be7f3'
 oldfiles=json.loads(oldmarker)['files'];assert oldfiles.keys()==files.keys() and [p for p in files if files[p]!=oldfiles[p]]==[TEST]
 common=b('show',START+':'+COMMON);assert h(common)=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
 map_before=b('show',START+':'+MAP);mv=json.loads(map_before);rows=[r for r in mv['changes'] if r['from']==PIN];assert len(mv['changes'])==129 and len(rows)==1
 row=rows[0];assert row['baselineBlob']=='0ac43dc444fa2234c2eb11fb9bebf129dbe4fb94' and row['replacementBlob']==blob(before);newblob=blob(after);assert map_before.count(blob(before).encode())==1
 map_after=map_before.replace(blob(before).encode(),newblob.encode(),1);em=copy.deepcopy(mv);next(r for r in em['changes'] if r['from']==PIN)['replacementBlob']=newblob;assert json.loads(map_after)==em and map_after.replace(newblob.encode(),blob(before).encode(),1)==map_before
 # Every source admission completed before either owned branch advances.
 q(H,'merge','--ff-only',SDK);assert ht('rev-parse','HEAD')==SDK and ht('status','--porcelain=v1','--untracked-files=all')==hstatus
 hp=subprocess.run(P+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',SDK+':'+HREF],capture_output=True,text=True)
 receipt.update(canonicalSDKPushExit=hp.returncode,canonicalSDKPushStdout=hp.stdout,canonicalSDKPushStderr=hp.stderr)
 assert hp.returncode==0 and pt('ls-remote','origin',HREF).split()[0]==SDK;receipt['canonicalSDKPublished']=SDK
 owned(PIN,after,False);owned(MAP,map_after,False)
 evidence={'expected-original-sdk-marker.json':marker,'root-fixture-review.json':review,'root-integration-controller.py':pathlib.Path(__file__).read_bytes(),'source-inverse-proof.json':q(H,'show',SDK+':'+HPREFIX+'/source-inverse-proof.json'),'unchanged-five-quota-declarations.json':q(H,'show',SDK+':'+HPREFIX+'/unchanged-five-quota-declarations.json')}
 for n,p,sha in [('prior-sdk35d-common57-integration.original.json','/tmp/pinkha-root-sdk35d-common57-integration-20261127.json','c7888c683aa4bc90383663e37182a75548ecb26f1ed7db9bc26d8eab7f6349bd'),('prior-styled51-integration.original.json','/tmp/pinkha-root-styled51-integration-20261127.json','476d9109a1deea00c378378cad8ee5f8fc274aabbb6c09f481463314ced7621e')]:
  data=pathlib.Path(p).read_bytes();assert h(data)==sha;evidence[n]=data
 note={'schema':'pinkha-root-sdk-cache-lifetime-intake/v1','rootParent':START,'oldSDK':OLD,'selectedSDK':SDK,'selectedSDKTree':SDK_TREE,'canonicalSDKFastForward':True,'packageTrees':trees,'solePackageDelta':TEST,'sdkCommitChangedFiles':sdk_delta,'oneFailedMethodFixtureCorrection':True,'twoCompleteLiteralInverses':True,'fiveOtherMethodsByteIdentical':True,'originalExpectationsRetained':37,'additionalLifetimeWitnesses':2,'productionAndNativeAndAllLocksUnchanged':True,'common57GateSHA256':h(common),'materialization':{'files':len(files),'sourceBytes':total,'archiveBytes':len(archive),'archiveSHA256':h(archive),'expectedMarkerBytes':len(marker),'expectedMarkerSHA256':h(marker),'unchangedFiles':1008,'actualFreshMaterialization':False},'pinLiteralInverse':True,'sourceMapChangedField':'Tools/Hanlin/source.json replacementBlob only; all129 baselines/reasons/validations retained','originalRun':{'runID':45963272356,'attempt':1,'controlCommit':'bd41cf7878c5f4df117af7bfcb67636bdff2eafa','overallStatus':'FAIL','quotaMethods':6,'passed':5,'failed':1,'widgetAndIOS':'NOT_REACHED','failedMethod':'cacheEvictionDoesNotFreeInlineOwnershipAndRemountDoesNotDoubleCharge()','failure':'Finalzero observed13bytes/1payload at original line44','sourceEvidencePrefix':HPREFIX},'scope':['A distinct non-inlined actual NSCache lookup scope and ObjectiveC autoreleasepool bound temporary lifetime; weak realBoxnil and positive inline quota are new required runtime witnesses. Cause remains hypothesis until execution.','Five unaffected methods and complete shared production/dependency closure support scoped reuse only after actual original evidence verification. The failed6-method suite stays FAIL.','No production reset/release/sleep, assertion deletion, SDK feature removal, native replacement or existing Dependencies write.','Continuation must run original failed1 plus never-reachedWidget2 and iOS, while retaining original Agent5/7 and five quota passes only where full closure holds.','This integration is not Apple App compilation or Hanlin/MiniApps/Otzaria/ABI/Release/TestFlight acceptance.'],'newTestsExecuted':0,'sourceRetentionExpected':129}
 evidence['root-source-review.json']=(json.dumps(note,indent=2,sort_keys=True)+'\n').encode()
 for n,data in evidence.items():owned(PREFIX+'/'+n,data)
 b('add','--',PIN,MAP,PREFIX);b('diff','--cached','--check');new_paths=sorted([PIN,MAP]+[PREFIX+'/'+n for n in evidence]);assert t('diff','--cached','--name-only').splitlines()==new_paths
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-sdk0ae-retention-20261127.json');assert not gate.exists();run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
 pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr);result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
 message='Pin the original SDK cache lifetime fixture with retained failure evidence\n\nAdvance canonical SDK35d to the single-test0ae successor. Bound actual cache lookup temporaries and require weak cache-owner death plus positive inline ownership before the original zero-charge assertion. Retain all production features and all original expectations; preserve the failed six-method run and exact five-pass evidence. Runtime validation remains separate.\n'
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True);head=t('rev-parse','HEAD');assert t('rev-parse','HEAD^')==START
 assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
 delta=t('diff','--name-only',START,head).splitlines();assert delta==new_paths
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
 receipt.update(head=head,tree=tree,files=delta,pinBeforeGitBlob=blob(before),pinAfterGitBlob=newblob,expectedSDKMarkerSHA256=h(marker),originalPackageFiles=len(files),packageTrees=trees,retentionSHA256=h(gate.read_bytes()),sourceRetentionPassed=True,reviewedRefactors=129,controllerSHA256=h(pathlib.Path(__file__).read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
 if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
 assert push.returncode==0;receipt['state']='SDK0AE_SOURCE_INTEGRATION_PUBLISHED'
except BaseException:
 receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
 receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree'),'expectedSDKMarkerSHA256':receipt.get('expectedSDKMarkerSHA256')}),flush=True)
