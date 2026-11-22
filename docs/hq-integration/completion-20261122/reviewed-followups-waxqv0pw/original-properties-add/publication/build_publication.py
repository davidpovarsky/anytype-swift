from pathlib import Path
import ast
import base64
import hashlib
import json
import zlib


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 'original_editor_property_join_waxqv0pw_20261122'
OUT = ROOT / 'publication'
PARENT = '06b639ff196a66c19d22dda7ea28b47ce6801705'
BRANCH = 'codex/otzaria-reviewed-followups-waxqv0pw-20261122'
DOCROOT = 'docs/hq-integration/completion-20261122/reviewed-followups-waxqv0pw/original-properties-add'
PATCH_SHA = '0e909411da157ffa3e5f25980f016017fd46629827ed181d0d11cf0740b8171e'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def encode(path, data):
    return {'path': path, 'bytes': len(data), 'sha256': sha(data), 'base64': base64.b64encode(data).decode()}


manifest = read(ROOT / 'SOURCE_MANIFEST.json')
seal = read(ROOT / 'FROZEN_SOURCE_SEAL.json')
assert manifest['base_commit'] == PARENT
assert manifest['files'] == seal['sources'] and len(manifest['files']) == 2
assert manifest['combined_patch']['sha256'] == PATCH_SHA
for row in seal['sealed_sidecars']:
    data = (ROOT / row['path']).read_bytes()
    assert len(data) == row['bytes'] and sha(data) == row['sha256']
patch_data = (ROOT / manifest['combined_patch']['path']).read_bytes()
assert sha(patch_data) == PATCH_SHA
source = []
for row in manifest['files']:
    before = (ROOT / 'base' / row['path']).read_bytes()
    after = (ROOT / 'source' / row['path']).read_bytes()
    assert sha(before) == row['base_sha256'] and sha(after) == row['source_sha256']
    assert hashlib.sha1(b'blob ' + str(len(before)).encode() + b'\0' + before).hexdigest() == row['base_git_blob']
    assert hashlib.sha1(b'blob ' + str(len(after)).encode() + b'\0' + after).hexdigest() == row['source_git_blob']
    source.append(encode(row['path'], after) | {'before_sha256': row['base_sha256'], 'base_git_blob': row['base_git_blob'], 'source_git_blob': row['source_git_blob']})
paths = {row['path'] for row in source}
historical = read(OLD / 'SOURCE_MANIFEST.json')
retained = []
for row in historical['files']:
    if row['path'] in paths:
        assert sha((ROOT / 'base' / row['path']).read_bytes()) == row['source_sha256']
    else:
        assert sha((OLD / 'source' / row['path']).read_bytes()) == row['source_sha256']
        retained.append({'path': row['path'], 'sha256': row['source_sha256'], 'git_blob': row['source_git_blob']})
assert len(retained) == 14
control_sources = [{key: row[key] for key in ('path', 'sha256', 'git_blob')} for row in read(OLD / 'review/CONTROL_PRODUCTION_IDENTITY.json')['files'] if not row['included_in_changed_source']]
assert len(control_sources) == 11 and all(row['path'] not in paths for row in control_sources)
workflow = read(OLD / 'review/PUSH_WORKFLOW_AUDIT.json')
assert workflow['matching_count'] == 0
syntax_raw = (ROOT / 'validation/PARSE_RESULT.json').read_bytes()
syntax = json.loads(syntax_raw)
binding = read(ROOT / 'validation/SOURCE_BINDING.json')
assert sha(syntax_raw) == binding['receipt_sha256'] == '515cb5f21a74fc9469232bb92690b4a4dac6ea9ce552975fb29c8ffeb8d1c380'
assert syntax['inputs'] == manifest['files'] and syntax['patch'] == manifest['combined_patch']
assert syntax['status'] == 'PASS_2_COMPLETE_SWIFT_FILES_SYNTAX' and syntax['exit_code'] == 0 and syntax['compiler_processes'] == 1
assert sha((ROOT / 'review/INDEPENDENT_SOURCE_REVIEW.json').read_bytes()) == 'f874f99c55aafd38589fc88bbc4c5a4f7d99eef3c9b870667f24d7b3e1fca51a'
publisher = (OUT / 'publish_source.py').read_bytes()
publisher_review = read(ROOT / 'review/PUBLISHER_FINAL_BOUNDARY_PEER_REVIEW.json')
assert sha(publisher) == 'ab769cf757c5da9bac6d18cd38c451cf32cd404e360623a42f7fa02d44bd7376'
ast.parse(publisher)

