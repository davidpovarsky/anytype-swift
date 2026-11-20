"""Source/export/receipt controls. Synthetic product fixtures are not Apple builds."""
import copy
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from framework_profile import HERE, TARGET, APP_TARGET, SOURCE_GROUP, read_manifest, verify_project
from framework_products import copy_product, export_products, consumer_project, inventory, verify_observation, verify_public_surface
from pbx_source import loads, object_text, render
from run_framework_acceptance import command

ROOT = HERE.parents[1]
BASELINE = (HERE / 'original_project.pbxproj').read_bytes()
CANDIDATE = (ROOT / 'Anytype.xcodeproj/project.pbxproj').read_bytes()
PROFILE = read_manifest()


class OriginalProjectPreservation(unittest.TestCase):
    def mutation(self, identifier, change):
        raw = CANDIDATE.decode()
        data = loads(raw)
        value = data['objects'][identifier]
        change(value)
        altered = raw.replace(object_text(raw, identifier), '\t\t' + identifier + ' = ' + render(value, 2) + ';\n', 1).encode()
        profile = copy.deepcopy(PROFILE)
        profile['candidate_project_sha256'] = hashlib.sha256(altered).hexdigest()
        return altered, profile

    def denied(self, identifier, change):
        raw, profile = self.mutation(identifier, change)
        with self.assertRaises(ValueError):
            verify_project(raw, BASELINE, profile)

    def test_genuine_additive_target_preserves_all_original_app_objects(self):
        proof = verify_project(CANDIDATE, BASELINE, PROFILE)
        self.assertEqual(proof['original_objects'], 298)
        self.assertEqual(proof['original_package_products'], 44)
        self.assertTrue(proof['whole_project_inverse_exact'])

    def test_original_project_does_not_already_claim_the_new_framework(self):
        old = loads(BASELINE.decode())['objects']
        self.assertFalse(any(value.get('name') == TARGET for value in old.values()))
        with self.assertRaises(ValueError):
            verify_project(BASELINE, BASELINE, PROFILE)

    def test_changed_original_app_target_is_rejected_beyond_candidate_hash(self):
        self.denied(APP_TARGET, lambda value: value.update(name='Replacement'))

    def test_changed_original_compilation_setting_is_rejected(self):
        data = loads(CANDIDATE.decode())['objects']
        config = data[data[APP_TARGET]['buildConfigurationList']]['buildConfigurations'][0]
        self.denied(config, lambda value: value['buildSettings'].update(SWIFT_VERSION='6.0'))

    def test_framework_cannot_depend_on_the_original_app_or_test_binary(self):
        self.denied(PROFILE['framework_target_id'], lambda value: value.update(dependencies=[APP_TARGET]))

    def test_framework_cannot_be_an_application_product(self):
        self.denied(PROFILE['framework_target_id'], lambda value: value.update(productType='com.apple.product-type.application'))

    def test_any_additional_original_source_exclusion_is_rejected(self):
        data = loads(CANDIDATE.decode())['objects']
        exception = data[SOURCE_GROUP]['exceptions'][0]
        self.denied(exception, lambda value: value['membershipExceptions'].append('PresentationLayer/TextEditor/EditorPage/EditorPageController.swift'))

    def test_entrypoint_exception_cannot_target_the_original_app(self):
        data = loads(CANDIDATE.decode())['objects']
        self.denied(data[SOURCE_GROUP]['exceptions'][0], lambda value: value.update(target=APP_TARGET))

    def test_new_target_cannot_substitute_the_original_package_product(self):
        data = loads(CANDIDATE.decode())['objects']
        package = data[PROFILE['framework_target_id']]['packageProductDependencies'][0]
        self.denied(package, lambda value: value.update(productName='FakeAssets'))

    def test_new_target_cannot_replace_real_source_groups(self):
        self.denied(PROFILE['framework_target_id'], lambda value: value.update(fileSystemSynchronizedGroups=[]))

    def test_original_baseline_snapshot_is_bound_to_its_git_blob(self):
        with self.assertRaises(ValueError):
            verify_project(CANDIDATE, BASELINE + b'\n', PROFILE)

    def test_framework_has_no_original_app_boot_scripts_or_extensions(self):
        data = loads(CANDIDATE.decode())['objects']
        target = data[PROFILE['framework_target_id']]
        self.assertEqual([data[key]['isa'] for key in target['buildPhases']],
                         ['PBXSourcesBuildPhase', 'PBXFrameworksBuildPhase', 'PBXResourcesBuildPhase'])
        self.assertEqual(target['dependencies'], [])

    def test_original_heart_installer_changes_only_one_new_branch_choice(self):
        raw = (ROOT / 'Tools/PinkhaNativeDerived/install_verified_heart.py').read_bytes()
        suffix = b",\n                             'codex/otzaria-original-editor-framework-v7-reviewed-20261120'"
        self.assertEqual(raw.count(suffix), 1)
        old = raw.replace(suffix, b'', 1)
        actual = hashlib.sha1(b'blob ' + str(len(old)).encode() + b'\0' + old).hexdigest()
        self.assertEqual(actual, PROFILE['original_heart_installer_blob'])


class RealFilesystemExportControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.producer = self.root / 'producer'
        self.products = self.producer / 'Build/Products/Debug-Anytype-iphonesimulator'
        self.products.mkdir(parents=True)
        self.exported = self.root / 'exported'
        framework = self.products / (TARGET + '.framework')
        framework.mkdir()
        (framework / TARGET).write_bytes(b'EXPLICIT_SYNTHETIC_EXPORT_FIXTURE_NOT_A_MACHO_BINARY')
        (framework / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': TARGET}))
        for bundle, path, data in [('Assets_Assets.bundle', 'Assets.car', b'synthetic asset fixture'),
                                  ('DesignKit_DesignKit.bundle', 'IBMPlexMono-Regular.ttf', b'synthetic font fixture'),
                                  ('Loc_Loc.bundle', 'he.lproj/UI.strings', b'synthetic strings fixture')]:
            destination = self.products / bundle / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)

    def export(self):
        return export_products(self.products, self.exported, self.producer)

    def test_export_preserves_every_real_fixture_byte_without_runtime_credit(self):
        value = self.export()
        self.assertEqual(value['files'], inventory(self.exported))
        self.assertNotIn('PASS', value)
        self.assertIn(TARGET + '.framework', value['frameworks'])

    def test_app_binary_is_never_accepted_as_framework_input(self):
        (self.products / 'Anytype.app').mkdir()
        with self.assertRaises(ValueError): self.export()

    def test_test_binary_is_never_accepted_as_framework_input(self):
        (self.products / 'AnytypeTests.xctest').mkdir()
        with self.assertRaises(ValueError): self.export()

    def test_duplicate_framework_product_name_fails_closed(self):
        path = self.products / 'PackageFrameworks' / (TARGET + '.framework')
        path.mkdir(parents=True)
        with self.assertRaises(ValueError): self.export()

    def test_external_resource_symlink_is_rejected(self):
        external = self.root / 'outside'
        external.write_bytes(b'not owned by producer')
        (self.products / 'Loc_Loc.bundle/escape').symlink_to(external)
        with self.assertRaises(ValueError): self.export()

    def test_internal_resource_alias_is_materialized_and_does_not_escape(self):
        (self.products / 'Loc_Loc.bundle/alias').symlink_to('he.lproj/UI.strings')
        self.export()
        self.assertFalse((self.exported / 'Bundles/Loc_Loc.bundle/alias').is_symlink())
        self.assertEqual((self.exported / 'Bundles/Loc_Loc.bundle/alias').read_bytes(), b'synthetic strings fixture')

    def test_missing_original_hebrew_bundle_is_rejected(self):
        shutil.rmtree(self.products / 'Loc_Loc.bundle')
        with self.assertRaises(ValueError): self.export()

    def test_missing_original_font_bundle_is_rejected(self):
        shutil.rmtree(self.products / 'DesignKit_DesignKit.bundle')
        with self.assertRaises(ValueError): self.export()

    def test_missing_original_asset_catalog_is_rejected(self):
        shutil.rmtree(self.products / 'Assets_Assets.bundle')
        with self.assertRaises(ValueError): self.export()

    def test_resources_inside_genuine_framework_are_preserved(self):
        for bundle in self.products.glob('*.bundle'):
            bundle.rename(self.products / (TARGET + '.framework') / bundle.name)
        self.export()
        self.assertTrue((self.exported / 'Frameworks' / (TARGET + '.framework') / 'Loc_Loc.bundle/he.lproj/UI.strings').is_file())

    def test_export_refuses_to_overwrite_prior_product(self):
        self.exported.mkdir()
        with self.assertRaises(ValueError): self.export()

    def test_external_consumer_compiles_only_its_own_importer(self):
        self.export()
        source = ROOT / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift'
        project = consumer_project(self.root / 'consumer', self.exported, source, [TARGET + '.framework'])
        data = loads((project / 'project.pbxproj').read_text())['objects']
        swift = [value for value in data.values() if value.get('lastKnownFileType') == 'sourcecode.swift']
        self.assertEqual([value['path'] for value in swift], ['ConsumerApp.swift'])
        self.assertFalse(any(value['isa'] in {'XCSwiftPackageProductDependency', 'XCRemoteSwiftPackageReference'} for value in data.values()))
        self.assertIn('import AnytypeOriginalEditor', (project.parent / 'ConsumerApp.swift').read_text())
        self.assertEqual(plistlib.loads((project.parent / 'Info.plist').read_bytes())['CFBundleLocalizations'], ['en', 'he'])


