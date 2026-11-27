import gzip, hashlib, json, pathlib, subprocess, time, traceback

ROOT = pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
G = PRE + ['git', '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', '-C', str(ROOT)]
START = '2207b131f45d305ba828c93deb0633e275e59cba'
START_TREE = '81db210134e5eb48125aeac2c8b6a1d51c9702cf'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX = 'docs/validation/20261127-wave3-rpc-torah-native23-source-intake'
OUT = pathlib.Path('/tmp/pinkha-root-rpc-torah-native23-integration-20261127.json')
PAYLOAD = pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-rpc-torah-native23-payload.json.gz')
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'

def h(data): return hashlib.sha256(data).hexdigest()
def blob(data): return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
def b(*args): return subprocess.check_output(G + list(args), stderr=subprocess.PIPE)
def t(*args): return b(*args).decode().strip()
def owned(path, data):
    code = 'import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT / path)], input=data, capture_output=True, check=True)
def exact_original_whitespace(args):
    check = subprocess.run(G + args, capture_output=True)
    assert check.returncode == 2 and not check.stderr and len(check.stdout) == 12680
    assert h(check.stdout) == 'c8f173a05f2a19fbb585781033285ac0afd05accecd60b5175fb22c9417fcc27'
    return {'exit': check.returncode, 'stdoutSHA256': h(check.stdout), 'stdout': check.stdout.decode(), 'passed': False,
            'reviewedScope': 'Exact75 original RPC diagnostics: one unchanged proto whitespace line plus74 literal raw patch context lines'}

