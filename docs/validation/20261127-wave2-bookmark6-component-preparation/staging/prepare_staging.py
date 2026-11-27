#!/usr/bin/env python3
"""Assemble one fixed local payload and literal stager derivative; never run either."""
from pathlib import Path
import ast
import base64
import difflib
import gzip
import hashlib
import json
import stat

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
EXECUTION = HERE / 'execution-preparation'
INPUTS = EXECUTION / 'inputs'
OUT = HERE / 'staging-preparation'
DONOR = WORK / 'wave2-hierarchy-rename-component/staging-preparation'
DONOR_ACTUAL = WORK / 'wave2-hierarchy-rename-component/runtime-attempt1-root-custody'
ROOT = '/mnt/development/projects/evidence/pinkha-wave2-bookmark6-20261127'
PRODUCT = '3d2abbf8b1017204e2b93b53ea83ff6f053e67b3'
PACKET_SHA = '2341bdb226521d368b37f37c402c83b6bb20ae1db6efe4d7f65938198f5f1353'
RUNNER_SHA = '3729eed7d91e3400c19137420df96465d4785c0bd9587d81553864e1041f176c'
PACKAGE_SHA = 'e030600787c19dee1002c8223b34fe499e5832d213259c8796eb164fb3ed83be'
ROOT_REVIEW_SHA = '4e829323bf17271712bfbb8696ed832d621be8ca3a6e794c2bcae5b21d44e8f0'
PEER_REVIEW_SHA = 'b9b104c5f9ab799c0f191746b50a745821607d55f4b29e1146c148fd30291329'
DONOR_SHA = 'b3cfea8a789c4abae7f2f2b8aa3202dc7cf2725a5fae2438eb5c5c9d6342f7eb'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def function_bodies(raw):
    lines = raw.decode().splitlines(keepends=True)
    return {node.name: ''.join(lines[node.lineno - 1:node.end_lineno]).encode()
            for node in ast.parse(raw).body if isinstance(node, ast.FunctionDef)}


assert not OUT.exists(), 'Retain any prior staging preparation; never overwrite it.'
packet_path = EXECUTION / 'input-packet.json'
packet_raw = packet_path.read_bytes()
assert sha(packet_raw) == PACKET_SHA
packet = json.loads(packet_raw)
assert packet['futureFixedRoot'] == ROOT and packet['productCommit'] == PRODUCT
assert packet['fileCount'] == len(packet['files']) == 90 and packet['bytes'] == 1344177
assert packet['runtimeReady'] is False and packet['runtimeSlotGranted'] is False
assert packet['proposedResourceBound'] == {
    'admissionMarginBytes': 33554432, 'developmentFloorBytes': 536870912,
    'finalEvidenceReserveWithinCapBytes': 1048576, 'jobs': 2,
    'memoryFloorBytes': 536870912, 'ownedAllocationCapBytes': 268435456,
    'rootFloorBytes': 2147483648, 'seconds': 300,
}
assert sha((INPUTS / 'run_component.py').read_bytes()) == RUNNER_SHA
assert sha((INPUTS / 'component/Package.swift').read_bytes()) == PACKAGE_SHA
review_path = EXECUTION / 'root-execution-source-review-v2.json'
peer_path = EXECUTION / 'torah-independent-review-v2.json'
assert sha(review_path.read_bytes()) == ROOT_REVIEW_SHA
assert sha(peer_path.read_bytes()) == PEER_REVIEW_SHA
assert RUNNER_SHA in review_path.read_text() and PACKET_SHA in review_path.read_text()

