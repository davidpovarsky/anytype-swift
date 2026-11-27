import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='be2b08abd891c52b398bf7afcc98713614fd1023'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-definitions-warm-ack-integrations.json')
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

# Exact original source/evidence intake; no account/test rerun.
audit=pathlib.Path('/tmp/pinkha-wave3-definitions-warm-intake-audit.json').read_bytes()
assert h(audit)=='51d37fd562fe6c83ad875106cbce4a9bca2a155b4df5d75ea334427470a0076b'
review=json.loads(audit);assert review['status']=='PASS_SOURCE_AND_ORIGINAL_EVIDENCE_REVIEW_NO_RERUN'
assert len(review['definitions']['sourceClosureDifferencesAtRoot'])==4 and all(x['addedByCandidate'] and x['currentRootSHA256'] is None for x in review['definitions']['sourceClosureDifferencesAtRoot'])
donor='5235bf902f8820fdc41fe802265ff5444407b363';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==38 and all(mode=='A' and not (ROOT/p).exists() for mode,p in rows)
q=json.loads(b('show',donor+':docs/validation/20261127-wave1-functional-migration/native-definition-directory/qualification.json'))
assert q['definitionCounts']['allEntries']==13 and q['definitionCounts']['unresolvedSourceDefinitions']==137 and q['wholeSpaceMigration'] is False
b('cherry-pick','-x','--no-commit',donor)
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
prefix='docs/validation/20261127-wave3-definition-directory-intake'
extras=[]
for name,data in [('original-source-evidence-audit.json',audit),('read-only-audit.py',pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-definitions-warm-audit-f056aed671d4.py').read_bytes())]:
 path=prefix+'/'+name;owned(path,data);extras.append(path)
note=prefix+'/root-source-review.json'
owned(note,(json.dumps({'candidate':donor,'rootParent':parent,'completeProductionSourcesReviewed':2,'completeNewTestSourcesReviewed':2,'originalPlanCardinalityGuardReviewed':True,
 'sourceClosure':{'members':306,'existingMembersByteIdenticalToRoot':302,'newMembers':4},'actualOriginalEvidenceReused':{'components':4,'uniqueNativeMethods':1,'nativeInvocations':3,'actualDefinitionPATCHes':6,'actualSIGKILL':1,'acceptedOriginalMigrationReplays':0},
 'sourceReview':'Exact UTF8 native addresses and original plan/receipt identity; archive infrastructure excluded; type/property/option provenance and enclosing parent provenance retained; active account/Space/lease checked around original reads; current edits reported independently from original descriptor; source admission and writes remain false.',
 'scope':'13 entries qualified;137 builtin definitions remain unresolved. Full history/source admission, Apple UI and schema-wide atomic concurrency are separate pending gates. Existing raw original failures are preserved.',
 'newCompilerOrTestsExecuted':0,'currentMacSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe'},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix);finish(parent,donor,'imported-native-definitions',[p for _,p in rows]+extras)

# Standalone closed consumer controls: all original common bytes remain intact.
donor='a89635ab5d911af37719d23adefa161d864c91f8';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==27 and all(mode=='A' and not (ROOT/p).exists() for mode,p in rows)
assert review['warmIntake']['inverseOperations']==42 and review['warmIntake']['readyForRuntimeAdmission'] is False
b('cherry-pick','-x','--no-commit',donor)
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
note='docs/validation/20261127-wave3-closed-warm-intake/root-source-review.json'
owned(note,(json.dumps({'candidate':donor,'rootParent':parent,'fullFragmentAndMaterializerAndTestsReviewed':True,'fragmentSHA256':'f097cdb1a12087475cda0728d34d7a7dcb2ef0d62ad67810fd9724d11d096bfa',
 'inverseOperations':42,'originalRestoredSHA256':'7ff8af54801d089fe6abad52fdd3c6fbec957c8f205be1d2299556a75d227ad5','changedOriginalFunctions':['w3_stage_proof'],'addedFunctions':['w3_stage_control_references'],
 'sourceReview':'Exact six control files and four-field bundle are bound to actuald22/506/cf181 stage metadata. Original two-field reference gate and common cloner remain unchanged. Full source/native/SDK/compiler/product/phase and process outcomes remain necessary. Ready alone cannot open runtime while actual admission/producer/delta pins are absent.',
 'originalPortableEvidence':{'methods':3,'negativeCases':7,'rerunByRoot':False,'scope':'Schema and closed-admission controls only; synthetic length buffer never accepted as Git bundle'},
 'readyForRuntimeAdmission':False,'newBuildsOrRuntimeTests':0,'resourceSuccessorNote':'This source binds original4GiB concurrent cache/template; any later root-approved512MiB resource reassessment requires an exact separately reviewed successor before runtime admission. No historical receipt is rewritten.'},indent=2,sort_keys=True)+'\n').encode())
b('add','--',note);finish(parent,donor,'closed-actual-warm-stage-consumer',[p for _,p in rows]+[note])

# Typed original native ACK and normalized body metadata in the existing chain.
import base64
donor='fc1483c72461f33c9bd0a138a097bc479018d9a8';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==5 and sum(mode=='M' for mode,p in rows)==3
proof_path='docs/validation/20261127-hanlin-save-message/atomic-ack-source-intake.json'
proof_raw=b('show',donor+':'+proof_path);assert h(proof_raw)=='e8f56dc61f0a09c26dfffd4a610d4b0008c5085099bd69ebb852aabc4c9e4bbb';proof=json.loads(proof_raw)
assert proof['testsExecuted']==0 and proof['authoredTests']['methods']==42 and proof['productionSaveBindingInstalled'] is False
for mode,p in rows:
 if mode=='M':assert b('show','HEAD:'+p)==b('show',donor+'^:'+p),p
 else:assert mode=='A' and not (ROOT/p).exists(),p
for record in proof['sources']:
 p=record['path'];after=b('show',donor+':'+p);assert h(after)==record['sha256'] and len(after)==record['bytes']
 assert t('rev-parse',donor+':'+p)==record['afterBlob']
 if record['beforeBlob'] is not None:
  before=b('show','HEAD:'+p);assert t('rev-parse','HEAD:'+p)==record['beforeBlob']
  lines=after.splitlines(keepends=True)
  for op in reversed(record['inverseOperations']):
   start=op['afterLineStart']-1;end=op['afterLineEnd'];assert h(b''.join(lines[start:end]))==op['expectedAfterSHA256']
   lines[start:end]=base64.b64decode(op['replacementOriginalBase64']).splitlines(keepends=True)
  assert b''.join(lines)==before,p
tests='AnyTypeTests/Pinkha/PinkhaHanlinSaveMessageStateTests.swift'
before=b('show','HEAD:'+tests);after=b('show',donor+':'+tests)
prefix_end=before.index(b'    func testConditionalBodyIsOneOperationWithoutSyntheticBlockEffects')
assert after.startswith(before[:prefix_end])
assert all(('func '+name+'(').encode() in after for name in proof['previousStateMethodNamesRetained'])
preview=t('merge-tree','--write-tree',parent,donor);assert len(preview)==40
b('merge','--no-ff','--no-commit',donor);assert t('write-tree')==preview
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
note='docs/validation/20261127-wave3-atomic-body-ack/root-source-review.json'
owned(note,(json.dumps({'candidate':donor,'rootParent':parent,'completeSourceAndTestDiffReviewed':True,'allThreeLiteralInversesRestoreOriginalBytes':True,'original23TestPrefixByteIdentical':True,'all36PreviousMethodNamesRetained':True,
 'sourceReview':'Retain bounded actual inserted/updated/deleted native IDs in the original journal metadata contract. Digest-only ACK cannot certify body. Late ACK metadata never reopens dispatch. Fresh original-page completion requires exact inserted-ID set, no changed/deleted/prior rows, matching opaque native version, semantic whole-body digest and separate bounded normalized Markdown digest/length.',
 'bounds':proof['bounds'],'authoredStateMethods':42,'allNewStateMethods':'NOT_RUN','newCompilerOrNativeCalls':0,'productionSaveInstalled':False,
 'dependenciesStillRequired':['SDK-owned original journal64KiB ACK event reservation','shared original Any authority/consent seam and real body operation','actual Apple compile/enumeration and native full-body/account-switch/drain acceptance'],
 'currentMacSourceUnchanged':'8f2c11713fb8a40ae13444104723666ffef68afe'},indent=2,sort_keys=True)+'\n').encode())
b('add','--',note);finish(parent,donor,'original-atomic-body-ack',[p for _,p in rows]+[note])
