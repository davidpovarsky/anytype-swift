"""Seal only the observed generated AnyCrypto SwiftPM Simulator export.

The producer is immutable. Native strict verification and every original
framework/consumer gate remain mandatory; this grants no editable API or runtime
qualification. Signing may alter only its terminal signature allocation and the
three allocation-size fields that describe it, plus the new resource seal.
"""
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import struct
import subprocess

from amplitude_simulator_signing import retain_files
from framework_products import framework_closure
from pbx_source import require

EXECUTABLE = 'AnyCryptoSwift_4B7B7B8889D5B5C4_PackageProduct'
NAME = EXECUTABLE + '.framework'
REVISION = '0d7429888f8ec60d1730341ff1122d5ddf0ff1ab'
SEAL = '_CodeSignature/CodeResources'


def diagnose_generated_package_exports(root, products, exported, evidence, frameworks, source_sha, command):
    """Read-only observation of all generated exports; never a qualification.

    The existing acceptance loop still verifies each framework independently.
    Bounded pre-sign byte attachments permit isolated packaging investigation
    without rebuilding the original application or publishing a consumer SDK.
    """
    root, products, exported, evidence = map(Path, (root, products, exported, evidence))
    rows, retained = [], 0
    report = {'schema': 1, 'status': 'OBSERVED_ONLY_NOT_QUALIFIED', 'source_sha': source_sha,
              'consumer_qualification': 'NOT_GRANTED', 'native_editor_ui_tests': 0,
              'retention_limit_bytes': 16 * 1024 * 1024, 'products': rows}
    try:
        for index, name in enumerate(sorted(n for n in frameworks if n.endswith('_PackageProduct.framework'))):
            original, target = products / 'PackageFrameworks' / name, exported / 'Frameworks' / name
            require(Path(name).name == name and original.resolve().is_relative_to(products.resolve())
                    and target.resolve().is_relative_to(exported.resolve()), 'Unowned package product diagnostic path')
            source_metadata, before = framework_closure(original), framework_closure(target)
            source_files = {p: (v['bytes'], v['sha256']) for p, v in source_metadata.items() if v['kind'] == 'file'}
            export_files = {p: (v['bytes'], v['sha256']) for p, v in before.items() if v['kind'] == 'file'}
            require(source_files == export_files, 'Diagnostic export differs from the actual original product')
            row = {'framework': name, 'original': str(original), 'export': str(target),
                   'before_export_metadata': before, 'before_source_metadata': source_metadata,
                   'resource_seal_present': SEAL in export_files, 'strict_status': 'NOT_RUN',
                   'signature_display_status': 'NOT_RUN', 'acceptance': 'NOT_GRANTED'}
            rows.append(row)
            size = sum(length for length, digest in export_files.values())
            if retained + size <= report['retention_limit_bytes']:
                row['retained_original_export'] = retain_files(evidence, 'package-product-' + str(index) + '-before',
                    {p: (target / p).read_bytes() for p in export_files})
                retained += size
            else:
                row['retained_original_export'] = 'NOT_RETAINED_SIZE_LIMIT; complete hashes remain recorded'
            for kind, args in [('strict', ['codesign', '--verify', '--strict', str(target)]),
                               ('signature_display', ['codesign', '--display', '--verbose=4', str(target)])]:
                label = 'package-product-' + str(index) + '-' + kind
                row[kind + '_evidence_prefix'] = label
                try:
                    command(args, root, evidence, label, 30)
                    row[kind + '_status'] = 'COMMAND_SUCCEEDED_OBSERVATION_ONLY'
                except (ValueError, subprocess.TimeoutExpired) as error:
                    row[kind + '_status'] = 'COMMAND_FAILED_OBSERVATION_ONLY'
                    row[kind + '_error'] = {'type': type(error).__name__, 'message': str(error)}
                require(framework_closure(original) == source_metadata and framework_closure(target) == before,
                        'Read-only signature diagnostics changed an original or exported product')
            row['original_and_export_unchanged'] = True
        return report
    finally:
        report['retained_bytes'] = retained
        (evidence / 'package-product-signature-diagnostics.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


def layout(binary, executable=EXECUTABLE):
    require(len(binary) >= 32, 'Truncated generated framework executable')
    magic, cpu, subtype, kind, count, size, flags, reserved = struct.unpack_from('<8I', binary)
    require((magic, cpu, subtype, kind) == (0xfeedfacf, 0x0100000c, 0, 6)
            and 0 < count <= 128 and 32 + size <= len(binary),
            'Only the original thin ARM64 dynamic framework is eligible')
    cursor, signature, linkedit, platforms, install_names, commands = 32, None, None, [], [], []
    for _ in range(count):
        require(cursor + 8 <= 32 + size, 'Truncated Mach-O load command')
        code, length = struct.unpack_from('<II', binary, cursor)
        require(length >= 8 and length % 8 == 0 and cursor + length <= 32 + size,
                'Malformed Mach-O load command')
        commands.append((code, length, cursor))
        if code == 0x19:
            require(length >= 72, 'Truncated segment command')
            if binary[cursor + 8:cursor + 24].split(b'\0', 1)[0] == b'__LINKEDIT':
                require(linkedit is None and struct.unpack_from('<I', binary, cursor + 64)[0] == 0,
                        'Ambiguous or sectional LINKEDIT')
                vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<4Q', binary, cursor + 24)
                linkedit = dict(command=cursor, vmaddr=vmaddr, vmsize=vmsize, fileoff=fileoff, filesize=filesize)
        elif code == 0x1d:
            require(signature is None and length == 16, 'Ambiguous signing command')
            offset, allocated = struct.unpack_from('<II', binary, cursor + 8)
            signature = dict(command=cursor, offset=offset, allocated=allocated)
        elif code in {0x24, 0x25, 0x2f, 0x30, 0x32}:
            require(code == 0x32 and length >= 24, 'Legacy or non-Simulator platform is ineligible')
            platforms.append(struct.unpack_from('<I', binary, cursor + 8)[0])
        elif code == 0xd:
            require(length >= 24, 'Truncated install-name command')
            start = struct.unpack_from('<I', binary, cursor + 8)[0]
            require(24 <= start < length, 'Malformed install name')
            install_names.append(binary[cursor + start:cursor + length].split(b'\0', 1)[0])
        cursor += length
    require(cursor == 32 + size and platforms == [7]
            and install_names == [('@rpath/' + executable + '.framework/' + executable).encode()]
            and linkedit is not None and signature is not None,
            'Generated product identity or Simulator command closure differs')
    require(32 + size <= linkedit['fileoff'] < signature['offset']
            and signature['allocated'] > 0
            and signature['offset'] + signature['allocated'] == len(binary)
            and linkedit['fileoff'] + linkedit['filesize'] == len(binary)
            and linkedit['vmsize'] >= linkedit['filesize'],
            'Signing allocation is not the terminal LINKEDIT allocation')
    return dict(signature=signature, linkedit=linkedit, commands=commands)


def executable_preservation(before, after, executable=EXECUTABLE):
    old, new = layout(before, executable), layout(after, executable)
    require(old['commands'] == new['commands']
            and old['signature']['offset'] == new['signature']['offset'],
            'Signing changed command layout or moved the original signature')
    left, right = old['linkedit'], new['linkedit']
    require(left['fileoff'] == right['fileoff'] and left['vmaddr'] == right['vmaddr']
            and right['vmsize'] == (right['filesize'] + 16383) // 16384 * 16384,
            'Signing changed LINKEDIT placement or native allocation rounding')
    end = old['signature']['offset']
    original, signed = bytearray(before[:end]), bytearray(after[:end])
    masks = [(left['command'] + 32, 8), (left['command'] + 48, 8),
             (old['signature']['command'] + 12, 4)]
    for offset, size in masks:
        original[offset:offset + size] = signed[offset:offset + size] = bytes(size)
    require(original == signed, 'Signing changed executable or nonsignature LINKEDIT bytes')
    raw = after[end:]
    require(len(raw) >= 12, 'Truncated new signing envelope')
    magic, length, count = struct.unpack_from('>III', raw)
    require(magic == 0xfade0cc0 and 12 <= length <= len(raw)
            and count == 3 and 12 + 8 * count <= length
            and len(raw) % 16 == 0 and 0 <= len(raw) - length <= 31,
            'Unexpected native ad-hoc signing envelope')
    prior_slack = before[end + length:end + len(raw)]
    require(raw[length:] == prior_slack + bytes(len(raw) - length - len(prior_slack)),
            'New signing slack differs from retained or zero-extended original bytes')
    slots, intervals = {}, []
    for index in range(count):
        slot, offset = struct.unpack_from('>II', raw, 12 + index * 8)
        require(slot not in slots and 12 + 8 * count <= offset <= length - 8,
                'Malformed native signing index')
        kind, size = struct.unpack_from('>II', raw, offset)
        require(size >= 8 and offset + size <= length
                and not any(offset < b and a < offset + size for a, b in intervals),
                'Malformed or overlapping signing subblob')
        intervals.append((offset, offset + size))
        slots[slot] = raw[offset:offset + size]
    require(set(slots) == {0, 2, 0x10000}
            and slots[2] == struct.pack('>III', 0xfade0c01, 12, 0)
            and slots[0x10000] == struct.pack('>II', 0xfade0b01, 8),
            'New authority or entitlements are not permitted')
    directory = slots[0]
    require(len(directory) >= 44 and struct.unpack_from('>I', directory)[0] == 0xfade0c02
            and struct.unpack_from('>I', directory, 12)[0] == 2
            and struct.unpack_from('>I', directory, 32)[0] == end,
            'Expected an ad-hoc CodeDirectory covering the original code prefix')
    return {'unchanged_signature_offset': end, 'masked_allocation_fields': masks,
            'normalized_payload_sha256': hashlib.sha256(original).hexdigest(),
            'before': old, 'after': new, 'native_strict_verification_required': True}


def observe(path, *, sealed=False):
    metadata = framework_closure(path)
    expected = {'.', EXECUTABLE, 'Info.plist'} | ({'_CodeSignature', SEAL} if sealed else set())
    require(set(metadata) == expected and all(row['kind'] ==
            ('directory' if name in {'.', '_CodeSignature'} else 'file')
            for name, row in metadata.items()), 'Unexpected generated framework members or aliases')
    files = {name: (path / name).read_bytes() for name, row in metadata.items() if row['kind'] == 'file'}
    info = plistlib.loads(files['Info.plist'])
    require(info.get('CFBundleExecutable') == EXECUTABLE and info.get('CFBundlePackageType') == 'FMWK'
            and info.get('CFBundleSupportedPlatforms') == ['iPhoneSimulator'],
            'Only the exact generated iOS Simulator product is eligible')
    layout(files[EXECUTABLE])
    return metadata, files


def expected_unsealed_failure(framework, root, evidence, name, command):
    arguments = ['codesign', '--verify', '--strict', str(framework)]
    try:
        command(arguments, root, evidence, name, 30)
    except ValueError:
        result = json.loads((evidence / (name + '.command.json')).read_bytes())
        message = (evidence / (name + '.stderr.log')).read_text().strip()
        require(result['command'] == arguments and result['returncode'] == 1
                and result['timed_out'] is False and message == str(framework)
                + ': code has no resources but signature indicates they must be present',
                'Only the observed missing generated resource seal is eligible')
        return result
    raise ValueError('Unexpected valid original signature; no export sealing is needed')


def prepare_anycrypto_simulator_export(root, products, exported, evidence, command):
    require(platform.system() == 'Darwin', 'Native export sealing requires an actual Apple host')
    root, products, exported, evidence = map(Path, (root, products, exported, evidence))
    build = (root / 'build').resolve()
    require(all(p.resolve().is_relative_to(build) for p in [products, exported, evidence])
            and products.resolve() != exported.resolve()
            and not products.resolve().is_relative_to(exported.resolve())
            and not exported.resolve().is_relative_to(products.resolve()), 'Unowned or overlapping export paths')
    original = products / 'PackageFrameworks' / NAME
    target = exported / 'Frameworks' / NAME
    require(not original.parent.is_symlink() and not target.parent.is_symlink()
            and original.resolve().is_relative_to(products.resolve())
            and target.resolve().is_relative_to(exported.resolve())
            and original.resolve() != target.resolve(), 'Refusing an aliased or original signing target')
    package = json.loads((root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_bytes())
    matching = [p for p in package['pins'] if p['identity'] == 'any-crypto-swift']
    require(len(matching) == 1 and matching[0]['state']['revision'] == REVISION,
            'Original AnyCrypto package revision differs')
    source_metadata, source_files = observe(original)
    before_metadata, before_files = observe(target)
    require(source_files == before_files, 'Export differs from the actual original producer')
    receipt = {'schema': 1, 'status': 'FAIL', 'scope': 'OWNED_ANYCRYPTO_SIMULATOR_EXPORT_SEAL',
               'source': str(original), 'export': str(target), 'package_revision': REVISION,
               'before_source_metadata': source_metadata, 'before_export_metadata': before_metadata,
               'native_post_signature': 'NOT_RUN', 'consumer_qualification': 'NOT_GRANTED',
               'editable_mount': 'NOT_EXPOSED', 'native_editor_ui_tests': 0}
    receipt['retained_original'] = retain_files(evidence, 'anycrypto-original', source_files)
    receipt['retained_export_before'] = retain_files(evidence, 'anycrypto-export-before', before_files)
    try:
        for label, path in [('original', original), ('export-before', target)]:
            receipt[label + '_strict_failure'] = expected_unsealed_failure(
                path, root, evidence, 'anycrypto-' + label + '-strict-signature', command)
        require(framework_closure(original) == source_metadata
                and framework_closure(target) == before_metadata, 'Inputs changed before export sealing')
        command(['codesign', '--force', '--sign', '-', '--timestamp=none', str(target)],
                root, evidence, 'anycrypto-export-adhoc-sign', 30)
        after_metadata, after_files = observe(target, sealed=True)
        require(after_files['Info.plist'] == before_files['Info.plist'], 'Original Info.plist bytes changed')
        for name, previous in before_metadata.items():
            actual = after_metadata[name]
            require({k: v for k, v in actual.items() if k not in {'bytes', 'sha256'}}
                    == {k: v for k, v in previous.items() if k not in {'bytes', 'sha256'}},
                    'Signing changed original filesystem metadata: ' + name)
        receipt['mach_o_preservation'] = executable_preservation(before_files[EXECUTABLE], after_files[EXECUTABLE])
        require(framework_closure(original) == source_metadata, 'Signing changed the original producer')
        command(['codesign', '--verify', '--strict', str(target)],
                root, evidence, 'anycrypto-export-after-strict-signature', 30)
        require(framework_closure(target) == after_metadata and framework_closure(original) == source_metadata,
                'Verification changed the original or exported input closure')
        receipt.update(status='PASS_CONSTRAINED_ANYCRYPTO_SIMULATOR_EXPORT_SIGNATURE',
                       native_post_signature='PASS', original_producer_unchanged=True,
                       original_info_unchanged=True, nonsignature_executable_unchanged=True)
        return receipt
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        retention_error = None
        try:
            observed = framework_closure(target)
            receipt['after_export_metadata'] = observed
            receipt['retained_export_after'] = retain_files(evidence, 'anycrypto-export-after',
                {name: (target / name).read_bytes() for name, row in observed.items() if row['kind'] == 'file'})
        except BaseException as observation_error:
            receipt['after_observation_error'] = {'type': type(observation_error).__name__,
                                                'message': str(observation_error)}
            if receipt['status'] != 'FAIL':
                receipt['status'] = 'FAIL'
                retention_error = observation_error
        (evidence / 'anycrypto-simulator-signing.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        if retention_error is not None:
            raise retention_error
