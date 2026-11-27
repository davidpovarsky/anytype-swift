import gzip, hashlib, json, pathlib, subprocess, time, traceback

ROOT = pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
G = PRE + ['git', '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', '-C', str(ROOT)]
START = '1786e7a60762036484127edfcb588ad45c4e0d9e'
START_TREE = '9d3a3e43af7b8a2eb3ac3881da5097bb9dac6f00'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX = 'docs/validation/20261127-wave3-g05-attachments-source-intake'
OUT = pathlib.Path('/tmp/pinkha-root-g05-attachments-integration-20261127.json')
PAYLOAD = pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-g05-attachments-payload.json.gz')
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'

def h(data): return hashlib.sha256(data).hexdigest()
def blob(data): return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
def b(*args): return subprocess.check_output(G + list(args), stderr=subprocess.PIPE)
def t(*args): return b(*args).decode().strip()
def owned(path, data):
    code = 'import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT / path)], input=data, capture_output=True, check=True)
def require_clean_diff(args):
    check = subprocess.run(G + args, capture_output=True)
    observed = {'exit': check.returncode, 'stdoutSHA256': h(check.stdout), 'stdout': check.stdout.decode(), 'stderr': check.stderr.decode(), 'passed': check.returncode == 0}
    if check.returncode or check.stderr:
        receipt['unexpectedDiffCheck'] = observed
        raise RuntimeError('Unreviewed whitespace finding; preserve original result and stop before promotion')
    return observed

