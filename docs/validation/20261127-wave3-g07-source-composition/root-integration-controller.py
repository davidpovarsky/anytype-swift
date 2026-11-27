"""Merge exact G07 source and explicitly compose the two reviewed source records."""
import gzip, hashlib, json, os, pathlib, subprocess, time, traceback

ROOT = pathlib.Path('/mnt/development/projects/worktrees/anytype-final-integration-20261125')
PRE = ['sudo', '-n', '-u', 'ubuntu', '-g', 'chatgpt-agent']
G = PRE + ['git', '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'user.name=ChatGPT', '-c', 'user.email=chatgpt@openai.com', '-C', str(ROOT)]
START = 'd8a2c67b6dae09a7b769e803a319de3d3080019c'
START_TREE = 'd6ef8cf91bc81732a1a506eabac5950d14ed56f2'
REF = 'refs/heads/codex/chatgpt-wave15-final-20261125'
PREFIX = 'docs/validation/20261127-wave3-g07-source-composition'
OUT = pathlib.Path('/tmp/pinkha-root-g07-composition-integration-20261127.json')
PAYLOAD = pathlib.Path('/var/lib/sentinelx/uploads/pinkha-root-g07-composition-payload.json.gz')
GATE = 'Tools/AnyEnginePort/verify_source_retention.py'

def h(raw): return hashlib.sha256(raw).hexdigest()
def blob(raw): return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
def b(*args): return subprocess.check_output(G + list(args), stderr=subprocess.PIPE)
def t(*args): return b(*args).decode().strip()
def match(raw, row):
    assert len(raw) == row['bytes'] and h(raw) == row['sha256'] and blob(raw) == row['gitBlob']
def resources():
    result = {}
    for name, path, floor in [('root', '/', 2147483648), ('development', str(ROOT), 536870912)]:
        s = os.statvfs(path); free = s.f_bavail * s.f_frsize
        assert free >= floor + 67108864, (name, free, floor, 'fixed64MiB source integration allowance')
        result[name] = {'freeBytes': free, 'floorBytes': floor, 'sourceAllowanceBytes': 67108864}
    return result
def owned(path, raw, replace=False):
    code = 'import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.parent.mkdir(parents=True,exist_ok=True);assert not p.is_symlink();p.open(sys.argv[2]).write(sys.stdin.buffer.read())'
    subprocess.run(PRE + ['python3', '-B', '-c', code, str(ROOT / path), 'wb' if replace else 'xb'], input=raw, capture_output=True, check=True)
def diff_check(args):
    run = subprocess.run(G + args, capture_output=True)
    receipt.setdefault('diffChecks', []).append({'argv': args, 'exit': run.returncode, 'stdout': run.stdout.decode(), 'stderr': run.stderr.decode()})
    assert run.returncode == 0 and not run.stdout and not run.stderr
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
receipt = {'schema': 'pinkha-root-g07-source-composition-integration/v1', 'startedAt': time.time(), 'parent': START, 'state': 'PREFLIGHT'}
OUT.open('x').write(json.dumps(receipt, indent=2) + '\n')
try:
    receipt['resourceBefore'] = resources()
    packed = PAYLOAD.read_bytes()
    assert len(packed) == 88083 and h(packed) == '6ac6c06e59a4ea00fec21c9a3a36d70b3975de70325b2d2080b01ff93ba2cf2b'
    raw = gzip.decompress(packed)
    assert len(raw) == 381899 and h(raw) == '0542101aaadee1d538cca3065fba7a56ea7e625c3bf98a5aa59607b55c56d24b'
    payload = json.loads(raw)
    assert payload['start'] == START and payload['startTree'] == START_TREE
    assert t('rev-parse', 'HEAD') == START and t('rev-parse', 'HEAD^{tree}') == START_TREE and t('symbolic-ref', 'HEAD') == REF
    assert not t('diff', '--name-only') and not t('diff', '--cached', '--name-only')
    assert not pathlib.Path(t('rev-parse', '--git-path', 'MERGE_HEAD')).exists()
    status = t('status', '--porcelain=v1', '--untracked-files=all')
    assert t('ls-remote', 'origin', REF).split()[0] == START
    original_paths = set(t('ls-tree', '-r', '--name-only', START).splitlines())
    before_pins = pins()
    donor, parent = payload['donor'], payload['donorParent']
    b('-c', 'credential.helper=!gh auth git-credential', 'fetch', '--no-tags', '--refmap=', 'origin', donor)
    assert t('show', '-s', '--format=%P', donor).split() == [parent]
    assert t('rev-parse', donor + '^{tree}') == payload['donorTree']
    subprocess.run(G + ['merge-base', '--is-ancestor', parent, START], capture_output=True, check=True)
    rows = {row['path']: row for row in payload['files']}
    assert len(rows) == 17 and sum(r['status'] == 'M' for r in rows.values()) == 6
    assert t('diff', '--name-only', parent, donor).splitlines() == sorted(rows)
    assert dict(line.split('\t')[::-1] for line in t('diff', '--name-status', parent, donor).splitlines()) == {p:r['status'] for p,r in rows.items()}
    for path, row in rows.items():
        if row['status'] == 'A': assert path not in original_paths
        else:
            assert row['status'] == 'M' and path in original_paths
            match(b('show', START + ':' + path), row['before'])
        match(b('show', donor + ':' + path), row['donor'])
        assert t('ls-tree', donor, '--', path).split()[0] == '100644'
        if path not in payload['composed']: assert row['after'] == row['donor']
    compositions = payload['composed']
    assert set(compositions) == {'docs/any-engine-port/SOURCE_REFACTOR_MAP.json', 'docs/architecture/UPSTREAM_EXCEPTION_REGISTER.md'}
    for path, row in compositions.items():
        value = row['text'].encode(); match(value, row); assert row['sha256'] == rows[path]['after']['sha256']
        written = subprocess.run(G + ['hash-object', '-w', '--stdin'], input=value, capture_output=True, check=True).stdout.decode().strip()
        assert written == row['gitBlob']
    for path, row in payload['currentDependencies'].items(): match(b('show', START + ':' + path), row)
    deps = json.loads(b('show', START + ':Tools/PinkhaDualEngineRuntime/hosted_core13/original_sources.json'))['files']
    assert len(deps) == 15
    for path, row in deps.items(): match(b('show', START + ':' + path), row)
    code = '''import os,subprocess,tempfile,json,sys
root,start,files=json.loads(sys.stdin.read());g=['git','--no-optional-locks','-c','gc.auto=0','-C',root]
with tempfile.TemporaryDirectory(prefix='pinkha-root-g07-index-') as temp:
 env=dict(os.environ,GIT_INDEX_FILE=temp+'/index');subprocess.run(g+['read-tree',start],env=env,check=True,capture_output=True)
 for path,row in sorted(files.items()):subprocess.run(g+['update-index','--add','--cacheinfo','100644,'+row['after']['gitBlob']+','+path],env=env,check=True,capture_output=True)
 print(subprocess.check_output(g+['write-tree'],env=env).decode().strip())
'''
    preview = subprocess.run(PRE + ['python3', '-B', '-c', code], input=json.dumps([str(ROOT), START, rows]).encode(), capture_output=True, check=True).stdout.decode().strip()
    assert t('diff', '--name-only', START, preview).splitlines() == sorted(rows)
    diff_check(['diff', '--check', START, preview]); resources()
    merge = subprocess.run(G + ['merge', '--no-ff', '--no-commit', donor], capture_output=True)
    conflicts = t('diff', '--name-only', '--diff-filter=U').splitlines()
    receipt['merge'] = {'exit': merge.returncode, 'stdout': merge.stdout.decode(), 'stderr': merge.stderr.decode(), 'conflicts': conflicts}
    assert merge.returncode in (0, 1) and set(conflicts) <= set(compositions)
    assert (merge.returncode == 0 and not conflicts) or (merge.returncode == 1 and conflicts)
    assert pathlib.Path(t('rev-parse', '--git-path', 'MERGE_HEAD')).read_text().strip() == donor
    for path, row in compositions.items(): owned(path, row['text'].encode(), replace=True)
    b('add', '--', *sorted(compositions))
    assert not t('diff', '--name-only', '--diff-filter=U')
    assert t('write-tree') == preview and t('diff', '--cached', '--name-only').splitlines() == sorted(rows)
    assert pins() == before_pins
    intake = {'schema': 'pinkha-root-g07-composed-source-intake/v1', 'parent': START, 'donor': donor, 'donorParent': parent,
              'expectedCompleteMergeTree': preview, 'wholeTreeEqualsReviewedComposition': True, 'allOtherTrackedBytesPreserved': True,
              'files': rows, 'compositions': {p:{k:v for k,v in row.items() if k!='text'} for p,row in compositions.items()},
              'independentDependencies': len(payload['currentDependencies']), 'coreDependencies': 15, 'inputPinsBeforeAndAfter': before_pins,
              'newTestsExecuted': 0, 'declaredNewMethods': 2, 'declaredNewCases': 2, 'inMethodRows': 7, 'expectedSourceRetentionRows': 132,
              'scope': 'Source drop preview and original insertion use the same exact existing block/relation/read-only predicate. Original internal MOVE, insertion writes, focus and context remain unchanged. Preserve all current G05 cache map rows and append both G07 records, plus the exact exception-register suffix.'}
    evidence = {'root-source-intake.json': (json.dumps(intake, sort_keys=True, indent=2) + '\n').encode(), 'root-integration-controller.py': pathlib.Path(__file__).read_bytes()}
    for name, row in payload['evidence'].items():
        value = row['text'].encode(); assert h(value) == row['sha256']; evidence[name] = value
    prior = pathlib.Path('/tmp/pinkha-root-cache-bin-e-c-integration2-20261127.json').read_bytes()
    assert h(prior) == 'ed5cdecc644a2526aa5460971be3a9dc6e7538ef02c8b3e89db28b18bccff1fd'
    evidence['prior-six-donor-integration.original.json'] = prior
    for name, value in evidence.items(): owned(PREFIX + '/' + name, value)
    b('add', '--', PREFIX); diff_check(['diff', '--cached', '--check'])
    expected = sorted(list(rows) + [PREFIX + '/' + name for name in evidence])
    assert t('diff', '--cached', '--name-only').splitlines() == expected
    assert dict(line.split('\t')[::-1] for line in t('diff', '--cached', '--name-status').splitlines()) == {**{p:r['status'] for p,r in rows.items()}, **{PREFIX+'/'+name:'A' for name in evidence}}
    tree = t('write-tree'); gate = pathlib.Path('/tmp/pinkha-root-g07-composition-retention-20261127.json'); assert not gate.exists()
    run = subprocess.run(PRE + ['python3', '-B', str(ROOT / GATE), '--base', '586c98bcc17dee425664224e508fc0e8df277678', '--ref', tree, '--output', str(gate)], cwd=ROOT, capture_output=True)
    pathlib.Path(str(gate) + '.stdout').open('xb').write(run.stdout); pathlib.Path(str(gate) + '.stderr').open('xb').write(run.stderr)
    result = json.loads(gate.read_bytes()); assert run.returncode == 0 and result['sourceRetentionPassed'] and len(result['reviewedRefactors']) == 132
    assert pins() == before_pins
    message = 'Merge source-drop permission parity with current cache records\n\nUse the existing insertion block/relation/read-only predicate during native source-drop preview. Preserve internal move, write, focus and context semantics. Bind all17 donor paths and six current preimages; explicitly compose only the source map and exception register so current G05 cache records and both new G07 records survive. Original132-row retention passes; actual App compilation and both new methods remain pending. SDK, Kit, Collections and native inputs remain unchanged.\n'
    subprocess.run(G + ['commit', '-F', '-'], input=message.encode(), capture_output=True, check=True)
    head = t('rev-parse', 'HEAD'); assert t('show', '-s', '--format=%P', head).split() == [START, donor]
    assert t('status', '--porcelain=v1', '--untracked-files=all') == status and t('ls-remote', 'origin', REF).split()[0] == START
    push = subprocess.run(G + ['-c', 'remote.origin.mirror=false', '-c', 'credential.helper=!gh auth git-credential', 'push', 'origin', head + ':' + REF], capture_output=True, text=True)
    receipt.update(head=head, tree=tree, donor=donor, files=expected, sourceRetentionPassed=True, reviewedRefactors=132,
                   retentionSHA256=h(gate.read_bytes()), intakeSHA256=h(evidence['root-source-intake.json']), controllerSHA256=h(pathlib.Path(__file__).read_bytes()),
                   payloadSHA256=h(raw), transportSHA256=h(packed), pushExit=push.returncode, pushStdout=push.stdout, pushStderr=push.stderr,
                   newTestsExecuted=0, inputPins=before_pins)
    if push.returncode == 0:
        assert t('ls-remote', 'origin', REF).split()[0] == head; receipt['normalPushReadback'] = head
    assert push.returncode == 0; receipt['resourceAfter'] = resources(); receipt['state'] = 'G07_SOURCE_COMPOSED_AND_PUBLISHED_RUNTIME_PENDING'
except BaseException:
    receipt['state'] = 'FAILED_PRESERVED'; receipt['error'] = traceback.format_exc(); raise
finally:
    receipt['completedAt'] = time.time(); OUT.write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'receipt': str(OUT), 'sha256': h(OUT.read_bytes()), 'state': receipt['state'], 'head': receipt.get('head'), 'tree': receipt.get('tree')}), flush=True)
