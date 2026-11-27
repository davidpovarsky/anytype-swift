import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='1984b8756922b1adfbe3626cfb45095e9aad0315'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-body-evidence-accessibility-integrations.json')
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

# Qualified new Any native Markdown body boundary: exact original evidence reuse.
donor='2619d5b144b23eb80247df613d5d128aa2efbfb6';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==22 and all(mode=='A' for mode,p in rows)
assert all(not (ROOT/p).exists() for _,p in rows)
source='Modules/PinkhaAnyEngine/Sources/PinkhaAnyEngine/AnyNativeMarkdownBody.swift'
assert h(b('show',donor+':'+source))=='7097c7c5f7bbf67eba21a961986a892064a1833425ff74b053917a0d4e11e4af'
prefix='docs/validation/20261127-wave1-markdown-body/'
qualification=json.loads(b('show',donor+':'+prefix+'result.json'))
assert h(b('show',donor+':'+prefix+'result.json'))=='83f5b3ff4c21d3ffe97a46247fa4689bd5f58d36f3234f80663ef248f039758e'
assert qualification['component']['methods']==18 and qualification['component']['failures']==qualification['component']['skips']==0
assert qualification['native']['conditionalBodyWritesApplied']==1 and qualification['native']['actualSIGKILLCount']==1 and qualification['native']['coldWrites']==0
for f in qualification['files']:
 data=b('show',donor+':'+prefix+f['path']);assert h(data)==f['sha256'] and len(data)==f['bytes']
originals=[
 ('components/observed-result.json','/var/lib/pinkha-w1-engine-contracts-20261127/markdown-body-components2/result.json'),
 ('native/observed-result.json','/var/lib/pinkha-w1-engine-contracts-20261127/markdown-body-native1/result.json'),
 ('failed-components/observed-result.json','/var/lib/pinkha-w1-engine-contracts-20261127/markdown-body-components1/result.json')]
for relative,path in originals:assert pathlib.Path(path).read_bytes()==b('show',donor+':'+prefix+relative),path
b('cherry-pick','-x','--no-commit',donor)
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
finish(parent,donor,'native-markdown-body',[p for _,p in rows])

# Exact retained join/three-node signed ACL evidence; two403 attempts are not zero attempts.
donor='f2b40968bd9347438b8fed432912f41944b43828';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==9 and all(p.startswith('Tools/AnyEngineValidation/native_file_peer_comparison/') for _,p in rows)
for mode,p in rows:
 if mode=='M':assert b('show','HEAD:'+p)==b('show',donor+'^:'+p),p
 else:assert mode=='A' and not (ROOT/p).exists(),p
base='Tools/AnyEngineValidation/native_file_peer_comparison/'
observed=b('show',donor+':'+base+'receipts/retained-recipient-continuation1.json')
assert h(observed)=='7ba37273e7c31492e5bc01c4c9e7e72de2f00fd123c64b3aec85050f66a5625d'
assert observed==pathlib.Path('/var/lib/pinkha-c-filesv2-20261126/retained-recipient-continuation1/result.json').read_bytes()
assert h(b('show',donor+':'+base+'receipts/retained-node-grant-comparison1.json'))=='b4ea294a8090cd867bae1246a635d0afba8a48e12ee073a9362f2598591321c6'
for p,digest in {
 'resume_retained_recipient.py':'f7972d8b90f9e614592e11ad35bc22ba86a073e442539d0c7f016272b516d0af',
 'compare_retained_acl_nodes.py':'5a033c8ca7aa46f635bf3014dac598b764556efebb10766780f003303fe62ee4',
 'compare_acl_nodes.go':'aef1a155ab50d36b86e1448a5dd470d699f0dd61d3a452ff66727ef3e218d7f6'}.items():assert h(b('show',donor+':'+base+p))==digest,p
