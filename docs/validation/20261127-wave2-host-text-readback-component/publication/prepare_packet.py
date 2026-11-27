from pathlib import Path
import datetime, fnmatch, hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[1]
PUB = ROOT / 'publication'
PACK = PUB / 'packet'
OLD = ROOT.parent / 'publication'
BASE = 'cde0b83a3f04f36232eed93e6ab2cb7be0e692a5'
TREE = 'd49c3aca52744a228e776211a4967f64f3da9b6b'
BRANCH = 'codex/chatgpt-wave15-wave2-host-text-component-20261127'
PREFIX = 'docs/validation/20261127-wave2-host-text-readback-component'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def api(name):
    value = json.loads((PUB / 'api' / (name + '.json')).read_text())
    assert not value.get('isError'), name
    return json.loads(value['structuredContent']['content'])


def tree_sha(rows):
    raw = b''
    for row in sorted(rows, key=lambda x: (x['path'] + ('/' if x['type'] == 'tree' else '')).encode()):
        raw += (('40000' if row['mode'] == '040000' else row['mode']) + ' ' + row['path']).encode() + b'\0' + bytes.fromhex(row['sha'])
    return hashlib.sha1(b'tree ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


commit, root = api('base-commit'), api('base-root')
assert commit['sha'] == BASE and commit['tree']['sha'] == root['sha'] == TREE
absence = json.loads((PUB / 'api/owned-ref-absence.json').read_text())
assert absence['isError'] and absence['structuredContent']['error_data']['status'] == '404'
trees = json.loads((OLD / 'base-trees.json').read_text())
trees.update(json.loads((OLD / 'expected-trees.json').read_text()))
assert trees['']['sha'] == TREE
for name, path in [('base-root', ''), ('base-docs', 'docs'), ('base-validation', 'docs/validation'),
                   ('base-github', '.github'), ('base-workflows', '.github/workflows')]:
    actual = api(name)
    assert not actual.get('truncated') and tree_sha(actual['tree']) == actual['sha']
    assert actual['sha'] == trees[path]['sha']
    assert {(r['path'], r['mode'], r['type'], r['sha']) for r in actual['tree']} == {
        (r['path'], r['mode'], r['type'], r['sha']) for r in trees[path]['tree']}
    trees[path] = actual
assert not any(row['path'] == PREFIX.split('/')[-1] for row in trees['docs/validation']['tree'])
previous_docs = OLD / 'packet/docs/validation/20261127-wave2-host-text-readback/publication'
workflow = json.loads((previous_docs / 'original-workflow-audit.json').read_text())
yaml_rows = [row for row in trees['.github/workflows']['tree'] if row['path'].endswith(('.yml', '.yaml'))]
assert len(yaml_rows) == len(workflow['workflows']) == 83
assert {row['path'].split('/')[-1]: row['gitBlob'] for row in workflow['workflows']} == {
    row['path']: row['sha'] for row in yaml_rows}
old_preflight = json.loads((OLD / 'preflight.json').read_text())
checks = []
for row in old_preflight['pushChecks']:
    selected = any(fnmatch.fnmatchcase(BRANCH, pattern) for pattern in row['branches'])
    assert not selected
    checks.append({**row, 'matchesNewBranch': selected})
default = api('default-ref')['object']['sha']
assert default == old_preflight['defaultCommit'] and old_preflight['noCreateTrigger']

assert not PACK.exists(), 'Retain earlier packet; never silently replace a frozen publication'
docs = PACK / PREFIX
docs.mkdir(parents=True)
packet = json.loads((ROOT / 'input-packet.json').read_text())
assert len(packet['files']) == 35 and packet['inputBytes'] == 448292
for row in packet['files']:
    source = ROOT / row['path']
    raw = source.read_bytes()
    assert sha(raw) == row['sha256'] and len(raw) == row['bytes']
    target = docs / row['path']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
names = [
    'README.md', 'input-packet.json', 'preparation-proof.json', 'package-derivation.json',
    'compiler-format-successor.json', 'compiler-format-successor.patch',
    'editor-driver-review-v1.json', 'editor-driver-review-v2.json', 'root-driver-review-v2.json',
    'portable_controls.py', 'portable-controls1/result.json',
    'compiler_format_controls.py', 'compiler-format-controls1/result.json',
    'interfaces-crypto-closure/README.md', 'interfaces-crypto-closure/local-extraction-review.json',
    'interfaces-crypto-closure/inspection-shape-attempt1.json',
    'interfaces-crypto-closure/extract_retained_crypto_closure.py',
]
for name in names:
    target = docs / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / name, target)
