"""Run the whole original driver with explicit Apple-tool/source boundary doubles.

The real exporter, notice copy, consumer project, inventories, orchestration,
final failure receipt and cleanup execute. No command invokes Apple tools; all
synthetic runs stop before installation and earn zero build/runtime credit.
"""
from contextlib import ExitStack, redirect_stdout
import io
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

import run_framework_acceptance as driver
from framework_profile import HERE, TARGET, read_manifest, sha256


class StopBeforeRuntime(RuntimeError):
    pass


class OriginalDriverFlowControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence = self.root / 'build/evidence'
        self.work = self.root / 'build/work'
        self.events = []
        self.failure = None
        self.corrupt_embedded = False
        self.notice_count = 1
        self.udid = '12345678-1234-1234-1234-1234567890AB'
        self.before = {'head_sha': 'a' * 40, 'run_id': '900001', 'run_attempt': '1',
                       'original_trees': {'EXPLICIT_SOURCE_BOUNDARY_DOUBLE': 'b' * 40}}
        self.environment = {'GITHUB_SHA': self.before['head_sha'], 'GITHUB_RUN_ID': '900001',
                            'GITHUB_RUN_ATTEMPT': '1'}
        self.preflight = {'status': 'PREFLIGHT_PASS_UI_NOT_RUN', 'source_sha': self.before['head_sha'],
                          'run_id': '900001', 'run_attempt': '1', 'selected': {'ipad': {
                              'udid': self.udid, 'name': 'Pinkha-UI27-900001-ipad'}}}
        driver.write(self.evidence / 'preflight/preflight.json', self.preflight)
        driver.write(self.evidence / 'heart/heart-installation.json', {
            'status': 'PASS', 'app_source_sha': self.before['head_sha'],
            'source_run_id': '44203168617', 'marker': 'EXPLICIT_HEART_BOUNDARY_DOUBLE'})
        member = self.root / 'Dependencies/Middleware/Lib.xcframework/synthetic-marker'
        member.parent.mkdir(parents=True)
        member.write_bytes(b'EXPLICIT_SYNTHETIC_HEART_NOT_A_BINARY')
        driver.write(self.root / 'Dependencies/Middleware/PinkhaNativeHeartBuild.json', {
            'status': 'PASS', 'marker': 'EXPLICIT_HEART_BOUNDARY_DOUBLE',
            'artifacts': [{'path': member.name, 'sha256': sha256(member)}]})
        (self.root / 'LICENSE.md').write_bytes(b'EXPLICIT_ORIGINAL_LICENSE_FIXTURE')
        pinned = self.root / read_manifest()['package_resolved_path']
        pinned.parent.mkdir(parents=True)
        pinned.write_bytes(b'{"pins": []}\n')
        consumer_source = self.root / 'Tools/OriginalEditor/Consumer/ConsumerApp.swift'
        consumer_source.parent.mkdir(parents=True)
        shutil.copyfile(HERE / 'Consumer/ConsumerApp.swift', consumer_source)
        self.addCleanup(self.retain_trace)

    def retain_trace(self):
        directory = os.environ.get('FRAMEWORK_FLOW_EVIDENCE')
        if directory:
            driver.write(Path(directory) / (self._testMethodName + '.json'), {
                'scope': 'Whole Python driver, explicit Apple/source doubles; no Apple execution',
                'events': self.events, 'receipt': getattr(self, 'receipt', None),
                'apple_builds_executed': 0, 'native_tests_executed': 0})

    def produce_framework_fixture(self):
        derived = self.work / 'producer-derived'
        products = derived / 'Build/Products/Debug-Anytype-iphonesimulator'
        framework = products / (TARGET + '.framework')
        framework.mkdir(parents=True)
        (framework / TARGET).write_bytes(b'EXPLICIT_SYNTHETIC_FRAMEWORK_NOT_A_MACHO')
        (framework / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': TARGET}))
        for bundle, name in [('Assets_Assets.bundle', 'Assets.car'),
                             ('DesignKit_DesignKit.bundle', 'IBMPlexMono-Regular.ttf'),
                             ('Loc_Loc.bundle', 'he.lproj/UI.strings')]:
            path = products / bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('EXPLICIT_SYNTHETIC_RESOURCE_' + name).encode())
        checkouts = derived / 'SourcePackages/checkouts'
        checkouts.mkdir(parents=True)
        for number in range(self.notice_count):
            notice = checkouts / ('dependency-' + str(number)) / 'LICENSE.md'
            notice.parent.mkdir()
            notice.write_bytes(('EXACT_SYNTHETIC_NOTICE_' + str(number)).encode())

    def command(self, arguments, cwd, evidence, name, timeout):
        self.events.append({'name': name, 'command': [str(x) for x in arguments],
                            'timeout_seconds': timeout})
        if name == self.failure:
            if name == 'boot-status':
                raise subprocess.TimeoutExpired(arguments, timeout)
            raise ValueError('EXPLICIT_TOOL_FAILURE:' + name)
        if name == 'actual-simulator-sdk':
            return '27.2'
        if name == 'actual-swift':
            return 'EXPLICIT_SWIFT_TOOL_DOUBLE_NOT_A_COMPILER'
        if name == 'framework-build':
            self.produce_framework_fixture()
        elif name.startswith('framework-header-'):
            return 'DYLIB'
        elif name == 'framework-architecture':
            return 'arm64'
        elif name == 'framework-platform':
            return 'platform IOSSIMULATOR'
        elif name == 'original-framework-symbols':
            return 'AnytypeOriginalEditor'
        elif name == 'actual-simulator-sdk-path':
            return '/EXPLICIT_SYNTHETIC_SDK_NOT_USED'
        elif name == 'actual-target-public-symbol-graph':
            directory = Path(arguments[arguments.index('-output-dir') + 1])
            driver.write(directory / (TARGET + '.symbols.json'), {'module': {'name': TARGET},
                'symbols': [{'accessLevel': 'public',
                    'pathComponents': ['AnytypeOriginalEditorModule', 'inspectResources()'],
                    'identifier': {'precise': 's:21AnytypeOriginalEditorInspection'},
                    'location': {'uri': (self.root / 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift').as_uri()}}]})
        elif name == 'external-consumer-build':
            app = self.work / 'consumer-derived/Build/Products/Debug-iphonesimulator/OriginalEditorConsumer.app'
            shutil.copytree(self.work / 'distribution/Frameworks', app / 'Frameworks')
            if self.corrupt_embedded:
                (app / 'Frameworks' / (TARGET + '.framework') / TARGET).write_bytes(b'UNRELATED_BINARY')
        elif name == 'install-external-consumer':
            raise StopBeforeRuntime('Synthetic control stops before real installation')
        return ''

    def cleanup_command(self, arguments, **kwargs):
        if arguments not in [['xcrun', 'simctl', op, self.udid] for op in ['shutdown', 'delete']]:
            raise AssertionError('Unexpected process escaped command boundary: ' + repr(arguments))
        self.events.append({'name': 'cleanup-' + arguments[2], 'command': arguments,
                            'timeout_seconds': kwargs['timeout']})
        return subprocess.CompletedProcess(arguments, 0, b'EXPLICIT_CLEANUP_DOUBLE', b'')

    def run_driver(self, source_only=False):
        sdk = ModuleType('prepare_sdk')
        sdk.verify = lambda root: {'EXPLICIT_HANLIN_SOURCE_BOUNDARY_DOUBLE': True}
        argv = ['driver', '--root', str(self.root), '--evidence', str(self.evidence), '--work', str(self.work)]
        if source_only:
            argv.append('--source-only')
        with ExitStack() as stack:
            stack.enter_context(patch.object(sys, 'argv', argv))
            stack.enter_context(patch.object(sys, 'path', sys.path.copy()))
            stack.enter_context(patch.dict(sys.modules, {'prepare_sdk': sdk}))
            stack.enter_context(patch.dict(os.environ, self.environment))
            stack.enter_context(patch.object(driver, 'source_observation', return_value=self.before))
            stack.enter_context(patch.object(driver, 'source_file_proof', return_value={'EXPLICIT_FILELIST_BOUNDARY_DOUBLE': True}))
            stack.enter_context(patch.object(driver, 'dependency_proof', return_value={'EXPLICIT_DEPENDENCY_BOUNDARY_DOUBLE': True}))
            stack.enter_context(patch.object(driver, 'original_oracles', return_value={'EXPLICIT_ORACLE_BOUNDARY_DOUBLE': True}))
            stack.enter_context(patch.object(driver.platform, 'system', return_value='Darwin'))
            stack.enter_context(patch.object(driver.platform, 'machine', return_value='arm64'))
            stack.enter_context(patch.object(driver, 'command', side_effect=self.command))
            stack.enter_context(patch.object(driver.subprocess, 'run', side_effect=self.cleanup_command))
            stack.enter_context(patch.object(driver.signal, 'signal'))
            stack.enter_context(redirect_stdout(io.StringIO()))
            code = driver.main()
        name = 'source-admission.json' if source_only else 'execution.json'
        self.receipt = json.loads((self.evidence / name).read_bytes())
        self.assertEqual(self.receipt['native_editor_ui_tests'], 0)
        self.assertEqual(self.receipt['verified_runtime_observations'], [])
        self.assertFalse((self.work / 'distribution/QUALIFICATION.json').exists())
        if not source_only:
            self.assertEqual(code, 1)
            self.assertEqual(self.receipt['status'], 'FAIL')
            self.assertEqual(json.loads((self.evidence / 'source-before.json').read_bytes()),
                             json.loads((self.evidence / 'source-after.json').read_bytes()))
            self.assertEqual([row['operation'] for row in json.loads((self.evidence / 'owned-simulator-cleanup.json').read_bytes())],
                             ['shutdown', 'delete'])
        return code

    def names(self):
        return [item['name'] for item in self.events]

    def event(self, name):
        matches = [item for item in self.events if item['name'] == name]
        self.assertEqual(len(matches), 1)
        return matches[0]

    def test_one_notice_preserves_selected_simulator_for_both_original_build_commands(self):
        self.run_driver()
        for name in ['framework-build', 'external-consumer-build']:
            args = self.event(name)['command']
            self.assertEqual(args[args.index('-destination') + 1], 'platform=iOS Simulator,id=' + self.udid)

    def test_multiple_notices_preserve_exact_contents_and_consumer_destination(self):
        self.notice_count = 3
        self.run_driver()
        notices = self.work / 'distribution/SourceProvenance'
        for number in range(3):
            self.assertEqual((notices / ('dependency-' + str(number)) / 'LICENSE.md').read_bytes(),
                             ('EXACT_SYNTHETIC_NOTICE_' + str(number)).encode())
        args = self.event('external-consumer-build')['command']
        self.assertEqual(args[args.index('-destination') + 1], 'platform=iOS Simulator,id=' + self.udid)

    def test_build_graph_consumer_and_signature_complete_before_original_boot_pair(self):
        self.run_driver()
        names = self.names()
        for name in ['framework-build', 'actual-target-public-symbol-graph', 'external-consumer-build', 'external-consumer-signature']:
            self.assertLess(names.index(name), names.index('boot-owned-simulator'))
        self.assertEqual(names[names.index('boot-owned-simulator'):names.index('install-external-consumer') + 1],
                         ['boot-owned-simulator', 'boot-status', 'install-external-consumer'])
        for name, timeout in [('framework-build', 6000), ('external-consumer-build', 600),
                              ('boot-owned-simulator', 60), ('boot-status', 180)]:
            self.assertEqual(self.event(name)['timeout_seconds'], timeout)

    def test_original_framework_compile_failure_cannot_boot_or_install(self):
        self.failure = 'framework-build'
        self.run_driver()
        self.assertNotIn('boot-owned-simulator', self.names())
        self.assertNotIn('external-consumer-build', self.names())
        self.assertNotIn('install-external-consumer', self.names())

    def test_original_public_surface_tool_failure_cannot_boot_or_install(self):
        self.failure = 'actual-target-public-symbol-graph'
        self.run_driver()
        self.assertNotIn('boot-owned-simulator', self.names())
        self.assertNotIn('external-consumer-build', self.names())

    def test_consumer_compile_failure_cannot_boot_or_install(self):
        self.failure = 'external-consumer-build'
        self.run_driver()
        self.assertNotIn('boot-owned-simulator', self.names())
        self.assertNotIn('install-external-consumer', self.names())

    def test_different_embedded_product_cannot_reach_boot_or_install(self):
        self.corrupt_embedded = True
        self.run_driver()
        self.assertIn('did not embed the exact exported framework', self.receipt['error'])
        self.assertNotIn('boot-owned-simulator', self.names())
        self.assertNotIn('install-external-consumer', self.names())

    def test_same_180_second_boot_timeout_retains_partial_builds_without_runtime_credit(self):
        self.failure = 'boot-status'
        self.run_driver()
        self.assertEqual(self.event('boot-status')['timeout_seconds'], 180)
        self.assertEqual(self.receipt['error_type'], 'TimeoutExpired')
        self.assertEqual(self.receipt['original_framework_build'], 'PASS')
        self.assertEqual(self.receipt['external_consumer_build'], 'PASS')
        self.assertNotIn('install-external-consumer', self.names())

    def test_boot_command_failure_keeps_build_evidence_but_never_runs_bootstatus_or_install(self):
        self.failure = 'boot-owned-simulator'
        self.run_driver()
        self.assertEqual(self.event('boot-owned-simulator')['timeout_seconds'], 60)
        self.assertEqual(self.receipt['original_framework_build'], 'PASS')
        self.assertEqual(self.receipt['external_consumer_build'], 'PASS')
        self.assertNotIn('boot-status', self.names())
        self.assertNotIn('install-external-consumer', self.names())

    def test_original_source_only_admission_never_invokes_any_tool_or_work_directory(self):
        self.assertEqual(self.run_driver(source_only=True), 0)
        self.assertEqual(self.receipt['status'], 'SOURCE_BOUND_FRAMEWORK_RUNTIME_NOT_RUN')
        self.assertEqual(self.events, [])
        self.assertFalse(self.work.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