candidate_paths = [ROOT / name for name in ('README.md', 'SOURCE_MANIFEST.json', 'FROZEN_SOURCE_SEAL.json', 'PRESERVATION_RECEIPT.json', 'VALIDATION_PLAN.json', 'original-property-add.patch')]
for directory in ('base', 'source', 'references'):
    candidate_paths += [path for path in (ROOT / directory).rglob('*') if path.is_file()]
candidate_paths += [path for path in (ROOT / 'review').rglob('*') if path.is_file() and not any(part.startswith('apply-check-') for part in path.parts)]
evidence = []
for path in sorted(set(candidate_paths)):
    evidence.append(encode(DOCROOT + '/candidate/' + path.relative_to(ROOT).as_posix(), path.read_bytes()))
for name in ('PARSE_RESULT.json', 'SOURCE_BINDING.json', 'ACTUAL_JOB_NOTIFICATION.json', 'PARSE_PAYLOAD.json', 'run_parse.py', 'run_parse.rendered.py'):
    path = ROOT / 'validation' / name
    evidence.append(encode(DOCROOT + '/validation/' + name, path.read_bytes()))
for name in ('publish_source.py', 'build_publication.py'):
    evidence.append(encode(DOCROOT + '/publication/' + name, (OUT / name).read_bytes()))
evidence.append(encode(DOCROOT + '/README.md', (OUT / 'DELIVERY_README.md').read_bytes()))
index = {
    'status': 'SOURCE_REVIEW_AND_ACTUAL_SYNTAX_EVIDENCE_READY',
    'parent': PARENT, 'patch_sha256': PATCH_SHA,
    'files': [{key: row[key] for key in ('path', 'bytes', 'sha256')} for row in evidence],
    'scope': 'Candidate packet preserves historical author statements; actual root syntax and source binding are separate. No runtime/Apple/Native pass.',
    'index_self_excluded': True, 'publication_receipt_and_attributes_generated_later': True,
}
index_raw = (json.dumps(index, indent=2) + '\n').encode()
(OUT / 'EVIDENCE_INDEX.json').write_bytes(index_raw)
evidence.append(encode(DOCROOT + '/EVIDENCE_INDEX.json', index_raw))
assert len({row['path'] for row in evidence}) == len(evidence)
payload = {
    'parent': PARENT, 'branch': BRANCH, 'docroot': DOCROOT,
    'source': source, 'patch': encode('original-property-add.patch', patch_data),
    'retained_property_sources': retained, 'unchanged_control_sources': control_sources,
    'workflow_audit': workflow,
    'syntax_receipt': {'host_path': binding['receipt_host_path'], 'bytes': len(syntax_raw), 'sha256': sha(syntax_raw)},
    'evidence': evidence,
}
raw = json.dumps(payload, separators=(',', ':')).encode()
compressed = zlib.compress(raw, 9)
(OUT / 'PAYLOAD.json').write_bytes(raw)
(OUT / 'PAYLOAD.zlib').write_bytes(compressed)
rendered = publisher.decode().replace('__PROPERTY_ADD_PUBLICATION_PAYLOAD__', base64.b64encode(compressed).decode()).replace('__PAYLOAD_SHA__', sha(raw))
assert '__PROPERTY_ADD_PUBLICATION_PAYLOAD__' not in rendered and '__PAYLOAD_SHA__' not in rendered
ast.parse(rendered)
(OUT / 'publish_source.rendered.py').write_text(rendered)
summary = {
    'status': 'READY_FOR_GUARDED_PUBLICATION_NOT_EXECUTED', 'source_files': 2,
    'source_patch_sha256': PATCH_SHA, 'evidence_files': len(evidence),
    'payload_bytes': len(raw), 'payload_sha256': sha(raw),
    'compressed_bytes': len(compressed), 'compressed_sha256': sha(compressed),
    'rendered_script_bytes': len(rendered.encode()), 'rendered_script_sha256': sha(rendered.encode()),
    'publisher_template_sha256': sha(publisher),
    'retained_property_files': len(retained), 'unchanged_control_sources': len(control_sources),
    'actual_syntax_receipt_sha256': sha(syntax_raw), 'new_tests_or_CI_runs': 0,
}
(OUT / 'BUILD_RESULT.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary))
