from pathlib import Path
import hashlib, json, shutil, difflib, subprocess, tempfile

root = Path(__file__).resolve().parent
workspace = root.parent
modal = workspace / 'original_editor_property_modal_waxqv0pw_20261122'
value = workspace / 'original_editor_property_value_entry_waxqv0pw_20261122'
mount = workspace / 'original_editor_property_mount_waxqv0pw_20261122'
view = workspace / 'original_editor_property_mount_view_waxqv0pw_20261122'

def sha(data): return hashlib.sha256(data).hexdigest()
def blob(data): return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
def read_json(path): return json.loads(path.read_bytes())

expected = read_json(root / 'review/F254_FC03_PREIMAGE_IDENTITY.json')
assert len(expected['files']) == 16
vm_path = 'Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Properties/Views/ObjectFieldsView/ObjectPropertiesViewModel.swift'
modal_inputs = read_json(modal / 'CANDIDATE_INPUTS.json')
value_inputs = read_json(value / 'SOURCE_MANIFEST_R2.json')
mount_inputs = read_json(mount / 'DRAFT_R2.json')
assert mount_inputs['patch_sha256'] == 'ca6ec5b788e40eb8206bfa6fa14744fe770f0ae6d7997cba2fab5540b1c2d21b'
assert sha((modal / 'original-property-modal-owner.patch').read_bytes()) == modal_inputs['patch_sha256']
assert sha((value / 'prepared-property-value-entry-r2.patch').read_bytes()) == value_inputs['patch_sha256']
assert sha((mount / 'prepared-property-mount-r2.patch').read_bytes()) == mount_inputs['patch_sha256']
assert sha((view / 'prepared-property-view-composition.patch').read_bytes()) == '0a5d41a35493dbc4563c912ba0456f341f4c32b204bdccd1c1768b922df85ae3'

paths = {}
for item in modal_inputs['files']:
    paths[item['path']] = (modal, modal, item['candidate_sha256'])
for item in value_inputs['files']:
    paths[item['path']] = (value, value, item['after_sha256'])
paths[vm_path] = (value, mount, mount_inputs['candidate_sha256'])
view_path = vm_path.replace('ObjectPropertiesViewModel.swift', 'ObjectPropertiesView.swift')
paths[view_path] = (view, view, '1388133f8336031315e70214b4ba1bf55808b22c6a96446aaec108b9338db8b5')
assert sorted(paths) == sorted(f['path'] for f in expected['files'])
assert (mount / 'base' / vm_path).read_bytes() == (value / 'source' / vm_path).read_bytes()

files, diffs = [], []
for item in sorted(expected['files'], key=lambda x: x['path']):
    path = item['path']
    before_root, after_root, output_sha = paths[path]
    before, after = (before_root / 'base' / path).read_bytes(), (after_root / 'source' / path).read_bytes()
    assert blob(before) == item['actual_blob'] == item['expected_blob'], path
    assert sha(after) == output_sha, path
    assert before != after and b'\r' not in before and b'\r' not in after
    for label, data in [('base', before), ('source', after)]:
        dest = root / label / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    files.append({'path': path, 'base_git_blob': blob(before), 'base_sha256': sha(before),
                  'source_git_blob': blob(after), 'source_sha256': sha(after), 'source_bytes': len(after)})
    diffs.extend(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                    fromfile='a/' + path, tofile='b/' + path))

patch = ''.join(diffs).encode()
patch_name = 'original-property-modal-value-mount.patch'
(root / patch_name).write_bytes(patch)
manifest = {'base_commit': expected['base'], 'compatible_frozen_producer': expected['frozen_producer'],
            'status': 'SOURCE_JOIN_REVIEW_AND_NEW_VALIDATION_PENDING', 'files': files,
            'combined_patch': {'path': patch_name, 'sha256': sha(patch), 'bytes': len(patch)},
            'components': {'modal13': modal_inputs['patch_sha256'], 'value2': value_inputs['patch_sha256'],
                           'mount_vm_increment': mount_inputs['patch_sha256'],
                           'mount_view': '0a5d41a35493dbc4563c912ba0456f341f4c32b204bdccd1c1768b922df85ae3'},
            'Apple_typecheck': 'NOT_RUN', 'Native': 'NOT_RUN'}
(root / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')

with tempfile.TemporaryDirectory(prefix='property-join-') as tmp:
    target = Path(tmp)
    shutil.copytree(root / 'base', target, dirs_exist_ok=True)
    commands = []
    for flags in [('--check', '--whitespace=error-all'), ('--whitespace=error-all',)]:
        cmd = ['git', '-c', 'core.autocrlf=false', 'apply', *flags, '-']
        result = subprocess.run(cmd, input=patch, cwd=target, capture_output=True)
        commands.append({'command': cmd, 'exit_code': result.returncode,
                         'stdout': result.stdout.decode(), 'stderr': result.stderr.decode()})
        assert result.returncode == 0, commands[-1]
    for item in files:
        assert (target / item['path']).read_bytes() == (root / 'source' / item['path']).read_bytes(), item['path']
receipt = {'status': 'PASS_EXACT_16_PREIMAGES_APPLIED_OUTPUTS', 'patch_sha256': sha(patch),
           'files': files, 'commands': commands, 'new_tests_or_compiler_calls': 0}
(root / 'review/COMBINED_SOURCE_APPLICATION.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({'files': len(files), 'patch': manifest['combined_patch'], 'application': receipt['status']}))
