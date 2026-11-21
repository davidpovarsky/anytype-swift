"""Real filesystem/driver controls with explicit synthetic Mach-O/tool doubles.

No codesign, Apple compilation or runtime executes here. The actual Apple run
must independently satisfy the original strict signature and consumer gates.
"""
import json
from pathlib import Path
import plistlib
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

import anycrypto_simulator_signing as signing
import run_framework_acceptance as driver
import test_framework_flow as original_flow


def fixture_binary():
    commands = bytearray()
    for name, address, fileoff, filesize in [(b'__TEXT', 0, 0, 3072),
                                            (b'__LINKEDIT', 16384, 3072, 1536)]:
        commands += struct.pack('<II16sQQQQIIII', 0x19, 72, name, address, 16384,
                                fileoff, filesize, 7, 5, 0, 0)
    commands += struct.pack('<4I', 0x1d, 16, 4096, 512)
    commands += struct.pack('<6I', 0x32, 24, 7, 0xf0000, 0x1b0000, 0)
    name = ('@rpath/' + signing.NAME + '/' + signing.EXECUTABLE).encode() + b'\0'
    size = (24 + len(name) + 7) // 8 * 8
    commands += struct.pack('<6I', 0xd, size, 24, 0, 0, 0) + name + bytes(size - 24 - len(name))
    data = bytearray(4608)
    data[:32] = struct.pack('<8I', 0xfeedfacf, 0x0100000c, 0, 6, 5, len(commands), 0, 0)
    data[32:32 + len(commands)] = commands
    marker = b'EXPLICIT_SYNTHETIC_NOT_EXECUTABLE_CODE'
    data[1024:1024 + len(marker)] = marker
    marker = b'EXPLICIT_SYNTHETIC_LINKEDIT'
    data[3072:3072 + len(marker)] = marker
    return bytes(data)


def signed_fixture(original):
    old = signing.layout(original)
    prefix = bytearray(original[:old['signature']['offset']])
    directory = bytearray(88)
    struct.pack_into('>5I', directory, 0, 0xfade0c02, 88, 0x20400, 2, 0)
    struct.pack_into('>I', directory, 32, len(prefix))
    chunks = [(0, directory), (2, struct.pack('>3I', 0xfade0c01, 12, 0)),
              (0x10000, struct.pack('>2I', 0xfade0b01, 8))]
    raw = bytearray(36)
    for index, (slot, data) in enumerate(chunks):
        struct.pack_into('>II', raw, 12 + index * 8, slot, len(raw))
        raw += data
    struct.pack_into('>3I', raw, 0, 0xfade0cc0, len(raw), 3)
    allocated = (len(raw) + 16 + 15) // 16 * 16
    raw += bytes(allocated - len(raw))
    struct.pack_into('<I', prefix, old['signature']['command'] + 12, allocated)
    struct.pack_into('<Q', prefix, old['linkedit']['command'] + 48,
                     len(prefix) + allocated - old['linkedit']['fileoff'])
    return bytes(prefix + raw)


def put_framework(path):
    path.mkdir(parents=True)
    (path / signing.EXECUTABLE).write_bytes(fixture_binary())
    (path / signing.EXECUTABLE).chmod(0o755)
    (path / 'Info.plist').write_bytes(plistlib.dumps({
        'CFBundleExecutable': signing.EXECUTABLE, 'CFBundlePackageType': 'FMWK',
        'CFBundleIdentifier': signing.EXECUTABLE, 'CFBundleSupportedPlatforms': ['iPhoneSimulator']}))


def put_package_pin(root, revision=signing.REVISION):
    path = root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({'pins': [{'identity': 'any-crypto-swift', 'state': {'revision': revision}}]}))


