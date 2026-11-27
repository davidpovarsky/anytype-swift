"""Prepare the two exact product pins for the reviewed original Kit successor."""
from pathlib import Path
import hashlib, json, gzip, difflib

ROOT = Path('/workspace/scratch/ae335eba85e3')
REVIEW = ROOT / 'kit-26beca-independent-review'
OUT = ROOT / 'kit-pin-promotion-prepared'
OLD = '9058b489e9acc271b4f8ef69e2ed24648f93b4ed'
NEW = '26beca175d64a4d34e3567f2bbb4bf308d714478'
PATHS = {
    'Modules/PinkhaTorahPresentation/Package.swift': '7709a4b4cc13b0b76f4e884c42ffca35d1016536c1d4cb78b7ee72cf8556da71',
    'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved': 'e22368e522ac795253935b0a31e39d1b36bd9043ef2ed1014845927914527ccd',
}

def identity(b):
    return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),
            'gitBlob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}

OUT.mkdir(exist_ok=False)
review = json.loads((REVIEW/'independent-review.json').read_bytes())
assert review['commit'] == NEW and review['parent'] == OLD
component = json.loads((REVIEW/'component-original-review.json').read_bytes())
assert component['status'] == 'PASS_ORIGINAL_SCOPED_COMPONENT_RECEIPT_QUALIFIED'
for relative in ('Sources/TorahInspectorUI/TorahDocumentLoadLifetime.swift',
                 'Tests/TorahInspectorUITests/TorahDocumentLoadLifetimeTests.swift'):
    source = (REVIEW/'source'/relative).read_bytes()
    assert identity(source)['sha256'] == component['sourceInputs'][relative]['sha256']
    assert len(source) == component['sourceInputs'][relative]['bytes']
files = {}
patch = ''
for path, expected in PATHS.items():
    before = (REVIEW/'app-cee06ac'/path).read_bytes()
    assert identity(before)['sha256'] == expected and before.count(OLD.encode()) == 1
    after = before.replace(OLD.encode(),NEW.encode())
    assert after.replace(NEW.encode(),OLD.encode()) == before
    if path.endswith('Package.resolved'):
        a,b = json.loads(before),json.loads(after)
        assert len(a['pins']) == len(b['pins']) == 55
        changes = [(x,y) for x,y in zip(a['pins'],b['pins']) if x != y]
        assert len(changes) == 1 and changes[0][0]['identity'] == 'torahinspectorkit'
        assert changes[0][1] == {**changes[0][0], 'state':{'revision':NEW}}
        assert a['originHash'] == b['originHash'] and a['version'] == b['version']
        collections = [x for x in b['pins'] if x['identity']=='swift-collections']
        assert len(collections) == 1 and collections[0]['state'] == {
            'revision':'7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e','version':'1.3.0'}
    p=OUT/'after'/path;p.parent.mkdir(parents=True,exist_ok=True);p.open('xb').write(after)
    files[path] = {'before':identity(before),'after':identity(after),'text':after.decode()}
    patch += ''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),
                                         fromfile='a/'+path,tofile='b/'+path))
evidence = {}
for name in ('independent-review.json','independent-byte-proof.json','component-original-review.json'):
    b=(REVIEW/name).read_bytes();evidence['kit-'+name]={**identity(b),'text':b.decode()}
for p in sorted((REVIEW/'component-originals').iterdir()):
    b=p.read_bytes();evidence['kit-component/'+p.name]={**identity(b),'text':b.decode()}
payload={'schema':'pinkha-reviewed-kit-two-pin-promotion/v1','sourceBase':OLD,'sourceCommit':NEW,
         'sourceTree':'91b2132ff8e55fbc0c3df2b14d0ad6ddf1626a41','files':files,'evidence':evidence,
         'originalComponentMethodsPassed':6,'originalComponentDeclaredCases':9,
         'actualComponentReceiptSHA256':'bdc048352dde0e89ff922ca97fc0ab37af21cce4610d16b707bcea813c86156c',
         'allOtherDependencyPinsUnchanged':True,'newTestsExecuted':0,
         'scope':'Two exact original-source pins only. Three SwiftUI callers/full Kit/App require the actual matching Apple build; the helper component is separately qualified. No SDK/native/source-control override.'}
b=(json.dumps(payload,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
(OUT/'payload.json').open('xb').write(b)
packed=gzip.compress(b,mtime=0);(OUT/'payload.json.gz').open('xb').write(packed)
(OUT/'changes.diff').open('x').write(patch)
summary={'files':{p:{k:v for k,v in r.items() if k!='text'} for p,r in files.items()},
         'payload':identity(b),'transport':identity(packed),'source':NEW,'sourceGateRowsExpected':132,
         'fullInverses':2,'compiledOrRuntimeTestsRunByPreparation':0}
(OUT/'prepared.json').open('x').write(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(summary,sort_keys=True))