b('cherry-pick','-x','--no-commit',donor)
note='docs/validation/20261127-wave3-retained-join-evidence/source-review.json'
owned(note,(json.dumps({'candidate':donor,'rootParent':parent,'independentReview':'sdk_hanlin read-only exact original bytes/controllers/four raw logs and signed three-peer comparison; no rerun',
 'scope':'Original pending Bob invitation becomes active Reader; fresh offline process preserves identity/Reader and refuses attachment. No whole FilesV2/Apple/peer-body qualification transfer.',
 'attachmentAttempts':2,'attachmentHTTPStatuses':[403,403],'successfulAttachments':0,'initCalls':0,'newJoinCalls':0,'newGrantCalls':0,'newInviteCalls':0,
 'originalReceiptFieldClarification':'attachmentCalls=0 is retained verbatim in the original evidence and denotes no successful attachment here; it must not be read as zero POST attempts.',
 'nativeBinarySHA256':'79248a63132a0146deff4e9fe1c4104a381a34d5c2ffcad536247a8429f98857','sourceFileCount':1597,
 'earlier90SecondFailureRetained':True,'laterOriginalPairFileContinuationIsSeparate':True,'newTestsExecutedByThisIntegration':0},indent=2,sort_keys=True)+'\n').encode())
b('add','--',note)
finish(parent,donor,'retained-join-acl-evidence',[p for _,p in rows]+[note])

# Shared complete semantic-body conversion and original Heart native operation.
donor='ca4d93e48dca616ab119739d71a1c4ffe7eddfa8';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
assert len(rows)==16
expected_modifications={
 'AnyTypeTests/Pinkha/PinkhaHanlinSaveMessageStateTests.swift',
 'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaHanlinSaveMessagePlan.swift',
 'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinCore/PinkhaHanlinSaveMessageProgress.swift',
 'docs/validation/20261127-hanlin-save-message/README.md'}
assert {p for mode,p in rows if mode=='M'}==expected_modifications
for mode,p in rows:
 if mode=='M':assert b('show','HEAD:'+p)==b('show',donor+'^:'+p),p
 else:assert mode=='A' and not (ROOT/p).exists(),p
for p,digest in {
 'Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinHeartSaveBody.swift':'dbfc51d0f120977b0dd59a160fb038ccf91479569837b77b5fc1a990977a47fe',
 'Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinHeartSaveMessageOperation.swift':'825f23cf66d10992d9885f0f800066fd626baacf6734a0bc81d8f247079afebf',
 'Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinSaveMessageRunner.swift':'63ce14ee38aa5dd00890412af6c422c92c50ccd1ba3bc98d4f3e64cb90e16126',
 'docs/validation/20261127-hanlin-save-message/body-source-intake.json':'b1fbd0db24ea396a18b9180084b9cc10268e0de1f87983a166f8a35c61b8a330'}.items():assert h(b('show',donor+':'+p))==digest,p
preview=t('merge-tree','--write-tree',parent,donor)
assert len(preview)==40
b('merge','--no-ff','--no-commit',donor);assert t('write-tree')==preview
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
finish(parent,donor,'original-semantic-body-source',[p for _,p in rows])

