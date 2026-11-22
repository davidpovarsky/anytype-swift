"""Actual pinned binary / complete Python signing-boundary controls.

The only signing operation here is an explicit Python fixture. It recomputes
ad-hoc page hashes to discriminate payload checks from page-hash failures, but
never invokes codesign, Apple tools or any native consumer. The workflow must
still execute the mandatory native signer and strict verification on Darwin.
"""
from contextlib import ExitStack
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
import zipfile

import amplitude_simulator_signing as signing
import framework_products as products
import run_framework_acceptance as driver
import test_framework_flow as original_flow

ROOT = Path(__file__).resolve().parents[2]
PROFILE = signing.read_profile()
ARCHIVE = ROOT / PROFILE['archive_path']
PREFIX = 'AmplitudeCore.xcframework/ios-arm64_x86_64-simulator/AmplitudeCore.framework/'

def original_files():
    raw = ARCHIVE.read_bytes()
    if len(raw) != PROFILE['archive_bytes'] or hashlib.sha256(raw).hexdigest() != PROFILE['archive_sha256']:
        raise AssertionError('Actual pinned upstream fixture differs')
    with zipfile.ZipFile(ARCHIVE) as archive:
        if archive.testzip() is not None:
            raise AssertionError('Actual upstream fixture CRC differs')
        return {name[len(PREFIX):]: archive.read(name) for name in archive.namelist()
                if name.startswith(PREFIX) and not name.endswith('/')}

def put_framework(path, files):
    path.mkdir(parents=True)
    for name, data in files.items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(PROFILE['files'][name]['mode'])

def fixture_ad_hoc_replacement(files, delta=0, edit_prefix=None, edit_directory=None, page_exponents=(12, 14)):
    """Explicit modern native-tool boundary; never invokes or replaces codesign."""
    result = dict(files)
    resources = plistlib.loads(files['_CodeSignature/CodeResources'])
    for table in ('files', 'files2'):
        for name in signing.MISSING:
            del resources[table][name]
    result['_CodeSignature/CodeResources'] = plistlib.dumps(resources)
    before = signing.read_macho(files[signing.EXECUTABLE], files)
    output = bytearray(48)
    struct.pack_into('>II', output, 0, 0xcafebabe, 2)
    for index, old in enumerate(before):
        signature = old['signature']
        prefix = bytearray(old['thin'][:signature['dataoff']])
        old_signature = old['thin'][signature['dataoff']:]
        magic, meaningful, count = struct.unpack_from('>III', old_signature)
        indices = [struct.unpack_from('>II', old_signature, 12 + 8 * item) for item in range(count)]
        blobs = {}
        for slot, start in indices:
            length = struct.unpack_from('>I', old_signature, start + 4)[0]
            blobs[slot] = old_signature[start:start + length]
        old_directory = blobs[0]
        hashes = struct.unpack_from('>I', old_directory, 16)[0]
        page_exponent = page_exponents[index]
        page_bytes = 1 << page_exponent
        pages = (len(prefix) + page_bytes - 1) // page_bytes
        directory = bytearray(old_directory[:hashes]) + bytearray(pages * 32)
        struct.pack_into('>I', directory, 4, len(directory))
        struct.pack_into('>I', directory, 28, pages)
        directory[39] = page_exponent
        directory[hashes - 96:hashes - 64] = hashlib.sha256(result['_CodeSignature/CodeResources']).digest()
        meaningful = 12 + count * 8 + len(directory) + sum(len(value) for slot, value in blobs.items() if slot != 0)
        new_signature_size = meaningful + 18 + delta
        if new_signature_size < meaningful:
            raise AssertionError('Synthetic signing fixture allocation is too small')
        new_thin_size = len(prefix) + new_signature_size
        linkedit = old['linkedit']
        filesize = new_thin_size - linkedit['fileoff']
        vmsize = (filesize + 16383) // 16384 * 16384
        struct.pack_into('<Q', prefix, linkedit['command_offset'] + 32, vmsize)
        struct.pack_into('<Q', prefix, linkedit['command_offset'] + 48, filesize)
        struct.pack_into('<I', prefix, signature['command_offset'] + 12, new_signature_size)
        if edit_prefix:
            edit_prefix(prefix, old, index)
        for page in range(pages):
            directory[hashes + page * 32:hashes + (page + 1) * 32] = hashlib.sha256(
                prefix[page * page_bytes:min((page + 1) * page_bytes, len(prefix))]).digest()
        if edit_directory:
            edit_directory(directory, old, index)
        blobs[0] = bytes(directory)
        payload = bytearray(12 + 8 * count)
        struct.pack_into('>III', payload, 0, magic, meaningful, count)
        for item, (slot, _) in enumerate(indices):
            struct.pack_into('>II', payload, 12 + 8 * item, slot, len(payload))
            payload.extend(blobs[slot])
        if len(payload) != meaningful:
            raise AssertionError('Synthetic SuperBlob length differs')
        start = signature['dataoff'] + meaningful
        stop = signature['dataoff'] + new_signature_size
        residue = old['thin'][start:stop]
        residue += bytes(new_signature_size - meaningful - len(residue))
        thin = prefix + payload + residue
        unit = 1 << old['fat_alignment']
        offset = (len(output) + unit - 1) // unit * unit
        output.extend(bytes(offset - len(output)))
        output.extend(thin)
        struct.pack_into('>IIIII', output, 8 + 20 * index, old['cpu'], old['subtype'],
                         offset, len(thin), old['fat_alignment'])
    result[signing.EXECUTABLE] = bytes(output)
    return result

