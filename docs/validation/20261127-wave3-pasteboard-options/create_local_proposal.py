"""Construct a source-only review packet from exact retained primary bytes."""
from pathlib import Path
import base64
import datetime
import hashlib
import json

BASE = Path('/workspace/scratch/ae335eba85e3')
ROOT = BASE / 'otzaria-pasteboard-retention-proposal'
CANDIDATE = BASE / 'otzaria-pasteboard-quarantined-candidate'
SOURCE = 'Anytype/Sources/ServiceLayer/Block/Pastboard/PasteboardHelper.swift'
MAP = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
REGISTER = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'


def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'gitBlob': hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()}


def put(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def put_json(path, value):
    put(path, (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n').encode())


original = (ROOT / 'original586c' / SOURCE).read_bytes()
current = (CANDIDATE / 'before' / SOURCE).read_bytes()
candidate = (CANDIDATE / 'after' / SOURCE).read_bytes()
assert original == current
assert identity(original)['gitBlob'] == '995df1ccf9a3131919d89bb398bed38594cb47f8'
assert identity(candidate)['gitBlob'] == 'e7d115cd681318953bc669a436b72a730114f7ea'
response = json.loads((ROOT / 'root275-gate.primary.json').read_text())['structuredContent']
gate = base64.b64decode(''.join(response['content'].split()), validate=True)
assert identity(gate)['gitBlob'] == response['sha']
assert b'"Anytype/Sources"' in gate and b'kind in ("refactor", "import_only")' in gate
put(ROOT / 'before/Tools/AnyEnginePort/verify_source_retention.py', gate)
map_raw = (ROOT / 'before' / MAP).read_bytes()
mapping = json.loads(map_raw)
assert mapping['schemaVersion'] == 1 and len(mapping['changes']) == 132
assert mapping['baselineCommit'] == '586c98bcc17dee425664224e508fc0e8df277678'
assert not any(row['from'] == SOURCE for row in mapping['changes'])
row = {
    'kind': 'refactor', 'from': SOURCE, 'to': SOURCE,
    'baselineBlob': identity(original)['gitBlob'],
    'replacementBlob': identity(candidate)['gitBlob'],
    'reason': 'Supply the explicit empty PropertyListSerialization read options required by the current original Foundation API at the existing pasteboard decode call; preserve every other original byte and the existing decode/result/error behavior.',
    'sharedSources': [],
    'validation': [
        '2026-11-27 Wave3: exact original586c98 and current2752229 source are byte-identical (6258 bytes, Git blob995df1ccf9a3131919d89bb398bed38594cb47f8, SHA2561edd18bf419c01fb88f72dcbca367e3417b2b8993394d1d0a3190dcb685b7eb0). One13-byte insertion of options:[] produces6271 bytes/Git blobe7d115cd681318953bc669a436b72a730114f7ea/SHA2560eee42f7036e43d74d82088b2bd21696dc3b248f4430e4c9dfc887bbbc1a60d9. The full literal inverse restores the entire original file.',
        'The candidate equals the original Otzaria SDK owner d609 cutover result published as Maktabah1b9a917b: CUTOVER_RESULT.json SHA256277a572634499e1498614d9c7a313a2853cea0884f881e3b81edfe6934176e88. That receipt records a source-only fast-forward and builds_run0; full framework ancestry/ABI adoption remains separate.',
        'Root authorized independent reuse against the exact current preimage. No framework target, SDK/native pin, account, storage, permission or public product API is changed. Apple compilation and native/runtime acceptance of this shared App delta remain NOT_RUN. See docs/validation/20261127-wave3-pasteboard-options/source-intake.json and literal-inverse.json.',
    ],
}
put_json(ROOT / 'proposed-row133.json', row)
marker = b'\n  ],\n  "integration": {'
assert map_raw.count(marker) == 1
offset = map_raw.index(marker)
assert map_raw[:offset].endswith(b'    }')
formatted = '\n'.join('    ' + line for line in json.dumps(row, indent=2, ensure_ascii=False).splitlines()).encode()
insert = b',\n' + formatted
map_candidate = map_raw[:offset] + insert + map_raw[offset:]
parsed = json.loads(map_candidate)
assert len(parsed['changes']) == 133 and parsed['changes'][:-1] == mapping['changes']
assert parsed['changes'][-1] == row
assert map_candidate[:offset] + map_candidate[offset + len(insert):] == map_raw
put(ROOT / 'after' / MAP, map_candidate)

register = (ROOT / 'before' / REGISTER).read_bytes()
append = '''

## 2026-11-27 — Original Pasteboard property-list options compatibility

The owner's Wave3 integration authorization covers this single original call-site correction. The pinned retention baseline is `586c98bcc17dee425664224e508fc0e8df277678`; its `Anytype/Sources/ServiceLayer/Block/Pastboard/PasteboardHelper.swift` is byte-identical to the reviewed integration source `2752229aacf72f468f32a4bfe5fe0a91142f5dbe`: 6,258 bytes, Git blob `995df1ccf9a3131919d89bb398bed38594cb47f8`, SHA-256 `1edd18bf419c01fb88f72dcbca367e3417b2b8993394d1d0a3190dcb685b7eb0`.

The existing call to `PropertyListSerialization.propertyList(from: data, format: nil)` receives the required explicit empty `options: []` argument. This is one thirteen-byte insertion at the original decode site. A downstream helper cannot supply a missing argument to this call without changing or redirecting the same original call site; retaining the existing call with the explicit empty options is the smaller compatibility change. The decoded data, property-list format handling, result conversion, errors and all other original bytes remain unchanged. No new parsing mode or mutable-container option is enabled.

The candidate is 6,271 bytes, Git blob `e7d115cd681318953bc669a436b72a730114f7ea`, SHA-256 `0eee42f7036e43d74d82088b2bd21696dc3b248f4430e4c9dfc887bbbc1a60d9`. It exactly matches the original Otzaria SDK owner's source correction recorded in Maktabah commit `1b9a917b5d129a98767e3e284edae55256d1d891`, `CUTOVER_RESULT.json` SHA-256 `277a572634499e1498614d9c7a313a2853cea0884f881e3b81edfe6934176e88`. The donor's local `d6090c03b9ac4e5760941e34f4c04478db4ae59f` and parent `1be970356c655bcef3688ddf1d129d5029bbc533` were not available through the observed public ref. This integration reuses the independently reconstructed, whole-hash-matching hunk against the published current preimage; it does not adopt the donor's framework target, public/SPI/ABI closure, native libraries or package graph.

The original SDK compiler failure and source-only cutover remain distinct: the retained cutover explicitly records `builds_run: 0`. No shared-App compiler, native journey or product acceptance is inferred from that source correction. The exact source preimage, immutable published donor evidence and full forward/inverse are retained under `docs/validation/20261127-wave3-pasteboard-options/`. The preservation map adds one `refactor` row for this original path, with the exact original and replacement blobs; existing 132 rows are retained. Concurrent root-owned SDK mapping updates are a separate integration decision.

Rollback removes only the explicit empty argument and this path's corresponding mapping/exception addition, using the complete retained original file. It does not reset framework checkouts, alter source pins, remove old failures or invalidate original evidence. The final shared Apple compile and ordinary pasteboard behavior remain part of the integrated acceptance.
'''.encode()
assert '## 2026-11-27 — Original Pasteboard property-list options compatibility'.encode() not in register
register_candidate = register + append
assert register_candidate[:len(register)] == register and register_candidate[:-len(append)] == register
put(ROOT / 'after' / REGISTER, register_candidate)
put(ROOT / 'before' / SOURCE, current)
put(ROOT / 'after' / SOURCE, candidate)
put(ROOT / 'literal-inverse.json', (CANDIDATE / 'literal-inverse.json').read_bytes())
for path in sorted((CANDIDATE / 'donor-evidence').iterdir()):
    assert path.is_file()
    put(ROOT / 'donor-evidence' / path.name, path.read_bytes())

put_json(ROOT / 'map-append-inverse.json', {
    'schema': 'pinkha-single-source-retention-row-append-v1', 'path': MAP,
    'before': identity(map_raw), 'after': identity(map_candidate),
    'originalRows': 132, 'newRows': 133, 'original132RowsUnchanged': True,
    'insertionByteOffset': offset, 'insertedUTF8': insert.decode(),
    'fullInverseRestoresOriginal': True, 'newRow': row,
    'concurrentRootRows': 'Rows17/102 and other separately reviewed SDK mapping changes are not modified. Append this row to the root-composed map; do not overwrite it with the illustrative full candidate.',
})
put_json(ROOT / 'exception-append-inverse.json', {
    'schema': 'pinkha-upstream-exception-append-v1', 'path': REGISTER,
    'before': identity(register), 'after': identity(register_candidate),
    'appendUTF8': append.decode(), 'completeOriginalPrefixUnchanged': True,
    'fullInverseRestoresOriginal': True,
})
proposal = {
    'schema': 'pinkha-original-pasteboard-retention-proposal-v1',
    'status': 'READY_SOURCE_PROPOSAL_NOT_APPLIED_OR_TESTED',
    'reviewedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'baselineCommit': '586c98bcc17dee425664224e508fc0e8df277678',
    'currentCommit': '2752229aacf72f468f32a4bfe5fe0a91142f5dbe',
    'baselineAndCurrentByteIdentical': True, 'sourcePath': SOURCE,
    'original': identity(original), 'candidate': identity(candidate),
    'originalSourceProtectedByCurrentGate': True, 'exclusionReason': None,
    'gate': {'path': 'Tools/AnyEnginePort/verify_source_retention.py', **identity(gate),
             'sourceOnlyRead': True, 'executed': False},
    'map': {'original': identity(map_raw), 'illustrativeCandidate': identity(map_candidate),
            'originalRows': 132, 'appendRows': 1, 'resultRows': 133,
            'originalRowsPreserved': True, 'rowFile': 'proposed-row133.json',
            'inverse': 'map-append-inverse.json',
            'applyPolicy': 'Root appends only this exact row after its own17/102 and other reviewed composition changes. The full illustrative map must not overwrite the root-composed map.'},
    'upstreamException': {'original': identity(register), 'illustrativeCandidate': identity(register_candidate),
                          'inverse': 'exception-append-inverse.json', 'originalPrefixRetained': True},
    'sourceCandidateIntake': {'path': str(CANDIDATE / 'source-intake.json'),
                              **identity((CANDIDATE / 'source-intake.json').read_bytes())},
    'publicationBoundary': 'This independent exact-preimage one-hunk correction does not wait for unavailable donor ancestry. Root accepted its reuse in principle. Full OriginalEditorFramework/SDK/ABI closure remains separate and pending.',
    'noOtherSourceChanges': True, 'noFrameworkTargetSDKNativeOrABIChange': True,
    'sourceRetentionGateResult': 'NOT_RUN_BY_THIS_SOURCE_PROPOSAL; root verifies the actual staged combined tree',
    'compilerTestsNativeRuns': 0, 'remoteOrRepositoryWrites': 0,
    'suggestedGitEvidencePrefix': 'docs/validation/20261127-wave3-pasteboard-options/',
    'localPreparationDiagnostic': 'An earlier inline packet script failed Python parsing on a non-ASCII bytes literal before any statement ran. The corrected source packet uses explicit UTF-8 encoding. No candidate test or retention gate was executed.',
}
put_json(ROOT / 'source-intake.json', proposal)
files = [{'path': str(path.relative_to(ROOT)), **identity(path.read_bytes())}
         for path in sorted(ROOT.rglob('*')) if path.is_file()]
put_json(ROOT / 'artifact-index.json', {'schema': 'pinkha-pasteboard-retention-index-v1', 'files': files})
print(json.dumps({'root': str(ROOT), 'sourceIntake': identity((ROOT / 'source-intake.json').read_bytes()),
                  'row': identity((ROOT / 'proposed-row133.json').read_bytes()),
                  'mapInverse': identity((ROOT / 'map-append-inverse.json').read_bytes()),
                  'exceptionInverse': identity((ROOT / 'exception-append-inverse.json').read_bytes()),
                  'artifactIndex': identity((ROOT / 'artifact-index.json').read_bytes()),
                  'filesBeforeIndex': len(files)}, indent=2))
