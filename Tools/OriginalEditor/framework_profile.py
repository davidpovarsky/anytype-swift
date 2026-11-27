"""Fail-closed source boundary for the genuine original-editor framework."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from pbx_source import loads, object_text, require
from generated_import_source import verify_generated_source
from local_execution import current_identity

BRANCH = 'codex/otzaria-original-editor-complete-framework-20261123'
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
            and value.get('package_pin_count') == 58, 'Unreviewed framework profile')
    require(set(value.get('reviewed_shared_dependency_objects', {})) == {
        '5333421A262E249100238121', '2A685D582B7B854200456E08', 'FA1000002F000001006805CC',
        '2E63D9B52D56520C008A733A', '538ABD4C284F9F88000D3CCC'},
        'Unreviewed shared runtime dependency object set')
    require(len(value.get('framework_facade_sources', [])) == 23
            and len(set(value['framework_facade_sources'])) == 23,
            'Incomplete reviewed Host facade source closure')
    require(sha256(HERE / 'public_host_contract.json') == value.get('public_host_contract_sha256'),
            'Reviewed public Host and qualification SPI contract differs')
    route = value['shared_runtime_route']
    require(sha256(HERE / 'SharedRuntime/Package.swift') == route['package_manifest_sha256']
            and sha256(HERE / 'SharedRuntime/dependencies.json') == route['dependency_contract_sha256'],
            'Shared runtime package or exact Host dependency contract differs')
    continuation = value['complete_source_continuation']
    require(continuation.get('path') == 'Tools/OriginalEditor/complete_source_continuation.json'
            and sha256(HERE / 'complete_source_continuation.json') == continuation.get('sha256'),
            'Complete source continuation inventory differs')
    verify_complete_source(value, json.loads((HERE / 'complete_source_continuation.json').read_text()))
    return value


def verify_complete_source(profile, continuation):
    require(continuation.get('schema') == 1
            and continuation.get('reviewed_source_sha') == 'cbe25cb467f989a1d40ed564d833616346a7d9b6'
            and continuation.get('prior_producer_source') == 'de63125b97cd5b91a1fa4f4b71d03738076e735f'
            and profile['complete_source_continuation']['reviewed_source_sha'] == continuation['reviewed_source_sha'],
            'Unreviewed complete original account/Import/local-annotation source continuation')
    original, reviewed = continuation['original_product_trees'], continuation['reviewed_product_trees']
    require(set(original) == set(reviewed) == {'Anytype/Sources', 'Anytype/Resources', 'Modules', 'OriginalEditorFramework'}
            and original['Anytype/Resources'] == reviewed['Anytype/Resources'] == '0827010674c089cfe9846e592e1d801e9d3f7a9b'
            and profile['original_trees'] == {key: reviewed[key] for key in ['Anytype/Sources', 'Anytype/Resources', 'Modules']},
            'Reviewed source/resource continuation tree differs')
    sources, facades = continuation['source_files'], continuation['framework_facade_sources']
    require(isinstance(sources, list) and sources == sorted(set(sources))
            and len(sources) == profile['original_swift_sources'] == 2256
            and all(p.startswith('Anytype/Sources/') and p.endswith('.swift') for p in sources),
            'Complete original Swift source inventory differs')
    require(profile['framework_facade_sources'] == sorted(facades + ['OriginalEditorFramework/AnytypeOriginalAnnotationRevision.swift',
                'OriginalEditorFramework/AnytypeOriginalAnnotationLifecycle.swift',
                'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotationBatch.swift'])
            and facades == sorted(set(facades))
            and len(facades) == 20
            and {'OriginalEditorFramework/AnytypeOriginalAnnotationImport.swift',
                 'OriginalEditorFramework/AnytypeOriginalEditorAccountSession.swift',
                 'OriginalEditorFramework/OriginalEditorAccountSessionView.swift',
                 'OriginalEditorFramework/AnytypeOriginalEditorLocalAnnotation.swift',
                 'OriginalEditorFramework/OriginalEditorLocalAnnotationJournal.swift',
                 'OriginalEditorFramework/OriginalEditorLocalAnnotationMaterialization.swift',
                 'OriginalEditorFramework/OriginalEditorLocalAnnotationNativeBody.swift',
                 'OriginalEditorFramework/OriginalEditorLocalAnnotationRuntime.swift'} <= set(facades),
            'Complete account-session/Import facade inventory differs')
    return {'reviewed_source_sha': continuation['reviewed_source_sha'],
            'prior_producer_source': continuation['prior_producer_source'],
            'reviewed_product_trees': reviewed, 'source_files': sources,
            'framework_facade_sources': facades, 'native_qualified': False}



ASSISTANT_CAPABILITY_ROUTE = {
    "package_id": "656317E261FEB6E8F0B504E0",
    "product_id": "66C53E67789D89F6AEA6AD38",
    "build_file_id": "1FB69AB809D9F78201546380",
    "framework_phase_id": "F4E9B92EDBC5AFFFB8F097CC",
    "target_id": "83B785D0C457FE3CCBAB196E",
    "package_path": "Dependencies/Hanlin",
    "product_name": "HanlinAssistantCapabilities",
}


def verify_assistant_capability_route(candidate, added, profile):
    route = profile.get("assistant_capability_route")
    if route is None:
        return None
    require(route == ASSISTANT_CAPABILITY_ROUTE,
            "Unreviewed original Hanlin capability composition")
    objects = candidate["objects"]
    package, product, build = route["package_id"], route["product_id"], route["build_file_id"]
    expected_product = {"isa": "XCSwiftPackageProductDependency", "package": package,
                        "productName": "HanlinAssistantCapabilities"}
    require({package, product, build} <= set(added)
            and objects[package] == {"isa": "XCLocalSwiftPackageReference",
                                     "relativePath": "Dependencies/Hanlin"}
            and objects[product] == expected_product
            and objects[build] == {"isa": "PBXBuildFile", "productRef": product},
            "Original Hanlin package, product or build binding differs")
    target = objects[route["target_id"]]
    phase = objects[route["framework_phase_id"]]
    require(target["name"] == TARGET
            and target["packageProductDependencies"].count(product) == 1
            and target["buildPhases"].count(route["framework_phase_id"]) == 1
            and phase["isa"] == "PBXFrameworksBuildPhase"
            and phase["files"].count(build) == 1
            and objects[candidate["rootObject"]]["packageReferences"].count(package) == 1,
            "Original Hanlin capability is not linked exactly once by its original framework owner")
    owners = [key for key, obj in objects.items()
              if obj.get("isa") == "PBXNativeTarget"
              and product in obj.get("packageProductDependencies", [])]
    phases = [key for key, obj in objects.items()
              if obj.get("isa") == "PBXFrameworksBuildPhase" and build in obj.get("files", [])]
    require(owners == [route["target_id"]] and phases == [route["framework_phase_id"]],
            "Original Hanlin capability acquired another implementation owner")
    return expected_product


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
    route = profile['shared_runtime_route']
    require(route['package_id'] in added
            and new[route['package_id']] == route['package']
            and route['package'] == {'isa': 'XCLocalSwiftPackageReference',
                                     'relativePath': 'Tools/OriginalEditor/SharedRuntime'}
            and new[route['target_product_id']] == route['runtime_product']
            and route['runtime_product'] == {'isa': 'XCSwiftPackageProductDependency',
                                             'package': route['package_id'],
                                             'productName': 'OriginalEditorSharedFirebase'}
            and route['original_product'] == {'isa': 'XCSwiftPackageProductDependency',
                                              'package': '2E63D9B52D56520C008A733A',
                                              'productName': 'FirebaseMessaging'},
            'Shared Firebase product route differs')
    source_phases = [new[key] for key in target['buildPhases'] if new[key]['isa'] == 'PBXSourcesBuildPhase']
    groups = [value for value in new.values()
              if value.get('isa') == 'PBXGroup' and value.get('path') == 'OriginalEditorFramework']
    require(len(source_phases) == len(groups) == 1, 'Ambiguous complete facade source group or phase')
    source_ids, child_ids = source_phases[0]['files'], groups[0]['children']
    original_source_phases = [old[key] for key in original_target['buildPhases']
                              if old[key]['isa'] == 'PBXSourcesBuildPhase']
    require(len(original_source_phases) == 1, 'Ambiguous original explicit compiler source phase')
    original_source_refs = [old[key]['fileRef'] for key in original_source_phases[0]['files']]
    require(len(child_ids) == len(set(child_ids)) == 23
            and len(original_source_refs) == len(set(original_source_refs))
            and not set(original_source_refs) & set(child_ids)
            and len(source_ids) == len(set(source_ids)) == len(child_ids) + len(original_source_refs),
            'Incomplete or repeated original/facade compiler membership')
    references = [new[key] for key in source_ids]
    require(all(item.get('isa') == 'PBXBuildFile' and set(item) == {'isa', 'fileRef'} for item in references)
            and len({item['fileRef'] for item in references}) == len(references)
            and {item['fileRef'] for item in references} == set(child_ids) | set(original_source_refs),
            'Compiler inputs differ from complete facades plus original explicit sources')
    require(all(new[key].get('isa') == 'PBXFileReference' and new[key].get('sourceTree') == '<group>'
                and new[key].get('lastKnownFileType') == 'sourcecode.swift' for key in child_ids)
            and sorted('OriginalEditorFramework/' + new[key]['path'] for key in child_ids)
                == profile['framework_facade_sources'],
            'A complete reviewed facade is absent from the actual framework compiler phase')
    products = [new[key] for key in target['packageProductDependencies']]
    require(products.count(route['runtime_product']) == 1,
            'Shared runtime is missing or repeated')
    assistant = verify_assistant_capability_route(candidate, added, profile)
    if assistant is not None:
        require(products.count(assistant) == 1, 'Original Hanlin capability product is missing or repeated')
    original_products = [route['original_product'] if p == route['runtime_product'] else p
                         for p in products if p != assistant]
    require(original_products == [old[key] for key in original_target['packageProductDependencies']],
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
    # Restore only the four additive structural objects and the five exact
    # reviewed shared package requirements. All original products stay intact.
    inverse = raw.decode()
    for key in sorted(added):
        inverse = inverse.replace(object_text(inverse, key), '', 1)
    for key in allowed:
        inverse = inverse.replace(object_text(inverse, key), object_text(baseline.decode(), key), 1)
    require(inverse.encode() == baseline, 'Complete original project inverse differs')
    return {'original_app_target_unchanged': True, 'original_objects': len(old),
            'new_objects': len(added), 'complete_facade_compiler_inputs': len(child_ids),
            'original_explicit_compiler_inputs': len(original_source_refs),
            'original_package_products': len(target['packageProductDependencies']),
            'shared_runtime_route': route, 'assistant_capability_route': profile.get('assistant_capability_route'),
            'framework_target_id': targets[0], 'only_excluded_source': 'ApplicationLayer/AppScene.swift',
            'reviewed_shared_dependency_objects': sorted(dependencies),
            'target_only_full_public_spi_graph': True, 'whole_project_inverse_exact': True,
            'framework_install_name_setting': '@rpath/$(EXECUTABLE_PATH)'}


def source_observation(root, environment=None):
    environment = os.environ if environment is None else environment
    profile = read_manifest()
    root = Path(root).resolve()
    head = git(root, 'rev-parse', 'HEAD')
    identity = current_identity(environment)
    if identity['producer_kind'] == 'local-mac':
        require(identity['source_sha'] == head
                and identity['local_execution']['root'] == str(root),
                'Local framework producer does not own this exact checkout')
    else:
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
    generated_source = verify_generated_source(root, profile)
    trees = {}
    for path in profile['original_trees']:
        expected = generated_source['composed_product_trees'][path]
        actual = git(root, 'rev-parse', 'HEAD:' + path)
        require(actual == expected, 'Original source/resource tree differs: ' + path)
        trees[path] = actual
    pinned = root / profile['package_resolved_path']
    require(blob(pinned.read_bytes()) == profile['package_resolved_blob'], 'Reviewed exact 58-pin package closure differs')
    require(len(json.loads(pinned.read_text())['pins']) == 58, 'Reviewed package pin inventory differs')
    before = (HERE / 'original_project.pbxproj').read_bytes()
    project = verify_project((root / 'Anytype.xcodeproj/project.pbxproj').read_bytes(), before, profile)
    installer_path = 'Tools/PinkhaNativeDerived/install_verified_heart.py'
    installer = (root / installer_path).read_text()
    reviewed = "                             'codex/otzaria-original-editor-framework-v13-body-reviewed-20261122',\n                             '" + BRANCH + "'],"
    original = "                             'codex/otzaria-original-editor-framework-v13-body-reviewed-20261122'],"
    require(installer.count(reviewed) == 1 and
            blob(installer.replace(reviewed, original, 1).encode()) == profile['original_heart_installer_blob'],
            'Original verified Heart installer has a change beyond the exact new consumer branch')
    tracked = subprocess.check_output(['git', '-C', str(root), 'ls-files', '-z']).decode().split('\0')
    selected = [p for p in tracked if p and (p.startswith('Tools/OriginalEditor/')
                or p.startswith('OriginalEditorFramework/') or p in profile['bound_original_helpers'] or p == installer_path
                or p == 'Modules/Services/Sources/Services/Auth/AuthMiddleService+OriginalLocalAnnotation.swift'
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
    complete = json.loads((HERE / 'complete_source_continuation.json').read_text())
    continuation = verify_complete_source(profile, complete)
    lifecycle = generated_source['annotation_exchange']['miniapps'].get('lifecycle_batch')
    require(lifecycle is not None, 'The original lifecycle/batch source continuation was not admitted')
    expected_sources = sorted(continuation['source_files'] + [
        'Anytype/Sources/Pinkha/Torah/Annotations/OriginalAnnotationSearchVisibility.swift'])
    require(source_files == expected_sources, 'Complete reviewed original source membership differs')
    require(git(root, 'rev-parse', 'HEAD:OriginalEditorFramework')
            == generated_source['composed_product_trees']['OriginalEditorFramework'],
            'Complete reviewed facade source bytes differ')
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
            'head_sha': head, 'run_id': identity['run_id'], 'run_attempt': identity['run_attempt'],
            'execution_identity': identity,
            'reviewed_complete_source_sha': continuation['reviewed_source_sha'],
            'original_trees': trees, 'generated_import_source': generated_source,
            'project': project, 'source_inputs': records,
            'original_swift_sources': len(source_files), 'source_files': source_files,
            'framework_facade_sources': facades,
            'public_host_contract_sha256': profile['public_host_contract_sha256'],
            'resource_and_module_couplings': package_main_uses,
            'editable_mount_api': 'SOURCE_DECLARED_NATIVE_EDITOR_NOT_RUN', 'original_app_native_runtime': 'NOT_RUN'}
