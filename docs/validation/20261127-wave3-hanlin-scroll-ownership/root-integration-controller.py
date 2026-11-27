"""Root-owned six-file source intake; no SDK materialization or build invocation."""
import copy
import gzip
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
import traceback

ROOT = pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
G = PRE + ['git', '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'user.name=ChatGPT',
           '-c', 'user.email=chatgpt@openai.com', '-C', str(ROOT)]
START = 'e4556ba1edbf7c698eb04cb1ecc9caaeed34e1ff'
START_TREE = 'e4781f05f8700d506317d6f43aeadbeb0c89dee9'
G07 = 'db7b1c8cc5be5950912b91b8cae4f6e5f19f3a16'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
OLD_SDK = '0ae1920d316b9592cbad0462bea96a07fd1ca351'
NEW_SDK = '4cb6454c1c6e110ead73179c06ada9e909bf250b'
KIT = '26beca175d64a4d34e3567f2bbb4bf308d714478'
PREFIX = 'docs/validation/20261127-wave3-hanlin-scroll-ownership'
SOURCE = 'Tools/Hanlin/source.json'
MAP = 'docs/any-engine-port/SOURCE_REFACTOR_MAP.json'
REGISTER = 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'
OUT = pathlib.Path('/tmp/pinkha-root-sdk4cb-host-source-integration-20261127.json')
PRIOR = pathlib.Path('/tmp/pinkha-root-t5-kit-source-integration-20261127.json')
PAYLOAD = pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-sdk4cb-host-source-payload.json.gz')
GATE_OUT = pathlib.Path('/tmp/pinkha-root-sdk4cb-host-source-retention-20261127.json')
PREVIEW = {
    'exit': 2,
    'stdout': 'docs/validation/20261127-wave3-hanlin-scroll-ownership/six-file-source.patch:10: trailing whitespace.\n+ \ndocs/validation/20261127-wave3-hanlin-scroll-ownership/six-file-source.patch:12: trailing whitespace.\n+ \ndocs/validation/20261127-wave3-hanlin-scroll-ownership/six-file-source.patch:36: trailing whitespace.\n+ \ndocs/validation/20261127-wave3-hanlin-scroll-ownership/six-file-source.patch:333: trailing whitespace.\n+ \ndocs/validation/20261127-wave3-hanlin-scroll-ownership/six-file-source.patch:423: trailing whitespace.\n+ \n',
    'stderr': '',
}
SIX = {
    SOURCE, MAP, REGISTER,
    'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinChatView.swift',
    'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/PinkhaHanlinStrings.swift',
    'Modules/PinkhaAnyHanlin/Sources/PinkhaHanlinUI/Resources/PinkhaHanlin.xcstrings',
}


def h(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def match(raw, row):
    assert len(raw) == row['bytes'] and h(raw) == row['sha256'] and blob(raw) == row['gitBlob']


def b(*args):
    return subprocess.run(G + list(args), capture_output=True, check=True, timeout=45).stdout


def t(*args):
    return b(*args).decode().strip()


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def resources():
    rows = {}
    for name, path, floor in [('root', '/', 2147483648), ('development', str(ROOT), 536870912)]:
        state = os.statvfs(path)
        free = state.f_bavail * state.f_frsize
        assert free >= floor + 67108864, (name, free, floor, 'fixed64MiB source allowance')
        rows[name] = {'freeBytes': free, 'floorBytes': floor, 'sourceAllowanceBytes': 67108864}
    return rows


def safe_path(path):
    p = pathlib.PurePosixPath(path)
    assert not p.is_absolute() and '..' not in p.parts and str(p) == path and '\0' not in path
    return path


def destination_preflight(path, previous):
    target = ROOT / safe_path(path)
    for parent in [target, *target.parents]:
        if parent == ROOT:
            break
        assert not parent.is_symlink(), str(parent)
    if previous is None:
        assert not target.exists(), ('preserve existing untracked destination', path)
    else:
        assert target.is_file() and target.read_bytes() == previous, path


def owned(path, raw, replace):
    safe_path(path)
    code = '''import pathlib,sys
root=pathlib.Path(sys.argv[1]);relative=pathlib.PurePosixPath(sys.argv[2]);p=root/relative
for parent in [p,*p.parents]:
 if parent==root:break
 assert not parent.is_symlink(),str(parent)
p.parent.mkdir(parents=True,exist_ok=True)
if sys.argv[3]=='wb':assert p.is_file()
with p.open(sys.argv[3]) as stream:stream.write(sys.stdin.buffer.read())
'''
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT), path, 'wb' if replace else 'xb'],
                   input=raw, capture_output=True, check=True, timeout=30)