# Future accessibility source after one real public-SDK importer qualification.
import base64
PROBE_FILES = json.loads(r'''{"receipt.json":{"base64":"ewogICJhcHBCdWlsZHMiOiAwLAogICJhcmd2IjogWwogICAgIi9BcHBsaWNhdGlvbnMvWGNvZGUuYXBwL0NvbnRlbnRzL0RldmVsb3Blci9Ub29sY2hhaW5zL1hjb2RlRGVmYXVsdC54Y3Rvb2xjaGFpbi91c3IvYmluL3N3aWZ0YyIsCiAgICAiLXR5cGVjaGVjayIsCiAgICAiLXBhcnNlLWFzLWxpYnJhcnkiLAogICAgIi1zd2lmdC12ZXJzaW9uIiwKICAgICI2IiwKICAgICItdGFyZ2V0IiwKICAgICJhcm02NC1hcHBsZS1pb3MyNy4wLXNpbXVsYXRvciIsCiAgICAiLXNkayIsCiAgICAiL0FwcGxpY2F0aW9ucy9YY29kZS5hcHAvQ29udGVudHMvRGV2ZWxvcGVyL1BsYXRmb3Jtcy9pUGhvbmVTaW11bGF0b3IucGxhdGZvcm0vRGV2ZWxvcGVyL1NES3MvaVBob25lU2ltdWxhdG9yMjcuMC5zZGsiLAogICAgIi1GIiwKICAgICIvQXBwbGljYXRpb25zL1hjb2RlLmFwcC9Db250ZW50cy9EZXZlbG9wZXIvUGxhdGZvcm1zL2lQaG9uZVNpbXVsYXRvci5wbGF0Zm9ybS9EZXZlbG9wZXIvTGlicmFyeS9GcmFtZXdvcmtzIiwKICAgICItbW9kdWxlLWNhY2hlLXBhdGgiLAogICAgIi9Vc2Vycy9tMS9idWlsZHMvcGlua2hhLXdhdmUzLXZvaWNlb3Zlci1hcGktcHJvYmUtMGU5NjQ2MjgtMjAyNjExMjcvYXR0ZW1wdDEvbW9kdWxlLWNhY2hlIiwKICAgICIvVXNlcnMvbTEvYnVpbGRzL3BpbmtoYS13YXZlMy12b2ljZW92ZXItYXBpLXByb2JlLTBlOTY0NjI4LTIwMjYxMTI3L2F0dGVtcHQxL1ZvaWNlT3ZlclB1YmxpY0FQSUNvbXBpbGVQcm9iZS5zd2lmdCIKICBdLAogICJjb21waWxlckludm9jYXRpb25zIjogMSwKICAiY29udHJvbGxlclNIQTI1NiI6ICJkMzEzYjU4MTNhMTQ2Yjc1NGJiZjhkZWFkOWU0ZTI2ZGFhZjVmMTkwOWVlNTU0YTk5YjRjZTI0MTY1ZGI0NmNhIiwKICAiZHVyYXRpb25TZWNvbmRzIjogNS44MzAwOTUwNTI3MTkxMTYsCiAgImV4aXRDb2RlIjogMCwKICAiZmluaXNoZWRBdCI6IDE3OTU3NTAyMDIuODE0NDMsCiAgImZyZWVCeXRlc0FmdGVyIjogOTA4MzI4NTUwNCwKICAibG9ncyI6IHsKICAgICJzdGRlcnIub3JpZ2luYWwubG9nIjogewogICAgICAiYnl0ZXMiOiAwLAogICAgICAic2hhMjU2IjogImUzYjBjNDQyOThmYzFjMTQ5YWZiZjRjODk5NmZiOTI0MjdhZTQxZTQ2NDliOTM0Y2E0OTU5OTFiNzg1MmI4NTUiCiAgICB9LAogICAgInN0ZG91dC5vcmlnaW5hbC5sb2ciOiB7CiAgICAgICJieXRlcyI6IDAsCiAgICAgICJzaGEyNTYiOiAiZTNiMGM0NDI5OGZjMWMxNDlhZmJmNGM4OTk2ZmI5MjQyN2FlNDFlNDY0OWI5MzRjYTQ5NTk5MWI3ODUyYjg1NSIKICAgIH0KICB9LAogICJvd25lZFByb2Nlc3NHcm91cEFic2VudCI6IHRydWUsCiAgInByb2Nlc3MiOiB7CiAgICAicGdpZCI6IDczMTgzLAogICAgInBpZCI6IDczMTgzCiAgfSwKICAicnVudGltZUFjY2VwdGFuY2UiOiAiTk9UX1JVTiIsCiAgInNjaGVtYSI6ICJwaW5raGEudm9pY2VvdmVyLnNlbGVjdGVkLXNpbXVsYXRvci1zZGstaW1wb3J0ZXIudjEiLAogICJzaGFyZWRTb3VyY2VPclByb2R1Y3RzQ2hhbmdlZCI6IGZhbHNlLAogICJzaW11bGF0b3JPclNlcnZpY2VTZXR0aW5nc0NoYW5nZWQiOiBmYWxzZSwKICAic291cmNlQ29tbWl0IjogIjBlOTY0NjI4YjUyMGY1ZjhmMTNjODI3ZjU1N2FkOWM1ODVlNzEwM2MiLAogICJzb3VyY2VTSEEyNTYiOiAiYTVhOTRmYzZkZWZjMmFmZmUyNjY2ZTI1NzkwYjc3NGFmMGQ5ZWRmNDk5ZTMzODExNGZjODVjMTA2ZTkzOGIxNCIsCiAgInN0YXJ0ZWRBdCI6IDE3OTU3NTAxOTYuOTg0MzM2LAogICJzdGF0dXMiOiAiUEFTU19UWVBFQ0hFQ0tfT05MWSIsCiAgInRlcm1pbmF0aW9uUmVhc29uIjogbnVsbCwKICAidGVzdHNFeGVjdXRlZCI6IDAsCiAgInZvaWNlT3ZlckNhbGxzRXhlY3V0ZWQiOiAwCn0K","sha256":"bbc7a3bec437e61e0792d6717fadbdb8b42d44ad4fe8ed59c3852ca2874fc045","bytes":1878},"admission.original.json":{"base64":"ewogICJhdCI6IDE3OTU3NTAxOTYuODM5NTI5LAogICJjb21waWxlciI6ICIvQXBwbGljYXRpb25zL1hjb2RlLmFwcC9Db250ZW50cy9EZXZlbG9wZXIvVG9vbGNoYWlucy9YY29kZURlZmF1bHQueGN0b29sY2hhaW4vdXNyL2Jpbi9zd2lmdGMiLAogICJjb21waWxlclZlcnNpb24iOiB7CiAgICAiYXJndiI6IFsKICAgICAgIi9BcHBsaWNhdGlvbnMvWGNvZGUuYXBwL0NvbnRlbnRzL0RldmVsb3Blci9Ub29sY2hhaW5zL1hjb2RlRGVmYXVsdC54Y3Rvb2xjaGFpbi91c3IvYmluL3N3aWZ0YyIsCiAgICAgICItLXZlcnNpb24iCiAgICBdLAogICAgImV4aXRDb2RlIjogMCwKICAgICJzdGRlcnIiOiAic3dpZnQtZHJpdmVyIHZlcnNpb246IDEuMTY4LjYgIiwKICAgICJzdGRvdXQiOiAiQXBwbGUgU3dpZnQgdmVyc2lvbiA2LjQgKHN3aWZ0bGFuZy02LjQuMC4zNC4xIGNsYW5nLTIxMDAuMy4zNC4xKVxuVGFyZ2V0OiBhcm02NC1hcHBsZS1tYWNvc3gyNy4wLjBcbiIKICB9LAogICJjb25jdXJyZW50QWxsb3dhbmNlQnl0ZXMiOiAxMDczNzQxODI0LAogICJkZWFkbGluZVNlY29uZHMiOiAxMjAsCiAgImVzdGltYXRlQnl0ZXMiOiA1MzY4NzA5MTIsCiAgImZvcmVpZ25Db21waWxlclByb2Nlc3NlcyI6IFtdLAogICJmcmVlQnl0ZXMiOiA5MTgyMjQ4OTYwLAogICJsaXZlRmxvb3JCeXRlcyI6IDIxNDc0ODM2NDgsCiAgInBoYXNlIjogIkNPTVBJTEVfT05MWV9JTVBPUlRFUl9QUk9CRSIsCiAgInBsYXRmb3JtIjogIi9BcHBsaWNhdGlvbnMvWGNvZGUuYXBwL0NvbnRlbnRzL0RldmVsb3Blci9QbGF0Zm9ybXMvaVBob25lU2ltdWxhdG9yLnBsYXRmb3JtIiwKICAic2RrIjogIi9BcHBsaWNhdGlvbnMvWGNvZGUuYXBwL0NvbnRlbnRzL0RldmVsb3Blci9QbGF0Zm9ybXMvaVBob25lU2ltdWxhdG9yLnBsYXRmb3JtL0RldmVsb3Blci9TREtzL2lQaG9uZVNpbXVsYXRvcjI3LjAuc2RrIiwKICAic2VsZWN0ZWREZXZlbG9wZXIiOiAiL0FwcGxpY2F0aW9ucy9YY29kZS5hcHAvQ29udGVudHMvRGV2ZWxvcGVyIiwKICAic2VwYXJhdGVBcHBBZG1pc3Npb25FbnZlbG9wZVVuY2hhbmdlZCI6IDEyODg0OTAxODg4LAogICJ4Y29kZSI6IHsKICAgICJhcmd2IjogWwogICAgICAiL3Vzci9iaW4veGNvZGVidWlsZCIsCiAgICAgICItdmVyc2lvbiIKICAgIF0sCiAgICAiZXhpdENvZGUiOiAwLAogICAgInN0ZGVyciI6ICIiLAogICAgInN0ZG91dCI6ICJYY29kZSAyNy4wXG5CdWlsZCB2ZXJzaW9uIDI3QTI2NmFcbiIKICB9Cn0K","sha256":"82a26717d695c306dbf906c809d397faf371251d4d2d822cb064a6c49b062263","bytes":1251},"command.original.json":{"base64":"ewogICJhcmd2IjogWwogICAgIi9BcHBsaWNhdGlvbnMvWGNvZGUuYXBwL0NvbnRlbnRzL0RldmVsb3Blci9Ub29sY2hhaW5zL1hjb2RlRGVmYXVsdC54Y3Rvb2xjaGFpbi91c3IvYmluL3N3aWZ0YyIsCiAgICAiLXR5cGVjaGVjayIsCiAgICAiLXBhcnNlLWFzLWxpYnJhcnkiLAogICAgIi1zd2lmdC12ZXJzaW9uIiwKICAgICI2IiwKICAgICItdGFyZ2V0IiwKICAgICJhcm02NC1hcHBsZS1pb3MyNy4wLXNpbXVsYXRvciIsCiAgICAiLXNkayIsCiAgICAiL0FwcGxpY2F0aW9ucy9YY29kZS5hcHAvQ29udGVudHMvRGV2ZWxvcGVyL1BsYXRmb3Jtcy9pUGhvbmVTaW11bGF0b3IucGxhdGZvcm0vRGV2ZWxvcGVyL1NES3MvaVBob25lU2ltdWxhdG9yMjcuMC5zZGsiLAogICAgIi1GIiwKICAgICIvQXBwbGljYXRpb25zL1hjb2RlLmFwcC9Db250ZW50cy9EZXZlbG9wZXIvUGxhdGZvcm1zL2lQaG9uZVNpbXVsYXRvci5wbGF0Zm9ybS9EZXZlbG9wZXIvTGlicmFyeS9GcmFtZXdvcmtzIiwKICAgICItbW9kdWxlLWNhY2hlLXBhdGgiLAogICAgIi9Vc2Vycy9tMS9idWlsZHMvcGlua2hhLXdhdmUzLXZvaWNlb3Zlci1hcGktcHJvYmUtMGU5NjQ2MjgtMjAyNjExMjcvYXR0ZW1wdDEvbW9kdWxlLWNhY2hlIiwKICAgICIvVXNlcnMvbTEvYnVpbGRzL3BpbmtoYS13YXZlMy12b2ljZW92ZXItYXBpLXByb2JlLTBlOTY0NjI4LTIwMjYxMTI3L2F0dGVtcHQxL1ZvaWNlT3ZlclB1YmxpY0FQSUNvbXBpbGVQcm9iZS5zd2lmdCIKICBdLAogICJzb3VyY2VTSEEyNTYiOiAiYTVhOTRmYzZkZWZjMmFmZmUyNjY2ZTI1NzkwYjc3NGFmMGQ5ZWRmNDk5ZTMzODExNGZjODVjMTA2ZTkzOGIxNCIsCiAgIndvcmtpbmdEaXJlY3RvcnkiOiAiL1VzZXJzL20xL2J1aWxkcy9waW5raGEtd2F2ZTMtdm9pY2VvdmVyLWFwaS1wcm9iZS0wZTk2NDYyOC0yMDI2MTEyNy9hdHRlbXB0MSIKfQo=","sha256":"333cba8b02bd0c43c6a3398c4133c5c08ecb913f4b2f6381127c729a36bf8432","bytes":938},"process.original.json":{"base64":"ewogICJwZ2lkIjogNzMxODMsCiAgInBpZCI6IDczMTgzCn0K","sha256":"f2266f8540db681b76f4a59c88f09e32f820a17813bdb0dd76a100f95dd9fb0a","bytes":36},"resource-samples.original.json":{"base64":"WwogIHsKICAgICJhdCI6IDE3OTU3NTAxOTYuOTg2MjcsCiAgICAiZnJlZUJ5dGVzIjogOTE4MjIxNjE5MgogIH0sCiAgewogICAgImF0IjogMTc5NTc1MDE5OC4xMzAyODg4LAogICAgImZyZWVCeXRlcyI6IDkxNjU1NjE4NTYKICB9LAogIHsKICAgICJhdCI6IDE3OTU3NTAxOTkuMjgwMzU0LAogICAgImZyZWVCeXRlcyI6IDkxNDM2MzE4NzIKICB9LAogIHsKICAgICJhdCI6IDE3OTU3NTAyMDAuNDMwNDcyLAogICAgImZyZWVCeXRlcyI6IDkxMTkxNTAwODAKICB9LAogIHsKICAgICJhdCI6IDE3OTU3NTAyMDEuNTcxMTc0OSwKICAgICJmcmVlQnl0ZXMiOiA5MDk2NDk1MTA0CiAgfQpdCg==","sha256":"05e0fea3c908ce1a5b0e7914ba9d8228482e0bb93718811fc67642545f3eb4d5","bytes":334},"stdout.original.log":{"base64":"","sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","bytes":0},"stderr.original.log":{"base64":"","sha256":"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855","bytes":0},"VoiceOverPublicAPICompileProbe.swift":{"base64":"aW1wb3J0IFhDVGVzdAoKLy8gQ09NUElMRS1PTkxZIFBST0JFLiBObyB0b3AtbGV2ZWwgY2FsbCwgWENUZXN0IGNhc2UsIGVudHJ5IHBvaW50IG9yIGV4ZWN1dGFibGUuCi8vIFRoZSBvd25lciBtdXN0IHVzZSBzd2lmdGMgLXR5cGVjaGVjayBhZ2FpbnN0IHRoZSBzZWxlY3RlZCByZWFsIFNpbXVsYXRvciBTREsuCi8vIERvIG5vdCBydW4gdGhpcyBmdW5jdGlvbjogZW5hYmxpbmcgVm9pY2VPdmVyIGJlbG9uZ3MgdG8gYSBzZXBhcmF0ZWx5IGFkbWl0dGVkCi8vIGZ1dHVyZSBVSSB0ZXN0IGFuZCBpcyBub3QgYXV0aG9yaXplZCBieSB0aGlzIGNvbXBpbGVyL2ltcG9ydGVyIGNoZWNrLgpATWFpbkFjdG9yCkBhdmFpbGFibGUoaU9TIDI3LjAsICopCmZ1bmMgcGlua2hhVm9pY2VPdmVyUHVibGljQVBJQ29tcGlsZVByb2JlKCkgdGhyb3dzIHsKICAgIGxldCBzZXJ2aWNlID0gWENVSURldmljZS5zaGFyZWQudm9pY2VPdmVyU2VydmljZQogICAgbGV0IHdhc0VuYWJsZWQ6IEJvb2wgPSBzZXJ2aWNlLmlzRW5hYmxlZAogICAgdHJ5IHNlcnZpY2UuZW5hYmxlKCkKICAgIGxldCBjdXJyZW50OiBYQ1VJVm9pY2VPdmVyU2VydmljZS5PdXRwdXQgPSB0cnkgc2VydmljZS5jdXJyZW50U3BlZWNoKCkKICAgIGxldCBmb3J3YXJkOiBYQ1VJVm9pY2VPdmVyU2VydmljZS5PdXRwdXQgPSB0cnkgc2VydmljZS5tb3ZlRm9yd2FyZCgpCiAgICBsZXQgYmFja3dhcmQ6IFhDVUlWb2ljZU92ZXJTZXJ2aWNlLk91dHB1dCA9IHRyeSBzZXJ2aWNlLm1vdmVCYWNrd2FyZCgpCiAgICBsZXQgdXR0ZXJhbmNlczogW1N0cmluZ10gPSBbY3VycmVudC51dHRlcmFuY2UsIGZvcndhcmQudXR0ZXJhbmNlLCBiYWNrd2FyZC51dHRlcmFuY2VdCiAgICB0cnkgc2VydmljZS5kaXNhYmxlKCkKICAgIF8gPSAod2FzRW5hYmxlZCwgdXR0ZXJhbmNlcywgc2VydmljZS5pc0VuYWJsZWQpCn0K","sha256":"a5a94fc6defc2affe2666e25790b774af0d9edf499e338114fc85c106e938b14","bytes":936}}''')
for name,row in PROBE_FILES.items():
 data=base64.b64decode(row['base64']);assert len(data)==row['bytes'] and h(data)==row['sha256']
