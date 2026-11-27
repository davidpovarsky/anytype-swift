#!/usr/bin/env python3
"""Local finite source derivation only; no stager/runner import or invocation."""
from pathlib import Path
import argparse
import ast
import base64
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
OLD = WORK / 'wave2-property-unicode-audit/component-preparation/staging-preparation'
OUT = HERE / 'staging-preparation'
ROOT = '/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127'
OLD_ROOT = '/mnt/development/projects/evidence/pinkha-wave2-property-text-readback-20261127'
PRODUCT = '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path, relative=False):
    raw = path.read_bytes()
    return {'path': path.name if relative else str(path), 'bytes': len(raw), 'sha256': sha(raw)}


def write(path, raw):
    assert not path.exists(), 'Retain prior preparation; do not silently overwrite: ' + str(path)
    path.write_bytes(raw)


def emit(path, value):
    write(path, (json.dumps(value, sort_keys=True, indent=2) + '\n').encode())


args_parser = argparse.ArgumentParser()
args_parser.add_argument('--runner-review', required=True)
args = args_parser.parse_args()
review_path = Path(args.runner_review).resolve(strict=True)
review_raw = review_path.read_bytes()
runner_path = HERE / 'execution-preparation/inputs/run_component.py'
runner_sha = sha(runner_path.read_bytes())
assert runner_sha == 'f63adbdfde8bfa5d1779371e1c046f196e617f2f286181dc6c8c7768414e3628'
assert runner_sha in review_raw.decode(), 'Review must explicitly bind this frozen runner.'

packet_path = HERE / 'execution-preparation/input-packet.json'
packet_raw = packet_path.read_bytes()
packet = json.loads(packet_raw)
assert sha(packet_raw) == 'ed3ef9bfce4119bc199934d4740a09f5e0e621abd0806a45e831f392cf043df6'
payload = json.loads((OUT / 'payload-readback.json').read_text())
packed_sha = payload['payload']['sha256']
assert packed_sha == 'b4ef0e166fe306118eeb099df5781451fc0716134ba382c9d8803861459c95b3'
packed_size = payload['payload']['bytes']
assert packed_size == 229322 and payload['rawJSONBytes'] == 1068552
upload_payload = 'pinkha-wave2-hierarchy-rename-inputs-' + packed_sha[:16] + '.json.gz'

old = (OLD / 'materialize_and_exec.py').read_bytes()
assert sha(old) == '2a7ef1c0d7f5957ef1194b27d34a5456d254b1d077f6e3eceda628925f236a1b'
source = old.decode()
replacements = [
    ('Stage one exact Property4 input packet', 'Stage one exact hierarchy4/8 input packet', 1),
    (OLD_ROOT, ROOT, 1),
    ('pinkha-wave2-property4-inputs-6ca564dc104259a8.json.gz', upload_payload, 1),
    ('6ca564dc104259a8de2aa593ac28bad1b11e0059b8f52a1cdd4dee701449459a', packed_sha, 1),
    ('b6a0e1b7e267986dc55bf1e2fd941174613890c088115789d29624d3a3a3c4c3', payload['rawJSONSHA256'], 1),
    ('66d0f3453087ac8df6a9bf54cf3bdcbc65f645934facfaaa91cc8fd703d81083', sha(packet_raw), 1),
    ('66f09e18e07cca8a2056d0c8b51ffa318433f28bf9cb7f255f7a0c9bd9db9ea8', runner_sha, 1),
    ('pinkha-property4-input-materialization-receipt/v1', 'pinkha-hierarchy-rename-input-materialization-receipt/v1', 1),
    ('937a8167700481b71c3c2eeb8771634d2c6bbc4f', PRODUCT, 2),
    ('f6e2f9f148c5acc34548a61353a4c0864c9952ccafd8f7c0cd007e7b4ea3790f', sha(review_raw), 1),
    ('before.st_size == 330008', 'before.st_size == ' + str(packed_size), 1),
    ('len(packed) == 330008', 'len(packed) == ' + str(packed_size), 1),
    ('len(raw) == 1499805', 'len(raw) == ' + str(payload['rawJSONBytes']), 1),
    ('pinkha-property4-fixed-input-materialization/v1', 'pinkha-hierarchy-rename-fixed-input-materialization/v1', 1),
    ("len(packet['files']) == len(payload['entries']) == 84", "len(packet['files']) == len(payload['entries']) == 61", 1),
    ("packet['bytes'] == 1098479", "packet['bytes'] == 781373", 1),
    ('len(expected) == 84', 'len(expected) == 61', 1),
    ('sum(map(len, decoded.values())) == 1098479', 'sum(map(len, decoded.values())) == 781373', 1),
]
for before, after, count in replacements:
    assert source.count(before) == count, (before, source.count(before), count)
    source = source.replace(before, after)
