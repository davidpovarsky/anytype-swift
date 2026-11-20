from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,shutil

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
SRC=APP/'build/any-engine-port/native-final-v9-object-runtime-v1'
DEST=APP/'Tools/AnyEngineValidation/evidence/native-final-v9-object-runtime-v1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')

result=json.loads((SRC/'result.json').read_text(encoding='utf-8'))
raw=json.loads((SRC/'native-runtime-result.json').read_text(encoding='utf-8'))
assert result['status'] in ('PASS_FINAL_NATIVE_V9_PEER16','FAIL')
assert result['finishedAtUTC'] and raw['finishedAt']
assert result['independentOwnedCleanup']['remainingOwnedRules']==0
assert result['independentOwnedCleanup']['remainingOwnedProcesses']==0
assert len(raw['firewallRules'])==2 and all(r['removalVerified'] for r in raw['firewallRules'])
if result['status']=='PASS_FINAL_NATIVE_V9_PEER16':
    assert result['checks']==16 and len(raw['checks'])==16 and all(r['status']=='PASS' for r in raw['checks'])
    assert result['sourceStable'] and result['binaryStable'] and result['manifestStable'] and result['harnessStable']
    assert raw['peerBRestoreBeforeAppend']['binAbsent'] is True
    assert raw['peerBRestoreBeforeAppend']['nativeObjectSnapshotComplete'] is True
    assert raw['peerBRestoreBeforeAppend']['businessAppendRetried'] is False
DEST.mkdir(parents=True,exist_ok=False)
files=[]
for p in sorted(SRC.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts:continue
    rel=p.relative_to(SRC)
    assert p.suffix in ('.json','.py','.log','.diff'),str(rel)
    saved=Path('run/stdout.log') if rel.as_posix()=='run/stdout.json' else rel
    target=DEST/saved;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    assert sha(p)==sha(target)
    files.append({'original':rel.as_posix(),'saved':saved.as_posix(),'sha256':sha(target),'bytes':target.stat().st_size})
shutil.copyfile(__file__,DEST/'executed-archiver.py')
files.append({'saved':'executed-archiver.py','sha256':sha(DEST/'executed-archiver.py')})
archive={'status':'ARCHIVED_EXACT_PEER_RUNTIME','runtimeStatus':result['status'],'checksPassed':sum(r['status']=='PASS' for r in raw['checks']),'checksFailed':sum(r['status']=='FAIL' for r in raw['checks']),'checksNotExecuted':16-len(raw['checks']),
 'resultSHA256':sha(DEST/'result.json'),'nativeResultSHA256':sha(DEST/'native-runtime-result.json'),
 'nativeBinarySHA256':result['nativeBinarySHA256'],'nativeManifestSHA256':result['nativeManifestSHA256'],
 'sourceStable':result.get('sourceStable'),'independentOwnedCleanup':result['independentOwnedCleanup'],
 'scope':'Original16 peer partition/rejoin/object/watch assertions on exactv9, with a bounded native peer-B eligibility read before the single original append. No10001-scale repeat, no business mutation retry, no private fixture logs/account secrets archived.',
 'preservedHistoricalFailure':'native-final-v8-object-runtime-v1/analysis.json',
 'files':files,'sealedAtUTC':datetime.now(timezone.utc).isoformat()}
write(DEST/'archive.json',archive)
print(json.dumps({k:archive[k] for k in ('status','runtimeStatus','checksPassed','checksFailed','checksNotExecuted','resultSHA256','nativeResultSHA256','sourceStable')}|{'path':str(DEST),'archiveSHA256':sha(DEST/'archive.json'),'files':len(files),'eligibilityBarrierDiffSHA256':sha(DEST/'eligibility-barrier-only.diff')}))
