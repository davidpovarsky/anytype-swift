"""Exact-policy filesystem controls with explicit native-tool doubles.

No Apple codesign/build/consumer/runtime credit is obtained by these controls.
The real workflow still executes the unchanged native gates independently.
"""
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import struct
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import anycrypto_simulator_signing as shared
import observed_package_simulator_signing as signing
import run_framework_acceptance as driver
import test_anycrypto_simulator_signing as original_crypto
import test_framework_flow as original_flow


def fixture_binary(name):
    with patch.object(shared, 'EXECUTABLE', name[:-len('.framework')]), patch.object(shared, 'NAME', name):
        return original_crypto.fixture_binary()


def signed_fixture(original, name, identifier):
    executable = name[:-len('.framework')]
    old = shared.layout(original, executable)
    prefix = bytearray(original[:old['signature']['offset']])
    directory = bytearray(88) + identifier.encode() + b'\0'
    struct.pack_into('>6I', directory, 0, 0xfade0c02, len(directory), 0x20400, 2, 0, 88)
    struct.pack_into('>I', directory, 32, len(prefix))
    chunks = [(0, directory), (2, struct.pack('>3I', 0xfade0c01, 12, 0)),
              (0x10000, struct.pack('>2I', 0xfade0b01, 8))]
    raw = bytearray(36)
    for index, (slot, payload) in enumerate(chunks):
        struct.pack_into('>II', raw, 12 + index * 8, slot, len(raw))
        raw += payload
    struct.pack_into('>3I', raw, 0, 0xfade0cc0, len(raw), 3)
    allocated = (len(raw) + 16 + 15) // 16 * 16
    raw += bytes(allocated - len(raw))
    struct.pack_into('<I', prefix, old['signature']['command'] + 12, allocated)
    size = len(prefix) + allocated - old['linkedit']['fileoff']
    struct.pack_into('<Q', prefix, old['linkedit']['command'] + 48, size)
    struct.pack_into('<Q', prefix, old['linkedit']['command'] + 32, (size + 16383) // 16384 * 16384)
    return bytes(prefix + raw)


def put_framework(path, name):
    profile = signing.PROFILES[name]
    executable = name[:-len('.framework')]
    path.mkdir(parents=True)
    (path / executable).write_bytes(fixture_binary(name))
    (path / executable).chmod(0o755)
    (path / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': executable, 'CFBundleIdentifier': profile['identifier'],
        'CFBundlePackageType': 'FMWK', 'CFBundleSupportedPlatforms': ['iPhoneSimulator']}))
    if profile.get('resource_bundle'):
        bundle = path / profile['resource_bundle']
        for relative in signing.RESOURCE_FILES:
            target = bundle / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(('EXPLICIT_SYNTHETIC_UNCHANGED_RESOURCE:' + relative).encode())


def put_pin(root, profile):
    path = root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'pins': [{'identity': profile['package'], 'state': {'revision': profile['revision']}}]}))


def tool_double(arguments, root, evidence, label, timeout):
    path = Path(arguments[-1])
    if label.endswith(('-original-strict-signature', '-export-before-strict-signature')):
        driver.write(evidence / (label + '.command.json'),
                     {'command': arguments, 'returncode': 1, 'timed_out': False})
        (evidence / (label + '.stderr.log')).write_text(str(path)
            + ': code has no resources but signature indicates they must be present\n')
        raise ValueError('EXPLICIT_NATIVE_FAILURE_DOUBLE')
    if label.endswith('-export-adhoc-sign'):
        profile = signing.PROFILES[path.name]
        executable = path.name[:-len('.framework')]
        source = path / executable
        source.write_bytes(signed_fixture(source.read_bytes(), path.name, profile['identifier']))
        (path / '_CodeSignature').mkdir()
        (path / shared.SEAL).write_bytes(plistlib.dumps({'files': {}, 'files2': {}}))
    return ''


