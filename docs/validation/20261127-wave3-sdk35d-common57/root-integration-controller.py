import ast, base64, copy, gzip, hashlib, io, json, os, pathlib, subprocess, tarfile, time, traceback
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
H=['sudo','-n','-u','chatgpt-agent','git','--no-optional-locks','-c','gc.auto=0','-C','/mnt/development/projects/worktrees/hanlin-pinkha-original-sdk-union-20261127']
START='6e3e25194bca7b117989135f3cc4c6d2dd1cf878'; DONOR='a8ae5032d3286706416586bb58ccbe3c130b785c'; OLD='caa0dac32afa18e58bba55fb4f0fdd262f181835'; SDK='35d26911f70794a41361cee710b1fed24a35e269'; SDK_TREE='e982eb1e5f4bb6759b8c18663b716abee65b6cc4'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'; PIN='Tools/Hanlin/source.json'; MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'; GATE='Tools/AnyEnginePort/verify_source_retention.py'; COMMON='Tools/MiniApps/receipt_admission.py'; PREFIX='docs/validation/20261127-wave3-sdk35d-common57'
OUT=pathlib.Path('/tmp/pinkha-root-sdk35d-common57-integration-20261127.json')
def h(b):return hashlib.sha256(b).hexdigest()
def blob(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
def q(cmd,*a):return subprocess.check_output(cmd+list(a),stderr=subprocess.PIPE)
def b(*a):return q(G,*a)
def t(*a):return b(*a).decode().strip()
def owned(path,data,exclusive=True):
 code='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open(sys.argv[2]).write(sys.stdin.buffer.read())'
 subprocess.run(PRE+['python3','-B','-c',code,str(ROOT/path),'xb' if exclusive else 'wb'],input=data,capture_output=True,check=True)
def declarations(data):
 s=data.decode();tree=ast.parse(s);return {n.name:ast.get_source_segment(s,n) for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef))}