new = source.encode()
ast.parse(new)
inverse_text = source
for before, after, count in reversed(replacements):
    assert inverse_text.count(after) == count, after
    inverse_text = inverse_text.replace(after, before)
assert inverse_text.encode() == old

old_lines, new_lines = old.splitlines(keepends=True), new.splitlines(keepends=True)
hunks = []
for tag, a, b, c, d in difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False).get_opcodes():
    if tag != 'equal':
        hunks.append({'originalByteOffset': sum(map(len, old_lines[:a])),
                      'candidateByteOffset': sum(map(len, new_lines[:c])),
                      'oldBase64': base64.b64encode(b''.join(old_lines[a:b])).decode(),
                      'newBase64': base64.b64encode(b''.join(new_lines[c:d])).decode()})
back = new
for row in reversed(hunks):
    pos = row['candidateByteOffset']; candidate = base64.b64decode(row['newBase64'])
    assert back[pos:pos+len(candidate)] == candidate
    back = back[:pos] + base64.b64decode(row['oldBase64']) + back[pos+len(candidate):]
assert back == old
forward = old
for row in reversed(hunks):
    pos = row['originalByteOffset']; original = base64.b64decode(row['oldBase64'])
    assert forward[pos:pos+len(original)] == original
    forward = forward[:pos] + base64.b64decode(row['newBase64']) + forward[pos+len(original):]
assert forward == new


def functions(raw):
    text = raw.decode(); lines = text.splitlines(keepends=True)
    return {node.name: ''.join(lines[node.lineno-1:node.end_lineno]) for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}


old_functions, new_functions = functions(old), functions(new)
unchanged = [name for name in old_functions if old_functions[name] == new_functions[name]]
assert unchanged == ['sha', 'now', 'physical', 'budget', 'mkdir_owned', 'crypto_sources']
assert source.count('os.execv(') == 1 and 'subprocess' not in source
write(OUT / 'materialize_and_exec.py', new)
write(OUT / 'source.patch', ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True), source.splitlines(keepends=True),
      fromfile='Property4/materialize_and_exec.py', tofile='HierarchyRename/materialize_and_exec.py')).encode())
derivation = {'schema': 'pinkha-hierarchy-rename-stager-source-derivation/v1',
              'status': 'LOCAL_EXACT_BIDIRECTIONAL_INVERSE_AND_AST_ONLY',
              'originalStager': pin(OLD / 'materialize_and_exec.py'), 'candidateStager': pin(OUT / 'materialize_and_exec.py'),
              'originalRootReview': pin(OLD / 'root-stager-review.json'),
              'originalPeerReview': pin(OLD / 'interfaces-independent-stager-review.json'),
              'newRunnerReview': pin(review_path), 'inputPacket': pin(packet_path),
              'replacements': [{'old': before, 'new': after, 'count': count} for before, after, count in replacements],
              'fullByteInverse': {'originalBytes': len(old), 'originalSHA256': sha(old), 'candidateBytes': len(new),
                                   'candidateSHA256': sha(new), 'hunks': hunks, 'bidirectionalExact': True},
              'unchangedFunctionBodies': [{'name': name, 'sha256': sha(new_functions[name].encode())} for name in unchanged],
              'onlyMainChanges': 'Source/root/schema/review/hash/size/count literals. All admission, immutable-path creation, payload validation, dependency custody, partial-failure retention, cwd/PWD and exec flow remain exact.',
              'newProcessManager': False, 'stagerOrRuntimeProcessInvocationsDuringPreparation': 0,
              'stagerExecuted': False, 'runnerExecuted': False, 'runtimeSlotGranted': False}
