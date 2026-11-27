import pathlib, subprocess, json, hashlib, datetime, copy
ROOT=pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE=['sudo','-n','-u','ubuntu','-g','chatgpt-agent']
G=PRE+['git','-c','gc.auto=0','-c','user.name=ChatGPT','-c','user.email=chatgpt@openai.com','-C',str(ROOT)]
START='ff6836a6d4db7f1a19b94280d3b2f548e8d7d622'
REF='refs/heads/codex/chatgpt-wave15-final-20261125'
MAP='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
GATE='Tools/AnyEnginePort/verify_source_retention.py'
OUT=pathlib.Path('/tmp/pinkha-wave3-helper680-integration.json')
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
DONOR='680364279e08dc69d7d7eee8f6f13169ea8d0be4'
assert not OUT.exists() and t('rev-parse','HEAD')==START and t('symbolic-ref','HEAD')==REF
assert t('rev-parse','MERGE_HEAD')==DONOR and t('write-tree')=='b95e8bde474d4c3f34ee0441390a998852c8bdaf' and not t('diff','--name-only')
STATUS='?? Tools/Hanlin/__pycache__/\n?? Tools/MiniApps/__pycache__/\n?? Tools/PinkhaSimulatorGate/__pycache__/'
PINNED=preserved();ROWS=[]
prefix='docs/validation/20261127-wave3-native-save-acceptance-intake'
rawcopy=prefix+'/original-byte-retention-style-controller.py'
assert h((ROOT/rawcopy).read_bytes())=='483096a94e087fd825dbf8b6ba6763b09a7fe47c9720069d01740f54c485308d'
failed=subprocess.run(G+['-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check'],capture_output=True)
assert failed.returncode==2 and not failed.stderr and failed.stdout.decode()==rawcopy+':164: new blank line at EOF.\n'
prior=pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-helper680-crlf-resume-0cf6ab453235.py').read_bytes()
assert h(prior)=='0cf6ab453235e2b26246e3fd88910521976aa98a97b7ec4beb252459fcf8fdfe'
owned(prefix+'/original-byte-retention-style-resume.json',(json.dumps({'status':'ORIGINAL_CRLF_CHECK_EXIT2_RAW_CONTROLLER_FINAL_BLANK_LINE','failedStdoutBase64':base64.b64encode(failed.stdout).decode(),'failedControllerBase64':base64.b64encode(prior).decode(),'failedControllerSHA256':h(prior),'exceptionPath':rawcopy,'exceptionSHA256':h((ROOT/rawcopy).read_bytes()),'decision':'Retain raw original executed controller bytes including its historical terminal blank line. Exclude exactly this evidence-copy file from style-only lint, never source retention; all product/test/new controller sources and all other staged files remain checked. No global Git config or source edits.'},indent=2,sort_keys=True)+'\n').encode())
note=ROOT/prefix/'root-source-review.json';v=json.loads(note.read_bytes());assert h(note.read_bytes())=='a6bd6e61c116b42aea97bc0a05707fa719a3ebdbd72e66c1e344e3318ca0f178'
v['exactWindowsReceiptStyle']['oneRawOriginalControllerBlankLineException']={'path':rawcopy,'sha256':h((ROOT/rawcopy).read_bytes()),'sourceRetentionStillRequired':True}
owned(str(note.relative_to(ROOT)),(json.dumps(v,indent=2,sort_keys=True)+'\n').encode(),exclusive=False)
for path in t('diff-tree','--no-commit-id','--name-only','-r',DONOR).splitlines():assert (ROOT/path).read_bytes()==b('show',DONOR+':'+path),path
b('add','--',prefix)
b('-c','core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol','diff','--cached','--check','--','.',':(exclude)'+rawcopy)
finish(START,DONOR,'native-save-acceptance-source',t('diff','--cached','--name-only').splitlines())
