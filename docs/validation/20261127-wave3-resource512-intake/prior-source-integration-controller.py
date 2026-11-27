import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='57b7ef615a7db0f95f44acb91857660e24716229'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-native-block-menu-integration.json')
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

import base64, gzip

donor='dc582ba3239d6dcb66dbe1f7098b95349e4289f9';fetch(donor);parent=t('rev-parse','HEAD')
preview=t('merge-tree','--write-tree',parent,donor)
assert preview=='40fc4951f69625867300120a6127bd5a9b9ae9dd'
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==30 and all(mode in {'A','M'} for mode,_ in rows)
assert t('diff','--name-only',parent,preview).splitlines()==sorted(p for _,p in rows)
for mode,path in rows:
    if mode=='M':assert b('show','HEAD:'+path)==b('show',donor+'^:'+path),path
    else:assert not (ROOT/path).exists(),path
for path,data in PINNED.items():assert b('show',preview+':'+path)==data,path

source_prefix='docs/validation/20261127-wave2-native-block-creation/'
proof=json.loads(b('show',donor+':'+source_prefix+'source-proof.json'))
assert proof['baseCommit']=='8f2c11713fb8a40ae13444104723666ffef68afe'
assert proof['AppleCompilation']==proof['UIVisual']==proof['native8acRuntime']=='NOT_RUN'
assert len(proof['files'])==6 and proof['componentMethods']==2
for row in proof['files']:
    data=b('show',donor+':'+row['path']);assert h(data)==row['sha256'] and len(data)==row['bytes'],row['path']
for row in proof['sourceRefactorEntries']:
    # These are reviews relative to 8f2, not baseline586c original upstream mappings.
    assert t('rev-parse','HEAD:'+row['from'])==row['baselineBlob']
    assert t('rev-parse',donor+':'+row['to'])==row['replacementBlob']
    assert not t('ls-tree','586c98bcc17dee425664224e508fc0e8df277678','--',row['from'])
    for shared in row['sharedSources']:assert t('rev-parse',donor+':'+shared['path'])==shared['gitBlob']
original_map=b('show','HEAD:'+MAP);mapping=json.loads(original_map)
assert len(mapping['changes'])==129
assert not any(r['to'] in {x['to'] for x in proof['sourceRefactorEntries']} for r in mapping['changes'])

receipt_bytes=b('show',donor+':'+source_prefix+'component-attempt1/receipt.json')
assert h(receipt_bytes)=='bbf101c3821fafca51f6d6e9a0bef009f1f415ff935ab4e2606ca0feb599e231'
receipt=json.loads(receipt_bytes)
assert receipt['status']=='PASS_COMPONENT_2_METHODS_NOT_APP_OR_NATIVE_ACCEPTANCE' and receipt['processExit']==0
assert len(receipt['observedTestPassLines'])==2 and not receipt['sourceTransformations'] and not receipt['dependencyTransformations']
assert receipt['runnerSHA256']=='dd2d6047f4affbe17b18600daf7638ea154bb447df9167c3cd288637fcd9c7c4'
assert h(b('show',donor+':Tools/PinkhaDualEngineRuntime/native_block_creation/run_component_tests.py'))==receipt['runnerSHA256']
verified_artifacts=[]
for row in receipt['artifacts']:
    name=pathlib.Path(row['path']).name
    stored=source_prefix+'component-attempt1/'+name
    data=gzip.decompress(b('show',donor+':'+stored+'.gz')) if name=='stderr.log' else b('show',donor+':'+stored)
    assert h(data)==row['sha256'] and len(data)==row['bytes'],name
    verified_artifacts.append({'name':name,'sha256':h(data),'bytes':len(data)})
assert len(verified_artifacts)==8
assert b('show',donor+':'+source_prefix+'component-attempt1/dependency-sources-before.json')==b('show',donor+':'+source_prefix+'component-attempt1/dependency-sources-after.json')