class RuntimeReceiptBoundary(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.app = Path(self.temporary.name) / 'Consumer.app'
        self.app.mkdir()
        self.nonce = 'AB285074-5AF2-46AD-9AB2-24E4529B26D8'
        self.oracle = {'translations': {'en': 'Cancel', 'he': 'ביטול'}, 'font_name': 'IBMPlexMono',
                       'font_sha256': 'a' * 64, 'font_bytes': 110308,
                       'colors': {'light': [37/255, 37/255, 37/255, 1.0], 'dark': [243/255, 243/255, 243/255, 1.0]}}
        self.value = {'schema': 1, 'status': 'ACTUAL_EXTERNAL_CONSUMER_RESOURCE_OBSERVATION', 'nonce': self.nonce,
                      'mainBundleIdentifier': 'org.otzaria.acceptance.original-editor', 'mainBundleURL': str(self.app),
                      'preferredLanguages': ['he-IL'], 'inspection': {
                          'moduleBundleIdentifier': 'org.otzaria.anytype.original-editor',
                          'moduleBundleURL': str(self.app / 'Frameworks/AnytypeOriginalEditor.framework'),
                          'originalTypeNames': [TARGET + '.' + name for name in ['EditorPageController',
                              'EditorPageModuleAssembly', 'PreparedEditorPageSession', 'EditorDocumentWriteOwner']],
                          'imagePNGBytes': 2048, 'imagePNGSHA256': 'b' * 64, 'imageWidth': 24.0, 'imageHeight': 24.0,
                          'localizedCancel': 'ביטול', 'fontName': 'IBMPlexMono',
                          'fontResourceURL': str(self.app / 'DesignKit_DesignKit.bundle/IBMPlexMono-Regular.ttf'),
                          'fontBytes': 110308, 'fontSHA256': 'a' * 64,
                          'lightTextRGBA': self.oracle['colors']['light'], 'darkTextRGBA': self.oracle['colors']['dark']}}

    def verify(self):
        return verify_observation(self.value, self.nonce, 'he', self.app, self.oracle)

    def denied(self):
        with self.assertRaises(ValueError): self.verify()

    def test_well_formed_synthetic_boundary_is_explicitly_zero_editor_ui(self):
        result = self.verify()
        self.assertEqual(result['native_editor_ui_tests'], 0)
        self.assertEqual(result['editable_mount'], 'NOT_EXPOSED')

    def test_stale_nonce_cannot_borrow_a_previous_language_result(self):
        self.value['nonce'] = 'other'; self.denied()

    def test_framework_loaded_from_producer_is_not_external_qualification(self):
        self.value['inspection']['moduleBundleURL'] = '/producer/AnytypeOriginalEditor.framework'; self.denied()

    def test_hebrew_generated_accessor_cannot_pass_with_english_fallback(self):
        self.value['inspection']['localizedCancel'] = 'Cancel'; self.denied()

    def test_expected_language_must_be_actual_process_language(self):
        self.value['preferredLanguages'] = ['en-US']; self.denied()

    def test_producer_font_fallback_is_rejected_even_with_matching_bytes(self):
        self.value['inspection']['fontResourceURL'] = '/producer/IBMPlexMono-Regular.ttf'; self.denied()

    def test_main_bundle_prefix_is_not_path_ownership(self):
        self.value['inspection']['fontResourceURL'] = str(self.app) + '-other/IBMPlexMono-Regular.ttf'; self.denied()

    def test_changed_font_bytes_cannot_pass(self):
        self.value['inspection']['fontSHA256'] = 'c' * 64; self.denied()

    def test_wrong_original_type_or_module_cannot_pass(self):
        self.value['inspection']['originalTypeNames'][0] = 'Fake.EditorPageController'; self.denied()

    def test_missing_actual_image_cannot_pass(self):
        self.value['inspection']['imagePNGBytes'] = 0; self.denied()

    def test_nonfinite_image_geometry_is_rejected(self):
        for value in [float('nan'), float('inf'), True, 0.0, 8193.0]:
            with self.subTest(value=value):
                self.value['inspection']['imageWidth'] = value; self.denied()

    def test_swapped_adaptive_color_appearances_cannot_pass(self):
        self.value['inspection']['darkTextRGBA'] = self.oracle['colors']['light']; self.denied()

    def test_unknown_error_or_partial_runtime_json_cannot_pass(self):
        self.value = {'status': 'RESOURCE_INSPECTION_FAILED', 'nonce': self.nonce}; self.denied()


class BoundedCommandEvidence(unittest.TestCase):
    def test_real_timeout_preserves_partial_stdout_and_nonpassing_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(subprocess.TimeoutExpired):
                command([sys.executable, '-c', "import time; print('observed-before-timeout', flush=True); time.sleep(30)"],
                        root, root, 'timeout', 0.25)
            self.assertIn('observed-before-timeout', (root / 'timeout.stdout.log').read_text())
            result = json.loads((root / 'timeout.command.json').read_text())
            self.assertTrue(result['timed_out'])
            self.assertNotEqual(result['returncode'], 0)

    def test_actual_nonzero_exit_is_preserved_and_cannot_be_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                command([sys.executable, '-c', 'raise SystemExit(19)'], root, root, 'failed', 5)
            self.assertEqual(json.loads((root / 'failed.command.json').read_text())['returncode'], 19)


class ActualTargetPublicSurfaceControls(unittest.TestCase):
    def graph(self):
        return {'module': {'name': TARGET}, 'symbols': [{
            'accessLevel': 'public', 'pathComponents': ['AnytypeOriginalEditorModule', 'inspectResources()'],
            'identifier': {'precise': 's:21AnytypeOriginalEditorInspection'},
            'location': {'uri': (ROOT / 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift').as_uri()}}]}

    def test_imported_dependency_symbols_do_not_become_our_public_editor_api(self):
        graph = self.graph()
        graph['symbols'].append({'accessLevel': 'public', 'pathComponents': ['EditorPageImportedDependency'],
            'identifier': {'precise': 's:11OtherModuleImported'},
            'location': {'uri': (ROOT / 'Modules/Dependency/Editor.swift').as_uri()}})
        result = verify_public_surface([graph], ROOT)
        self.assertEqual(len(result['own_public_symbols']), 1)
        self.assertEqual(result['imported_dependency_symbols_not_rejected'], 1)

    def test_original_public_editor_constructor_is_rejected(self):
        graph = self.graph()
        graph['symbols'].append({'accessLevel': 'public', 'pathComponents': ['EditorPageController', 'init()'],
            'identifier': {'precise': 's:21AnytypeOriginalEditorController'},
            'location': {'uri': (ROOT / 'Anytype/Sources/PresentationLayer/TextEditor/EditorPage/EditorPageController.swift').as_uri()}})
        with self.assertRaises(ValueError): verify_public_surface([graph], ROOT)

    def test_graph_for_another_module_cannot_qualify_the_inspection_facade(self):
        graph = self.graph(); graph['module']['name'] = 'OtherModule'
        with self.assertRaises(ValueError): verify_public_surface([graph], ROOT)


class ObservedOriginalBuildBudget(unittest.TestCase):
    def test_new_route_budget_contains_actual_original_build_and_consumer(self):
        import ast
        import gzip
        import re
        from datetime import datetime
        receipt = ROOT / 'docs/pinkha/torah-integration/evidence/original-editor-framework-20261120/raw/budget-original-command-44750790626.json.gz'
        raw = gzip.decompress(receipt.read_bytes())
        self.assertEqual(hashlib.sha256(raw).hexdigest(),
                         '014603e7857815a762a7d7f93168e88ed25768bf47a932c7efbbcc322029ce3f')
        observed = json.loads(raw)
        self.assertEqual(observed['exit_code'], 0)
        self.assertEqual(observed['command'][:2], ['xcodebuild', 'build-for-testing'])
        elapsed = (datetime.fromisoformat(observed['finished_at'])
                   - datetime.fromisoformat(observed['started_at'])).total_seconds()
        self.assertGreater(elapsed, 3600)  # The sealed v1 budget is discriminated.
        driver = ast.parse((HERE / 'run_framework_acceptance.py').read_text())
        commands = {node.args[3].value: node.args[4].value for node in ast.walk(driver)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == 'command' and len(node.args) == 5
                    and isinstance(node.args[3], ast.Constant) and isinstance(node.args[4], ast.Constant)}
        self.assertGreaterEqual(commands['framework-build'], elapsed)
        self.assertEqual(commands['framework-build'], 6000)
        self.assertEqual(commands['external-consumer-build'], 600)
        workflow = (ROOT / '.github/workflows/pinkha-original-editor-framework.yml').read_text()
        self.assertEqual(re.findall(r'^\s*timeout-minutes: (\d+)\s*$', workflow, re.M), ['140', '120'])
        self.assertGreaterEqual(120 * 60, commands['framework-build'] + commands['external-consumer-build'] + 600)
        self.assertGreaterEqual(140 * 60, 120 * 60 + 20 * 60)


if __name__ == '__main__':
    unittest.main(verbosity=2)
