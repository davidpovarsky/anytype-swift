from pathlib import Path, PurePosixPath
import base64
import datetime
import hashlib
import json
import subprocess
import zlib


PACKED = '__PROPERTY_ADD_PUBLICATION_PAYLOAD__'
PAYLOAD_SHA = '__PAYLOAD_SHA__'
PARENT = '06b639ff196a66c19d22dda7ea28b47ce6801705'
BRANCH = 'codex/otzaria-reviewed-followups-waxqv0pw-20261122'
DOCROOT = 'docs/hq-integration/completion-20261122/reviewed-followups-waxqv0pw/original-properties-add'
SOURCES = {
    'Anytype/Sources/PresentationLayer/PropertyValueFlow/PropertyValueCoordinator/OriginalEditorPropertyScope.swift',
    'Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/ObjectFieldsView/ObjectPropertiesViewModel.swift',
}
worktree = Path(r'C:\Users\DAVID\Code\anytype-followups-waxqv0pw-20261122')
checkpoint = Path(r'C:\Users\DAVID\Code\Codex-Agent-HQ\build\anytype-properties-add-waxqv0pw-20261122')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def git(*args, data=None, timeout=120):
    prefix = ['git', '-c', 'core.autocrlf=false'] if args[0] == 'apply' else ['git']
    result = subprocess.run([*prefix, *args], cwd=worktree, input=data, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(json.dumps({'args': args, 'exit_code': result.returncode,
            'stdout': result.stdout.decode(errors='replace')[-1500:],
            'stderr': result.stderr.decode(errors='replace')[-3000:]}))
    return result.stdout


def save(name, value):
    (checkpoint / name).write_bytes((json.dumps(value, indent=2) + '\n').encode())


def decode(record):
    data = base64.b64decode(record['base64'], validate=True)
    assert len(data) == record['bytes'] and sha(data) == record['sha256']
    return data


def safe_path(value):
    path = PurePosixPath(value)
    assert not path.is_absolute() and '..' not in path.parts and '\\' not in value
    return path


raw = zlib.decompress(base64.b64decode(PACKED, validate=True))
assert sha(raw) == PAYLOAD_SHA
payload = json.loads(raw)
assert payload['parent'] == PARENT and payload['branch'] == BRANCH and payload['docroot'] == DOCROOT
assert len(payload['source']) == 2 and {row['path'] for row in payload['source']} == SOURCES
assert not checkpoint.exists(), 'Existing checkpoint requires diagnosis, never a blind retry'
assert git('rev-parse', 'HEAD').decode().strip() == PARENT
assert git('branch', '--show-current').decode().strip() == BRANCH
assert not git('status', '--porcelain').strip()
assert git('remote', 'get-url', 'origin').decode().strip() in (
    'https://github.com/davidpovarsky/anytype-swift.git',
    'https://github.com/davidpovarsky/anytype-swift',
)
assert git('ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH).decode().split()[0] == PARENT

workflow_paths = [path for path in git('ls-tree', '-r', '--name-only', 'HEAD', '--', '.github/workflows').decode().splitlines()
                  if path.endswith(('.yml', '.yaml'))]
audit = payload['workflow_audit']
assert audit['matching_count'] == 0
assert sorted(workflow_paths) == sorted(row['path'] for row in audit['workflows'])
for row in audit['workflows']:
    assert git('rev-parse', 'HEAD:' + row['path']).decode().strip() == row['git_blob']
assert len(payload['retained_property_sources']) == 14
for row in payload['retained_property_sources'] + payload['unchanged_control_sources']:
    assert row['path'] not in SOURCES
    assert sha(git('show', 'HEAD:' + row['path'])) == row['sha256']

receipt_info = payload['syntax_receipt']
syntax_raw = Path(receipt_info['host_path']).read_bytes()
assert len(syntax_raw) == receipt_info['bytes'] and sha(syntax_raw) == receipt_info['sha256']
syntax = json.loads(syntax_raw)
assert syntax['status'] == 'PASS_2_COMPLETE_SWIFT_FILES_SYNTAX' and syntax['exit_code'] == 0
assert syntax['compiler_processes'] == 1 and syntax['prior_suites_rerun'] is False
assert syntax['Apple_typecheck'] == syntax['Native'] == 'NOT_RUN'
assert {row['path']: row['source_sha256'] for row in syntax['inputs']} == {
    row['path']: row['sha256'] for row in payload['source']
}
assert syntax['patch']['sha256'] == payload['patch']['sha256']
evidence_paths = set()
for row in payload['evidence']:
    safe_path(row['path'])
    assert row['path'].startswith(DOCROOT + '/') and row['path'] not in evidence_paths
    assert not (worktree / row['path']).exists()
    evidence_paths.add(row['path'])
    decode(row)
assert DOCROOT + '/SOURCE_PUBLICATION.json' not in evidence_paths
assert DOCROOT + '/.gitattributes' not in evidence_paths
patch = decode(payload['patch'])
for row in payload['source']:
    safe_path(row['path'])
    decode(row)

checkpoint.mkdir(parents=True)
(checkpoint / 'PAYLOAD.json').write_bytes(raw)
save('START.json', {'created_at': now(), 'parent': PARENT, 'branch': BRANCH, 'payload_sha256': PAYLOAD_SHA})
normalizations = []
for row in payload['source']:
    canonical = git('show', 'HEAD:' + row['path'])
    assert sha(canonical) == row['before_sha256']
    assert git('rev-parse', 'HEAD:' + row['path']).decode().strip() == row['base_git_blob']
    current = (worktree / row['path']).read_bytes()
    assert current == canonical or current.replace(b'\r\n', b'\n') == canonical
    if current != canonical:
        backup = checkpoint / 'raw-preimages' / row['path']
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(current)
        (worktree / row['path']).write_bytes(canonical)
        normalizations.append({'path': row['path'], 'stage': 'preimage', 'raw_sha256': sha(current), 'canonical_sha256': sha(canonical)})
git('apply', '--check', '--whitespace=error-all', '-', data=patch)
git('apply', '--whitespace=error-all', '-', data=patch)
for row in payload['source']:
    expected = decode(row)
    current = (worktree / row['path']).read_bytes()
    assert current == expected or current.replace(b'\r\n', b'\n') == expected
    if current != expected:
        backup = checkpoint / 'raw-postimages' / row['path']
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(current)
        (worktree / row['path']).write_bytes(expected)
        normalizations.append({'path': row['path'], 'stage': 'postimage', 'raw_sha256': sha(current), 'canonical_sha256': sha(expected)})
paths = sorted(SOURCES)
assert sorted(git('diff', '--name-only').decode().splitlines()) == paths
git('diff', '--check', '--', *paths)
git('add', '--', *paths)
assert sorted(git('diff', '--cached', '--name-only').decode().splitlines()) == paths
for row in payload['source']:
    assert sha(git('show', ':' + row['path'])) == row['sha256']
git('commit', '-m', 'fix(editor): enable source-bound original object property addition')
code = git('rev-parse', 'HEAD').decode().strip()
assert git('rev-parse', 'HEAD^').decode().strip() == PARENT
assert sorted(git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().splitlines()) == paths
for row in payload['source'] + payload['retained_property_sources'] + payload['unchanged_control_sources']:
    assert sha(git('show', 'HEAD:' + row['path'])) == row['sha256']
for path in ['.github', 'Tools', 'Anytype.xcodeproj', 'Anytype/Resources', 'Modules']:
    assert git('rev-parse', 'HEAD:' + path) == git('rev-parse', PARENT + ':' + path)
receipt = {
    'created_at': now(), 'parent': PARENT, 'source_commit': code, 'branch': BRANCH,
    'patch_sha256': payload['patch']['sha256'],
    'source_files': [{key: value for key, value in row.items() if key != 'base64'} for row in payload['source']],
    'preimages_index_committed_bytes_and_whitespace': 'PASS',
    'syntax_receipt': receipt_info, 'syntax_full_files': 2,
    'retained_property_source_files_unchanged': 14,
    'unchanged_control_sources': payload['unchanged_control_sources'],
    'historical_controls': 'Previously executed property14 remain historical bounded evidence; no claim that Add UI was executed.',
    'new_tests_or_CI_runs_during_publication': 0,
    'Apple_typecheck': 'NOT_RUN', 'Native_Add_create_attach_save_reopen': 'NOT_RUN',
    'workflow_blobs_verified': len(workflow_paths), 'matching_push_workflows': 0,
    'CRLF_only_canonicalizations': normalizations, 'Git_configuration_changed': False,
}
save('SOURCE_PUBLICATION.json', receipt)
for row in payload['evidence']:
    destination = worktree / row['path']
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(decode(row))
(worktree / DOCROOT / 'SOURCE_PUBLICATION.json').write_bytes((checkpoint / 'SOURCE_PUBLICATION.json').read_bytes())
(worktree / DOCROOT / '.gitattributes').write_bytes(b'* -text\n')
git('add', '--', DOCROOT)
for row in payload['evidence']:
    assert sha(git('show', ':' + row['path'])) == row['sha256']
staged = git('diff', '--cached', '--name-only').decode().splitlines()
assert len(staged) == len(payload['evidence']) + 2 and all(path.startswith(DOCROOT + '/') for path in staged)
git('commit', '-m', 'docs(editor): retain same-object property Add review and syntax evidence')
head = git('rev-parse', 'HEAD').decode().strip()
assert git('rev-parse', 'HEAD^').decode().strip() == code
expected_evidence_paths = sorted(evidence_paths | {
    DOCROOT + '/SOURCE_PUBLICATION.json', DOCROOT + '/.gitattributes',
})
assert sorted(git('diff-tree', '--no-commit-id', '--name-only', '-r', head).decode().splitlines()) == expected_evidence_paths
for row in payload['evidence'] + payload['source'] + payload['retained_property_sources'] + payload['unchanged_control_sources']:
    assert sha(git('show', head + ':' + row['path'])) == row['sha256']
assert git('show', head + ':' + DOCROOT + '/SOURCE_PUBLICATION.json') == (checkpoint / 'SOURCE_PUBLICATION.json').read_bytes()
assert git('show', head + ':' + DOCROOT + '/.gitattributes') == b'* -text\n'
for path in ['.github', 'Tools', 'Anytype.xcodeproj', 'Anytype/Resources', 'Modules']:
    assert git('rev-parse', head + ':' + path) == git('rev-parse', PARENT + ':' + path)
assert git('rev-parse', head + ':Anytype/Sources') == git('rev-parse', code + ':Anytype/Sources')
assert not git('status', '--porcelain').strip()
assert git('ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH).decode().split()[0] == PARENT
save('PUSH_ATTEMPT.json', {'started_at': now(), 'old_remote': PARENT, 'new_remote': head, 'nonforce': True})
git('push', 'origin', head + ':refs/heads/' + BRANCH, timeout=180)
remote = git('ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH).decode().split()[0]
assert remote == head
save('FINAL.json', {
    'finished_at': now(), 'status': 'PUBLISHED_NEUTRAL_SOURCE_ONLY', 'source_commit': code,
    'evidence_commit': head, 'remote_head': remote, 'branch': BRANCH, 'files': 2,
    'syntax_full_files': 2, 'new_tests_or_CI_runs': 0, 'Native': 'NOT_RUN',
    'shared_producer_ref_written': False,
    'url': 'https://github.com/davidpovarsky/anytype-swift/tree/' + head + '/' + DOCROOT,
})
print((checkpoint / 'FINAL.json').read_text(encoding='utf-8'))