class ObservedExportSigningControls(unittest.TestCase):
    def fixture(self, name='BigInt_175F1397B99A03_PackageProduct.framework'):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root, self.name = Path(temporary.name), name
        self.profile = signing.PROFILES[name]
        self.products = self.root / 'build/producer/Build/Products/Debug-Anytype-iphonesimulator'
        self.exported, self.evidence = self.root / 'build/distribution', self.root / 'build/evidence'
        self.evidence.mkdir(parents=True)
        self.original, self.target = self.products / 'PackageFrameworks' / name, self.exported / 'Frameworks' / name
        self.executable = name[:-len('.framework')]
        put_framework(self.original, name)
        self.target.parent.mkdir(parents=True)
        shutil.copytree(self.original, self.target)
        self.calls, self.mutation = [], None
        self.original_module_bytes = b'// EXPLICIT_SYNTHETIC_ORIGINAL_MODULE\n'
        if 'package' in self.profile:
            put_pin(self.root, self.profile)
        else:
            module = self.root / self.profile['module']
            module.mkdir(parents=True)
            (module / 'Original.swift').write_bytes(self.original_module_bytes)
        if self.profile.get('resource_bundle'):
            privacy = (self.original / self.profile['resource_bundle'] / 'PrivacyInfo.xcprivacy').read_bytes()
            altered = dict(self.profile, privacy_sha256=hashlib.sha256(privacy).hexdigest())
            patcher = patch.dict(signing.PROFILES, {name: altered})
            patcher.start(); self.addCleanup(patcher.stop)
            self.profile = altered

    def git_double(self, root, *args):
        if args[0] == 'rev-parse':
            return (self.profile['tree'] + '\n').encode()
        original = self.original_module_bytes
        digest = hashlib.sha1(b'blob ' + str(len(original)).encode() + b'\0' + original).hexdigest()
        return ('100644 blob ' + digest + '\tOriginal.swift\0').encode()

    def command(self, args, root, evidence, label, timeout):
        self.calls.append((label, list(args)))
        result = tool_double(args, root, evidence, label, timeout)
        if label.endswith('-export-adhoc-sign') and self.mutation:
            self.mutation()
        return result

    def run_export(self, command=None):
        with patch.object(signing.platform, 'system', return_value='Darwin'), \
             patch.object(signing, 'git_bytes', side_effect=self.git_double):
            return signing.prepare_observed_package_simulator_export(
                self.root, self.products, self.exported, self.evidence, self.name, command or self.command)

    def test_every_exact_profile_preserves_all_original_and_nested_bytes(self):
        for name in signing.PROFILES:
            with self.subTest(name=name):
                self.fixture(name)
                before = signing.framework_closure(self.original)
                result = self.run_export()
                self.assertEqual(signing.framework_closure(self.original), before)
                self.assertTrue(result['original_resources_and_nested_signatures_unchanged'])
                self.assertTrue(result['original_metadata_unchanged'])
                self.assertEqual(result['consumer_qualification'], 'NOT_GRANTED')
                self.assertEqual(result['native_editor_ui_tests'], 0)
                self.assertEqual(result['editable_mount'], 'NOT_EXPOSED')
                self.assertTrue(all('--deep' not in args for _, args in self.calls))
                self.assertEqual(sum('--sign' in args for _, args in self.calls), 1)
                self.assertTrue(any(label.endswith('-export-after-strict-signature') for label, _ in self.calls))
                if self.profile.get('resource_bundle'):
                    self.assertEqual(sum(label.endswith('-nested-resource-strict') for label, _ in self.calls), 3)

    def test_unreviewed_product_name_has_no_wildcard_exception(self):
        self.fixture()
        self.name = 'Another_0000_PackageProduct.framework'
        with self.assertRaisesRegex(ValueError, 'Unreviewed generated'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_wrong_external_revision_never_reaches_native_signer(self):
        self.fixture(); put_pin(self.root, dict(self.profile, revision='0' * 40))
        with self.assertRaisesRegex(ValueError, 'revision differs'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_wrong_local_module_tree_never_reaches_native_signer(self):
        self.fixture('AppTarget_-256A0C750C206F_PackageProduct.framework')
        self.git_double = lambda *args: b'0000000000000000000000000000000000000000\n'
        with self.assertRaisesRegex(ValueError, 'module tree differs'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_dirty_local_module_bytes_fail_against_pinned_blob(self):
        self.fixture('AppTarget_-256A0C750C206F_PackageProduct.framework')
        (self.root / self.profile['module'] / 'Original.swift').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'bytes differ'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_extra_local_module_file_is_not_in_the_source_closure(self):
        self.fixture('NotificationsCore_5AD5AD79262EBF4_PackageProduct.framework')
        (self.root / self.profile['module'] / 'Extra.swift').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'Unreviewed original local module'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_alias_cannot_redirect_signing_to_original_producer(self):
        self.fixture(); shutil.rmtree(self.target); self.target.symlink_to(self.original, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'aliased or original'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_unknown_resource_or_signature_member_is_refused(self):
        self.fixture(); (self.original / 'unreviewed').write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError, 'Unexpected observed'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_export_must_match_original_before_native_signing(self):
        self.fixture(); (self.target / 'Info.plist').write_bytes((self.target / 'Info.plist').read_bytes() + b' ')
        with self.assertRaises(ValueError): self.run_export()
        self.assertEqual(self.calls, [])

    def test_device_product_is_not_an_eligible_simulator_export(self):
        self.fixture()
        for target in [self.original, self.target]:
            path = target / self.executable; data = bytearray(path.read_bytes())
            struct.pack_into('<I', data, 200, 2); path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'Simulator command closure'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_resource_and_nested_signature_mutations_are_rejected(self):
        for relative in signing.RESOURCE_FILES:
            with self.subTest(relative=relative):
                self.fixture('Crypto_17A3B1FFC41E47_PackageProduct.framework')
                path = self.target / self.profile['resource_bundle'] / relative
                self.mutation = lambda: path.write_bytes(path.read_bytes() + b'changed')
                with self.assertRaises(ValueError): self.run_export()

    def test_nested_resource_metadata_mutation_is_rejected(self):
        self.fixture('SwiftProtobuf_7CEE9AB92C12BC6B_PackageProduct.framework')
        path = self.target / self.profile['resource_bundle'] / '_CodeSignature/CodeResources'
        self.mutation = lambda: path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'filesystem metadata'): self.run_export()

    def test_nested_signature_must_verify_before_any_root_signing(self):
        self.fixture('Crypto_17A3B1FFC41E47_PackageProduct.framework')
        def command(args, root, evidence, label, timeout):
            if label.endswith('-nested-resource-strict'): raise ValueError('NESTED_STRICT_FAILURE')
            return self.command(args, root, evidence, label, timeout)
        with self.assertRaisesRegex(ValueError, 'NESTED_STRICT_FAILURE'): self.run_export(command)
        self.assertFalse(any('--sign' in args for _, args in self.calls))

    def test_unexpected_valid_original_is_not_resigned(self):
        self.fixture()
        with self.assertRaisesRegex(ValueError, 'Unexpected valid'): self.run_export(lambda *args: '')
        self.assertFalse((self.target / shared.SEAL).exists())

    def test_different_native_failure_is_not_a_signing_exception(self):
        self.fixture()
        def command(args, root, evidence, label, timeout):
            try: return self.command(args, root, evidence, label, timeout)
            finally: (evidence / (label + '.stderr.log')).write_text('UNRELATED_NATIVE_ERROR')
        with self.assertRaisesRegex(ValueError, 'observed missing'): self.run_export(command)
        self.assertEqual(len(self.calls), 1)

    def test_modified_original_producer_stops_acceptance(self):
        self.fixture(); self.mutation = lambda: (self.original / 'Info.plist').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'original producer or module'): self.run_export()

    def test_modified_executable_instruction_stops_acceptance(self):
        self.fixture()
        def mutate():
            path = self.target / self.executable; raw = bytearray(path.read_bytes()); raw[1024] ^= 1; path.write_bytes(raw)
        self.mutation = mutate
        with self.assertRaisesRegex(ValueError, 'nonsignature LINKEDIT'): self.run_export()

    def test_wrong_new_signing_identifier_is_rejected(self):
        self.fixture()
        self.mutation = lambda: (self.target / self.executable).write_bytes(
            signed_fixture((self.original / self.executable).read_bytes(), self.name, 'wrong.original.identity'))
        with self.assertRaisesRegex(ValueError, 'identifier differs'): self.run_export()

    def test_native_post_sign_failure_preserves_receipt_without_qualification(self):
        self.fixture()
        def command(args, root, evidence, label, timeout):
            if label.endswith('-export-after-strict-signature'): raise ValueError('POST_STRICT_FAILED')
            return self.command(args, root, evidence, label, timeout)
        with self.assertRaisesRegex(ValueError, 'POST_STRICT_FAILED'): self.run_export(command)
        receipt = json.loads((self.evidence / ('observed-' + self.profile['label'] + '-simulator-signing.json')).read_bytes())
        self.assertEqual(receipt['status'], 'FAIL'); self.assertEqual(receipt['native_post_signature'], 'NOT_RUN')
        self.assertEqual(receipt['consumer_qualification'], 'NOT_GRANTED')
        self.assertIn('retained_export_after', receipt)


class ObservedPackageOriginalDriverControls(unittest.TestCase):
    def run_flow(self, corrupt_distribution=False, fail_signer=False):
        case = original_flow.OriginalDriverFlowControls('test_one_notice_preserves_selected_simulator_for_both_original_build_commands')
        case._testMethodName = self._testMethodName
        case.setUp(); self.addCleanup(case.doCleanups)
        name = 'BigInt_175F1397B99A03_PackageProduct.framework'
        put_pin(case.root, signing.PROFILES[name])
        produce, original_command = case.produce_framework_fixture, case.command
        def produce_with_package():
            produce()
            put_framework(case.work / 'producer-derived/Build/Products/Debug-Anytype-iphonesimulator/PackageFrameworks' / name, name)
        def command(args, root, evidence, label, timeout):
            if label.startswith('observed-'):
                case.events.append({'name': label, 'command': list(args), 'timeout_seconds': timeout})
                if label.endswith('-export-adhoc-sign') and fail_signer: raise ValueError('EXPLICIT_SIGNER_FAILURE_DOUBLE')
                result = tool_double(args, root, evidence, label, timeout)
                if label.endswith('-export-adhoc-sign') and corrupt_distribution:
                    (case.work / 'distribution/SourceProvenance/Anytype-LICENSE.md').write_bytes(b'not original')
                return result
            return original_command(args, root, evidence, label, timeout)
        case.produce_framework_fixture, case.command = produce_with_package, command
        case.run_driver()
        return case

    def test_original_driver_keeps_full_strict_gate_before_external_consumer(self):
        case = self.run_flow(); names = case.names()
        self.assertLess(names.index('observed-bigint-export-after-strict-signature'), names.index('framework-signature-1'))
        self.assertLess(names.index('framework-signature-1'), names.index('external-consumer-build'))
        self.assertEqual(case.receipt['external_consumer_build'], 'PASS')
        self.assertIn('Synthetic control stops before real installation', case.receipt['error'])
        proof = json.loads((case.evidence / 'framework-distribution.json').read_bytes())
        self.assertEqual(proof['simulator_signing_transformations'][0]['consumer_qualification'], 'NOT_GRANTED')

    def test_unrelated_distribution_change_cannot_reach_consumer(self):
        case = self.run_flow(corrupt_distribution=True)
        self.assertNotIn('external-consumer-build', case.names())
        self.assertIn('unrelated distribution bytes', case.receipt['error'])

    def test_failed_signer_keeps_failure_inventory_and_stops_native_acceptance(self):
        case = self.run_flow(fail_signer=True)
        self.assertNotIn('framework-signature-1', case.names())
        self.assertNotIn('external-consumer-build', case.names())
        self.assertNotIn('boot-owned-simulator', case.names())
        result = json.loads((case.evidence / 'framework-distribution-after-failed-observed-bigint-signing.json').read_bytes())
        self.assertEqual(result['status'], 'OBSERVED_ONLY_NOT_QUALIFIED')


class DependencyCheckoutSourceClosureControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.derived, self.evidence = self.root / 'build/producer-derived', self.root / 'build/evidence'
        self.evidence.mkdir(parents=True)
        self.checkouts = self.derived / 'SourcePackages/checkouts'
        dependencies, pins = [], []
        for name in ['torahinspectorkit', 'swift-ai-sdk']:
            checkout = self.checkouts / name
            (checkout / 'Sources').mkdir(parents=True)
            (checkout / 'Resources').mkdir()
            (checkout / 'Sources/Original.swift').write_text('// Actual disposable Git fixture\n')
            (checkout / 'Resources/Original.json').write_text('{"original":true}\n')
            (checkout / '.gitignore').write_text('Sources/Ignored.swift\n')
            subprocess.run(['git', 'init', '-q', str(checkout)], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(checkout), 'add', '.'], check=True, capture_output=True)
            subprocess.run(['git', '-C', str(checkout), '-c', 'user.name=Fixture', '-c',
                            'user.email=fixture@example.invalid', 'commit', '-qm', 'Disposable source fixture'],
                           check=True, capture_output=True)
            head = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD']).decode().strip()
            pins.append({'identity': name, 'state': {'revision': head}})
            dependencies.append({'packageRef': {'identity': name},
                                 'state': {'name': 'sourceControlCheckout', 'checkoutState': {'revision': head}},
                                 'subpath': name})
        (self.root / 'Package.resolved').write_text(json.dumps({'pins': pins}))
        (self.derived / 'SourcePackages/workspace-state.json').write_text(json.dumps({'object': {'dependencies': dependencies}}))
        # Real generated build metadata is retained outside immutable sources.
        (self.derived / 'Build/Intermediates.noindex').mkdir(parents=True)
        (self.derived / 'Build/Intermediates.noindex/generated-accessor.swift').write_text('// generated\n')
        self.profile = {'package_resolved_path': 'Package.resolved'}

    def test_unchanged_source_accepts_separate_owned_generated_build_metadata(self):
        result = driver.dependency_proof(self.root, self.derived, self.profile, self.evidence)
        self.assertTrue(result['all_checkout_files_tracked'])
        self.assertEqual(set(result['actual_checkout_revisions']), {'torahinspectorkit', 'swift-ai-sdk'})
        self.assertTrue((self.derived / 'Build/Intermediates.noindex/generated-accessor.swift').is_file())

    def test_untracked_swift_resource_and_ignored_source_are_rejected_without_cleanup(self):
        checkout = self.checkouts / 'torahinspectorkit'
        for relative in ['Sources/Extra.swift', 'Resources/Extra.json', 'Sources/Ignored.swift']:
            with self.subTest(relative=relative):
                path = checkout / relative; path.write_text('unexpected source or resource\n')
                self.assertEqual(subprocess.check_output(['git', '-C', str(checkout), 'diff', '--name-only', 'HEAD']), b'')
                with self.assertRaisesRegex(ValueError, 'Untracked dependency inputs'):
                    driver.dependency_proof(self.root, self.derived, self.profile, self.evidence)
                self.assertTrue(path.is_file())
                path.unlink()  # Disposable fixture only; the actual verifier never removes inputs.


if __name__ == '__main__':
    unittest.main()
