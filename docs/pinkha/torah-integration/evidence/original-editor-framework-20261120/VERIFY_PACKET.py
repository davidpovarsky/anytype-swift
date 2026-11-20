import ast
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = next(path for path in HERE.parents if (path / 'Tools/OriginalEditor/framework_profile.json').is_file())
index = json.loads((HERE / 'PACKET_INDEX.json').read_text())
for row in index['payloads']:
    path = ROOT / row['path']
    assert path.is_file() and not path.is_symlink(), row['path']
    value = path.read_bytes()
    assert len(value) == row['bytes'] and hashlib.sha256(value).hexdigest() == row['sha256'], row['path']
    assert hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == row['git_blob'], row['path']

def raw(name):
    return gzip.decompress((HERE / 'raw' / (name + '.gz')).read_bytes())

v2 = json.loads((HERE / 'V2_BUDGET_AND_IMPORT_PROOF.json').read_text())
archive = (HERE / 'raw/sealed-v1.tar.gz').read_bytes()
assert hashlib.sha256(archive).hexdigest() == v2['sealed_v1_archive_sha256']
with tarfile.open(fileobj=io.BytesIO(gzip.decompress(archive)), mode='r:') as handle:
    members = handle.getmembers()
    assert all(item.isfile() for item in members)
    old = {item.name: handle.extractfile(item).read() for item in members}
    assert len(old) == len(members) == 36
old_index_path = HERE.relative_to(ROOT).as_posix() + '/PACKET_INDEX.json'
assert hashlib.sha256(old[old_index_path]).hexdigest() == 'b6b8c27f225a393ef8bc17dcf0756ad7fca979923bb2beb5f257106fbc900860'
old_index = json.loads(old[old_index_path])
for item in old_index['payloads']:
    value = old[item['path']]
    assert len(value) == item['bytes'] and hashlib.sha256(value).hexdigest() == item['sha256']
    assert hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == item['git_blob']
old_result_path = HERE.relative_to(ROOT).as_posix() + '/raw/validation/final43/RESULT.json.gz'
previous = json.loads(gzip.decompress(old[old_result_path]))
assert previous['returncode'] == 0 and previous['qualified_local_controls'] and previous['inputs_unchanged']
assert len(previous['expected_cases']) == len(set(previous['expected_cases'])) == 43
assert sorted(previous['expected_cases']) == sorted(previous['observed_passed_cases'])

result = json.loads(raw('validation/final44/RESULT.json'))
assert result['returncode'] == 0 and result['inputs_unchanged'] and not result['failed_cases']
assert len(result['passed_cases']) == len(set(result['passed_cases'])) == 44
assert set(previous['observed_passed_cases']).issubset(result['passed_cases'])
tree = ast.parse((ROOT / 'Tools/OriginalEditor/test_framework.py').read_text())
declared = {'__main__.' + item.name + '.' + method.name for item in tree.body if isinstance(item, ast.ClassDef)
            for method in item.body if isinstance(method, ast.FunctionDef) and method.name.startswith('test_')}
assert set(result['passed_cases']) == declared
before = json.loads(raw('validation/final44/INPUTS_BEFORE.json'))
assert before == json.loads(raw('validation/final44/INPUTS_AFTER.json'))
for path, observed in before.items():
    value = (ROOT / path).read_bytes()
    assert len(value) == observed['bytes'] and hashlib.sha256(value).hexdigest() == observed['sha256'], path
red = json.loads(raw('validation/budget-red-v1/RESULT.json'))
assert red['returncode'] == 1 and len(red['failed_cases']) == 1 and not red['passed_cases'] and red['inputs_unchanged']

p = 'Tools/OriginalEditor/run_framework_acceptance.py'
assert (ROOT / p).read_bytes().replace(b"'framework-build', 6000)", b"'framework-build', 3600)", 1) == old[p]
p = '.github/workflows/pinkha-original-editor-framework.yml'
assert (ROOT / p).read_bytes().replace(b'    timeout-minutes: 140', b'    timeout-minutes: 120', 1).replace(b'        timeout-minutes: 120', b'        timeout-minutes: 100', 1) == old[p]
p = 'Tools/OriginalEditor/test_framework.py'
current = (ROOT / p).read_bytes()
begin = current.index(b'class ObservedOriginalBuildBudget(unittest.TestCase):')
end = current.index(b"if __name__ == '__main__':", begin)
assert current[:begin] + current[end:] == old[p]
for path in v2['unchanged_runtime_paths']:
    assert (ROOT / path).read_bytes() == old[path], path
sys.path.insert(0, str(ROOT / 'Tools/OriginalEditor'))
from framework_profile import read_manifest, verify_project
profile = read_manifest()
proof = verify_project((ROOT / 'Anytype.xcodeproj/project.pbxproj').read_bytes(),
                       (ROOT / 'Tools/OriginalEditor/original_project.pbxproj').read_bytes(), profile)
installer = (ROOT / 'Tools/PinkhaNativeDerived/install_verified_heart.py').read_bytes()
suffix = b",\n                             'codex/otzaria-original-editor-framework-reviewed-20261120'"
assert installer.count(suffix) == 1
original = installer.replace(suffix, b'', 1)
assert hashlib.sha1(b'blob ' + str(len(original)).encode() + b'\0' + original).hexdigest() == profile['original_heart_installer_blob']
print(json.dumps({'payloads_verified': len(index['payloads']), 'sealed_v1_payloads': 35,
                  'local_controls': 44, 'discriminating_budget_red': '0/1 actual exit1',
                  'original_app_project_inverse': proof['whole_project_inverse_exact'],
                  'original_products': 44, 'original_package_pins': 44,
                  'Apple_framework_import_resources': 'NOT_RUN', 'native_editor_ui': 'NOT_RUN',
                  'workflow_activated': False}, sort_keys=True))
