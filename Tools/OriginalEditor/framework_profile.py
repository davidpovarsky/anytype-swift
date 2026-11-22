"""Fail-closed source boundary for the genuine original-editor framework."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from pbx_source import loads, object_text, require

BRANCH = 'codex/otzaria-original-editor-framework-v13-body-reviewed-20261122'
REPOSITORY = 'davidpovarsky/anytype-swift'
TARGET = 'AnytypeOriginalEditor'
APP_TARGET = '0303ECFA22D8EDAA005C552B'
SOURCE_GROUP = '3D69B4E82CAEA9CB003F5A91'
HERE = Path(__file__).resolve().parent


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args]).decode().strip()


def read_manifest():
    value = json.loads((HERE / 'framework_profile.json').read_text())
    require(value.get('schema') == 1 and value.get('branch') == BRANCH
            and value.get('package_pin_count') == 51, 'Unreviewed framework profile')
    require(set(value.get('reviewed_shared_dependency_objects', {})) == {
        '5333421A262E249100238121', '2A685D582B7B854200456E08', 'FA1000002F000001006805CC'},
        'Unreviewed shared runtime dependency object set')
    require(len(value.get('framework_facade_sources', [])) == 12
            and len(set(value['framework_facade_sources'])) == 12,
            'Incomplete reviewed Host facade source closure')
    require(sha256(HERE / 'public_host_contract.json') == value.get('public_host_contract_sha256'),
            'Reviewed public Host and qualification SPI contract differs')
    return value


def verify_project(raw, baseline, profile):
    require(blob(baseline) == profile['baseline_project_blob'], 'Original project snapshot differs')
    require(hashlib.sha256(raw).hexdigest() == profile['candidate_project_sha256'],
            'Reviewed additive framework project differs')
    original = loads(baseline.decode())
    candidate = loads(raw.decode())
    old, new = original['objects'], candidate['objects']
    dependencies = profile['reviewed_shared_dependency_objects']
    allowed = set(profile['allowed_original_structural_objects']) | set(dependencies)
    require(set(old) <= set(new), 'An original project object was removed')
    require(all(new[key] == value for key, value in old.items() if key not in allowed),
            'An original application, configuration, resource or dependency object changed')
    original_target = old[APP_TARGET]
    require(new[APP_TARGET] == original_target, 'Original app target was changed')
    require(all(key in old and new[key] == expected for key, expected in dependencies.items()),
            'Reviewed shared runtime package requirement differs')
    added = set(new) - set(old)
    require(len(added) == profile['new_project_objects'], 'Unexpected additional project objects')
    targets = [key for key in added if new[key]['isa'] == 'PBXNativeTarget']
    require(targets == [profile['framework_target_id']], 'Unexpected new product target')
    target = new[targets[0]]
    require(target['name'] == TARGET and target['productType'] == 'com.apple.product-type.framework'
            and target['dependencies'] == [], 'Framework borrows an app/test product')
    require(target['fileSystemSynchronizedGroups'] == original_target['fileSystemSynchronizedGroups'],
            'Framework does not compile the genuine original synchronized source/resource groups')
    exceptions = new[SOURCE_GROUP].get('exceptions')
    require(isinstance(exceptions, list) and len(exceptions) == 1, 'Unreviewed original-source exclusions')
    exception = new[exceptions[0]]
    require(exception == {'isa': 'PBXFileSystemSynchronizedBuildFileExceptionSet',
                         'membershipExceptions': ['ApplicationLayer/AppScene.swift'],
                         'target': targets[0]}, 'Only the original app entrypoint may be excluded')
    require([new[key] for key in target['packageProductDependencies']]
            == [old[key] for key in original_target['packageProductDependencies']],
            'Original package product closure differs')
    framework_configurations = new[target['buildConfigurationList']]['buildConfigurations']
    require(len(framework_configurations) == 4
            and all(new[key]['buildSettings'].get('LD_DYLIB_INSTALL_NAME') == '@rpath/$(EXECUTABLE_PATH)'
                    for key in framework_configurations),
            'Framework install identity is not explicitly relocatable in every target configuration')
    emission = profile['symbol_graph_emission']
    configuration = new[emission['configuration_id']]
    require(emission['configuration_id'] in new[target['buildConfigurationList']]['buildConfigurations']
            and configuration['name'] == emission['configuration_name'] == 'Debug-Anytype'
            and configuration['buildSettings'].get(emission['setting']) == emission['value'],
            'Public/SPI compiler graph emission is not bound to the framework target')
    emitters = [key for key, value in new.items() if value.get('isa') == 'XCBuildConfiguration'
                and emission['setting'] in value.get('buildSettings', {})]
    require(emitters == [emission['configuration_id']], 'A dependency or original app emits the Host graph')
    # Restore only the four additive structural objects and the three exact
    # reviewed shared package requirements. All original products stay intact.
    inverse = raw.decode()
    for key in sorted(added):
        inverse = inverse.replace(object_text(inverse, key), '', 1)
    for key in allowed:
        inverse = inverse.replace(object_text(inverse, key), object_text(baseline.decode(), key), 1)
    require(inverse.encode() == baseline, 'Complete original project inverse differs')
    return {'original_app_target_unchanged': True, 'original_objects': len(old),
            'new_objects': len(added), 'original_package_products': len(target['packageProductDependencies']),
            'framework_target_id': targets[0], 'only_excluded_source': 'ApplicationLayer/AppScene.swift',
            'reviewed_shared_dependency_objects': sorted(dependencies),
            'target_only_full_public_spi_graph': True, 'whole_project_inverse_exact': True,
            'framework_install_name_setting': '@rpath/$(EXECUTABLE_PATH)'}


def source_observation(root, environment=None):
    environment = os.environ if environment is None else environment
    profile = read_manifest()
    root = Path(root).resolve()
    head = git(root, 'rev-parse', 'HEAD')
    require(environment.get('GITHUB_REPOSITORY') == REPOSITORY
            and environment.get('GITHUB_EVENT_NAME') == 'push'
            and environment.get('GITHUB_REF') == 'refs/heads/' + BRANCH
            and environment.get('GITHUB_WORKFLOW_REF') == REPOSITORY + '/.github/workflows/pinkha-original-editor-framework.yml@refs/heads/' + BRANCH
            and environment.get('GITHUB_SHA') == head
            and re.fullmatch(r'[0-9a-f]{40}', head)
            and re.fullmatch(r'[1-9][0-9]*', environment.get('GITHUB_RUN_ID', ''))
            and re.fullmatch(r'[1-9][0-9]*', environment.get('GITHUB_RUN_ATTEMPT', '')),
            'Framework qualification requires the exact reviewed owned push/ref/run/head')
    require(git(root, 'branch', '--show-current') == BRANCH, 'Wrong actual framework checkout branch')
    require(not git(root, 'diff', '--name-only', 'HEAD'), 'Tracked framework source changed')
    require(not git(root, 'status', '--porcelain', '--untracked-files=all', '--',
                    'Anytype/Sources', 'Anytype/Resources', 'Modules', 'OriginalEditorFramework',
                    'Tools/OriginalEditor', 'Anytype.xcodeproj'), 'Unreviewed source/resource files in the build closure')
    trees = {}
    for path, expected in profile['original_trees'].items():
        actual = git(root, 'rev-parse', 'HEAD:' + path)
        require(actual == expected, 'Original source/resource tree differs: ' + path)
        trees[path] = actual
    pinned = root / profile['package_resolved_path']
    require(blob(pinned.read_bytes()) == profile['package_resolved_blob'], 'Reviewed exact 51-pin package closure differs')
    require(len(json.loads(pinned.read_text())['pins']) == 51, 'Reviewed package pin inventory differs')
    before = (HERE / 'original_project.pbxproj').read_bytes()
    project = verify_project((root / 'Anytype.xcodeproj/project.pbxproj').read_bytes(), before, profile)
    installer_path = 'Tools/PinkhaNativeDerived/install_verified_heart.py'
    installer = (root / installer_path).read_text()
    reviewed = "                             'codex/otzaria-original-editor-framework-v12-composed-20261122',\n                             '" + BRANCH + "'],"
    original = "                             'codex/otzaria-original-editor-framework-v12-composed-20261122'],"
    require(installer.count(reviewed) == 1 and
            blob(installer.replace(reviewed, original, 1).encode()) == profile['original_heart_installer_blob'],
            'Original verified Heart installer has a change beyond the exact new consumer branch')
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    selected = [p for p in tracked if p and (p.startswith('Tools/OriginalEditor/')
                or p.startswith('OriginalEditorFramework/') or p in profile['bound_original_helpers'] or p == installer_path
                or p in ['Anytype.xcodeproj/project.pbxproj',
                         'Anytype.xcodeproj/xcshareddata/xcschemes/AnytypeOriginalEditor.xcscheme',
                         '.github/workflows/pinkha-original-editor-framework.yml'])]
    records = {}
    for path in selected:
        actual = root / path
        require(actual.is_file() and not actual.is_symlink(), 'Missing or aliased source input: ' + path)
        raw = actual.read_bytes()
        require(blob(raw) == git(root, 'rev-parse', 'HEAD:' + path), 'Working bytes differ from Git: ' + path)
        records[path] = {'git_blob': blob(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    require(set(profile['bound_original_helpers']) <= set(records), 'Missing original execution helper')
    for path, expected in profile['bound_original_helpers'].items():
        require(records[path]['git_blob'] == expected, 'Original helper differs: ' + path)
    source_files = [p for p in tracked if p.startswith('Anytype/Sources/') and p.endswith('.swift')]
    require(len(source_files) == profile['original_swift_sources'], 'Original whole-source count differs')
    main_files = [p for p in source_files if re.search(r'(?m)^\s*@main\b', (root / p).read_text())]
    require(main_files == ['Anytype/Sources/ApplicationLayer/AppScene.swift'], 'Unexpected application entrypoints')
    facades = sorted(p for p in tracked if p.startswith('OriginalEditorFramework/') and p.endswith('.swift'))
    require(facades == profile['framework_facade_sources'], 'Reviewed Host/qualification facade membership differs')
    package_main_uses = []
    for path in source_files:
        for number, line in enumerate((root / path).read_text().splitlines(), 1):
            if 'Bundle.main' in line or 'Bundle(for:' in line or 'Anytype.' in line:
                package_main_uses.append({'path': path, 'line': number, 'source': line.strip()})
    return {'schema': 1, 'status': 'SOURCE_BOUND_FRAMEWORK_RUNTIME_NOT_RUN',
            'head_sha': head, 'run_id': environment['GITHUB_RUN_ID'], 'run_attempt': environment['GITHUB_RUN_ATTEMPT'],
            'original_trees': trees, 'project': project, 'source_inputs': records,
            'original_swift_sources': len(source_files), 'source_files': source_files,
            'framework_facade_sources': facades,
            'public_host_contract_sha256': profile['public_host_contract_sha256'],
            'resource_and_module_couplings': package_main_uses,
            'editable_mount_api': 'SOURCE_DECLARED_NATIVE_EDITOR_NOT_RUN', 'original_app_native_runtime': 'NOT_RUN'}