shutil.copytree(ROOT / 'review-v1-compiler-input-format', docs / 'review-v1-compiler-input-format')
for name in ['uploader-components-attempt2.original.json', 'uploader-source-context.primary.json']:
    target = docs / 'originals' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT.parent / name, target)
for name in ['original-workflow-audit.json', 'original-default-workflow-audit.json']:
    target = docs / 'publication' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(previous_docs / name, target)
shutil.copyfile(Path(__file__), docs / 'publication/prepare_packet.py')
shutil.copyfile(PUB / 'preparation-attempt1.json', docs / 'publication/preparation-attempt1.json')
preflight = {
    'schema': 'host2-execution-packet-publication/v1', 'status': 'PASS_SOURCE_PUBLICATION_PREFLIGHT_NOT_RUNTIME',
    'atUTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'parentCommit': BASE, 'parentTree': TREE,
    'branch': BRANCH, 'prefix': PREFIX, 'ownedRef404': True, 'newEvidenceSubtreeAbsent': True,
    'workflowTree': trees['.github/workflows']['sha'], 'workflowYAMLCount': 83,
    'unchangedAdditionalMarkdownEntries': 1, 'fullWorkflowBlobIdentitiesMatchOriginalAudit': True,
    'workflowAuditSHA256': sha((previous_docs / 'original-workflow-audit.json').read_bytes()),
    'defaultWorkflowAuditSHA256': sha((previous_docs / 'original-default-workflow-audit.json').read_bytes()),
    'defaultCommit': default, 'pushChecks': checks, 'noCreateTrigger': True, 'automaticWorkflowSelected': False,
    'runtimeInputFiles': 35, 'runtimeInputBytes': 448292, 'actualRuntimeExecuted': False,
    'compilerCalls': 0, 'OracleCalls': 0, 'NativeCalls': 0, 'MacCalls': 0,
    'sourceGateExecuted': False, 'inheritedSourceMapRows': 132,
    'allExistingProductSourceTreesPreserved': True,
    'protectedToolsTree': next(row['sha'] for row in root['tree'] if row['path'] == 'Tools'),
    'full1747InputDumpIncluded': False,
}
write(PUB / 'preflight.json', preflight)
write(docs / 'publication/preflight.json', preflight)


def files():
    result = []
    for path in sorted(PACK.rglob('*')):
        if path.is_file():
            raw = path.read_bytes()
            result.append({'path': path.relative_to(PACK).as_posix(), 'mode': '100644', 'type': 'blob',
                           'bytes': len(raw), 'sha256': sha(raw), 'gitBlob': blob(raw)})
    return result


rows = files()
assert sum(row['bytes'] for row in rows) < 1024**2
write(docs / 'packet-manifest.json', {'schema': 'host2-execution-source-packet/v1', 'selfExcluding': True,
    'parentCommit': BASE, 'prefix': PREFIX, 'files': rows, 'bytes': sum(row['bytes'] for row in rows),
    'runtimeAdmission': False, 'actualSwiftHTTPXCTestNativeApple': 'NOT_RUN'})
rows = files()
new = {path: {**value, 'tree': [dict(row) for row in value['tree']]} for path, value in trees.items()}
changed = set()
for row in rows:
    parent, _, name = row['path'].rpartition('/')
    cursor = parent
    while cursor:
        changed.add(cursor)
        new.setdefault(cursor, {'tree': [], 'truncated': False})
        cursor = cursor.rpartition('/')[0]
    changed.add('')
    new[parent]['tree'].append({'path': name, 'mode': row['mode'], 'type': row['type'], 'sha': row['gitBlob'], 'size': row['bytes']})
for path in sorted(changed, key=lambda x: x.count('/') + (1 if x else 0), reverse=True):
    new[path]['sha'] = tree_sha(new[path]['tree'])
    if path:
        parent, _, name = path.rpartition('/')
        new[parent]['tree'][:] = [row for row in new[parent]['tree'] if row['path'] != name]
        new[parent]['tree'].append({'path': name, 'mode': '040000', 'type': 'tree', 'sha': new[path]['sha']})
write(PUB / 'base-trees.json', trees)
write(PUB / 'expected-trees.json', {path: new[path] for path in sorted(changed)})
write(PUB / 'expected-files.json', rows)
write(PUB / 'api/create-tree-input.json', {'repository_full_name': 'davidpovarsky/anytype-swift', 'base_tree_sha': TREE,
    'tree_elements': [{'path': row['path'], 'mode': row['mode'], 'type': row['type'],
                       'content': (PACK / row['path']).read_text()} for row in rows]})
print(json.dumps({'files': len(rows), 'bytes': sum(row['bytes'] for row in rows), 'changedTrees': len(changed),
                  'expectedRoot': new['']['sha'], 'preflightSHA256': sha((PUB / 'preflight.json').read_bytes())}))
