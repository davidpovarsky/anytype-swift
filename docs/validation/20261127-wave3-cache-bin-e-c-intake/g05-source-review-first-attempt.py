"""Qualify exact G05 source; no compiler, runtime or remote mutation."""
from pathlib import Path
import copy
import hashlib
import json
import subprocess

ROOT = Path('/workspace/scratch/ae335eba85e3')
BASE = ROOT / 'w2-g05-cache-primary-review'
SOURCE = BASE / 'source'
DOC = SOURCE / 'docs/validation/20261127-wave2-property-picker-cache'
CURRENT = ROOT / 'w2-attachments-g05-primary-review/g05/source'
OUT = BASE / 'root-review'
OUT.mkdir(exist_ok=False)
def sha(b): return hashlib.sha256(b).hexdigest()
def rec(b): return {'bytes': len(b), 'sha256': sha(b), 'gitBlob': hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def write(n, d):
    b=(json.dumps(d, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode()
    p=OUT/n; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(b)
    return rec(b)

identities=json.loads((BASE/'primary-identities.json').read_bytes())
for path, want in identities.items(): assert rec((SOURCE/path).read_bytes()) == want, path
manifest=json.loads((DOC/'candidate-manifest.json').read_bytes())
proof={}
for row in manifest['files']:
    path=row['path']; new=(SOURCE/path).read_bytes(); old=(CURRENT/path).read_bytes()
    assert sha(new)==row['candidateSHA256'] and sha(old)==row['originalSHA256']
    assert (DOC/'originals'/path).read_bytes()==old
    dest=OUT/'inverse'/path; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(new)
    patch=DOC/'diffs'/(path+'.diff')
    run=subprocess.run(['git','apply','--reverse',str(patch)],cwd=OUT/'inverse',capture_output=True)
    assert run.returncode==0,(path,run.stderr.decode())
    assert dest.read_bytes()==old
    proof[path]={'before':rec(old),'after':rec(new),'entireInverseEqualsAcceptedCurrentDonor':True,'inverseExitCode':run.returncode}
test='AnyTypeTests/Pinkha/PropertyCreationSearchTests.swift'
assert (SOURCE/test).read_bytes().startswith((CURRENT/test).read_bytes())
definitions=json.loads((DOC/'native-property-definitions-source.json').read_bytes())
definition_bytes=definitions['content'].encode()
assert rec(definition_bytes)['gitBlob']==definitions['sha']
array=definitions['content'].split('    public static let all: [Self] = [',1)[1].split('    ]',1)[0]
assert array.count('Self(kind:')==3
path='docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
current_map=(ROOT/'w2-g07-bin-primary-review/current'/path).read_bytes()
scope=json.loads((DOC/'map-scope.json').read_bytes())
assert sha(current_map)==scope['originalSHA256']
old=json.loads(current_map); donor=json.loads((SOURCE/path).read_bytes())
assert len(old['changes'])==len(donor['changes'])==130
changes=[i for i in range(130) if old['changes'][i]!=donor['changes'][i]]
assert changes==scope['changedIndices']==[121,122,123,124,129]
assert {k:v for k,v in old.items() if k!='changes'}=={k:v for k,v in donor.items() if k!='changes'}
combined=json.loads((ROOT/'w2-g07-bin-primary-review/g07/root-review/composed'/path).read_bytes())
assert len(combined['changes'])==132
for i in changes:
    assert combined['changes'][i]==old['changes'][i]
    assert donor['changes'][i]['validation'].startswith(old['changes'][i]['validation'])
    combined['changes'][i]=copy.deepcopy(donor['changes'][i])
combined_bytes=(json.dumps(combined,ensure_ascii=False,indent=2)+'\n').encode()
dest=OUT/'composed'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(combined_bytes)
byteproof=write('independent-byte-proof.json',{'current':'cee06ac951f735514059e616fbea48f07d4e7c09','donor':'551108022574a8e2f1d7f307425280e6b5c56f1d','primaryFiles':len(identities),'primaryBytes':sum(x['bytes'] for x in identities.values()),'wholeFileInverses':proof,'definitionArray':{'count':3,'source':rec(definition_bytes),'twoUncancelledFullReadCalls':6},'sourceMap':{'before':rec(current_map),'donor':rec((SOURCE/path).read_bytes()),'combinedG07AndG05':rec(combined_bytes),'updatedIndices':changes,'totalRows':132},'originalTestPrefixBytes':19495,'compilerInvocations':0,'testsExecuted':0})
report={'schema':'pinkha-wave3-g05-cache-independent-review/v1','status':'SOURCE_REVIEWED_RUNTIME_PENDING','current':'cee06ac951f735514059e616fbea48f07d4e7c09','donor':'551108022574a8e2f1d7f307425280e6b5c56f1d','byteProof':byteproof,'findings':[
    'The native cache snapshots cache and Space generations under its existing lock. Invalidated asynchronous lookup, bootstrap refresh and reentrant storage reads cannot republish descriptors or diagnostics from an older generation.',
    'Conditional invalidation cannot retire a newer retry cache. Publication validates the same generation atomically. Invalidation is surfaced as CancellationError, not a completed empty read.',
    'The read-only production loader receives descriptors and diagnostics in one immutable result, avoiding a later global diagnostic read. Provisioning remains disabled for the picker; original provisioning consumers and public array API are retained.',
    'All three complete changed Swift files reverse exactly to the accepted 1cc7 bytes integrated into current cee. The entire old19495-byte test file is preserved as a prefix.',
    'The primary native definition array has THREE entries. The deliberately uncancelled older read and fresh read each finish three searches, so the six-call assertion matches the source. No suspected defect remains on that boundary.',
    'Three new actual methods/six cases cover invalidation of Space/all success/failure, bootstrap refresh and reentrant storage. Together with the prior read-only successor the new G05 scope is six methods/thirteen cases. No compile or execution has occurred.',
    'The combined prospective132-row map preserves the independently reviewed G07 additions/updates and changes only five established G05 rows from the current130-row source.'
], 'remaining':['Actual original App compiler and exact selected methods in the Wave2-owned aggregate.','Actual picker UI, Hebrew/English appearance and current engine/account transitions.','Same-generation completion order and IdentityStore snapshot race are outside this generation-invalidation patch.'], 'runtime':'NOT_RUN','retentionGateOnCombinedTree':'NOT_RUN'}
print(json.dumps({'byteProof':byteproof,'review':write('independent-review.json',report),'combinedMap':rec(combined_bytes)}))
