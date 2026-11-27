"""Preserve and merge the exact reviewed six-donor W1/W2 source checkpoint."""
import gzip, hashlib, json, os, pathlib, subprocess, time, traceback

ROOT = pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
G = PRE + ['git', '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', '-C', str(ROOT)]
START = 'cee06ac951f735514059e616fbea48f07d4e7c09'
START_TREE = '7a1793b6fb4f074653814642fdae56b5e8a21633'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX = 'docs/validation/20261127-wave3-cache-bin-e-c-intake'
OUT = pathlib.Path('/tmp/pinkha-root-cache-bin-e-c-integration2-20261127.json')
PAYLOAD = pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-cache-bin-e-c-payload2.json.gz')
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'

def h(raw): return hashlib.sha256(raw).hexdigest()
def blob(raw): return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
def b(*args): return subprocess.check_output(G + list(args), stderr=subprocess.PIPE)
def t(*args): return b(*args).decode().strip()
def resources():
    result = {}
    for name, path, floor in [('root', '/', 2147483648), ('development', str(ROOT), 536870912)]:
        s = os.statvfs(path); free = s.f_bavail * s.f_frsize
        assert free >= floor + 67108864, (name, free, floor, 'fixed64MiB source integration allowance')
        result[name] = {'freeBytes': free, 'floorBytes': floor, 'sourceAllowanceBytes': 67108864}
    return result
def owned(path, raw):
    code = 'import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);p.open("xb").write(sys.stdin.buffer.read())'
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT / path)], input=raw, capture_output=True, check=True)
def observed_diff(args, expected):
    run = subprocess.run(G + args, capture_output=True)
    result = {'exit': run.returncode, 'stdoutSHA256': h(run.stdout), 'stdoutBytes': len(run.stdout),
              'stdout': run.stdout.decode(), 'stderr': run.stderr.decode(), 'cleanDiffClaimed': False,
              'scope': 'Exact immutable primary donor evidence whitespace; no product source diagnostic admitted'}
    if run.returncode != expected['exit'] or run.stderr or run.stdout != expected['stdout'].encode():
        receipt['unexpectedDiffCheck'] = result
        raise RuntimeError('Different or additional whitespace finding; original state retained before promotion')
    assert len(run.stdout) == expected['bytes'] and h(run.stdout) == expected['sha256']
    return result
def pins():
    source = json.loads(b('show', ':Tools/Hanlin/source.json'))
    assert source['revision'] == '0ae1920d316b9592cbad0462bea96a07fd1ca351'
    common = b('show', ':Tools/MiniApps/receipt_admission.py')
    assert h(common) == 'd63b8a04bd424a92bf852449c2ecbf8a22bd5ccae95b61ae32feb6be63e6b901'
    stage = b('show', ':PinkhaStage1Acceptance/Tests/PinkhaStage1AcceptanceUITests.swift')
    assert h(stage) == 'c1e37371ce061cfec1ec6d30fc2f55a0df0e477f9727ffd96d635f46e91e0906'
    kit = b('show', ':Modules/PinkhaTorahPresentation/Package.swift')
    assert b'9058b489e9acc271b4f8ef69e2ed24648f93b4ed' in kit
    lock = b('show', ':Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved')
    assert b'9058b489e9acc271b4f8ef69e2ed24648f93b4ed' in lock and b'7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e' in lock
    return {'hanlin': source['revision'], 'common57SHA256': h(common), 'stage1SHA256': h(stage),
            'torahKit': '9058b489e9acc271b4f8ef69e2ed24648f93b4ed', 'kitManifestSHA256': h(kit),
            'packageResolvedSHA256': h(lock), 'collections': '7b847a3b7008b2dc2f47ca3110d8c782fb2e5c7e'}