payload_path=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-native-block-review-payload.json')
payload=json.loads(payload_path.read_bytes());assert len(payload)==4
expected={
 'independent-six-source-and-component-review.json':'78fee375d3992ea798685c92f62c6f871d486d813c7de0162a08860b6caa93c4',
 'original-readonly-dependency-audit.json':'f88f8b379ae4afd92de5a4de36294411233d4e54ec8545b9a51553b45e97c2ad',
 'save-runtime-matrix.md':'7561ded2f777c26a784ac0405100f7a7a8bbd5a8139ee9d20ce9f22ec75d7e62',
 'selected-save-source-test-methods.json':'51d8963702f569a730ba317e828665466aa4be9262c548ea751aaec919296c24'}
assert set(payload)==set(expected)
proofs={name:base64.b64decode(value) for name,value in payload.items()}
for name,data in proofs.items():assert h(data)==expected[name],name
independent=json.loads(proofs['independent-six-source-and-component-review.json'])
assert independent['commit']==donor and independent['originalEightArtifactHashesMatch'] and independent['readonlyOriginalDependencyAudit']['result']['closedFileCount']==370
prior=pathlib.Path('/tmp/pinkha-wave3-local-readiness-integration.json').read_bytes()
assert h(prior)=='ac3c1ca0f42839bba6726c07ccdf63a6715f2ac50fafde20b5d4595d3b07f7e9'
assert json.loads(prior)['head']==parent
prior_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-local-readiness-integration-e0d64c17c5dc.py').read_bytes()
assert h(prior_controller)=='e0d64c17c5dc839d22ff64a56fdf311f7cc6250d54a5a17323dad104d5551b78'
proofs['prior-integration-receipt.json']=prior
proofs['prior-integration-controller.py']=prior_controller

b('merge','--no-ff','--no-commit',donor);assert t('write-tree')==preview
for _,path in rows:assert (ROOT/path).read_bytes()==b('show',donor+':'+path),path
assert (ROOT/MAP).read_bytes()==original_map
prefix='docs/validation/20261127-wave3-native-block-menu-intake';extras=[]
for name,data in proofs.items():
    path=prefix+'/'+name;owned(path,data);extras.append(path)
note=prefix+'/root-review.json'
owned(note,(json.dumps({
 'rootParent':parent,'candidate':donor,'mergePreview':preview,
 'allSixSwiftDiffsAndFullComponentRunnerReviewed':True,
 'originalGuardedCreationRetained':'Paragraph and Inspector quote keep exact style, escaping, writing direction, placement and original mount/flush/lease/writer/owner/journal/readback/focus path. Nine native kinds use the same path; no native or Host contract changed.',
 'componentEvidence':{'receiptSHA256':h(receipt_bytes),'methods':2,'artifacts':verified_artifacts,'sourceClosureFiles':370,'sourceClosureCommit':proof['baseCommit'],'AppleUIFilesExcluded':4,'Crypto':'3.12.3','ASN1':'1.7.5','TorahInspectorKit':'9058b489e9acc271b4f8ef69e2ed24648f93b4ed','AppleLockEquality':False},
 'sourceMapDisposition':'Three donor entries describe downstream edits relative to8f2. These files are absent from the original586c upstream baseline, so they must not be appended as original-baseline mappings. All129 existing mappings and verifier bytes stay unchanged; the donor entries remain retained as local source review evidence.',
 'reviewedDownstreamEntries':proof['sourceRefactorEntries'],
 'existingRendererLimitation':'Heading levels still share the existing title2 base font and code starts at existing body font; typography work is separate and pending.',
 'retainedSaveRuntimeSpecification':'97 authored source methods, not compiled discovery; all new native/UI Save execution pending. The subsequently planned shared editor entry is async throws under the original native lease; no synchronous fixture admission is implied by this historical matrix.',
 'newCompilerOrNativeRuns':0,'native8acMenuFocusColdVisual':'NOT_RUN','AppleCompilation':'NOT_RUN',
 'macFrozenSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe'
},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix);finish(parent,donor,'native-block-menu-and-component-evidence',[p for _,p in rows]+extras)
