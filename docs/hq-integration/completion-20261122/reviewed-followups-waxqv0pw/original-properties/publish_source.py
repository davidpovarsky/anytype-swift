from pathlib import Path
import base64, hashlib, json, subprocess, datetime, zlib

PACKED = '__PROPERTY_JOIN_PAYLOAD__'
PAYLOAD_SHA = '__PAYLOAD_SHA__'
raw = zlib.decompress(base64.b64decode(PACKED, validate=True))
assert hashlib.sha256(raw).hexdigest() == PAYLOAD_SHA
p = json.loads(raw)
w = Path(r'C:\Users\DAVID\Code\anytype-followups-waxqv0pw-20261122')
c = Path(r'C:\Users\DAVID\Code\Codex-Agent-HQ\build\anytype-properties-waxqv0pw-20261122')

def sha(b): return hashlib.sha256(b).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def git(*args, data=None, timeout=120):
    cmd = ['git', '-c', 'core.autocrlf=false'] if args[0] == 'apply' else ['git']
    r = subprocess.run([*cmd, *args], cwd=w, input=data, capture_output=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(json.dumps({'args': args, 'code': r.returncode,
            'stdout': r.stdout.decode(errors='replace')[-2000:], 'stderr': r.stderr.decode(errors='replace')[-3000:]}))
    return r.stdout
def save(name, value): (c / name).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
def decode(f):
    b = base64.b64decode(f['base64'], validate=True)
    assert len(b) == f['bytes'] and sha(b) == f['sha256']
    return b

assert not c.exists(), 'Existing checkpoint requires read-only diagnosis, never a blind publication retry'
assert p['parent'] == 'f25442b59f021ebb8dd5b2ec2a5be1f5f2c6be5e'
assert git('rev-parse', 'HEAD').decode().strip() == p['parent']
assert git('branch', '--show-current').decode().strip() == p['branch']
assert not git('status', '--porcelain').strip()
assert git('remote', 'get-url', 'origin').decode().strip() in [
    'https://github.com/davidpovarsky/anytype-swift.git', 'https://github.com/davidpovarsky/anytype-swift']
assert git('ls-remote', '--heads', 'origin', 'refs/heads/' + p['branch']).decode().split()[0] == p['parent']
for f in p['unchanged_control_sources']:
    assert sha(git('show', 'HEAD:' + f['path'])) == f['sha256'], ('Control production source differs', f['path'])
workflows = [x for x in git('ls-tree', '-r', '--name-only', 'HEAD', '--', '.github/workflows').decode().splitlines()
             if x.endswith(('.yml', '.yaml'))]
assert sorted(workflows) == sorted(f['path'] for f in p['workflow_audit']['workflows'])
assert p['workflow_audit']['matching_count'] == 0
assert p['control_summary']['executed'] == p['control_summary']['passed']
assert p['control_summary']['executed'] > 0 and not p['control_summary']['prior_suites_rerun']
for f in p['validation_receipts']:
    assert sha(Path(f['host_path']).read_bytes()) == f['sha256'], ('Actual validation receipt changed', f['host_path'])
for f in p['workflow_audit']['workflows']:
    assert git('rev-parse', 'HEAD:' + f['path']).decode().strip() == f['git_blob']
c.mkdir(parents=True)
(c / 'PAYLOAD.json').write_bytes(raw)
save('START.json', {'started_at': now(), 'parent': p['parent'], 'branch': p['branch'], 'payload_sha256': PAYLOAD_SHA})
normalizations = []
for f in p['source']:
    canonical = git('show', 'HEAD:' + f['path'])
    assert sha(canonical) == f['before_sha256']
    assert git('rev-parse', 'HEAD:' + f['path']).decode().strip() == f['base_git_blob']
    current = (w / f['path']).read_bytes()
    assert current == canonical or current.replace(b'\r\n', b'\n') == canonical
    if current != canonical:
        backup = c / 'raw-preimages' / f['path']
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(current)
        (w / f['path']).write_bytes(canonical)
        normalizations.append({'path': f['path'], 'stage': 'preimage', 'raw_sha256': sha(current), 'canonical_sha256': sha(canonical)})
patch = decode(p['patch'])
git('apply', '--check', '--whitespace=error-all', '-', data=patch)
git('apply', '--whitespace=error-all', '-', data=patch)
for f in p['source']:
    current, expected = (w / f['path']).read_bytes(), decode(f)
    assert current == expected or current.replace(b'\r\n', b'\n') == expected
    if current != expected:
        backup = c / 'raw-postimages' / f['path']
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(current)
        (w / f['path']).write_bytes(expected)
        normalizations.append({'path': f['path'], 'stage': 'postimage', 'raw_sha256': sha(current), 'canonical_sha256': sha(expected)})
paths = sorted(f['path'] for f in p['source'])
assert len(paths) == 16 and sorted(git('diff', '--name-only').decode().splitlines()) == paths
git('diff', '--check', '--', *paths)
git('add', '--', *paths)
assert sorted(git('diff', '--cached', '--name-only').decode().splitlines()) == paths
for f in p['source']: assert sha(git('show', ':' + f['path'])) == f['sha256']
git('commit', '-m', 'fix(editor): bind original property modals and mount to prepared source')
code = git('rev-parse', 'HEAD').decode().strip()
assert git('rev-parse', 'HEAD^').decode().strip() == p['parent']
assert sorted(git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().splitlines()) == paths
for f in p['source']: assert sha(git('show', 'HEAD:' + f['path'])) == f['sha256']
for keep in ['.github', 'Tools', 'Anytype.xcodeproj', 'Anytype/Resources', 'Modules/PinkhaHeart',
             'Modules/ProtobufMessages/Sources/Generated', 'Modules/ProtobufMessages/Sources/Protocol']:
    assert git('rev-parse', 'HEAD:' + keep) == git('rev-parse', p['parent'] + ':' + keep)
receipt = {'created_at': now(), 'parent': p['parent'], 'source_commit': code, 'branch': p['branch'],
           'patch_sha256': p['patch']['sha256'], 'source_files': [{k: v for k, v in f.items() if k != 'base64'} for f in p['source']],
           'preimages_index_commit_and_whitespace': 'PASS', 'retained_syntax_files': 16, 'retained_new_controls': p['control_summary']['executed'],
           'control_scope': p['control_summary']['scope'],
           'unchanged_control_sources_verified_in_git': p['unchanged_control_sources'],
           'workflow_blobs_verified': len(workflows), 'matching_push_workflows': 0,
           'new_tests_or_CI_runs_during_publication': 0, 'Apple_typecheck': 'NOT_RUN', 'Native_property_create_update_remove_save_reopen': 'NOT_RUN',
           'CRLF_only_canonicalizations': normalizations, 'Git_configuration_changed': False}
save('SOURCE_PUBLICATION.json', receipt)
for f in p['evidence']:
    dest = w / f['path']
    assert not dest.exists()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(decode(f))
(w / p['docroot'] / 'SOURCE_PUBLICATION.json').write_bytes((c / 'SOURCE_PUBLICATION.json').read_bytes())
(w / p['docroot'] / '.gitattributes').write_bytes(b'* -text\n')
git('add', '--', p['docroot'])
for f in p['evidence']: assert sha(git('show', ':' + f['path'])) == f['sha256']
staged = git('diff', '--cached', '--name-only').decode().splitlines()
assert len(staged) == len(p['evidence']) + 2 and all(x.startswith(p['docroot'] + '/') for x in staged)
git('commit', '-m', 'docs(editor): seal original property source review and bounded acceptance evidence')
head = git('rev-parse', 'HEAD').decode().strip()
assert git('rev-parse', 'HEAD^').decode().strip() == code
assert not git('status', '--porcelain').strip()
assert git('ls-remote', '--heads', 'origin', 'refs/heads/' + p['branch']).decode().split()[0] == p['parent']
save('PUSH_ATTEMPT.json', {'started_at': now(), 'old_remote': p['parent'], 'new_remote': head, 'nonforce': True})
push = git('push', 'origin', 'HEAD:refs/heads/' + p['branch'], timeout=180).decode()
remote = git('ls-remote', '--heads', 'origin', 'refs/heads/' + p['branch']).decode().split()[0]
assert remote == head
save('FINAL.json', {'finished_at': now(), 'status': 'PUBLISHED_NEUTRAL_SOURCE_ONLY', 'source_commit': code,
                   'evidence_commit': head, 'remote_head': remote, 'branch': p['branch'], 'files': 16,
                   'retained_controls': p['control_summary']['executed'], 'retained_syntax_files': 16, 'new_tests_or_CI_runs': 0,
                   'Native': 'NOT_RUN', 'shared_producer_ref_written': False,
                   'url': 'https://github.com/davidpovarsky/anytype-swift/tree/' + head + '/' + p['docroot']})
print((c / 'FINAL.json').read_text(encoding='utf-8'))