assert not OUT.exists()
receipt = {'schema': 'pinkha-root-six-donor-source-integration/v1', 'startedAt': time.time(), 'parent': START, 'state': 'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt, indent=2) + '\n')
try:
    receipt['resourceBefore'] = resources()
    packed = PAYLOAD.read_bytes()
    assert len(packed) == 70351 and h(packed) == 'd67db1d6d1d9f9b3c804ce3b8b7ca4bb01497ab465a9c7cb4c244cd7352ea2fd'
    raw = gzip.decompress(packed)
    assert len(raw) == 363224 and h(raw) == 'baf46b230ddeb19aee8fcffa385ae92445ea5f33b109d89de5242207c82a2b56'
    payload = json.loads(raw)
    assert payload['start'] == START and payload['startTree'] == START_TREE
    assert t('rev-parse', 'HEAD') == START and t('rev-parse', 'HEAD^{tree}') == START_TREE and t('symbolic-ref', 'HEAD') == REF
    assert not t('diff', '--name-only') and not t('diff', '--cached', '--name-only')
    assert not pathlib.Path(t('rev-parse', '--git-path', 'MERGE_HEAD')).exists()
    status = t('status', '--porcelain=v1', '--untracked-files=all')
    assert t('ls-remote', 'origin', REF).split()[0] == START
    original_paths = set(t('ls-tree', '-r', '--name-only', START).splitlines())
    before_pins = pins()
    files = {}; donors = []
    for donor in payload['donors']:
        resources()
        source, parent, base = donor['sha'], donor['parent'], donor['diffBase']
        b('-c', 'credential.helper=!gh auth git-credential', 'fetch', '--no-tags', '--refmap=', 'origin', source)
        assert t('show', '-s', '--format=%P', source).split() == [parent]
        subprocess.run(G + ['merge-base', '--is-ancestor', base, START], capture_output=True, check=True)
        paths = sorted(row['path'] for row in donor['files'])
        assert t('diff', '--name-only', base, source).splitlines() == paths
        assert dict(line.split('\t')[::-1] for line in t('diff', '--name-status', base, source).splitlines()) == {r['path']: r['status'] for r in donor['files']}
        for row in donor['files']:
            path = row['path']; assert path not in files
            if row['status'] == 'A': assert path not in original_paths
            else:
                assert row['status'] == 'M' and path in original_paths
                data = b('show', START + ':' + path)
                assert len(data) == row['before']['bytes'] and h(data) == row['before']['sha256'] and blob(data) == row['beforeGitBlob']
            data = b('show', source + ':' + path)
            assert len(data) == row['bytes'] and h(data) == row['sha256'] and blob(data) == row['gitBlob'], path
            assert t('ls-tree', source, '--', path).split()[0] == '100644'
            files[path] = row
        donors.append({'sha': source, 'parent': parent, 'diffBase': base, 'tree': t('rev-parse', source + '^{tree}'), 'files': len(paths)})
    assert len(files) == 225 and sum(r['status'] == 'M' for r in files.values()) == 7
    deps = json.loads(b('show', START + ':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json'))['files']
    assert len(deps) == 15
    for path, row in {**deps, **payload['currentDependencyFiles']}.items():
        data = b('show', START + ':' + path)
        assert len(data) == row['bytes'] and h(data) == row['sha256'] and blob(data) == row['gitBlob'], path
    code = '''import os,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-six-donor-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview = subprocess.run(PRE + ['python3', '-B', '-c', code], input=json.dumps([str(ROOT), START, files]).encode(), capture_output=True, check=True).stdout.decode().strip()
    assert t('diff', '--name-only', START, preview).splitlines() == sorted(files)
    whitespace = observed_diff(['diff', '--check', START, preview], payload['ordinaryDiffCheck'])
    resources()
    b('merge', '--no-ff', '--no-commit', *[d['sha'] for d in donors])
    assert t('write-tree') == preview and t('diff', '--cached', '--name-only').splitlines() == sorted(files)
    assert pins() == before_pins
    intake = {'schema': 'pinkha-root-reviewed-w1-w2-source-intake/v1', 'sourceParent': START, 'donors': donors,
              'expectedCompleteMergeTree': preview, 'allOtherTrackedBytesPreserved': True, 'sourceFiles': files,
              'exactNewDonorFiles': 218, 'exactModifiedSwiftFiles': 6, 'exactModifiedSourceRecords': 1,
              'currentDependencyFilesVerified': len(payload['currentDependencyFiles']), 'coreDependencyFilesVerified': 15,
              'inputPinsBeforeAndAfter': before_pins, 'ordinaryDiffCheck': whitespace,
              'newTestsExecuted': 0, 'expectedSourceRetentionRows': 130,
              'scope': ['G05 generations reject stale descriptor/diagnostic publication and preserve read-only lookup.',
                        'Bin current read failures retire stale rows and expose explicit retry without changing restore/archive authority.',
                        'Original Properties9 and Sharing5 component results remain scoped to their original exact sources/envelopes.',
                        'W1 FullSpace37/reader/custody and C30 packets remain source/evidence; actual failures are preserved and no native, migration, permission or product gate is opened.']}
    evidence = {'root-source-intake.json': (json.dumps(intake, indent=2, sort_keys=True) + '\n').encode(),
                'root-integration-controller.py': pathlib.Path(__file__).read_bytes()}
    for name, row in payload['evidence'].items():
        data = row['text'].encode(); assert h(data) == row['sha256']; evidence[name] = data
    prior = pathlib.Path('/tmp/pinkha-root-g05-attachments-integration2-20261127.json').read_bytes()
    assert h(prior) == '35f4ade5705f830414934c824ce696105a54d15901247e7a97a7a50af96ce6f6'
    evidence['prior-g05-attachments-integration.original.json'] = prior
    failed = pathlib.Path('/tmp/pinkha-root-cache-bin-e-c-integration-20261127.json').read_bytes()
    assert len(failed) == 941 and h(failed) == '49ae712b985854e64dc4e18098d27ae9306be06da0c0a61d9add5407e6fc9c2a'
    evidence['first-current-dependency-preflight.original.json'] = failed
    receipt['retainedFirstPreflightFailureSHA256'] = h(failed)
    for name, data in evidence.items(): owned(PREFIX + '/' + name, data)
    b('add', '--', PREFIX)
    receipt['ordinaryDiffCheck'] = observed_diff(['diff', '--cached', '--check'], payload['ordinaryDiffCheck'])
    expected = sorted(list(files) + [PREFIX + '/' + name for name in evidence])
    assert t('diff', '--cached', '--name-only').splitlines() == expected
    assert dict(line.split('\t')[::-1] for line in t('diff', '--cached', '--name-status').splitlines()) == {**{p:r['status'] for p,r in files.items()}, **{PREFIX+'/'+name:'A' for name in evidence}}
    tree = t('write-tree')
    gate = pathlib.Path('/tmp/pinkha-root-cache-bin-e-c-retention-20261127.json'); assert not gate.exists()
    run = subprocess.run(PRE + ['python3', '-B', str(ROOT / GATE), '--base', '586c98bcc17dee425664224e508fc0e8df277678', '--ref', tree, '--output', str(gate)], cwd=ROOT, capture_output=True)
    pathlib.Path(str(gate) + '.stdout').open('xb').write(run.stdout)
    pathlib.Path(str(gate) + '.stderr').open('xb').write(run.stderr)
    result = json.loads(gate.read_bytes())
    assert run.returncode == 0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors']) == 130
    assert pins() == before_pins
    message = 'Merge reviewed cache, Bin, E and C source checkpoints\n\nIntegrate exact generation-bound native property lookup and explicit Bin read failure/retry while preserving existing mutation semantics. Retain all original component evidence, scoped W1 FullSpace and held-reader source, first failures and archive authority limitations. All225 donor paths and seven current preimages are exact; all other tracked bytes and SDK/Kit/Collections pins are preserved. Original evidence whitespace is recorded without rewriting it or claiming a clean diff. Product, Apple and final native runtime acceptance remain pending.\n'
    subprocess.run(G + ['commit', '-F', '-'], input=message.encode(), capture_output=True, check=True)
    head = t('rev-parse', 'HEAD')
    assert t('show', '-s', '--format=%P', head).split() == [START] + [d['sha'] for d in donors]
    assert t('status', '--porcelain=v1', '--untracked-files=all') == status and t('ls-remote', 'origin', REF).split()[0] == START
    push = subprocess.run(G + ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential', 'push', 'origin', head + ':' + REF], capture_output=True, text=True)
    receipt.update(head=head, tree=tree, donors=donors, files=expected, sourceRetentionPassed=True, reviewedRefactors=130,
                   retentionSHA256=h(gate.read_bytes()), intakeSHA256=h(evidence['root-source-intake.json']), controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(raw), transportSHA256=h(packed), pushExit=push.returncode,
                   pushStdout=push.stdout, pushStderr=push.stderr, newTestsExecuted=0, inputPins=before_pins)
    if push.returncode == 0:
        assert t('ls-remote', 'origin', REF).split()[0] == head; receipt['normalPushReadback'] = head
    assert push.returncode == 0
    receipt['resourceAfter'] = resources()
    receipt['state'] = 'SIX_DONOR_SOURCE_CHECKPOINT_PUBLISHED_RUNTIME_PENDING'
except BaseException:
    receipt['state'] = 'FAILED_PRESERVED'; receipt['error'] = traceback.format_exc(); raise
finally:
    receipt['completedAt'] = time.time()
    OUT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'receipt': str(OUT), 'sha256': h(OUT.read_bytes()), 'state': receipt['state'], 'head': receipt.get('head'), 'tree': receipt.get('tree')}), flush=True)
