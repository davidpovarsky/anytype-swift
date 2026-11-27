import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='96f5711e43561711fc24fcf4af417992b61bb90d'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-message-action-integration-corrected.json')
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
assert not t('diff','--name-only')
assert t('write-tree')=='6f8a80122cbdde5b33d5dcf6746d2bca18aa7807'
assert t('rev-parse','MERGE_HEAD')=='8932c43f59f9976efd9930e4f8c5ba0b0fee72dd'
STATUS='\n'.join(line for line in t('status','--porcelain').splitlines() if line.startswith('?? '));ROWS=[]
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



import base64
DONOR='8932c43f59f9976efd9930e4f8c5ba0b0fee72dd'
FAILED_TREE='6f8a80122cbdde5b33d5dcf6746d2bca18aa7807'
PREFIX='docs/validation/20261127-wave3-message-action-intake'
FAILED=PREFIX+'/original-retention-failure'
failed_gate=pathlib.Path('/tmp/pinkha-wave3-original-message-save-action-retention.json')
failed_raw=failed_gate.read_bytes()
assert h(failed_raw)=='3448ce787d34d6b7f7d2287c47c1c87b9f1588608ae4a9325230b5019ddb35d1'
f=json.loads(failed_raw);assert f['sourceRetentionPassed'] is False and f['inventoryErrors']==['Replacement blob mismatch: Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/Resources/PinkhaHanlin.xcstrings'] and not f['unreviewedChangedExistingFiles']
original_map=(ROOT/MAP).read_bytes();assert h(original_map)=='3ae1e2505e76b952fdef1394524a22037295f7009829e9625a7ac6fb1a931b4e'
assert original_map==b('show',':'+MAP)
controller=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-message-action-integration-5fce3380f5c7.py').read_bytes();assert h(controller)=='5fce3380f5c70eef71a7ba7b44911376922f7f0b0aa566f32879c10b7f1f4190'
original_note=(ROOT/PREFIX/'root-source-review.json').read_bytes()
for name,data in [('retention.json',failed_raw),('retention.stdout',pathlib.Path(str(failed_gate)+'.stdout').read_bytes()),('retention.stderr',pathlib.Path(str(failed_gate)+'.stderr').read_bytes()),('source-map.json',original_map),('root-source-review.json',original_note),('controller.py',controller)]:owned(FAILED+'/'+name,data)
diff=b('diff','--binary','--full-index',START,FAILED_TREE)
owned(FAILED+'/staged-diff.json',(json.dumps({'parent':START,'donor':DONOR,'stagedTree':FAILED_TREE,'bytes':len(diff),'sha256':h(diff),'base64':base64.b64encode(diff).decode()},sort_keys=True,indent=2)+'\n').encode())
path='Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/Resources/PinkhaHanlin.xcstrings'
old=json.loads(b('show','HEAD:'+path));raw=(ROOT/path).read_bytes();new=json.loads(raw)
assert b('show',DONOR+':'+path)==raw and t('rev-parse',DONOR+':'+path)=='9d45063cfcc8776898c0affe757b9d726105da53'
assert len(old['strings'])==26 and all(new['strings'][k]==v for k,v in old['strings'].items()) and set(new['strings'])-set(old['strings'])=={'pinkha.hanlin.savedMessageTitle'}
mapping=json.loads(original_map);candidates=[row for row in mapping['changes'] if row['to']==path];assert len(candidates)==1
row=candidates[0];assert row['baselineBlob']=='52ba2e3fd9bc0709250538541d11154c0bd84707' and row['replacementBlob']=='7eff883a40b0ea8dc20a097f77135acab712a70a' and row['kind']=='move'
row['replacementBlob']='9d45063cfcc8776898c0affe757b9d726105da53'
row['reason']+=' Reviewed2026-11-27 Wave3 message-Save localization: preserve all26 existing localized entries byte-for-byte and add only the original shared saved-message title in English and Hebrew.'
row['validation'].append('Original gate3448ce78 correctly rejected the missing third localization mapping; preserved failed map/source-review/controller/full staged diff and actual gate output. Only reviewed replacement7eff883a→9d45063c and explanation were updated. No test or source gate was weakened; new Apple/native acceptance remains NOT_RUN.')
for oldrow,newrow in zip(json.loads(original_map)['changes'],mapping['changes']):
 assert all(oldrow[k]==newrow[k] for k in ['from','to','kind','baselineBlob'])
 if oldrow['to']!=path:assert oldrow==newrow
owned(MAP,(json.dumps(mapping,indent=2,ensure_ascii=False)+'\n').encode(),exclusive=False)
note=json.loads(original_note);note.pop('mapBaselineAndReplacementIdentityUnchanged')
note['mapBaselinesUnchanged']=True;note['mapChanges'].append(path);note['localizationReplacement']={'before':'7eff883a40b0ea8dc20a097f77135acab712a70a','after':'9d45063cfcc8776898c0affe757b9d726105da53','originalEntriesRetained':26,'newEntries':1};note['originalFailedSourceGatePreserved']={'sha256':h(failed_raw),'prefix':FAILED,'onlyFinding':'Missing localization replacement mapping, no unreviewed existing source changes.'}
owned(PREFIX+'/root-source-review.json',(json.dumps(note,indent=2,sort_keys=True)+'\n').encode(),exclusive=False)
b('add','--',MAP,PREFIX);b('diff','--cached','--check')
finish(START,DONOR,'original-message-save-action-localization-map',t('diff','--cached','--name-only').splitlines())