assert PROBE_FILES['receipt.json']['sha256']=='bbc7a3bec437e61e0792d6717fadbdb8b42d44ad4fe8ed59c3852ca2874fc045'
probe_receipt=json.loads(base64.b64decode(PROBE_FILES['receipt.json']['base64']))
assert probe_receipt['status']=='PASS_TYPECHECK_ONLY' and probe_receipt['exitCode']==0 and probe_receipt['testsExecuted']==0 and probe_receipt['voiceOverCallsExecuted']==0
donor='0e964628b520f5f8f13c827f557ad9c585e7103c';fetch(donor);parent=t('rev-parse','HEAD')
rows=[line.split('\t') for line in t('diff-tree','--no-commit-id','--name-status','-r',donor).splitlines()]
source='NativeApp/UITests/NativeLaunchTests.swift'
assert len(rows)==6 and [p for mode,p in rows if mode=='M']==[source]
before=b('show','HEAD:'+source);after=b('show',donor+':'+source)
assert before==b('show',donor+'^:'+source) and len(before)==214858
assert h(before)=='31c64474cebf4890050f9077d3c44fac63264d878a77bd6f55811cc407e02422'
assert h(after)=='5d3462b25dd64423cf33fc1243b2d734acea55011a9e5da4c66004022685958a' and after.startswith(before)
assert after[len(before):].count(b'@objc func test')==2
probe='Tools/PinkhaDualEngineRuntime/native_accessibility_future/VoiceOverPublicAPICompileProbe.swift'
assert b('show',donor+':'+probe)==base64.b64decode(PROBE_FILES['VoiceOverPublicAPICompileProbe.swift']['base64'])
del PINNED[source]
b('cherry-pick','-x','--no-commit',donor)
for _,p in rows:assert (ROOT/p).read_bytes()==b('show',donor+':'+p)
prefix='docs/validation/20261127-wave3-voiceover-api-probe'
extras=[]
for name,row in PROBE_FILES.items():
 p=prefix+'/'+name;owned(p,base64.b64decode(row['base64']));extras.append(p)
note=prefix+'/root-source-review.json'
owned(note,(json.dumps({'candidate':donor,'rootParent':parent,'originalNativeLaunchPrefixSHA256':h(before),'originalNativeLaunchPrefixBytes':len(before),'candidateNativeLaunchSHA256':h(after),
 'originalNineteenMethodsUnchanged':True,'futureMethodsAdded':2,'actualProbeReceiptSHA256':PROBE_FILES['receipt.json']['sha256'],
 'rootSourceReview':'Complete425-line appended AX/VoiceOver code read: original audit issues remain failures, bounded actual speech trace, disable verification, final private AX/PNG before termination including startup failure; actual source/preference proof remains external closed controller responsibility.',
 'fullNativeLaunchTypecheck':'NOT_RUN','actualAuditOrVoiceOverRuntime':'NOT_RUN','visualReview':'NOT_RUN','physicalDevice':'NOT_RUN',
 'currentMacSource':'8f2c11713fb8a40ae13444104723666ffef68afe','currentMacNativeLaunchSHA256':h(before),'currentControllersWidened':False},indent=2,sort_keys=True)+'\n').encode());extras.append(note)
b('add','--',prefix);finish(parent,donor,'future-native-accessibility',[p for _,p in rows]+extras)