assert not OUT.exists()
receipt = {'schema': 'pinkha-root-rpc-torah-native23-integration/v1', 'startedAt': time.time(), 'parent': START, 'state': 'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt, indent=2) + '\n')
try:
    payload_bytes = gzip.decompress(PAYLOAD.read_bytes())
    assert len(payload_bytes) == 683478 and h(payload_bytes) == '37556fe7f635de833a4ee63ee85412af5ebe999e979540e1921f5c233f246d4f'
    payload = json.loads(payload_bytes)
    assert t('rev-parse', 'HEAD') == START and t('rev-parse', 'HEAD^{tree}') == START_TREE and t('symbolic-ref', 'HEAD') == REF
    assert not t('diff', '--name-only') and not t('diff', '--cached', '--name-only')
    assert not pathlib.Path(t('rev-parse', '--git-path', 'MERGE_HEAD')).exists()
    status = t('status', '--porcelain=v1', '--untracked-files=all')
    assert t('ls-remote', 'origin', REF).split()[0] == START
    original_paths = set(t('ls-tree', '-r', '--name-only', START).splitlines())
    files = {}
    donors = []
    for donor in payload['donors']:
        source, parent = donor['sha'], donor['parent']
        b('-c', 'credential.helper=!gh auth git-credential', 'fetch', '--no-tags', '--refmap=', 'origin', source)
        assert t('show', '-s', '--format=%P', source).split() == [parent]
        assert t('rev-parse', source + '^{tree}') == donor['tree']
        diff_base = donor.get('diffBase', parent)
        subprocess.run(G + ['merge-base', '--is-ancestor', diff_base, START], capture_output=True, check=True)
        paths = sorted(row['path'] for row in donor['files'])
        assert t('diff', '--name-only', diff_base, source).splitlines() == paths
        assert dict(line.split('\t')[::-1] for line in t('diff', '--name-status', diff_base, source).splitlines()) == {p: 'A' for p in paths}
        for row in donor['files']:
            path = row['path']
            assert path not in files and path not in original_paths and row['status'] == 'A'
            data = b('show', source + ':' + path)
            assert len(data) == row['bytes'] and h(data) == row['sha256'] and blob(data) == row['gitBlob'], path
            assert t('ls-tree', source, '--', path).split()[0] == '100644'
            files[path] = row
        donors.append({'sha': source, 'parent': parent, 'diffBase': diff_base, 'tree': donor['tree'], 'files': len(paths)})
    assert len(files) == 158
    dep = json.loads(b('show', START + ':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json'))
    assert len(dep['files']) == 15
    for path, row in {**dep['files'], **payload['currentDependencyFiles']}.items():
        data = b('show', START + ':' + path)
        assert len(data) == row['bytes'] and h(data) == row['sha256'] and blob(data) == row['gitBlob'], path
    assert h(payload['rootReview'].encode()) == payload['rootReviewSHA256'] == 'c2514ca2a531b2bd936d9d001e4e22edaa691447172233e48f995513fe0a50a9'
    assert json.loads(b('show', START + ':Tools/Hanlin/source.json'))['revision'] == '0ae1920d316b9592cbad0462bea96a07fd1ca351'
    assert h(b('show', START + ':Tools/MiniApps/receipt_admission.py')) == 'd63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    assert h(b('show', START + ':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift')) == 'c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    code = '''import os,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-rpc-torah-native23-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview = subprocess.run(PRE + ['python3', '-B', '-c', code], input=json.dumps([str(ROOT), START, files]).encode(), capture_output=True, check=True).stdout.decode().strip()
    assert t('diff', '--name-only', START, preview).splitlines() == sorted(files)
    preview_whitespace = exact_original_whitespace(['diff', '--check', START, preview])
    b('merge', '--no-ff', '--no-commit', *[d['sha'] for d in donors])
    assert t('write-tree') == preview and t('diff', '--cached', '--name-only').splitlines() == sorted(files)
    review = {'schema': 'pinkha-root-rpc-torah-native23-source-intake/v1', 'sourceParent': START, 'donors': donors,
              'expectedCompleteMergeTree': preview, 'allPreviouslyTrackedBytesPreserved': True, 'exactNewDonorFiles': 158,
              'sourceFiles': files, 'sourceReviewSHA256': payload['rootReviewSHA256'], 'currentDependencyFilesVerified': len(payload['currentDependencyFiles']),
              'coreDependencyFilesVerified': 15, 'ordinaryDiffCheck': preview_whitespace,
              'sdkRevision': '0ae1920d316b9592cbad0462bea96a07fd1ca351', 'newTestsExecuted': 0,
              'bothFutureUIGatesRemainClosed': True, 'newNativeOrAppleRuntimeAccepted': False,
              'scope': ['Preserve exact native Cutover RPC and all original Linux results/failures.',
                        'Preserve future Torah G03 control and separate Native23/accessibility controls as closed source.',
                        'No existing product source, source-retention map, lockfile or active native binary changes.',
                        'Separate current native/App/UI compiler products and reviewed runtime successors remain mandatory.']}
    evidence = {'root-source-intake.json': (json.dumps(review, indent=2, sort_keys=True) + '\n').encode(),
                'root-source-review.json': payload['rootReview'].encode(), 'root-integration-controller.py': pathlib.Path(__file__).read_bytes()}
    for name, row in payload['evidence'].items():
        data = row['text'].encode()
        assert h(data) == row['sha256']
        evidence[name] = data
    prior = pathlib.Path('/tmp/pinkha-root-native9eb-integration-20261127.json').read_bytes()
    assert h(prior) == '6e12ecff451f3c013b7bc4609a4caef8b0fa103f2901b8422eb6c0cb368f5fec'
    evidence['prior-native-tuple-integration.original.json'] = prior
    for name, data in evidence.items(): owned(PREFIX + '/' + name, data)
    b('add', '--', PREFIX)
    receipt['ordinaryDiffCheck'] = exact_original_whitespace(['diff', '--cached', '--check'])
    expected = sorted(list(files) + [PREFIX + '/' + name for name in evidence])
    assert t('diff', '--cached', '--name-only').splitlines() == expected
    assert dict(line.split('\t')[::-1] for line in t('diff', '--cached', '--name-status').splitlines()) == {p: 'A' for p in expected}
    tree = t('write-tree')
    gate = pathlib.Path('/tmp/pinkha-root-rpc-torah-native23-retention-20261127.json')
    assert not gate.exists()
    run = subprocess.run(PRE + ['python3', '-B', str(ROOT / GATE), '--base', '586c98bcc17dee425664224e508fc0e8df277678', '--ref', tree, '--output', str(gate)], cwd=ROOT, capture_output=True)
    pathlib.Path(str(gate) + '.stdout').open('xb').write(run.stdout)
    pathlib.Path(str(gate) + '.stderr').open('xb').write(run.stderr)
    result = json.loads(gate.read_bytes())
    assert run.returncode == 0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors']) == 129
    message = 'Merge native Cutover RPC and closed Torah and Native23 controls\n\nPreserve all158 original additions and prior tracked source bytes. Reuse exact Linux RPC/crash/host/negative-byte evidence with original failed attempts intact. Keep Torah and Native23/accessibility runtime gates closed pending actual current native/App/UI products and reviewed lifecycle successors. Retain the75 original whitespace diagnostics as exact evidence; no runtime acceptance is implied.\n'
    subprocess.run(G + ['commit', '-F', '-'], input=message.encode(), capture_output=True, check=True)
    head = t('rev-parse', 'HEAD')
    assert t('show', '-s', '--format=%P', head).split() == [START] + [d['sha'] for d in donors]
    assert t('status', '--porcelain=v1', '--untracked-files=all') == status and t('ls-remote', 'origin', REF).split()[0] == START
    push = subprocess.run(G + ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential', 'push', 'origin', head + ':' + REF], capture_output=True, text=True)
    receipt.update(head=head, tree=tree, donors=donors, files=expected, sourceRetentionPassed=True, reviewedRefactors=129,
                   retentionSHA256=h(gate.read_bytes()), intakeSHA256=h(evidence['root-source-intake.json']), controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(payload_bytes), transportSHA256=h(PAYLOAD.read_bytes()), pushExit=push.returncode,
                   pushStdout=push.stdout, pushStderr=push.stderr, newTestsExecuted=0)
    if push.returncode == 0:
        assert t('ls-remote', 'origin', REF).split()[0] == head
        receipt['normalPushReadback'] = head
    assert push.returncode == 0
    receipt['state'] = 'RPC_AND_CLOSED_TORAH_NATIVE23_SOURCE_PUBLISHED'
except BaseException:
    receipt['state'] = 'FAILED_PRESERVED'
    receipt['error'] = traceback.format_exc()
    raise
finally:
    receipt['completedAt'] = time.time()
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'receipt': str(OUT), 'sha256': h(OUT.read_bytes()), 'state': receipt['state'], 'head': receipt.get('head'), 'tree': receipt.get('tree')}), flush=True)
