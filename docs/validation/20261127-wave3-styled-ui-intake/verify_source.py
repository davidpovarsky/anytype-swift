#!/usr/bin/env python3
"""Read-only byte audit of retained original source; not compilation or XCTest."""
import hashlib
import json
import re
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CURRENT = '53a300d3a77920a2a4db09d13d9dc2e00ef5398e'
DONOR = '7380a797d13b279b6d19e43ade7af1929089b8ef'
sha = lambda data: hashlib.sha256(data).hexdigest()
blob = lambda data: hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
read_json = lambda path: json.loads(path.read_text())

def ident(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': sha(data), 'gitBlob': blob(data)}

inputs = []
for row in read_json(ROOT / 'download-source-index.json'):
    path = ROOT / row['local']
    item = ident(path)
    assert item['gitBlob'] == row['blob'], row
    inputs.append(dict(row, bytes=item['bytes'], sha256=item['sha256']))
assert len(inputs) == 17

owner = read_json(ROOT / 'docs/source-proof.json')
for row in owner['files']:
    item = ident(ROOT / 'sources' / DONOR / row['path'])
    for key in ['bytes', 'sha256', 'gitBlob']:
        assert item[key] == row[key], (row['path'], key)
for group in ['reviews', 'sourceInverseFiles']:
    for row in owner[group]:
        assert sha((ROOT / 'docs' / row['path']).read_bytes()) == row['sha256']
assert sha((ROOT / 'docs/source-references.json').read_bytes()) == owner['referenceManifestSHA256']
assert sha((ROOT / 'docs/installed-content-size-api.json').read_bytes()) == owner['installedAPISourceManifestSHA256']

source_prefix = Path('Modules/PinkhaAnyUI/Sources/PinkhaAnyUI')
inverse = []
for name in ['AnyNativeEditor.swift', 'AnySemanticAnchorObservation.swift']:
    before = (ROOT / 'sources' / CURRENT / source_prefix / name).read_bytes()
    after = (ROOT / 'sources' / DONOR / source_prefix / name).read_bytes()
    spec = read_json(ROOT / 'docs' / (name + '.inverse.json'))
    assert sha(before) == spec['beforeSHA256'] and sha(after) == spec['afterSHA256']
    restored = after
    for change in reversed(spec['changes']):
        new, old = change['new'].encode(), change['old'].encode()
        assert restored.count(new) == 1, (name, change['operation'])
        restored = restored.replace(new, old, 1)
    assert restored == before
    inverse.append({'file': str(source_prefix / name), 'literalOperations': len(spec['changes']),
                    'beforeSHA256': sha(before), 'afterSHA256': sha(after),
                    'inverseRestoresCurrent53aExactBytes': True})

test_path = Path('NativeApp/UITests/NativeLaunchTests.swift')
old = (ROOT / 'sources' / CURRENT / test_path).read_bytes()
new = (ROOT / 'sources' / DONOR / test_path).read_bytes()
assert len(old) == owner['exactPrefixBytes'] and sha(old) == owner['exactPrefixSHA256']
assert new.startswith(old)
assert sha(new[:owner['original19Bytes']]) == owner['original19SHA256']
suffix = new[len(old):]
assert suffix == (ROOT / 'native-styled-suffix.swift').read_bytes()
assert sha(suffix) == owner['suffixSHA256']
methods = lambda data: re.findall(rb'\bfunc\s+(test\w+)\s*\(', data)
assert [x.decode() for x in methods(old)] == owner['originalMethods']
assert [x.decode() for x in methods(suffix)] == owner['addedMethods']
assert len(methods(new)) == 23 and len(set(methods(new))) == 23

editor_before = (ROOT / 'sources' / CURRENT / source_prefix / 'AnyNativeEditor.swift').read_text()
editor_after = (ROOT / 'sources' / DONOR / source_prefix / 'AnyNativeEditor.swift').read_text()
pattern = r'    public func presentHanlin\(\) \{.*?\n    \}\n'
before_function = re.search(pattern, editor_before, re.S).group().encode()
after_function = re.search(pattern, editor_after, re.S).group().encode()
assert after_function == before_function
assert sha(after_function) == owner['preservedHanlinFunctionSHA256']

refs = read_json(ROOT / 'docs/source-references.json')
verified_refs = []
for row in refs['references']:
    path = (ROOT / 'references/PinkhaWritingDirectionPolicy.swift') if row['path'].endswith('PinkhaWritingDirectionPolicy.swift') else (
        ROOT.parent / 'miniapps-independent-typography-review' / refs['designKitReferenceCommit'] / row['path'])
    item = ident(path)
    assert item['sha256'] == row['sha256'] and item['gitBlob'] == row['gitBlob'], row['path']
    verified_refs.append(dict(row, localPath=str(path), bytes=item['bytes']))

donor = read_json(ROOT / 'github-donor-commit.json')
parent = read_json(ROOT / 'github-donor-parent.json')
assert donor['sha'] == DONOR and len(donor['parents']) == 1
assert donor['parents'][0]['sha'] == parent['sha'] == '9e685fe9a19187b8b00430506e34ab5d74c1b1d4'
assert {p['sha'] for p in parent['parents']} == {
    'dfbb481102226e5484b5b8e4dd730661f9b03d14', '0e964628b520f5f8f13c827f557ad9c585e7103c'}
source_changes = [x['filename'] for x in donor['files'] if not x['filename'].startswith('docs/')]
assert set(source_changes) == {str(source_prefix / 'AnyNativeEditor.swift'), str(source_prefix / 'AnySemanticAnchorObservation.swift'), str(test_path)}
assert len(donor['files']) == 14

initial = (ROOT / 'docs/native_styled_block_addition.swift.txt').read_bytes()
assert sha(initial) == owner['priorReviewedSuffixSHA256']
correction_diff = ''.join(difflib.unified_diff(initial.decode().splitlines(True), suffix.decode().splitlines(True),
    fromfile='retained-initial-suffix', tofile='published-final-suffix'))
(ROOT / 'font-run-correction.diff').write_text(correction_diff)

proof = {
    'schema': 'pinkha-independent-w2-styled-byte-review/v1',
    'status': 'PASS_SOURCE_BYTES_ONLY_NOT_COMPILER_OR_RUNTIME',
    'currentRootCommit': CURRENT, 'donorCommit': DONOR, 'donorTree': donor['commit']['tree']['sha'],
    'donorParent': parent['sha'], 'dependencyParents': [x['sha'] for x in parent['parents']],
    'donorChangedPaths': [{k:x[k] for k in ['filename','sha','status','additions','deletions'] if k in x} for x in donor['files']],
    'verifiedInputs': inputs, 'inverse': inverse,
    'original21': {'bytes': len(old), 'sha256': sha(old), 'methods': [x.decode() for x in methods(old)], 'completeExactPrefix': True},
    'original19': {'bytes': owner['original19Bytes'], 'sha256': owner['original19SHA256'], 'completeExactPrefix': True},
    'candidate23': ident(ROOT / 'sources' / DONOR / test_path),
    'additiveSuffix': {'bytes':len(suffix), 'sha256':sha(suffix), 'methods':[x.decode() for x in methods(suffix)]},
    'preservedHanlinFunction': {'bytes':len(after_function),'sha256':sha(after_function),'exactCurrent53aBytes':True},
    'sourceReferences':verified_refs, 'fontRunCorrectionDiff':ident(ROOT / 'font-run-correction.diff'),
    'reuseBoundary': 'Original source identities and retained owner reviews verified. No compilation, enumeration, XCTest, simulator, native or product execution occurred.',
}
(ROOT / 'independent-byte-proof.json').write_text(json.dumps(proof,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'status':proof['status'],'inputs':len(inputs),'literalInverseOperations':sum(x['literalOperations'] for x in inverse),
    'sourceReferences':len(verified_refs),'originalMethods':len(methods(old)),'candidateMethods':len(methods(new)),
    'proof':ident(ROOT / 'independent-byte-proof.json')},indent=2))