assert not OUT.exists();receipt={'schema':'pinkha-root-sdk35d-common57-integration/v1','parent':START,'donor':DONOR,'sdkRevision':SDK,'startedAt':time.time(),'state':'PREFLIGHT'};OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
 assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
 assert not t('diff','--name-only') and not t('diff','--cached','--name-only')
 assert not pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).exists()
 status=t('status','--porcelain=v1','--untracked-files=all');assert t('ls-remote','origin',REF).split()[0]==START
 free=os.statvfs(ROOT);receipt['developmentFreeBytesBefore']=free.f_bavail*free.f_frsize
 if subprocess.run(G+['cat-file','-e',DONOR+'^{commit}'],capture_output=True).returncode:
  subprocess.run(G+['-c','credential.helper=!gh auth git-credential','fetch','--no-tags','--refmap=','origin',DONOR],capture_output=True,check=True)
 assert t('rev-parse',DONOR+'^')==START and t('rev-parse',DONOR+'^{tree}')=='3e53c9675b3ab8d1c0dd860f51681fd73a7e4d98'
 donor_paths=t('diff','--name-only',START,DONOR).splitlines();assert len(donor_paths)==8 and donor_paths[0]==COMMON and all(p.startswith('docs/validation/20261127-wave3-receipt57/') for p in donor_paths[1:])
 inv=json.loads(b('show',DONOR+':docs/validation/20261127-wave3-receipt57/source-inverse.json'));oldgate=b('show',START+':'+COMMON);newgate=b('show',DONOR+':'+COMMON)
 assert h(oldgate)=='9ce1288feb8f3c534bb7eb784909624fc66168473e93eedff2f2945583d6a18d' and h(newgate)=='d63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
 a,z=inv['edit']['after'].encode(),inv['edit']['before'].encode();assert newgate.count(a)==1 and newgate.replace(a,z,1)==oldgate
 assert newgate==b('show',START+':Tools/CurrentAppleValidation/combined_heart_semantics/wave2/native-core-hosted/receipt_admission_native_core.py')
 assert declarations(oldgate)==declarations(newgate) and len(declarations(newgate))==16
 assert q(H,'rev-parse','HEAD').decode().strip()==SDK and q(H,'rev-parse',SDK+'^{tree}').decode().strip()==SDK_TREE and q(H,'rev-parse',SDK+'^').decode().strip()==OLD
 before=b('show',START+':'+PIN);assert blob(before)=='d5ecbc7a644e20a1da96f9c1cbced6906819d481' and before.count(OLD.encode())==1
 after=before.replace(OLD.encode(),SDK.encode(),1);source=json.loads(before);expected=copy.deepcopy(source);expected['revision']=SDK;assert json.loads(after)==expected and after.replace(SDK.encode(),OLD.encode(),1)==before
 assert source['swiftAISDKRevision']=='abf0921c6e89e6521cc2b510ff11016b45a0ef08' and source['minimumIOS']=='27.0'
 trees={'Packages/HanlinAgentSDK':'bbe6a0e4387f3f33d6592e24c1927182a1aceb22','Packages/HanlinPlatform':'db6e9533242f08bb1bb7accdf6970a436aa953d1','Packages/HanlinPresentationSDK':'d45cd087e058be46a37ff7669f5bd33399dada15','Packages/HanlinMiniAppsBridge':'98ef5d2b47c03f4ea98319a851abae183f500a40'}
 assert set(source['packages'])==set(trees)
 for p,tree in trees.items():assert q(H,'rev-parse',SDK+':'+p).decode().strip()==tree
 changed_test='Packages/HanlinPresentationSDK/Tests/HanlinChatUITests/ChatCodeFencePayloadRetentionTests.swift'
 assert q(H,'diff','--name-only',OLD,SDK,'--',*source['packages']).decode().splitlines()==[changed_test]
 test=q(H,'show',SDK+':'+changed_test);assert len(test)==7501 and h(test)=='2838bf7cd353b80cea82f72ac30851059d6998728c5ed5876cacafb0a3957d18'
 archive=q(H,'archive','--format=tar',SDK,*source['packages']);files={};total=0
 with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
  for m in bundle:
   p=pathlib.PurePosixPath(m.name.rstrip('/'));assert not p.is_absolute() and '..' not in p.parts and (m.isdir() or m.isfile())
   if m.isfile():
    data=bundle.extractfile(m).read();assert m.name not in files and not data.startswith(b'version https://git-lfs.github.com/spec/v1');files[m.name]=h(data);total+=len(data)
 assert len(files)==1009 and total==39763268
 files={p:files[p] for p in sorted(files,key=pathlib.Path)};marker=(json.dumps({'revision':SDK,'files':files},indent=2)+'\n').encode();assert len(marker)==178454 and h(marker)=='db6916542999e9f0044479627edd2e2a9c79809dbdbdfe2a8e04d4cfc83be7f3'
 oldmarker=b('show',START+':docs/validation/20261127-wave3-original-sdk-consumer-pin/expected-original-sdk-marker.json');assert h(oldmarker)=='2733c88978c7a6404e31c502468b879c9451fe612d4660088ee34b597968c26f';oldfiles=json.loads(oldmarker)['files'];assert oldfiles.keys()==files.keys() and [p for p in files if files[p]!=oldfiles[p]]==[changed_test]
 map_before=b('show',START+':'+MAP);mv=json.loads(map_before);rows=[r for r in mv['changes'] if r['from']==PIN];assert len(mv['changes'])==129 and len(rows)==1
 row=rows[0];assert row['baselineBlob']=='0ac43dc444fa2234c2eb11fb9bebf129dbe4fb94' and row['replacementBlob']==blob(before);newblob=blob(after);assert map_before.count(blob(before).encode())==1
 map_after=map_before.replace(blob(before).encode(),newblob.encode(),1);em=copy.deepcopy(mv);next(r for r in em['changes'] if r['from']==PIN)['replacementBlob']=newblob;assert json.loads(map_after)==em and map_after.replace(newblob.encode(),blob(before).encode(),1)==map_before
 allpaths=t('ls-tree','-r','--name-only',START).splitlines();protected=[p for p in allpaths if p.endswith('/Package.resolved') or p.endswith('.pbxproj') or p.startswith('AnyTypeTests/Pinkha/') and p.endswith('.swift') or p.startswith('NativeApp/UITests/') and p.endswith('.swift')]
 protected+=inv['addedExactPaths']+[GATE,'Tools/Hanlin/prepare_sdk.py','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json']
 preserved={p:b('show',START+':'+p) for p in set(protected)};assert h(preserved['Tools/Hanlin/prepare_sdk.py'])=='234f597c629da30045392f74e2b6d204f2bbc6349b70bdccd5562dc0db491fe2'
 payload=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-sdk35d-common57-evidence.json.gz').read_bytes();assert h(payload)=='50fc8f231cdfa2dac164a309e0e36ae5521bf97e0facc58e8af91f8b316e2d3e';entries=json.loads(gzip.decompress(payload));evidence={}
 for n,v in entries.items():
  assert pathlib.PurePosixPath(n).name==n;data=base64.b64decode(v['base64']);assert h(data)==v['sha256'] and len(data)==v['bytes'];evidence[n]=data
 for n,p,sha in [('prior-properties-core-page-integration.original.json','/tmp/pinkha-root-wave2-properties-core-page-integration-resume1.json','b2453de279dd61da116ccf90c69664b37f1885dacfec090e0cb06f3e979f6a14'),('canonical-sdk-publication.original.json','/tmp/pinkha-root-hanlin-quota-test-source-fastforward-20261127.json','07123475814acf33741ae16337d2eb9fbee867f1385337b9502d205087e67371')]:
  data=pathlib.Path(p).read_bytes();assert h(data)==sha;evidence[n]=data
 # All admissions complete before the owned final branch advances.
 b('merge','--ff-only',DONOR);assert t('rev-parse','HEAD')==DONOR
 owned(PIN,after,False);owned(MAP,map_after,False)
 evidence['expected-original-sdk-marker.json']=marker;evidence['root-integration-controller.py']=pathlib.Path(__file__).read_bytes()
 note={'schema':'pinkha-root-sdk35d-common57-review/v1','rootParent':START,'commonDonor':DONOR,'commonSHA256':h(newgate),'commonExactExistingDerivedBytes':True,'commonThreePathInverse':True,'all16DeclarationBytesPreserved':True,'originalSDK':OLD,'selectedSDK':SDK,'selectedSDKTree':SDK_TREE,'packageTrees':trees,'solePackageDelta':changed_test,'sourceOnlyTestMacroFix':True,'nativeAndLocksUnchanged':True,'materialization':{'files':len(files),'sourceBytes':total,'archiveBytes':len(archive),'archiveSHA256':h(archive),'expectedMarkerBytes':len(marker),'expectedMarkerSHA256':h(marker),'unchangedFiles':1008,'actualFreshMaterialization':False},'pinLiteralInverse':True,'sourceMapChangedField':'Tools/Hanlin/source.json replacementBlob only; all129 baselines/reasons/validations retained','scope':['Original six quota methods and37 expectations preserve all16 ordered retain calls; nine mutating calls are evaluated once outside Swift Testing macros. No production API or capability changed.','Common gate lists exactly57 native Swift inputs:50 original AnyTypeTests/Pinkha plus7 originals. All canonical-path/source/compiler/receipt validators unchanged. Old closed consumer profiles and nativeCore runtime rejection remain untouched.','SDK hosted continuation45963272356/attempt1/controlbd41 runs original quota6/Widget2/iOS on35d and reuses source-identical original Agent5/7 proof. Dispatch is not acceptance.','This source commit is not Apple App compilation or MiniApps/Hanlin/Otzaria/ABI/Release/TestFlight acceptance. Existing Dependencies snapshots and all required entitlements remain untouched.'],'newTestsExecuted':0,'sourceRetentionExpected':129}
 evidence['root-source-review.json']=(json.dumps(note,indent=2,sort_keys=True)+'\n').encode()
 for n,data in evidence.items():owned(PREFIX+'/'+n,data)
 b('add','--',PIN,MAP,PREFIX);b('diff','--cached','--check');new_paths=sorted([PIN,MAP]+[PREFIX+'/'+n for n in evidence]);assert t('diff','--cached','--name-only').splitlines()==new_paths
 for p,data in preserved.items():assert (ROOT/p).read_bytes()==data,p
 assert (ROOT/COMMON).read_bytes()==newgate
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-sdk35d-common57-retention-20261127.json');assert not gate.exists();run=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True)
 pathlib.Path(str(gate)+'.stdout').open('xb').write(run.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(run.stderr);result=json.loads(gate.read_bytes());assert run.returncode==0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors'])==129
 message='Bind the shared SDK quota test fix and 57 original test inputs\n\nFast-forward the exact three-path common receipt allowlist, retaining every validator. Pin both engine consumers to original Hanlin35d, whose sole package change evaluates nine mutating test calls before Swift Testing macros. Preserve all production code, native/lock pins and existing materializations; retain full source and original failed-run evidence. Runtime acceptance remains separately required.\n'
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True);head=t('rev-parse','HEAD');assert t('rev-parse','HEAD^')==DONOR
 assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
 delta=t('diff','--name-only',START,head).splitlines();assert delta==sorted(set(donor_paths+new_paths))
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True)
 receipt.update(head=head,tree=tree,files=delta,pinBeforeGitBlob=blob(before),pinAfterGitBlob=newblob,expectedSDKMarkerSHA256=h(marker),originalPackageFiles=len(files),retentionSHA256=h(gate.read_bytes()),sourceRetentionPassed=True,reviewedRefactors=129,controllerSHA256=h(pathlib.Path(__file__).read_bytes()),pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0,protectedSourceFiles=len(preserved))
 if push.returncode==0:assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
 assert push.returncode==0;receipt['state']='SDK35D_COMMON57_PUBLISHED'
except BaseException:
 receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
 receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