assert not OUT.exists()
receipt = {'schema': 'pinkha-root-g05-attachments-integration/v1', 'startedAt': time.time(), 'parent': START, 'state': 'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt, indent=2) + '\n')
try:
    payload_bytes = gzip.decompress(PAYLOAD.read_bytes())
    assert len(payload_bytes) == 355040 and h(payload_bytes) == '5f49ea8f4d182e73fd72c07d85f3bb3d77cc5e057fdbb34d5227a6d4e251a804'
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
        source_tree = t('rev-parse', source + '^{tree}')
        diff_base = donor.get('diffBase', parent)
        subprocess.run(G + ['merge-base', '--is-ancestor', diff_base, START], capture_output=True, check=True)
        paths = sorted(row['path'] for row in donor['files'])
        assert t('diff', '--name-only', diff_base, source).splitlines() == paths
        assert dict(line.split('\t')[::-1] for line in t('diff', '--name-status', diff_base, source).splitlines()) == {r['path']: r['status'] for r in donor['files']}
        for row in donor['files']:
            path = row['path']
            assert path not in files
            if row['status'] == 'A':
                assert path not in original_paths
            else:
                assert row['status'] == 'M' and path in original_paths
                assert blob(b('show', START + ':' + path)) == row['beforeGitBlob'], path
            data = b('show', source + ':' + path)
            assert len(data) == row['bytes'] and h(data) == row['sha256'] and blob(data) == row['gitBlob'], path
            assert t('ls-tree', source, '--', path).split()[0] == '100644'
            files[path] = row
        donors.append({'sha': source, 'parent': parent, 'diffBase': diff_base, 'tree': source_tree, 'files': len(paths)})
    assert len(files) == 48 and sum(x['status'] == 'M' for x in files.values()) == 8
    dep = json.loads(b('show', START + ':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json'))
    assert len(dep['files']) == 15
    for path, row in {**dep['files'], **payload['currentDependencyFiles']}.items():
        data = b('show', START + ':' + path)
        assert len(data) == row['bytes'] and h(data) == row['sha256'] and blob(data) == row['gitBlob'], path
    assert h(payload['rootReview'].encode()) == payload['rootReviewSHA256'] == '57d03bdd410eaef2ce6324e03fbc85d52f22a6d3450ed73310c931ed6dd1b382'
    assert json.loads(b('show', START + ':Tools/Hanlin/source.json'))['revision'] == '0ae1920d316b9592cbad0462bea96a07fd1ca351'
    assert h(b('show', START + ':Tools/MiniApps/receipt_admission.py')) == 'd63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    assert h(b('show', START + ':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift')) == 'c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    code = '''import os,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-g05-attachments-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview = subprocess.run(PRE + ['python3', '-B', '-c', code], input=json.dumps([str(ROOT), START, files]).encode(), capture_output=True, check=True).stdout.decode().strip()
    assert t('diff', '--name-only', START, preview).splitlines() == sorted(files)
    preview_whitespace = require_clean_diff(['diff', '--check', START, preview])
    b('merge', '--no-ff', '--no-commit', *[d['sha'] for d in donors])
    assert t('write-tree') == preview and t('diff', '--cached', '--name-only').splitlines() == sorted(files)
    review = {'schema': 'pinkha-root-g05-attachments-source-intake/v1', 'sourceParent': START, 'donors': donors,
              'expectedCompleteMergeTree': preview, 'allNonChangedTrackedBytesPreserved': True, 'exactNewDonorFiles': 40, 'exactModifiedProductFiles': 6, 'exactModifiedSourceRecords': 2,
              'sourceFiles': files, 'sourceReviewSHA256': payload['rootReviewSHA256'], 'currentDependencyFilesVerified': len(payload['currentDependencyFiles']),
              'coreDependencyFilesVerified': 15, 'ordinaryDiffCheck': preview_whitespace,
              'sdkRevision': '0ae1920d316b9592cbad0462bea96a07fd1ca351', 'newTestsExecuted': 0,
              'existingFutureUIGatesUnchanged': True, 'newProductRuntimeAccepted': False, 'expectedSourceRetentionRows': 130,
              'scope': ['Read-only property picker lookup and pre-selection identity policy preserve original mutation behavior.',
                        'Attachment UI exposes actual durability and one authorized retry with separate status readback.',
                        'Full48-file donor source identity and eight exact preimages are bound; all other tracked bytes remain unchanged.',
                        'Retain actual source-scoped SDK b14 results and original native dependency custody without broadening acceptance.']}
    evidence = {'root-source-intake.json': (json.dumps(review, indent=2, sort_keys=True) + '\n').encode(),
                'root-source-review.json': payload['rootReview'].encode(), 'root-integration-controller.py': pathlib.Path(__file__).read_bytes()}
    for name, row in payload['evidence'].items():
        data = row['text'].encode()
        assert h(data) == row['sha256']
        evidence[name] = data
    prior = pathlib.Path('/tmp/pinkha-root-rpc-torah-native23-integration-20261127.json').read_bytes()
    assert h(prior) == 'b552368c4a88b0a9690990ec4e137cb131a39b044b3e0a5b4683f970c4cffc45'
    evidence['prior-rpc-torah-native23-integration.original.json'] = prior
    for name, data in evidence.items(): owned(PREFIX + '/' + name, data)
    b('add', '--', PREFIX)
    receipt['ordinaryDiffCheck'] = require_clean_diff(['diff', '--cached', '--check'])
    expected = sorted(list(files) + [PREFIX + '/' + name for name in evidence])
    assert t('diff', '--cached', '--name-only').splitlines() == expected
    assert dict(line.split('\t')[::-1] for line in t('diff', '--cached', '--name-status').splitlines()) == {**{p:r['status'] for p,r in files.items()}, **{PREFIX+'/'+name:'A' for name in evidence}}
    tree = t('write-tree')
    gate = pathlib.Path('/tmp/pinkha-root-g05-attachments-retention-20261127.json')
    assert not gate.exists()
    run = subprocess.run(PRE + ['python3', '-B', str(ROOT / GATE), '--base', '586c98bcc17dee425664224e508fc0e8df277678', '--ref', tree, '--output', str(gate)], cwd=ROOT, capture_output=True)
    pathlib.Path(str(gate) + '.stdout').open('xb').write(run.stdout)
    pathlib.Path(str(gate) + '.stderr').open('xb').write(run.stderr)
    result = json.loads(gate.read_bytes())
    assert run.returncode == 0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors']) == 130
    message = 'Merge read-only property picker and attachment storage controls\n\nIntegrate the exact reviewed G05 and attachment source: preserve original writes, callbacks, cancellation, previews and MiniApps handoff while removing optional provisioning from picker lookup and adding current native durability plus a single authorized retry. Preserve source-map129 history and append the130th policy record. Retain original SDK b14 acceptance and exact native dependency transport receipts with their explicit limits. Actual current App/UI/native and release acceptance remain pending.\n'
    subprocess.run(G + ['commit', '-F', '-'], input=message.encode(), capture_output=True, check=True)
    head = t('rev-parse', 'HEAD')
    assert t('show', '-s', '--format=%P', head).split() == [START] + [d['sha'] for d in donors]
    assert t('status', '--porcelain=v1', '--untracked-files=all') == status and t('ls-remote', 'origin', REF).split()[0] == START
    push = subprocess.run(G + ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential', 'push', 'origin', head + ':' + REF], capture_output=True, text=True)
    receipt.update(head=head, tree=tree, donors=donors, files=expected, sourceRetentionPassed=True, reviewedRefactors=130,
                   retentionSHA256=h(gate.read_bytes()), intakeSHA256=h(evidence['root-source-intake.json']), controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(payload_bytes), transportSHA256=h(PAYLOAD.read_bytes()), pushExit=push.returncode,
                   pushStdout=push.stdout, pushStderr=push.stderr, newTestsExecuted=0)
    if push.returncode == 0:
        assert t('ls-remote', 'origin', REF).split()[0] == head
        receipt['normalPushReadback'] = head
    assert push.returncode == 0
    receipt['state'] = 'G05_AND_ATTACHMENT_PRODUCT_SOURCE_PUBLISHED_RUNTIME_PENDING'
except BaseException:
    receipt['state'] = 'FAILED_PRESERVED'
    receipt['error'] = traceback.format_exc()
    raise
finally:
    receipt['completedAt'] = time.time()
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'receipt': str(OUT), 'sha256': h(OUT.read_bytes()), 'state': receipt['state'], 'head': receipt.get('head'), 'tree': receipt.get('tree')}), flush=True)