def tool_double(arguments, root, evidence, name, timeout):
    target = Path(arguments[-1])
    if name in {'anycrypto-original-strict-signature', 'anycrypto-export-before-strict-signature'}:
        driver.write(evidence / (name + '.command.json'), {
            'command': arguments, 'returncode': 1, 'timed_out': False})
        (evidence / (name + '.stderr.log')).write_text(str(target)
            + ': code has no resources but signature indicates they must be present\n')
        raise ValueError('EXPLICIT_NATIVE_TOOL_FAILURE_DOUBLE')
    if name == 'anycrypto-export-adhoc-sign':
        path = target / signing.EXECUTABLE
        path.write_bytes(signed_fixture(path.read_bytes()))
        (target / '_CodeSignature').mkdir()
        (target / signing.SEAL).write_bytes(plistlib.dumps({'files': {}, 'files2': {}}))
    return ''


class AnyCryptoExportSigningControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.products = self.root / 'build/producer/Build/Products/Debug-Anytype-iphonesimulator'
        self.exported = self.root / 'build/distribution'
        self.evidence = self.root / 'build/evidence'
        self.evidence.mkdir(parents=True)
        self.original = self.products / 'PackageFrameworks' / signing.NAME
        self.target = self.exported / 'Frameworks' / signing.NAME
        put_framework(self.original)
        self.target.parent.mkdir(parents=True)
        shutil.copytree(self.original, self.target)
        put_package_pin(self.root)
        self.calls = []
        self.sign_mutation = None

    def command(self, args, root, evidence, name, timeout):
        self.calls.append((name, args))
        result = tool_double(args, root, evidence, name, timeout)
        if name == 'anycrypto-export-adhoc-sign' and self.sign_mutation:
            self.sign_mutation()
        return result

    def run_export(self, command=None):
        with patch.object(signing.platform, 'system', return_value='Darwin'):
            return signing.prepare_anycrypto_simulator_export(self.root, self.products,
                self.exported, self.evidence, command or self.command)

    def test_exact_export_preserves_original_bytes_and_keeps_native_strict_gate(self):
        before = signing.framework_closure(self.original)
        result = self.run_export()
        self.assertEqual(signing.framework_closure(self.original), before)
        self.assertEqual(result['native_post_signature'], 'PASS')
        self.assertEqual(result['consumer_qualification'], 'NOT_GRANTED')
        self.assertEqual(result['native_editor_ui_tests'], 0)
        self.assertEqual(self.calls[2][1], ['codesign', '--force', '--sign', '-', '--timestamp=none', str(self.target)])
        self.assertEqual(self.calls[-1][1], ['codesign', '--verify', '--strict', str(self.target)])
        self.assertTrue((self.evidence / 'anycrypto-export-after-attachments' / signing.SEAL).is_file())

    def test_wrong_package_revision_cannot_reach_signer(self):
        put_package_pin(self.root, '0' * 40)
        with self.assertRaisesRegex(ValueError, 'revision differs'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_aliased_export_cannot_sign_original_producer(self):
        shutil.rmtree(self.target)
        self.target.symlink_to(self.original, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'aliased or original'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_extra_original_resource_is_not_an_authorized_generated_product(self):
        (self.original / 'unexpected').write_bytes(b'not reviewed')
        with self.assertRaisesRegex(ValueError, 'Unexpected generated'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_export_source_byte_difference_fails_before_signing(self):
        p = self.target / signing.EXECUTABLE
        b = bytearray(p.read_bytes()); b[1024] ^= 1; p.write_bytes(b)
        with self.assertRaisesRegex(ValueError, 'Export differs'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_non_simulator_product_fails_before_signing(self):
        for path in [self.original, self.target]:
            p = path / signing.EXECUTABLE
            b = bytearray(p.read_bytes()); struct.pack_into('<I', b, 200, 2); p.write_bytes(b)
        with self.assertRaisesRegex(ValueError, 'Simulator command closure'): self.run_export()
        self.assertEqual(self.calls, [])

    def test_different_native_failure_never_authorizes_signing(self):
        def command(args, root, evidence, name, timeout):
            try: return self.command(args, root, evidence, name, timeout)
            finally: (evidence / (name + '.stderr.log')).write_text('different failure')
        with self.assertRaisesRegex(ValueError, 'observed missing'): self.run_export(command)
        self.assertEqual(len(self.calls), 1)

    def test_unexpected_existing_strict_success_does_not_resign(self):
        with self.assertRaisesRegex(ValueError, 'Unexpected valid'): self.run_export(lambda *args: '')
        self.assertFalse((self.target / signing.SEAL).exists())

    def test_native_signer_failure_retains_fail_receipt_and_partial_observation(self):
        def command(args, root, evidence, name, timeout):
            if name == 'anycrypto-export-adhoc-sign': raise ValueError('SIGNER_FAILED')
            return self.command(args, root, evidence, name, timeout)
        with self.assertRaisesRegex(ValueError, 'SIGNER_FAILED'): self.run_export(command)
        result = json.loads((self.evidence / 'anycrypto-simulator-signing.json').read_bytes())
        self.assertEqual(result['status'], 'FAIL')
        self.assertIn('retained_export_after', result)
        self.assertEqual(result['native_post_signature'], 'NOT_RUN')

    def test_native_post_sign_strict_failure_remains_failure(self):
        def command(args, root, evidence, name, timeout):
            if name == 'anycrypto-export-after-strict-signature': raise ValueError('STRICT_FAILED')
            return self.command(args, root, evidence, name, timeout)
        with self.assertRaisesRegex(ValueError, 'STRICT_FAILED'): self.run_export(command)
        result = json.loads((self.evidence / 'anycrypto-simulator-signing.json').read_bytes())
        self.assertEqual(result['status'], 'FAIL')

    def test_signing_cannot_change_original_producer(self):
        self.sign_mutation = lambda: (self.original / 'Info.plist').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'original producer'): self.run_export()

    def test_signing_cannot_change_original_info_bytes(self):
        def mutate():
            p = self.target / 'Info.plist'; value = plistlib.loads(p.read_bytes())
            value['extra'] = 'mutation'; p.write_bytes(plistlib.dumps(value))
        self.sign_mutation = mutate
        with self.assertRaisesRegex(ValueError, 'Info.plist bytes changed'): self.run_export()

    def test_instruction_and_symbol_bytes_are_preserved_even_with_successful_tool_double(self):
        original = fixture_binary()
        for offset in [1024, 3072]:
            with self.subTest(offset=offset):
                altered = bytearray(signed_fixture(original)); altered[offset] ^= 1
                with self.assertRaisesRegex(ValueError, 'nonsignature LINKEDIT'):
                    signing.executable_preservation(original, altered)

    def test_signature_movement_and_unreviewed_size_fields_are_rejected(self):
        original = fixture_binary(); altered = bytearray(signed_fixture(original))
        struct.pack_into('<I', altered, 184, 4080)
        with self.assertRaises(ValueError): signing.executable_preservation(original, altered)

    def test_new_entitlements_or_authority_slot_is_rejected(self):
        original = fixture_binary(); altered = bytearray(signed_fixture(original))
        struct.pack_into('>I', altered, 4096 + 12 + 16, 5)
        with self.assertRaisesRegex(ValueError, 'authority or entitlements'):
            signing.executable_preservation(original, altered)

    def test_unobserved_payload_cannot_hide_in_signature_slack(self):
        original = fixture_binary(); altered = bytearray(signed_fixture(original)); altered[-1] = 1
        with self.assertRaisesRegex(ValueError, 'signing slack'):
            signing.executable_preservation(original, altered)

    def test_diagnostics_report_all_failures_without_signing_or_qualification(self):
        other = 'UnreviewedOther_PackageProduct.framework'
        shutil.copytree(self.original, self.products / 'PackageFrameworks' / other)
        shutil.copytree(self.target, self.exported / 'Frameworks' / other)
        seen = []
        def command(args, root, evidence, name, timeout):
            seen.append(list(args))
            if '--verify' in args: raise ValueError('EXPLICIT_DIAGNOSTIC_FAILURE_DOUBLE')
            return ''
        before = signing.framework_closure(self.target)
        result = signing.diagnose_generated_package_exports(self.root, self.products, self.exported,
            self.evidence, [signing.NAME, other], 'a' * 40, command)
        self.assertEqual(len(result['products']), 2)
        self.assertTrue(all(p['strict_status'] == 'COMMAND_FAILED_OBSERVATION_ONLY' for p in result['products']))
        self.assertTrue(all(p['signature_display_status'] == 'COMMAND_SUCCEEDED_OBSERVATION_ONLY' for p in result['products']))
        self.assertEqual(result['status'], 'OBSERVED_ONLY_NOT_QUALIFIED')
        self.assertTrue(all('--sign' not in args for args in seen))
        self.assertEqual(signing.framework_closure(self.target), before)


class AnyCryptoOriginalDriverControls(unittest.TestCase):
    def run_flow(self, corrupt_distribution=False, fail_signer=False):
        case = original_flow.OriginalDriverFlowControls('test_one_notice_preserves_selected_simulator_for_both_original_build_commands')
        case._testMethodName = self._testMethodName
        case.setUp(); self.addCleanup(case.doCleanups)
        put_package_pin(case.root)
        produce, original_command = case.produce_framework_fixture, case.command
        def produce_with_anycrypto():
            produce()
            put_framework(case.work / 'producer-derived/Build/Products/Debug-Anytype-iphonesimulator/PackageFrameworks' / signing.NAME)
        def command(args, root, evidence, name, timeout):
            if name.startswith('anycrypto-'):
                case.events.append({'name': name, 'command': list(args), 'timeout_seconds': timeout})
                if name == 'anycrypto-export-adhoc-sign' and fail_signer:
                    raise ValueError('EXPLICIT_SIGNER_FAILURE_DOUBLE')
                result = tool_double(args, root, evidence, name, timeout)
                if name == 'anycrypto-export-adhoc-sign' and corrupt_distribution:
                    (case.work / 'distribution/SourceProvenance/Anytype-LICENSE.md').write_bytes(b'not original')
                return result
            return original_command(args, root, evidence, name, timeout)
        case.produce_framework_fixture, case.command = produce_with_anycrypto, command
        case.run_driver()
        return case

    def test_original_driver_requires_strict_signature_before_binary_consumer(self):
        case = self.run_flow(); names = case.names()
        self.assertLess(names.index('anycrypto-export-after-strict-signature'), names.index('framework-signature-0'))
        self.assertLess(names.index('framework-signature-0'), names.index('external-consumer-build'))
        self.assertEqual(case.receipt['external_consumer_build'], 'PASS')
        self.assertIn('Synthetic control stops before real installation', case.receipt['error'])
        proof = json.loads((case.evidence / 'framework-distribution.json').read_bytes())
        self.assertEqual(proof['simulator_signing_transformations'][0]['consumer_qualification'], 'NOT_GRANTED')

    def test_unrelated_distribution_mutation_stops_consumer(self):
        case = self.run_flow(corrupt_distribution=True)
        self.assertNotIn('external-consumer-build', case.names())
        self.assertIn('unrelated distribution bytes', case.receipt['error'])

    def test_failed_signer_preserves_observation_and_blocks_all_later_gates(self):
        case = self.run_flow(fail_signer=True)
        self.assertNotIn('framework-signature-0', case.names())
        self.assertNotIn('external-consumer-build', case.names())
        self.assertNotIn('boot-owned-simulator', case.names())
        result = json.loads((case.evidence / 'framework-distribution-after-failed-anycrypto-signing.json').read_bytes())
        self.assertEqual(result['status'], 'OBSERVED_ONLY_NOT_QUALIFIED')


if __name__ == '__main__':
    unittest.main()
