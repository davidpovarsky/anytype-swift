import base64,hashlib,json,gzip,pathlib,subprocess,time,traceback
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','--no-optional-locks','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='ba7d491211f13984795df8c6ddfcc74e19a3963e'
DONORS=['54079356628487f7ecedf5cfe87434c8cc57ea36','897687a02defdc8a69603a5a27c561839db26bf4']
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX='docs/validation/20261127-wave3-properties-core-page-intake'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json';GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-root-wave2-properties-core-page-integration-resume1.json')
def h(x):return hashlib.sha256(x).hexdigest()
def b(*a):return subprocess.check_output(G+list(a),stderr=subprocess.PIPE,timeout=90)
def t(*a):return b(*a).decode().strip()
def owned(path,data):
 c='import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
 subprocess.run(PRE+['python3','-B','-c',c,str(ROOT/path)],input=data,capture_output=True,check=True,timeout=30)
assert not OUT.exists()
receipt={'schema':'pinkha-root-wave2-properties-core-page-source-integration/v1','parent':START,'donors':DONORS,'startedAt':time.time(),'state':'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt,indent=2)+'\n')
try:
 failed_path=pathlib.Path('/tmp/pinkha-root-wave2-properties-core-page-integration.json')
 failed_bytes=failed_path.read_bytes();assert h(failed_bytes)=='d66f6de34627ca3ee3c1f6347df8cbe05b65064d2839fc33f7436abf88dbda13'
 failed=json.loads(failed_bytes);assert failed['state']=='FAILED_PRESERVED' and failed['error'].endswith("KeyError: 'sha256'\n")
 original_controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-wave2-properties-core-page-integration.py').read_bytes();assert h(original_controller)=='c666ae12c7f86df00201394fc63c81ec1ed67c4d6ddcb4f892bc4516dbe01251'
 plan_bytes=pathlib.Path('/tmp/pinkha-root-wave2-properties-core-page-source-plan-20261127.json').read_bytes()
 assert h(plan_bytes)=='15ab29d47548018a7467981301cad574e2eb30f8b8e3fb579a0b971dd762a1d5'
 plan=json.loads(plan_bytes);assert plan['base']==START and [d['sha'] for d in plan['donors']]==DONORS and len(plan['files'])==87
 packed=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-wave2-properties-core-page-evidence.json.gz').read_bytes()
 assert h(packed)=='eba9a16e2f67a027da4adc056dd73055dfe1a9b350b4a811ea00b38bfcaa1e54'
 payload=json.loads(gzip.decompress(packed));assert payload['parent']==START and len(payload['files'])==13
 extras={}
 for row in payload['files']:
  path=pathlib.PurePosixPath(row['path']);assert not path.is_absolute() and '..' not in path.parts and str(path) not in extras
  value=base64.b64decode(row['base64'],validate=True);assert len(value)==row['bytes'] and h(value)==row['sha256'];extras[str(path)]=value
 assert h(extras['core-properties/independent-review.json'])=='43d61930fd4fa6fabd3d384d05d839075ce58e22eb7bb84c142b442ad4263322'
 assert h(extras['page154-root-independent-review.json'])=='44c2815e06fdc855e954ff934c3a9f21a52c0b15924744d3c55ffaee15d2ebd4'
 assert h(extras['page154-original-timeout/original-result.json'])=='bcfa06bea94cc0ce89541dc3e165160d6574ce1c9f551c56857102a24d00a5e0'
 assert t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
 assert not t('diff','--name-only')
 assert pathlib.Path(t('rev-parse','--git-path','MERGE_HEAD')).read_text().splitlines()==DONORS
 assert t('write-tree')=='332dc530892b38d6288ce2b3db0d586c0457f7d9'
 assert t('diff','--cached','--name-status').splitlines()==[r['status']+'\t'+r['path'] for r in plan['files']]
 status='\n'.join(line for line in t('status','--porcelain=v1','--untracked-files=all').splitlines() if line.startswith('?? '))
 assert len(status.splitlines())==4 and t('ls-remote','origin',REF).split()[0]==START
 for donor in plan['donors']:
  assert t('rev-parse',donor['sha']+'^{tree}')==donor['tree'] and t('merge-base',START,donor['sha'])==donor['mergeBase']
  preview=subprocess.run(G+['merge-tree','--write-tree',START,donor['sha']],capture_output=True,text=True,timeout=60)
  assert preview.returncode==0 and len(preview.stdout.strip())==40
  delta=t('diff','--name-status',START,preview.stdout.strip()).splitlines()
  assert delta==[r['status']+'\t'+r['path'] for r in plan['files'] if r['donor']==donor['sha']]
 for row in plan['files']:
  p=row['path'];data=b('show',row['donor']+':'+p)
  assert len(data)==row['bytes'] and h(data)==row['sha256'] and t('rev-parse',row['donor']+':'+p)==row['blob']
  if row['status']=='A':assert (ROOT/p).is_file()
  else:
   assert row['status']=='M' and p in ['Anytype.xcodeproj/project.pbxproj','Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertyPresentation.swift','Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift']
   assert h(b('show',START+':'+p))==row['beforeSHA256'] and t('rev-parse',START+':'+p)==row['beforeBlob']
  assert (ROOT/p).read_bytes()==data
 identities=json.loads(extras['core-properties/primary-source-identities.json']);assert len(identities)==97
 for row in identities:
  data=b('show',row['ref']+':'+row['path']);assert len(data)==row['bytes'] and h(data)==row['sha256'] and t('rev-parse',row['ref']+':'+row['path'])==row['gitBlob']
 closed='Tools/CurrentAppleValidation/combined_heart_semantics/wave2/page154-future-intake/prepare_wave2_page154_shared_profile_closed.py'
 inv=json.loads(b('show',DONORS[1]+':docs/validation/20261127-wave2-page154-closed-intake/source-inverse.json'))
 restored=b('show',DONORS[1]+':'+closed).decode();assert h(restored.encode())==inv['candidateSHA256']=='0893c414fb7bacde191679df7cde048235463413832b3937d43553d20c786789'
 for row in reversed(inv['edits']):assert restored.count(row['after'])==1;restored=restored.replace(row['after'],row['before'],1)
 assert restored.encode()==b('show',inv['originalCommit']+':'+inv['originalPath']) and h(restored.encode())==inv['originalSHA256']
 preserved_paths=[MAP,GATE,'Tools/Hanlin/source.json','Tools/Hanlin/prepare_sdk.py','Tools/PinkhaDualEngineRuntime/source-permission-manifest.json','NativeApp/UITests/NativeLaunchTests.swift']
 preserved_paths += [p for p in t('ls-tree','-r','--name-only',START).splitlines() if p.endswith('/Package.resolved') or (p.endswith('.pbxproj') and p!='Anytype.xcodeproj/project.pbxproj')]
 preserved={p:b('show',START+':'+p) for p in preserved_paths}
 receipt['continuedOriginalMerge']=failed['merge'];assert failed['merge']['exit']==0
 receipt['originalFailureSHA256']=h(failed_bytes)
 assert not t('ls-files','-u') and t('write-tree')=='332dc530892b38d6288ce2b3db0d586c0457f7d9'
 assert t('diff','--cached','--name-status').splitlines()==[r['status']+'\t'+r['path'] for r in plan['files']]
 for row in plan['files']:assert (ROOT/row['path']).read_bytes()==b('show',row['donor']+':'+row['path'])
 future=json.loads(extras['core-properties/future-57-native-source-inventory.json']);assert len(future['rows'])==57 and future['base']==START
 qualified_inputs=[]
 for row in future['rows']:
  value=(ROOT/row['path']).read_bytes();assert len(value)==row['bytes']
  assert value==b('show',row['ref']+':'+row['path']) and t('rev-parse',row['ref']+':'+row['path'])==row['gitBlob']
  assert hashlib.sha1(b'blob '+str(len(value)).encode()+b'\0'+value).hexdigest()==row['gitBlob']
  if 'sha256' in row:assert h(value)==row['sha256']
  qualified_inputs.append({'path':row['path'],'bytes':len(value),'sha256':h(value),'gitBlob':row['gitBlob'],'originalRef':row['ref']})
 assert len(qualified_inputs)==57
 extras['exact-staged-native-source-inputs.json']=(json.dumps({'status':'SOURCE_BYTES_VERIFIED_NOT_COMPILER_ACCEPTANCE','stagedSourceTree':'332dc530892b38d6288ce2b3db0d586c0457f7d9','rows':qualified_inputs},indent=2,sort_keys=True)+'\n').encode()
 extras['original-intake-failure.json']=failed_bytes
 extras['original-intake-controller.py']=original_controller
 assert len(list((ROOT/'AnyTypeTests/Pinkha').glob('*.swift')))==50 and len(list((ROOT/'PinkhaStage1Acceptance/Tests').glob('*.swift')))==10
 prior=pathlib.Path('/tmp/pinkha-root-network-restore-source-integration.json').read_bytes();assert h(prior)=='150b20ace8878bf23f9db9e0c25321378e9079a3ebcff09a53b02332b9ebe68b' and json.loads(prior)['head']==START
 preview_bytes=pathlib.Path('/tmp/pinkha-root-new-wave2-three-source-preview-no-fetch-20261127.json').read_bytes();assert h(preview_bytes)=='2111d01e74e4eaaa430c2e3331eb083803d9ee2414d645547f7f5a89f7578721'
 note={'schema':'pinkha-wave3-root-properties-core-page-review/v1','base':START,'donors':DONORS,'originalReviewedPaths':87,'sourceReview':'ACCEPTED_SOURCE_ONLY','nativeSourceFiles':57,'stage1UISourceFiles':10,'nativeLaunch23Separate':True,'review':[
  'Root read the exact three-file production/project delta and original peer review. Properties clears displayed snapshot and Undo on current owned read failure/deactivation, preserving pending uncertain write, read/write authority, epochs and explicit reconciliation. Original seven test methods remain with one corrected expectation and two new methods; no test execution is inferred.',
  'Exactly three original package source files are directly registered in AnytypeTests and the existing DesignKit package product is linked only to that test target. Existing complete project bytes are retained through seven inverse edits; no new package version, lock or production target dependency is added.',
  'Independent source review checked97 primary Git identities and26 exact inverses to all five original files. Root rechecked the97 identities and verified the57 final staged source bytes. The six original closed-Core controls are reused without rerun; future13-method runtime still requires matching real compiler/FileList/product admission.',
  'Root read the complete closed Page154 preparer and reversed all five edits to the exact original4005 bytes. It remains unconditionally closed without separately reviewed exact source/controller/admission pins; no native or simulator operation occurs in this intake.',
  'Original Page154 bcfa timeout receipt and five command records were actually read and retained. The180.200s enumeration was terminated by its own supervisor, leader reaped, PG absent; no method was invoked.757-byte raw log does not diagnose the underlying hang. No timeout/7200s fixture-authority increase or expired fixture reuse is justified.',
  'All87 donor paths are integrated without conflict or unrelated ancestor changes. Existing129 source-map entries, verifier, SDKcaa0/native8ac pins, locks, NativeLaunch23 and other projects remain byte-identical. Apple/runtime/visual/physical/TestFlight acceptance remain open.'
 ],'testsExecutedNow':0,'AppleBuildsNow':0,'runtimePlansActivated':0}
 extras.update({'root-source-review.json':(json.dumps(note,indent=2,sort_keys=True)+'\n').encode(),'root-integration-controller.py':pathlib.Path(__file__).read_bytes(),'approved-source-plan.json':plan_bytes,'original-merge-previews.json':preview_bytes,'prior-integration-receipt.json':prior})
 for name,data in extras.items():owned(PREFIX+'/'+name,data)
 b('add','--',PREFIX)
 b('diff','--cached','--check','--','Anytype.xcodeproj/project.pbxproj','Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertyPresentation.swift','Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift',PREFIX+'/root-source-review.json',PREFIX+'/root-integration-controller.py')
 for p,v in preserved.items():assert (ROOT/p).read_bytes()==v,p
 expected=sorted([r['path'] for r in plan['files']]+[PREFIX+'/'+n for n in extras]);assert t('diff','--cached','--name-only').splitlines()==expected
 tree=t('write-tree');gate=pathlib.Path('/tmp/pinkha-root-wave2-properties-core-page-retention.json');assert not gate.exists()
 result=subprocess.run(PRE+['python3','-B',str(ROOT/GATE),'--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(gate)],cwd=ROOT,capture_output=True,timeout=90)
 pathlib.Path(str(gate)+'.stdout').open('xb').write(result.stdout);pathlib.Path(str(gate)+'.stderr').open('xb').write(result.stderr)
 verified=json.loads(gate.read_bytes());assert result.returncode==0 and verified['sourceRetentionPassed'] and len(verified['reviewedRefactors'])==129
 message='Integrate original Properties lifecycle and native core compiler inputs\n\nPreserve current ownership and uncertain writes while clearing stale displayed values. Register the three original package suites in the existing AnytypeTests target and preserve closed Core13 and Page154 acceptance controls with original timeout evidence.\n\nSource-only integration; matching Apple compilation and runtime acceptance remain pending.\n'
 subprocess.run(G+['commit','-F','-'],input=message.encode(),capture_output=True,check=True,timeout=90)
 head=t('rev-parse','HEAD');assert t('show','-s','--format=%P',head).split()==[START,*DONORS]
 assert t('status','--porcelain=v1','--untracked-files=all')==status and t('ls-remote','origin',REF).split()[0]==START
 push=subprocess.run(G+['-c','remote.origin.mirror=false','-c','credential.helper=!gh auth git-credential','push','origin',head+':'+REF],capture_output=True,text=True,timeout=90)
 receipt.update(head=head,tree=tree,files=expected,sourceRetentionPassed=True,reviewedRefactors=129,retentionSHA256=h(gate.read_bytes()),controllerSHA256=h(pathlib.Path(__file__).read_bytes()),planSHA256=h(plan_bytes),evidencePayloadSHA256=h(packed),nativeSourceFiles=57,stage1UISourceFiles=10,pushExit=push.returncode,pushStdout=push.stdout,pushStderr=push.stderr,newTestsExecuted=0)
 if push.returncode==0:
  assert t('ls-remote','origin',REF).split()[0]==head;receipt['normalPushReadback']=head
 assert push.returncode==0;receipt['state']='SOURCE_AND_ORIGINAL_EVIDENCE_INTEGRATED_AND_PUBLISHED'
except BaseException:
 receipt['state']='FAILED_PRESERVED';receipt['error']=traceback.format_exc();raise
finally:
 receipt['completedAt']=time.time();OUT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'receipt':str(OUT),'sha256':h(OUT.read_bytes()),'state':receipt['state'],'head':receipt.get('head'),'tree':receipt.get('tree')}),flush=True)
