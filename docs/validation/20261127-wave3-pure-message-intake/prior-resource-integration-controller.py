import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='cbaf6cdc2caf6c503c730a3cda05354f71b61369'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-resource512-integration.json')
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

import ast, base64

donor='ac606cc0add9a861ed02edb38af956924e7b017c';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==36 and all(mode=='A' and not (ROOT/path).exists() for mode,path in rows)
source='Tools/CurrentAppleValidation/combined_heart_semantics/wave2/wave3-warm-resource512/'
proofs='docs/validation/20261127-wave2-warm-resource512/'
oldsource='Tools/CurrentAppleValidation/combined_heart_semantics/wave2/wave3-warm-staged/'
new=b('show',donor+':'+source+'wave3_intake.py').decode()
old=b('show','HEAD:'+oldsource+'wave3_intake.py').decode()
inverse=json.loads(b('show',donor+':'+proofs+'resource-successor-inverse.json'))
assert h(new.encode())==inverse['fragmentSHA256']=='cd66d442acccbbc29758561f771a565f73a6fc2e805db65f6f0ea36dba9eb27b'
assert h(old.encode())==inverse['priorFragmentSHA256']=='f097cdb1a12087475cda0728d34d7a7dcb2ef0d62ad67810fd9724d11d096bfa'
restored=new
for row in reversed(inverse['changes']):
    start=row['newOffset'];end=start+len(row['new']);assert restored[start:end]==row['new'];restored=restored[:start]+row['old']+restored[end:]
assert restored==old
def defs(s):return {n.name:ast.get_source_segment(s,n) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
a,c=defs(old),defs(new)
assert [name for name in a if a[name]!=c[name]]==['w3_stage_proof']
assert [name for name in c if name not in a]==['w3_resource512_delta','w3_resource512_restore_admission']
assert len([name for name in a if a[name]==c[name]])==14
newmat=b('show',donor+':'+source+'materialize_wave3_intake.py')
oldmat=b('show','HEAD:'+oldsource+'materialize_wave3_intake.py')
assert newmat.replace(inverse['fragmentSHA256'].encode(),inverse['priorFragmentSHA256'].encode())==oldmat
handoff=json.loads(b('show',donor+':'+proofs+'handoff.json'))
assert handoff['readyForRuntimeAdmission'] is False and handoff['actualProductAdmitted'] is False
for key in ['actualApprovedAdmissionSHA256','actualExecutedProducerDeltaSHA256','actualExecutedProducerSHA256']:assert handoff[key] is None
for name,row in handoff['preparedFiles'].items():
    if name in {'wave3_intake.py','materialize_wave3_intake.py','frozen-profile.resource512.closed.json','test_resource512_intake.py'}:path=source+name
    elif name=='materialized-closed1/materialization.json':path=proofs+'closed-materialization.json'
    else:path=proofs+name
    data=b('show',donor+':'+path);assert h(data)==row['sha256'] and len(data)==row['bytes'],path
profile=json.loads(b('show',donor+':'+source+'frozen-profile.resource512.closed.json'))
assert profile['readyForRuntimeAdmission'] is False
for key in ['buildAdmission','builder','builderDelta']:assert profile['evidence']['app16Producer'][key] is None
retained=[]
for folder,namekey in [('actual-inputs','name'),('retained-originals','localName')]:
    custody=json.loads(b('show',donor+':'+proofs+folder+'/custody.json'))
    for row in custody:
        data=b('show',donor+':'+proofs+folder+'/'+row.get('storedName',row[namekey]))
        if row.get('storageEncoding')=='base64-json':
            wrapped=json.loads(data);data=base64.b64decode(wrapped['data'],validate=True)
            assert wrapped['sha256']==row['sha256'] and wrapped['bytes']==row['bytes']
        assert len(data)==row['bytes'] and h(data)==row['sha256'],row['path']
        retained.append({'path':row['path'],'sha256':h(data),'bytes':len(data)})
assert len(retained)==19
portable=json.loads(b('show',donor+':'+proofs+'portable-controls-attempt2.json'))
portable_log=b('show',donor+':'+proofs+'portable-controls-attempt2.log')
assert portable['exitCode']==0 and portable['fragmentSHA256']==inverse['fragmentSHA256']
assert h(portable_log)==portable['logSHA256']=='8957cc0ff667b4b351bd7a32b82e1976e4f15fe29f0aa152198aeb799d99b310'
assert portable_log.count(b' ... ok\n')==5 and b'Ran 5 tests in ' in portable_log and portable_log.endswith(b'\nOK\n')
assert h(b('show',donor+':'+source+'test_resource512_intake.py'))==portable['testSourceSHA256']
for name,row in handoff['independentReview'].items():
    data=b('show',donor+':'+proofs+name);assert h(data)==row['sha256'] and len(data)==row['bytes']
original_map=b('show','HEAD:'+MAP)
payload_raw=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-resource512-review-payload.json').read_bytes()
assert h(payload_raw)=='bf653615114f09924a860c695dc1fe6b24fd345e2cbe58007ce045199ed3dff0'
payload=json.loads(payload_raw);assert len(payload)==8
files={}
for name,row in payload.items():
    data=base64.b64decode(row['base64'],validate=True);assert len(data)==row['bytes'] and h(data)==row['sha256'];files[name]=data
assert h(files['root-resource-intake-review.json'])=='bfc4271ae38f83d6ba4c0e5629a61fac9f147a1d04c2084bb756b7ca67960f27'
prior=pathlib.Path('/tmp/pinkha-wave3-native-block-menu-integration.json').read_bytes()
assert h(prior)=='892ad4a1065c21173198da0e015e1e243d7b9edd653f752a351b0fe73bc25b06' and json.loads(prior)['head']==parent
prior_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-native-block-menu-e2d81e714f79.py').read_bytes()
assert h(prior_controller)=='e2d81e714f797cba3d00213f1f48d2183f0009fbac06231a28b5e8234d0c1010'
files['prior-source-integration-receipt.json']=prior;files['prior-source-integration-controller.py']=prior_controller
files['root-resource-metadata-custody.json']=(json.dumps({'candidate':donor,'exactRetainedOriginals':retained,'newMacReads':0,'newRuntimeAdmission':False,'unchangedOriginalBaselineMappings':129,'noTestsRepeated':True},indent=2,sort_keys=True)+'\n').encode()
b('cherry-pick','-x','--no-commit',donor)
for _,path in rows:assert (ROOT/path).read_bytes()==b('show',donor+':'+path),path
assert (ROOT/MAP).read_bytes()==original_map
prefix='docs/validation/20261127-wave3-resource512-intake';extras=[]
for name,data in files.items():
    path=prefix+'/'+name;owned(path,data);extras.append(path)
b('add','--',prefix);finish(parent,donor,'closed-resource512-intake-with-actual-refusals',[path for _,path in rows]+extras)