entries = []
originals = {}
for row in packet['files']:
    relative = Path(row['path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    assert relative.as_posix() == row['path'] and row['mode'] == '100644'
    source = INPUTS / relative
    assert source.is_file() and not source.is_symlink()
    raw = source.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    assert git_blob(raw) == row['gitBlob']
    destination = 'inputs/' + row['path']
    assert destination not in originals
    originals[destination] = raw
    entries.append({'path': destination, 'contentBase64': base64.b64encode(raw).decode()})
assert len(entries) == 90 and sum(map(len, originals.values())) == 1344177
assert {p.relative_to(INPUTS).as_posix() for p in INPUTS.rglob('*') if p.is_file()} == {
    row['path'] for row in packet['files']
}
payload_value = {'schema': 'pinkha-bookmark6-fixed-input-materialization/v1',
                 'packetBase64': base64.b64encode(packet_raw).decode(), 'entries': entries}
payload_raw = json.dumps(payload_value, sort_keys=True, separators=(',', ':')).encode()
packed = gzip.compress(payload_raw, compresslevel=9, mtime=0)
transport_base64 = base64.b64encode(packed) + b'\n'
decoded = json.loads(gzip.decompress(base64.b64decode(transport_base64, validate=False)))
assert gzip.decompress(packed) == payload_raw
assert base64.b64decode(decoded['packetBase64'], validate=True) == packet_raw
assert len(decoded['entries']) == 90
for entry in decoded['entries']:
    assert base64.b64decode(entry['contentBase64'], validate=True) == originals[entry['path']]

payload_name = 'bookmark6-inputs.json.gz'
base64_name = payload_name + '.base64'
payload_pin = {'path': payload_name, 'bytes': len(packed), 'sha256': sha(packed)}
base64_pin = {'path': base64_name, 'bytes': len(transport_base64), 'sha256': sha(transport_base64)}
upload_payload = 'pinkha-wave2-bookmark6-inputs-' + sha(packed)[:16] + '.json.gz'
old = (DONOR / 'materialize_and_exec.py').read_bytes()
assert len(old) == 9998 and sha(old) == DONOR_SHA
source = old.decode()
replacements = [
    ('Stage one exact hierarchy4/8 input packet', 'Stage one exact Bookmark6 input packet', 1),
    ('/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127', ROOT, 1),
    ('pinkha-wave2-hierarchy-rename-inputs-b4ef0e166fe30611.json.gz', upload_payload, 1),
    ('b4ef0e166fe306118eeb099df5781451fc0716134ba382c9d8803861459c95b3', sha(packed), 1),
    ('ec0c1a2e04af03cac8e85cc6c7d726c74897768a31825819744e6914dc8016a6', sha(payload_raw), 1),
    ('ed3ef9bfce4119bc199934d4740a09f5e0e621abd0806a45e831f392cf043df6', PACKET_SHA, 1),
    ('f63adbdfde8bfa5d1779371e1c046f196e617f2f286181dc6c8c7768414e3628', RUNNER_SHA, 1),
    ('pinkha-hierarchy-rename-input-materialization-receipt/v1', 'pinkha-bookmark6-input-materialization-receipt/v1', 1),
    ('9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce', PRODUCT, 2),
    ('e152db9ef0e57c44206497b73b2bdfb726e5d83fe942ec3f4f8bb369a968aab8', ROOT_REVIEW_SHA, 1),
    ('before.st_size == 229322', 'before.st_size == ' + str(len(packed)), 1),
    ('len(packed) == 229322', 'len(packed) == ' + str(len(packed)), 1),
    ('len(raw) == 1068552', 'len(raw) == ' + str(len(payload_raw)), 1),
    ('pinkha-hierarchy-rename-fixed-input-materialization/v1', 'pinkha-bookmark6-fixed-input-materialization/v1', 1),
    ("len(packet['files']) == len(payload['entries']) == 61", "len(packet['files']) == len(payload['entries']) == 90", 1),
    ("packet['bytes'] == 781373", "packet['bytes'] == 1344177", 1),
    ('len(expected) == 61', 'len(expected) == 90', 1),
    ('sum(map(len, decoded.values())) == 781373', 'sum(map(len, decoded.values())) == 1344177', 1),
]
for before, after, count in replacements:
    assert source.count(before) == count, (before, count)
    source = source.replace(before, after)
new = source.encode()
ast.parse(new)
restored = source
for before, after, count in reversed(replacements):
    assert restored.count(after) == count, after
    restored = restored.replace(after, before)
assert restored.encode() == old
old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
hunks = []
for tag, a, b, c, d in difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False).get_opcodes():
    if tag != 'equal':
        hunks.append({'originalByteOffset': sum(map(len, old_lines[:a])),
                      'candidateByteOffset': sum(map(len, new_lines[:c])),
                      'oldBase64': base64.b64encode(b''.join(old_lines[a:b])).decode(),
                      'newBase64': base64.b64encode(b''.join(new_lines[c:d])).decode()})
for start, expected, offset_key, from_key, to_key in [
    (new, old, 'candidateByteOffset', 'newBase64', 'oldBase64'),
    (old, new, 'originalByteOffset', 'oldBase64', 'newBase64'),
]:
    value = start
    for hunk in reversed(hunks):
        offset = hunk[offset_key]
        remove = base64.b64decode(hunk[from_key], validate=True)
        assert value[offset:offset + len(remove)] == remove
        value = value[:offset] + base64.b64decode(hunk[to_key], validate=True) + value[offset + len(remove):]
    assert value == expected
old_functions, new_functions = function_bodies(old), function_bodies(new)
unchanged = [name for name in old_functions if old_functions[name] == new_functions[name]]
assert unchanged == ['sha', 'now', 'physical', 'budget', 'mkdir_owned', 'crypto_sources']
assert set(old_functions) == set(new_functions) and source.count('os.execv(') == 1
assert 'subprocess' not in source and '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c' in source

donor_publication = json.loads((WORK / 'wave2-hierarchy-rename-publication/publication-result.json').read_text())
assert donor_publication['commit'] == '8b70497157758f3ae8148842f1236d215d6d2d50'
assert DONOR_SHA in (DONOR_ACTUAL / 'launcher.py').read_text()
donor_result = json.loads((DONOR_ACTUAL / 'root-independent-result-review.json').read_text())
derivation = {
    'schema': 'pinkha-bookmark6-stager-source-derivation/v1',
    'status': 'LOCAL_EXACT_BIDIRECTIONAL_INVERSE_AND_AST_ONLY',
    'originalStager': pin(DONOR / 'materialize_and_exec.py'),
    'originalPublishedCommit': donor_publication['commit'],
    'originalPublishedPath': 'docs/validation/20261127-wave2-hierarchy-rename-component-preparation/staging/materialize_and_exec.py',
    'originalRootStagerReview': pin(DONOR / 'root-stager-review.json'),
    'originalActualLauncher': pin(DONOR_ACTUAL / 'launcher.py'),
    'originalActualResultReview': pin(DONOR_ACTUAL / 'root-independent-result-review.json'),
    'originalActualEvidenceCommit': '0b748192d230966160df010b93987638f5e161b9',
    'candidateStager': {'path': 'materialize_and_exec.py', 'bytes': len(new), 'sha256': sha(new)},
    'newRunnerReview': pin(review_path), 'newRunnerPeerReview': pin(peer_path),
    'inputPacket': pin(packet_path), 'unchangedPackage': pin(INPUTS / 'component/Package.swift'),
    'replacements': [{'old': before, 'new': after, 'count': count} for before, after, count in replacements],
    'fullByteInverse': {'originalBytes': len(old), 'originalSHA256': sha(old), 'candidateBytes': len(new),
                        'candidateSHA256': sha(new), 'hunks': hunks, 'bidirectionalExact': True},
    'unchangedFunctionBodies': [{'name': name, 'sha256': sha(new_functions[name])} for name in unchanged],
    'onlyMainChanges': 'Fixed root/source/review/payload pins, schema labels, sizes and file counts; original admission, source/alias custody, exclusive creation, failure retention and cwd/PWD/exec flow are unchanged.',
    'noHistoricalGroupQueries': True, 'newProcessManager': False,
    'stagerImportedOrExecuted': False, 'runnerImportedOrExecuted': False, 'runtimeSlotGranted': False,
}
readback = {
    'schema': 'pinkha-bookmark6-exact-payload-readback/v1', 'status': 'LOCAL_FULL_90_INPUT_PAYLOAD_READBACK_MATCHES',
    'productCommit': PRODUCT, 'root': ROOT, 'packetSHA256': PACKET_SHA,
    'fileCount': 90, 'inputBytes': 1344177, 'files': packet['files'],
    'payload': payload_pin, 'base64Transport': base64_pin, 'rawJSONBytes': len(payload_raw),
    'rawJSONSHA256': sha(payload_raw), 'gzipMtime': 0, 'gzipCompressLevel': 9,
    'embeddedPacketExactBytes': len(packet_raw), 'allInputGitBlobIDsMatched': True,
    'payloadContainsOuterDocsOrReviewFiles': False, 'cryptoArtifactBodiesIncluded': 0,
    'newDuplicateUncompressedInputTreeCreated': False,
    'stagerOrRunnerInvoked': False, 'uploaded': False,
}
upload_stager = 'pinkha-wave2-bookmark6-stage-' + sha(new)[:16] + '.py'
transport = {
    'schema': 'pinkha-bookmark6-exact-transport/v1', 'status': 'PREPARED_NOT_UPLOADED_OR_EXECUTED',
    'productCommit': PRODUCT, 'root': ROOT, 'inputFiles': 90, 'inputBytes': 1344177,
    'packetSHA256': PACKET_SHA, 'controllerSHA256': RUNNER_SHA,
    'stager': derivation['candidateStager'], 'stagerUploadRelativePath': upload_stager,
    'stagerAbsolutePath': '/var/lib/sentinelx/uploads/' + upload_stager,
    'payload': payload_pin, 'base64Transport': base64_pin,
    'payloadUploadRelativePath': upload_payload, 'payloadAbsolutePath': '/var/lib/sentinelx/uploads/' + upload_payload,
    'rawJSONBytes': len(payload_raw), 'rawJSONSHA256': sha(payload_raw), 'gzipMtime': 0,
    'decodedPayloadMatchesAll90ExactInputRows': True, 'payloadEnumeratesOuterDocs': False,
    'uploaded': False, 'runtimeExecuted': False,
}
derivation_raw = json_bytes(derivation)
transport_raw = json_bytes(transport)
invocation = {
    'schema': 'pinkha-bookmark6-one-shot-handoff/v1', 'status': 'NOT_ADMITTED_NOT_UPLOADED_NOT_EXECUTED',
    'remoteMutationOwner': '/root', 'attemptCount': 1, 'automaticRetries': 0, 'coordinationStory': None,
    'requiredCoordinationStoryPattern': '^[0-9]{16}$',
    'argvPrefixRequiringExactlyOneActualCoordinationStory': ['/usr/bin/python3', '-B', transport['stagerAbsolutePath'], '--coordination-story'],
    'expectedWorkingDirectoryBeforeControllerExec': ROOT, 'expectedPWD': ROOT,
    'expectedSwiftPMWorkingDirectory': ROOT + '/component', 'expectedCompilerWorkingDirectory': ROOT,
    'controllerSwiftCommandDeadlineSeconds': 300, 'originalOuterJobDeadlineSeconds': 360,
    'originalOwnedCleanupSHA256': '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924',
    'originalResourceBound': packet['proposedResourceBound'],
    'stagerCreatesNoChildProcess': True, 'noExternalTimeoutProcessManagerAdded': True,
    'sourceDerivative': {'path': 'stager-derivation.json', 'bytes': len(derivation_raw), 'sha256': sha(derivation_raw)},
    'transportManifest': {'path': 'transport-manifest.json', 'bytes': len(transport_raw), 'sha256': sha(transport_raw)},
    'requiredBeforeInvocation': ['Root and peer accept the exact stager and payload tuple',
        'Separate preparation publication and exact upload/readback complete',
        'W1 current runtime owner releases the slot; Root records an actual coordination story',
        'Fresh original source/dependency/resource predicates all pass'],
    'runtimeSlotGranted': False,
}
artifacts = {
    'materialize_and_exec.py': new,
    payload_name: packed,
    base64_name: transport_base64,
    'payload-readback.json': json_bytes(readback),
    'stager-derivation.json': derivation_raw,
    'transport-manifest.json': transport_raw,
    'one-shot-invocation.json': json_bytes(invocation),
    'source.patch': ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True), source.splitlines(keepends=True),
                    fromfile='ExecutedHierarchy/materialize_and_exec.py', tofile='Bookmark6/materialize_and_exec.py')).encode(),
}
OUT.mkdir()
for name, raw in artifacts.items():
    destination = OUT / name
    with destination.open('xb') as output:
        output.write(raw)
    destination.chmod(0o644)
    assert destination.read_bytes() == raw and stat.S_IMODE(destination.stat().st_mode) == 0o644
print(json.dumps({'stager': derivation['candidateStager'], 'payload': payload_pin,
                  'rawJSONBytes': len(payload_raw), 'rawJSONSHA256': sha(payload_raw),
                  'inverseSHA256': sha(derivation_raw), 'transportSHA256': sha(transport_raw),
                  'inputFiles': 90, 'inputBytes': 1344177, 'unchangedHelperFunctions': unchanged,
                  'stagerOrRunnerInvocations': 0, 'hostCalls': 0}, indent=2))