emit(OUT / 'stager-derivation.json', derivation)

stager_sha = sha(new)
upload_stager = 'pinkha-wave2-hierarchy-rename-stage-' + stager_sha[:16] + '.py'
transport = {'schema': 'pinkha-hierarchy-rename-exact-transport/v1', 'status': 'PREPARED_NOT_UPLOADED_OR_EXECUTED',
             'productCommit': PRODUCT, 'root': ROOT, 'inputFiles': 61, 'inputBytes': 781373,
             'packetSHA256': sha(packet_raw), 'controllerSHA256': runner_sha,
             'stager': pin(OUT / 'materialize_and_exec.py', True),
             'stagerUploadRelativePath': upload_stager, 'stagerAbsolutePath': '/var/lib/sentinelx/uploads/' + upload_stager,
             'payload': payload['payload'], 'base64Transport': payload['base64Transport'],
             'payloadUploadRelativePath': upload_payload, 'payloadAbsolutePath': '/var/lib/sentinelx/uploads/' + upload_payload,
             'rawJSONBytes': payload['rawJSONBytes'], 'rawJSONSHA256': payload['rawJSONSHA256'],
             'gzipMtime': 0, 'decodedPayloadMatchesAll61ExactInputRows': True,
             'payloadEnumeratesOuterDocs': False, 'outerDocsAndReviewsAreSeparatePublicationEvidence': True,
             'uploaded': False, 'runtimeExecuted': False}
emit(OUT / 'transport-manifest.json', transport)
invocation = {'schema': 'pinkha-hierarchy-rename-one-shot-handoff/v1', 'status': 'NOT_ADMITTED_NOT_UPLOADED_NOT_EXECUTED',
              'remoteMutationOwner': '/root', 'attemptCount': 1, 'automaticRetries': 0, 'coordinationStory': None,
              'requiredCoordinationStoryPattern': '^[0-9]{16}$',
              'argvPrefixRequiringExactlyOneActualCoordinationStory': ['/usr/bin/python3', '-B', transport['stagerAbsolutePath'], '--coordination-story'],
              'expectedWorkingDirectoryBeforeControllerExec': ROOT, 'expectedPWD': ROOT,
              'controllerSwiftCommandDeadlineSeconds': 300,
              'originalOwnedCleanupSHA256': '58624c3f6eae79e5417576ba88d24fe15919681ca6ac112e14e664b9ab12b924',
              'stagerCreatesNoChildProcess': True, 'noExternalTimeoutProcessManagerAdded': True,
              'sourceDerivative': pin(OUT / 'stager-derivation.json', True),
              'transportManifest': pin(OUT / 'transport-manifest.json', True),
              'requiredBeforeInvocation': ['Root/peer accept the exact stager and payload tuple',
                  'Preparation publication and exact upload/readback complete',
                  'W1 current runtime owner releases the slot; root records the actual coordination story',
                  'Fresh original source/dependency/resource predicates all pass'],
              'runtimeSlotGranted': False}
emit(OUT / 'one-shot-invocation.json', invocation)
print(json.dumps({'stager': pin(OUT / 'materialize_and_exec.py'), 'inverse': pin(OUT / 'stager-derivation.json'),
                  'transport': pin(OUT / 'transport-manifest.json'), 'invocation': pin(OUT / 'one-shot-invocation.json'),
                  'unchangedFunctions': unchanged}, indent=2))