class KnownSimulatorSigningControls(unittest.TestCase):
    def setUp(self):
        self.original = original_files()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.products = self.root / 'build/producer/Build/Products/Debug-Anytype-iphonesimulator'
        self.exported = self.root / 'build/distribution'
        self.evidence = self.root / 'build/evidence'
        self.evidence.mkdir(parents=True)
        self.source = self.products / signing.NAME
        self.target = self.exported / 'Frameworks' / signing.NAME
        put_framework(self.source, self.original)
        put_framework(self.target, self.original)
        package_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
        destination = self.root / package_path
        destination.parent.mkdir(parents=True)
        destination.write_bytes((ROOT / package_path).read_bytes())
        self.commands = []
        self.signer = lambda: fixture_ad_hoc_replacement(self.original)
        self.failure = None
        self.pre_verification_succeeds = False
        self.wrong_error = False
        self.mutate_source_after = False

    def command(self, args, root, evidence, name, timeout):
        self.commands.append((name, list(args), timeout))
        if name == self.failure:
            raise subprocess.TimeoutExpired(args, timeout)
        if name in {'amplitude-original-strict-signature', 'amplitude-export-before-strict-signature'}:
            if self.pre_verification_succeeds:
                return ''
            stdout = b''
            stderr = (b'EXPLICIT_DIFFERENT_TOOL_FAILURE' if self.wrong_error else
                      b'EXPLICIT_TOOL_BOUNDARY: a sealed resource is missing or invalid\n')
            (self.evidence / (name + '.stdout.log')).write_bytes(stdout)
            (self.evidence / (name + '.stderr.log')).write_bytes(stderr)
            driver.write(self.evidence / (name + '.command.json'), {
                'command': list(args), 'returncode': 1, 'timed_out': False,
                'timeout_seconds': timeout, 'stdout_sha256': signing.digest(stdout),
                'stderr_sha256': signing.digest(stderr), 'scope': 'EXPLICIT_NATIVE_TOOL_DOUBLE'})
            raise ValueError('Actual command failed: ' + name)
        if name == 'amplitude-export-adhoc-sign':
            for relative, data in self.signer().items():
                (self.target / relative).write_bytes(data)
        if name == 'amplitude-export-after-strict-signature' and self.mutate_source_after:
            (self.source / 'Headers/AmplitudeCore-Swift.h').write_bytes(b'changed original')
        return ''

    def prepare(self):
        with patch.object(signing.platform, 'system', return_value='Darwin'):
            return signing.prepare_amplitude_simulator_export(
                self.root, self.products, self.exported, self.evidence, self.command)

    def test_actual_pinned_upstream_has_only_the_two_required_missing_members(self):
        self.assertEqual(signing.seal_members(self.original, signing.MISSING),
                         {'missing': sorted(signing.MISSING), 'present_digests': 21})
        self.assertEqual(len(self.original), 13)

    def test_actual_original_two_slices_and_all_signing_page_hashes_parse(self):
        values = signing.read_macho(self.original[signing.EXECUTABLE], self.original)
        self.assertEqual([value['signature']['dataoff'] for value in values], [292784, 307792])
        self.assertEqual([value['signature_proof']['code_pages'] for value in values], [72, 76])
        self.assertEqual([value['signature_proof']['entitlements'] for value in values], [[], []])

    def test_same_allocation_replacement_preserves_every_nonsignature_byte(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        proof = signing.executable_preservation(self.original, candidate)
        self.assertEqual(len(proof), 2)
        self.assertEqual(signing.seal_members(candidate, set())['missing'], [])
        self.assertEqual({p for p in candidate if candidate[p] != self.original[p]},
                         {signing.EXECUTABLE, '_CodeSignature/CodeResources'})

    def test_native_signature_uses_documented_fixed_16k_vm_rounding(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        proof = signing.executable_preservation(self.original, candidate)
        for row in proof:
            after = row['after']['linkedit']
            self.assertEqual(after['vmsize'], (after['filesize'] + 16383) // 16384 * 16384)

    def test_smaller_signature_shrinks_only_to_exact_rounded_allocation(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        proof = signing.executable_preservation(self.original, candidate)
        self.assertEqual([row['before']['linkedit']['vmsize'] for row in proof], [212992, 212992])
        self.assertEqual([row['after']['linkedit']['vmsize'] for row in proof], [196608, 180224])
        self.assertEqual([row['after']['signature']['datasize'] for row in proof], [2576, 880])

    def test_rehashed_executable_code_change_is_refused(self):
        def edit(prefix, old, index):
            prefix[8192] ^= 1
        candidate = fixture_ad_hoc_replacement(self.original, edit_prefix=edit)
        signing.read_macho(candidate[signing.EXECUTABLE], candidate,
                           previous_slices=signing.read_macho(self.original[signing.EXECUTABLE], self.original))
        with self.assertRaisesRegex(ValueError, 'nonsignature LINKEDIT'):
            signing.executable_preservation(self.original, candidate)

    def test_rehashed_linkedit_symbols_change_is_refused(self):
        def edit(prefix, old, index):
            prefix[old['signature']['dataoff'] - 64] ^= 1
        candidate = fixture_ad_hoc_replacement(self.original, edit_prefix=edit)
        signing.read_macho(candidate[signing.EXECUTABLE], candidate,
                           previous_slices=signing.read_macho(self.original[signing.EXECUTABLE], self.original))
        with self.assertRaisesRegex(ValueError, 'nonsignature LINKEDIT'):
            signing.executable_preservation(self.original, candidate)

    def test_rehashed_dylib_timestamp_change_is_refused(self):
        def edit(prefix, old, index):
            location = next(offset for command, size, offset in old['commands'] if command == 0xd)
            value = struct.unpack_from('<I', prefix, location + 12)[0]
            struct.pack_into('<I', prefix, location + 12, value ^ 1)
        candidate = fixture_ad_hoc_replacement(self.original, edit_prefix=edit)
        with self.assertRaisesRegex(ValueError, 'nonsignature LINKEDIT'):
            signing.executable_preservation(self.original, candidate)

    def test_unnecessary_virtual_range_growth_is_refused(self):
        def edit(prefix, old, index):
            struct.pack_into('<Q', prefix, old['linkedit']['command_offset'] + 32,
                             old['linkedit']['vmsize'] + 16384)
        candidate = fixture_ad_hoc_replacement(self.original, edit_prefix=edit)
        with self.assertRaisesRegex(ValueError, 'virtual allocation'):
            signing.executable_preservation(self.original, candidate)

    def test_signature_dataoff_movement_is_not_a_general_padding_exemption(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        binary = bytearray(candidate[signing.EXECUTABLE])
        value = signing.read_macho(candidate[signing.EXECUTABLE], candidate,
                           previous_slices=signing.read_macho(self.original[signing.EXECUTABLE], self.original))[0]
        at = value['offset'] + value['signature']['command_offset'] + 8
        struct.pack_into('<I', binary, at, value['signature']['dataoff'] + 16)
        candidate[signing.EXECUTABLE] = bytes(binary)
        with self.assertRaisesRegex(ValueError, 'terminal signing allocation'):
            signing.executable_preservation(self.original, candidate)

    def test_nonzero_fat_padding_is_refused(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        value = bytearray(candidate[signing.EXECUTABLE]);value[100] = 1
        candidate[signing.EXECUTABLE] = bytes(value)
        with self.assertRaisesRegex(ValueError, 'padding'):
            signing.executable_preservation(self.original, candidate)

    def test_extra_alignment_size_zero_fat_gap_is_refused(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        value = candidate[signing.EXECUTABLE]
        second = struct.unpack_from('>IIIII', value, 28)
        offset = second[2]
        binary = bytearray(value[:offset] + bytes(16384) + value[offset:])
        struct.pack_into('>I', binary, 36, offset + 16384)
        candidate[signing.EXECUTABLE] = bytes(binary)
        with self.assertRaisesRegex(ValueError, 'alignment'):
            signing.executable_preservation(self.original, candidate)

    def test_changed_architecture_or_unexpected_third_slice_is_refused(self):
        for replacement in [3, 1]:
            value = bytearray(self.original[signing.EXECUTABLE])
            struct.pack_into('>I', value, 4, replacement)
            with self.assertRaisesRegex(ValueError, 'two-architecture'):
                signing.read_macho(bytes(value), self.original)

    def test_entitlement_slot_cannot_replace_the_empty_cms_slot(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        values = signing.read_macho(candidate[signing.EXECUTABLE], candidate,
                           previous_slices=signing.read_macho(self.original[signing.EXECUTABLE], self.original))
        binary = bytearray(candidate[signing.EXECUTABLE])
        for old in values:
            at = old['offset'] + old['signature']['dataoff'] + 12 + 16
            struct.pack_into('>I', binary, at, 5)
        candidate[signing.EXECUTABLE] = bytes(binary)
        with self.assertRaisesRegex(ValueError, 'entitlements'):
            signing.executable_preservation(self.original, candidate)

    def test_signing_identifier_cannot_change(self):
        def edit(directory, old, index):
            location = struct.unpack_from('>I', directory, 20)[0]
            directory[location] = ord('X')
        candidate = fixture_ad_hoc_replacement(self.original, edit_directory=edit)
        with self.assertRaisesRegex(ValueError, 'identifier'):
            signing.executable_preservation(self.original, candidate)

    def test_ordinary_resource_or_unknown_payload_is_refused_before_any_signer(self):
        for relative in ['Headers/AmplitudeCore-Swift.h', 'Unexpected.dat']:
            target = self.target / relative
            prior = target.read_bytes() if target.exists() else None
            target.write_bytes(b'changed')
            with self.assertRaises(ValueError):
                self.prepare()
            self.assertEqual(self.commands, [])
            if prior is None:
                target.unlink()
            else:
                target.write_bytes(prior)

    def test_missing_original_product_is_refused_before_any_signer(self):
        shutil.rmtree(self.source)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.commands, [])

    def test_symbolic_export_root_is_refused_before_any_signer(self):
        actual = self.target.with_name('retained')
        self.target.rename(actual)
        self.target.symlink_to(actual, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'real directory'):
            self.prepare()
        self.assertEqual(self.commands, [])

    def test_another_package_revision_cannot_get_the_exception(self):
        path = self.root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
        package = json.loads(path.read_bytes())
        item = next(item for item in package['pins'] if item['identity'] == 'amplitudecore-swift')
        item['state']['revision'] = '0' * 40
        path.write_text(json.dumps(package))
        with self.assertRaisesRegex(ValueError, 'package revision'):
            self.prepare()
        self.assertEqual(self.commands, [])

    def test_device_platform_cannot_get_the_simulator_exception(self):
        data = plistlib.loads(self.original['Info.plist'])
        data['CFBundleSupportedPlatforms'] = ['iPhoneOS']
        (self.target / 'Info.plist').write_bytes(plistlib.dumps(data))
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual(self.commands, [])

    def test_pipeline_retains_actual_payloads_and_signs_only_owned_export(self):
        proof = self.prepare()
        self.assertEqual(proof['status'], 'PASS_CONSTRAINED_SIMULATOR_EXPORT_SIGNATURE')
        self.assertEqual(proof['upstream_signature'], 'INVALID_MISSING_SEALED_MEMBERS')
        self.assertEqual(proof['consumer_qualification'], 'NOT_GRANTED')
        self.assertEqual([row[0] for row in self.commands], [
            'amplitude-original-strict-signature', 'amplitude-export-before-strict-signature',
            'amplitude-export-adhoc-sign', 'amplitude-export-after-strict-signature'])
        signed = self.commands[2]
        self.assertEqual(signed[1], ['codesign', '--force', '--sign', '-', '--timestamp=none', str(self.target)])
        self.assertEqual([row[2] for row in self.commands], [30, 30, 30, 30])
        for name in self.original:
            self.assertEqual((self.source / name).read_bytes(), self.original[name])
            self.assertEqual((self.evidence / proof['retained_original'] / name).read_bytes(), self.original[name])
            self.assertEqual((self.evidence / proof['retained_export_before'] / name).read_bytes(), self.original[name])
            self.assertEqual((self.evidence / proof['retained_export_after'] / name).read_bytes(),
                             (self.target / name).read_bytes())

    def test_unexpected_upstream_signature_success_never_signs(self):
        self.pre_verification_succeeds = True
        with self.assertRaisesRegex(ValueError, 'unexpectedly passed'):
            self.prepare()
        self.assertEqual(len(self.commands), 1)

    def test_different_native_preverification_failure_never_signs(self):
        self.wrong_error = True
        with self.assertRaisesRegex(ValueError, 'was not observed'):
            self.prepare()
        self.assertEqual(len(self.commands), 1)

    def test_native_signer_timeout_cannot_produce_qualification(self):
        self.failure = 'amplitude-export-adhoc-sign'
        with self.assertRaises(subprocess.TimeoutExpired):
            self.prepare()
        receipt = json.loads((self.evidence / 'amplitude-simulator-signing.json').read_bytes())
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['native_post_signature'], 'NOT_RUN')
        self.assertEqual(len(self.commands), 3)

    def test_post_sign_resource_mutation_is_refused_without_native_credit(self):
        def altered():
            value = fixture_ad_hoc_replacement(self.original)
            value['Headers/AmplitudeCore-Swift.h'] += b'corruption'
            return value
        self.signer = altered
        with self.assertRaisesRegex(ValueError, 'ordinary resources'):
            self.prepare()
        self.assertEqual(len(self.commands), 3)

    def test_post_sign_executable_mutation_with_valid_page_hashes_is_refused(self):
        def edit(prefix, old, index):
            prefix[8192] ^= 1
        self.signer = lambda: fixture_ad_hoc_replacement(self.original, edit_prefix=edit)
        with self.assertRaisesRegex(ValueError, 'nonsignature LINKEDIT'):
            self.prepare()
        self.assertEqual(len(self.commands), 3)

    def test_actual_post_sign_strict_failure_remains_failure(self):
        self.failure = 'amplitude-export-after-strict-signature'
        with self.assertRaises(subprocess.TimeoutExpired):
            self.prepare()
        receipt = json.loads((self.evidence / 'amplitude-simulator-signing.json').read_bytes())
        self.assertEqual(receipt['status'], 'FAIL')
        self.assertEqual(receipt['native_post_signature'], 'NOT_RUN')

    def test_original_source_change_during_verification_is_refused(self):
        self.mutate_source_after = True
        with self.assertRaisesRegex(ValueError, 'changed the verified input'):
            self.prepare()
        receipt = json.loads((self.evidence / 'amplitude-simulator-signing.json').read_bytes())
        self.assertEqual(receipt['status'], 'FAIL')

    def test_existing_packager_retains_complete_signing_attachments(self):
        proof = self.prepare()
        packager = ROOT / 'Tools/PinkhaNativeDerived/package_evidence.py'
        result = subprocess.run([__import__('sys').executable, str(packager), str(self.evidence)],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        with zipfile.ZipFile(self.evidence / 'Pinkha-Native-Derived-Evidence.zip') as archive:
            self.assertIsNone(archive.testzip())
            for key in ['retained_original', 'retained_export_before', 'retained_export_after']:
                for relative in self.original:
                    name = proof[key] + '/' + relative
                    self.assertEqual(archive.read(name), (self.evidence / name).read_bytes())

    def test_native_shape_preserves_exact_residue_and_architecture_pages(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        proof = signing.executable_preservation(self.original, candidate)
        self.assertEqual([row['after']['signature_proof']['page_exponent'] for row in proof], [12, 14])
        self.assertEqual([row['after']['signature_proof']['code_pages'] for row in proof], [72, 19])
        parsed = signing.read_macho(candidate[signing.EXECUTABLE], candidate,
                                   previous_slices=signing.read_macho(self.original[signing.EXECUTABLE], self.original))
        originals = signing.read_macho(self.original[signing.EXECUTABLE], self.original)
        for index, (old, new) in enumerate(zip(originals, parsed)):
            start = new['signature']['dataoff'] + new['signature_proof']['superblob_bytes']
            stop = new['signature']['dataoff'] + new['signature']['datasize']
            self.assertEqual(stop - start, 18)
            self.assertEqual(new['thin'][start:stop], old['thin'][start:stop])
            self.assertEqual(any(new['thin'][start:stop]), index == 1)

    def test_one_changed_residue_byte_is_refused_on_either_architecture(self):
        for index in (0, 1):
            with self.subTest(index=index):
                candidate = fixture_ad_hoc_replacement(self.original)
                binary = bytearray(candidate[signing.EXECUTABLE])
                _, _, offset, size, _ = struct.unpack_from('>IIIII', binary, 8 + index * 20)
                binary[offset + size - 1] ^= 1
                candidate[signing.EXECUTABLE] = bytes(binary)
                with self.assertRaisesRegex(ValueError, 'exact preimage'):
                    signing.executable_preservation(self.original, candidate)

    def test_zeroing_the_nonzero_prior_arm_residue_is_not_an_exemption(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        binary = bytearray(candidate[signing.EXECUTABLE])
        _, _, offset, size, _ = struct.unpack_from('>IIIII', binary, 28)
        self.assertTrue(any(binary[offset + size - 18:offset + size]))
        binary[offset + size - 18:offset + size] = bytes(18)
        candidate[signing.EXECUTABLE] = bytes(binary)
        with self.assertRaisesRegex(ValueError, 'exact preimage'):
            signing.executable_preservation(self.original, candidate)

    def test_slack_must_fit_inside_the_parsed_original_allocation(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        original = signing.read_macho(self.original[signing.EXECUTABLE], self.original)
        _, _, _, size, _ = struct.unpack_from('>IIIII', candidate[signing.EXECUTABLE], 28)
        original[1] = dict(original[1], thin=original[1]['thin'][:size - 1])
        with self.assertRaisesRegex(ValueError, 'exact preimage'):
            signing.read_macho(candidate[signing.EXECUTABLE], candidate, previous_slices=original)

    def test_other_page_policy_is_refused_even_when_its_page_hashes_match(self):
        originals = signing.read_macho(self.original[signing.EXECUTABLE], self.original)
        for exponents, index in (((12, 12), 1), ((14, 14), 0)):
            with self.subTest(exponents=exponents):
                candidate = fixture_ad_hoc_replacement(self.original, page_exponents=exponents)
                binary = candidate[signing.EXECUTABLE]
                _, _, offset, size, _ = struct.unpack_from('>IIIII', binary, 8 + index * 20)
                thin = binary[offset:offset + size]
                old = originals[index]
                start, extent = struct.unpack_from('<II', thin, old['signature']['command_offset'] + 8)
                valid_hashes = signing.read_signature(
                    thin, start, extent, candidate, previous_thin=old['thin'], expected_page=exponents[index])
                self.assertEqual(valid_hashes['page_exponent'], exponents[index])
                with self.assertRaisesRegex(ValueError, 'signing semantics'):
                    signing.executable_preservation(self.original, candidate)

    def test_changed_native_code_page_hash_is_refused(self):
        def alter(directory, old, index):
            hashes = struct.unpack_from('>I', directory, 16)[0]
            directory[hashes] ^= 1
        candidate = fixture_ad_hoc_replacement(self.original, edit_directory=alter)
        with self.assertRaisesRegex(ValueError, 'Executable signing page hash'):
            signing.executable_preservation(self.original, candidate)

    def test_changed_native_special_hash_is_refused(self):
        def alter(directory, old, index):
            hashes = struct.unpack_from('>I', directory, 16)[0]
            directory[hashes - 32] ^= 1
        candidate = fixture_ad_hoc_replacement(self.original, edit_directory=alter)
        with self.assertRaisesRegex(ValueError, 'Special signing slot'):
            signing.executable_preservation(self.original, candidate)

    def test_old_x86_four_kib_rounding_is_refused_after_rehashing(self):
        def alter(prefix, old, index):
            if index == 0:
                filesize = struct.unpack_from('<Q', prefix, old['linkedit']['command_offset'] + 48)[0]
                struct.pack_into('<Q', prefix, old['linkedit']['command_offset'] + 32,
                                 (filesize + 4095) // 4096 * 4096)
        candidate = fixture_ad_hoc_replacement(self.original, edit_prefix=alter)
        with self.assertRaisesRegex(ValueError, 'virtual allocation'):
            signing.executable_preservation(self.original, candidate)

    def test_rehashed_linkedit_overlap_with_an_original_segment_is_refused(self):
        def alter(prefix, old, index):
            prior_ends = []
            for command, length, at in old['commands']:
                if command == 0x19 and at != old['linkedit']['command_offset']:
                    address, extent = struct.unpack_from('<QQ', prefix, at + 24)
                    if extent:
                        prior_ends.append(address + extent)
            self.assertTrue(prior_ends)
            overlapping_address = max(prior_ends) - 1
            self.assertLess(overlapping_address, old['linkedit']['vmaddr'])
            struct.pack_into('<Q', prefix, old['linkedit']['command_offset'] + 24, overlapping_address)
        candidate = fixture_ad_hoc_replacement(self.original, edit_prefix=alter)
        with self.assertRaisesRegex(ValueError, 'LINKEDIT address changed'):
            signing.executable_preservation(self.original, candidate)

    def test_payload_after_the_terminal_fat_allocation_is_refused(self):
        candidate = fixture_ad_hoc_replacement(self.original)
        candidate[signing.EXECUTABLE] += bytes(16)
        with self.assertRaisesRegex(ValueError, 'trailing FAT'):
            signing.executable_preservation(self.original, candidate)

    def test_unaligned_native_signing_allocation_is_refused(self):
        candidate = fixture_ad_hoc_replacement(self.original, delta=1)
        with self.assertRaisesRegex(ValueError, 'allocation alignment'):
            signing.executable_preservation(self.original, candidate)


class OriginalSigningDriverFlowControls(unittest.TestCase):
    def run_flow(self, fail_other=False, corrupt_signer=False):
        case = original_flow.OriginalDriverFlowControls('test_one_notice_preserves_selected_simulator_for_both_original_build_commands')
        # The shared original driver is invoked manually by this new test;
        # keep its retained trace under this actual test's unique identity.
        case._testMethodName = self._testMethodName
        case.setUp()
        self.addCleanup(case.doCleanups)
        files = original_files()
        produce = case.produce_framework_fixture
        original_command = case.command
        package_path = 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
        (case.root / package_path).write_bytes((ROOT / package_path).read_bytes())
        def produce_with_real_amplitude():
            produce()
            destination = case.work / 'producer-derived/Build/Products/Debug-Anytype-iphonesimulator' / signing.NAME
            put_framework(destination, files)
        def command(args, root, evidence, name, timeout):
            if name.startswith('amplitude-'):
                case.events.append({'name': name, 'command': list(args), 'timeout_seconds': timeout})
                if name.endswith('before-strict-signature') or name == 'amplitude-original-strict-signature':
                    stderr = b'EXPLICIT_NATIVE_TOOL_DOUBLE: a sealed resource is missing or invalid\n'
                    (evidence / (name + '.stdout.log')).write_bytes(b'')
                    (evidence / (name + '.stderr.log')).write_bytes(stderr)
                    driver.write(evidence / (name + '.command.json'), {
                        'command': list(args), 'returncode': 1, 'timed_out': False,
                        'timeout_seconds': timeout, 'stdout_sha256': signing.digest(b''),
                        'stderr_sha256': signing.digest(stderr)})
                    raise ValueError('Actual command failed: ' + name)
                if name == 'amplitude-export-adhoc-sign':
                    updated = fixture_ad_hoc_replacement(files)
                    if corrupt_signer:
                        updated['Headers/AmplitudeCore-Swift.h'] = b'bad'
                    for relative, value in updated.items():
                        (Path(args[-1]) / relative).write_bytes(value)
                return ''
            return original_command(args, root, evidence, name, timeout)
        case.produce_framework_fixture = produce_with_real_amplitude
        case.command = command
        if fail_other:
            case.failure = 'framework-signature-1'
        with patch.object(signing.platform, 'system', return_value='Darwin'):
            case.run_driver()
        return case

    def test_whole_driver_keeps_strict_gate_and_exact_transformed_consumer_inputs(self):
        case = self.run_flow()
        names = case.names()
        self.assertLess(names.index('amplitude-export-after-strict-signature'), names.index('framework-signature-0'))
        self.assertLess(names.index('framework-signature-0'), names.index('external-consumer-build'))
        self.assertEqual(case.receipt['external_consumer_build'], 'PASS')
        self.assertEqual(case.receipt['status'], 'FAIL')
        self.assertIn('Synthetic control stops before real installation', case.receipt['error'])
        proof = json.loads((case.evidence / 'framework-distribution.json').read_bytes())
        before = json.loads((case.evidence / 'framework-distribution-before-simulator-signing.json').read_bytes())
        # Clang declarations are exported after signing. Require that exact
        # fixture addition while still checking every pre-signing file below.
        clang_additions = {
            'Clang/Packages/EXPLICIT_DECLARATION_FIXTURE/include/EXPLICIT.h',
            'Clang/Packages/EXPLICIT_DECLARATION_FIXTURE/include/module.modulemap',
            'SourceProvenance/ClangImportContext.json',
        }
        self.assertEqual(set(proof['files']), set(before['files']) | clang_additions)
        self.assertEqual({p for p in before['files'] if proof['files'][p] != before['files'][p]},
                         {'Frameworks/AmplitudeCore.framework/AmplitudeCore',
                          'Frameworks/AmplitudeCore.framework/_CodeSignature/CodeResources'})
        self.assertEqual(proof['simulator_signing_transformations'][0]['consumer_qualification'], 'NOT_GRANTED')

    def test_other_framework_signature_failure_still_blocks_consumer_and_boot(self):
        case = self.run_flow(fail_other=True)
        self.assertIn('amplitude-export-after-strict-signature', case.names())
        self.assertNotIn('external-consumer-build', case.names())
        self.assertNotIn('boot-owned-simulator', case.names())
        self.assertEqual(case.receipt['external_consumer_build'], 'NOT_RUN')

    def test_corrupt_signer_stops_original_driver_before_strict_gate_or_consumer(self):
        case = self.run_flow(corrupt_signer=True)
        self.assertNotIn('framework-signature-0', case.names())
        self.assertNotIn('external-consumer-build', case.names())
        self.assertEqual(case.receipt['external_consumer_build'], 'NOT_RUN')

    def test_failed_signing_retains_full_after_inventory_without_qualification(self):
        case = self.run_flow(corrupt_signer=True)
        before = json.loads((case.evidence / 'framework-distribution-before-simulator-signing.json').read_bytes())
        observed = json.loads((case.evidence / 'framework-distribution-after-failed-signing.json').read_bytes())
        self.assertEqual(observed['status'], 'OBSERVED_ONLY_NOT_QUALIFIED')
        self.assertEqual(set(observed['files']), set(before['files']))
        path = 'Frameworks/AmplitudeCore.framework/Headers/AmplitudeCore-Swift.h'
        self.assertNotEqual(observed['files'][path], before['files'][path])
        self.assertEqual(case.receipt['status'], 'FAIL')
        self.assertNotIn('framework-signature-0', case.names())
        self.assertNotIn('external-consumer-build', case.names())
        self.assertNotIn('boot-owned-simulator', case.names())


if __name__ == '__main__':
    unittest.main()