def write_blob(raw):
    result = subprocess.run(G + ['hash-object', '-w', '--stdin'], input=raw,
                            capture_output=True, check=True, timeout=30).stdout.decode().strip()
    assert result == blob(raw)
    return result


def private_tree(entries):
    code = '''import json,os,subprocess,sys,tempfile
root,start,entries=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-sdk4cb-full-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index')
 subprocess.run(g+['read-tree',start],env=env,capture_output=True,check=True,timeout=30)
 for path,sha in sorted(entries.items()):
  subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+sha+','+path],env=env,capture_output=True,check=True,timeout=30)
 print(subprocess.run(g+['write-tree'],env=env,capture_output=True,check=True,timeout=30).stdout.decode().strip())
'''
    return subprocess.run(PRE + ['python3', '-B', '-c', code],
                          input=json.dumps([str(ROOT), START, entries]).encode(),
                          capture_output=True, check=True, timeout=90).stdout.decode().strip()


def exact_changes(reference, expected):
    values = t('diff', '--name-status', '-z', START, reference).split('\0')
    if values and values[-1] == '':
        values.pop()
    assert len(values) % 2 == 0
    actual = dict(zip(values[1::2], values[0::2]))
    assert len(actual) == len(expected) and actual == expected, actual


def diff_check(args):
    result = subprocess.run(G + args, capture_output=True, timeout=45)
    observed = {'exit': result.returncode, 'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()}
    receipt.setdefault('diffChecks', []).append({'argv': args, **observed})
    assert observed == PREVIEW, observed


def pinned_inputs(ref, expected_sdk):
    def read(path):
        return b('show', ref + ':' + path)
    manifest = read(SOURCE)
    sdk = json.loads(manifest)
    assert sdk['revision'] == expected_sdk
    assert sdk == {'repository': 'https://github.com/davidpovarsky/hanlin-ai.git',
                   'revision': expected_sdk,
                   'packages': ['Packages/HanlinAgentSDK', 'Packages/HanlinPlatform',
                                'Packages/HanlinPresentationSDK', 'Packages/HanlinMiniAppsBridge'],
                   'swiftAISDKRevision': 'abf0921c6e89e6521cc2b510ff11016b45a0ef08', 'minimumIOS': '27.0'}
    kit_manifest = read('Modules/PinkhaTorahPresentation/Package.swift')
    assert h(kit_manifest) == 'e519cc067165f89741485fd10566b63e788f9219d11a56429b2d33fd1f21c494'
    assert KIT.encode() in kit_manifest
    lock = read('Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved')
    assert h(lock) == '4065a37e9e6dd3c117bd72bec90c2039108a0985df6989f9dc66b0f47840f689'
    values = json.loads(lock)['pins']
    assert len(values) == 56 and len({v['identity'] for v in values}) == 56
    pins = {v['identity']: v['state'] for v in values}
    assert pins['torahinspectorkit'] == {'revision': KIT}
    assert pins['swift-collections'] == {'revision': '7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e', 'version': '1.3.0'}
    common = read('Tools/MiniApps/receipt_admission.py')
    stage = read('PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift')
    assert h(common) == 'd63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    assert h(stage) == 'c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    core_raw = read('Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json')
    core = json.loads(core_raw)['files']
    assert len(core) == 15
    for path, row in core.items():
        match(read(path), row)
    return {'sdk': sdk, 'kitManifestSHA256': h(kit_manifest), 'packageResolvedSHA256': h(lock),
            'all56PackagePins': values, 'common57SHA256': h(common), 'stage1SHA256': h(stage),
            'core15ManifestSHA256': h(core_raw), 'core15OriginalFiles': core,
            'materializerBlob': blob(read('Tools/Hanlin/prepare_sdk.py'))}


def same_protected_inputs(a, b):
    expected = copy.deepcopy(a)
    expected['sdk']['revision'] = NEW_SDK
    assert b == expected


assert not OUT.exists()
receipt = {'schema': 'pinkha-root-sdk4cb-host-source-integration/v1', 'startedAt': time.time(),
           'parent': START, 'state': 'PREFLIGHT', 'newTestsExecuted': 0, 'materializations': 0}
OUT.open('x').write(json.dumps(receipt, indent=2) + '\n')
try:
    receipt['resourceBefore'] = resources()
    assert not PRIOR.is_symlink()
    prior_raw = PRIOR.read_bytes()
    assert len(prior_raw) == 16417 and h(prior_raw) == '0276688325fbf903b20923b719d48e7635475809e09073d0025aa475343b5f9e'
    prior = json.loads(prior_raw)
    assert prior['schema'] == 'pinkha-root-t5-kit-source-integration/v1'
    assert prior['state'] == 'SOURCE_MERGED_KIT_PIN_PROMOTED_RUNTIME_PENDING'
    assert prior['head'] == START and prior['tree'] == START_TREE and prior['normalPushReadback'] == START
    assert prior['sourceRetentionPassed'] is True and prior['reviewedRefactors'] == 132 and prior['pushExit'] == 0
    assert prior['controllerSHA256'] == '3bd2dccbe1cdad803fa2554ad1d28eff754083e923241744672b71445f629729'
    assert prior['payloadSHA256'] == 'b31aa907de71c7ff8456d7a100b7ab19563c0b91ab829d9c6dd9825ebdca1d86'
    receipt['positivePriorReceiptSHA256'] = h(prior_raw)
    packed = PAYLOAD.read_bytes()
    assert len(packed) == 122914 and h(packed) == '11371cf69c1d0037964ca009a389ee6de0eb37ee303bb6ae52157b8953b24f58'
    raw = gzip.decompress(packed)
    assert len(raw) == 553788 and h(raw) == '1374352be7a1b5b0a37dd3dc86165a5648a03917849fe44760b95ce648d27aac'
    payload = json.loads(raw)
    assert payload['reviewBase'] == G07 and payload['expectedRetentionRows'] == 132
    assert payload['allOriginalPreimagesRequired'] and payload['rootSoleApplyPublishMaterializationOwner']
    assert t('rev-parse', 'HEAD') == START and t('rev-parse', 'HEAD^{tree}') == START_TREE
    assert t('symbolic-ref', 'HEAD') == REF
    subprocess.run(G + ['merge-base', '--is-ancestor', G07, START], capture_output=True, check=True, timeout=30)
    assert not t('diff', '--name-only') and not t('diff', '--cached', '--name-only')
    assert t('write-tree') == START_TREE
    assert not pathlib.Path(t('rev-parse', '--git-path', 'MERGE_HEAD')).exists()
    status_before = b('status', '--porcelain=v1', '--untracked-files=all')
    untracked_before = b('ls-files', '--others', '--exclude-standard', '-z')
    assert t('ls-remote', 'origin', REF).split()[0] == START
    paths = set(t('ls-tree', '-r', '--name-only', START).splitlines())
    rows = payload['files']
    assert len(rows) == 6 and {r['path'] for r in rows} == SIX
    original, candidate, contents = {}, {}, {}
    for row in rows:
        path = safe_path(row['path'])
        assert row['status'] == 'M' and path in paths
        assert t('ls-tree', START, '--', path).split()[0] == '100644'
        original[path] = b('show', START + ':' + path)
        match(original[path], row['before'])
        candidate[path] = row['text'].encode()
        match(candidate[path], row['after'])
        assert row['fullOriginalRestored'] is True
        destination_preflight(path, original[path])
        contents[path] = candidate[path]
    assert json.loads(candidate[SOURCE]) == {**json.loads(original[SOURCE]), 'revision': NEW_SDK}
    assert original[SOURCE].count(OLD_SDK.encode()) == 1
    assert candidate[SOURCE] == original[SOURCE].replace(OLD_SDK.encode(), NEW_SDK.encode(), 1)
    assert len(payload['evidence']) == 17
    for path, row in payload['evidence'].items():
        safe_path(path)
        assert path.startswith(PREFIX + '/') and path not in paths and path not in contents
        data = row['text'].encode()
        match(data, row)
        destination_preflight(path, None)
        contents[path] = data
    inverses = json.loads(contents[PREFIX + '/full-original-literal-inverses.json'])
    assert len(inverses) == 6 and {r['path'] for r in inverses} == SIX
    assert sum(len(r['operations']) for r in inverses) == 17
    for row in inverses:
        restored = candidate[row['path']]
        last = len(restored) + 1
        for op in sorted(row['operations'], key=lambda item: item['newStartByte'], reverse=True):
            begin, end = op['newStartByte'], op['newEndByte']
            assert 0 <= begin <= end < last
            assert restored[begin:end] == op['newLiteral'].encode()
            restored = restored[:begin] + op['originalLiteral'].encode() + restored[end:]
            last = begin
        assert restored == original[row['path']]
    old_map, new_map = json.loads(original[MAP]), json.loads(candidate[MAP])
    assert len(old_map['changes']) == len(new_map['changes']) == 132
    expected_map = copy.deepcopy(old_map)
    delta = json.loads(contents[PREFIX + '/source-map-delta.json'])
    assert delta['changedRowIndices'] == [17, 27, 28, 102] and delta['unchangedWholeRows'] == 128
    assert len(delta['rows']) == 4
    literal_map = original[MAP]
    for row in delta['rows']:
        i, path = row['zeroBasedIndex'], row['path']
        assert row['originalRow'] == old_map['changes'][i]
        assert row['oldBlob'] == blob(original[path]) and row['newBlob'] == blob(candidate[path])
        value = expected_map['changes'][i]
        for key in row['keyPath'][:-1]:
            value = value[key]
        assert value[row['keyPath'][-1]] == row['oldBlob']
        value[row['keyPath'][-1]] = row['newBlob']
        assert expected_map['changes'][i] == row['replacementRow']
        assert literal_map.count(row['oldBlob'].encode()) == 1
        literal_map = literal_map.replace(row['oldBlob'].encode(), row['newBlob'].encode(), 1)
    assert literal_map == candidate[MAP] and new_map == expected_map
    assert [i for i, (a, z) in enumerate(zip(old_map['changes'], new_map['changes'])) if a != z] == [17, 27, 28, 102]
    assert candidate[REGISTER].startswith(original[REGISTER]) and len(candidate[REGISTER]) > len(original[REGISTER])
    assert b'Original Hanlin viewport ownership and shared host follow controls' in candidate[REGISTER][len(original[REGISTER]):]
    before_pins = pinned_inputs(START, OLD_SDK)
    gate_original = b('show', START + ':' + GATE)
    self_raw = pathlib.Path(__file__).read_bytes()
    expected_status = {r['path']: 'M' for r in rows}
    expected_status.update({path: 'A' for path in payload['evidence']})
    entries = {path: write_blob(data) for path, data in contents.items()}
    preview_tree = private_tree(entries)
    exact_changes(preview_tree, expected_status)
    diff_check(['diff', '--check', START, preview_tree])
    expected_after_pins = pinned_inputs(preview_tree, NEW_SDK)
    same_protected_inputs(before_pins, expected_after_pins)
    intake = {
        'schema': 'pinkha-root-sdk4cb-host-source-intake/v1', 'parent': START, 'parentTree': START_TREE,
        'reviewBase': G07, 'positivePriorReceiptSHA256': h(prior_raw), 'positivePriorReceiptOriginalText': prior_raw.decode(),
        'files': [{k: v for k, v in r.items() if k != 'text'} for r in rows],
        'sourceAnd17EvidenceTree': preview_tree, 'fullOriginalInverseOperations': 17,
        'sourceMapRows': 132, 'changedMapIndices': [17, 27, 28, 102], 'unchangedWholeMapRows': 128,
        'allOriginalBaselinesPreserved': True, 'priorRegisterPrefixPreservedBytes': len(original[REGISTER]),
        'beforePins': before_pins, 'afterPins': expected_after_pins,
        'payloadSHA256': h(raw), 'transportSHA256': h(packed), 'controllerSHA256': h(self_raw),
        'originalEvidenceDiffCheck': PREVIEW, 'localPreviewReceiptSHA256': 'c6ef6404467228bc8828321bc64b4d4a4f5b234d55ff900b10d0c03a52fe3543',
        'untrackedPathListSHA256': h(untracked_before), 'originalGateBlob': blob(gate_original),
        'newTestsExecuted': 0, 'materializations': 0,
        'scope': 'Source-only SDK4cb plus corrected shared host. Keep exact original Agent7/quota6/Widget2 scopes. UIKit20 and actual Anytype host/SDK06/NativeScript/Release acceptance remain pending. No Dependencies/Hanlin snapshot is touched.',
    }
    for name, data in [('root-source-intake.json', encode(intake)), ('root-integration-controller.py', self_raw)]:
        path = PREFIX + '/' + name
        assert path not in paths and path not in contents
        destination_preflight(path, None)
        contents[path] = data
        entries[path] = write_blob(data)
        expected_status[path] = 'A'
    assert len(contents) == 25 and len(expected_status) == 25
    expected_tree = private_tree(entries)
    exact_changes(expected_tree, expected_status)
    diff_check(['diff', '--check', START, expected_tree])
    resources()
    assert t('rev-parse', 'HEAD') == START and t('write-tree') == START_TREE
    assert b('status', '--porcelain=v1', '--untracked-files=all') == status_before
    assert b('ls-files', '--others', '--exclude-standard', '-z') == untracked_before
    assert t('ls-remote', 'origin', REF).split()[0] == START
    # Only after the complete private index and every original preimage agree.
    receipt.update(phase='APPLY_SOURCE', expectedTree=expected_tree, sourceAndEvidenceTree=preview_tree)
    for path, data in sorted(contents.items()):
        owned(path, data, replace=path in SIX)
    b('add', '--sparse', '--', *sorted(contents))
    assert t('write-tree') == expected_tree
    exact_changes(expected_tree, expected_status)
    assert t('diff', '--cached', '--name-only').splitlines() == sorted(contents)
    assert not t('diff', '--name-only')
    diff_check(['diff', '--cached', '--check'])
    after_pins = pinned_inputs('', NEW_SDK)
    same_protected_inputs(before_pins, after_pins)
    assert after_pins == expected_after_pins
    assert b('show', ':' + GATE) == gate_original and (ROOT / GATE).read_bytes() == gate_original
    assert not GATE_OUT.exists() and not pathlib.Path(str(GATE_OUT) + '.stdout').exists() and not pathlib.Path(str(GATE_OUT) + '.stderr').exists()
    receipt['phase'] = 'SOURCE_RETENTION_GATE'
    gate = subprocess.run(PRE + ['python3', '-B', str(ROOT / GATE), '--base',
                          '586c98bcc17dee425664224e508fc0e8df277678', '--ref', expected_tree,
                          '--output', str(GATE_OUT)], cwd=ROOT, capture_output=True, timeout=120)
    pathlib.Path(str(GATE_OUT) + '.stdout').open('xb').write(gate.stdout)
    pathlib.Path(str(GATE_OUT) + '.stderr').open('xb').write(gate.stderr)
    result = json.loads(GATE_OUT.read_bytes())
    receipt['gate'] = {'exit': gate.returncode, 'sha256': h(GATE_OUT.read_bytes()),
                       'stdoutSHA256': h(gate.stdout), 'stderrSHA256': h(gate.stderr)}
    assert gate.returncode == 0 and result['sourceRetentionPassed'] is True and len(result['reviewedRefactors']) == 132
    assert b('ls-files', '--others', '--exclude-standard', '-z') == untracked_before
    assert pinned_inputs('', NEW_SDK) == after_pins
    assert t('write-tree') == expected_tree and t('rev-parse', 'HEAD') == START
    message = ('Integrate original Hanlin viewport ownership and shared follow controls\n\n'
               'Promote only the common SDK revision to4cb and apply the reviewed three shared UI files. '
               'Preserve original Composer, native worker/drain, permissions, Save and account/engine fences. '
               'All six exact preimages,17 inverse operations,128 unchanged map rows and132 original retention rows are checked. '
               'Preserve the five literal raw evidence-patch whitespace diagnostics. '
               'Kit26, all55 other package pins, common57, Stage1 and Core15 are unchanged. '
               'No SDK materialization, Apple build, runtime acceptance or Release/TestFlight claim.\n')
    receipt['phase'] = 'COMMIT_SOURCE'
    subprocess.run(G + ['commit', '-F', '-'], input=message.encode(), capture_output=True, check=True, timeout=60)
    head = t('rev-parse', 'HEAD')
    receipt['head'] = head
    assert t('show', '-s', '--format=%P', head).split() == [START]
    assert t('rev-parse', 'HEAD^{tree}') == expected_tree
    assert b('status', '--porcelain=v1', '--untracked-files=all') == status_before
    assert b('ls-files', '--others', '--exclude-standard', '-z') == untracked_before
    assert t('symbolic-ref', 'HEAD') == REF and t('ls-remote', 'origin', REF).split()[0] == START
    receipt.update(head=head, tree=expected_tree, sourceAndEvidenceTree=preview_tree, files=sorted(contents),
                   beforePins=before_pins, inputPins=after_pins, sourceRetentionPassed=True, reviewedRefactors=132,
                   retentionSHA256=h(GATE_OUT.read_bytes()), intakeSHA256=h(encode(intake)),
                   controllerSHA256=h(self_raw), payloadSHA256=h(raw), transportSHA256=h(packed),
                   untrackedPathListSHA256=h(untracked_before))
    receipt['phase'] = 'NORMAL_PUSH'
    push = subprocess.run(G + ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential',
                          'push', 'origin', head + ':' + REF], capture_output=True, text=True, timeout=120)
    receipt.update(pushExit=push.returncode, pushStdout=push.stdout, pushStderr=push.stderr)
    if push.returncode == 0:
        assert t('ls-remote', 'origin', REF).split()[0] == head
        receipt['normalPushReadback'] = head
    assert push.returncode == 0
    receipt['resourceAfter'] = resources()
    receipt['state'] = 'SDK4CB_HOST_SOURCE_PUBLISHED_RUNTIME_PENDING'
except BaseException:
    receipt['state'] = 'FAILED_PRESERVED'
    receipt['error'] = traceback.format_exc()
    raise
finally:
    receipt['completedAt'] = time.time()
    try:
        OUT.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        print(json.dumps({'receipt': str(OUT), 'sha256': h(OUT.read_bytes()), 'state': receipt['state'],
                          'head': receipt.get('head'), 'tree': receipt.get('tree')}), flush=True)
    except BaseException:
        if receipt['state'] != 'FAILED_PRESERVED':
            raise
        print(json.dumps({'state': 'FAILED_PRESERVED', 'firstFailure': receipt.get('error'),
                          'terminalReceiptFailure': traceback.format_exc(), 'head': receipt.get('head')}), flush=True)
