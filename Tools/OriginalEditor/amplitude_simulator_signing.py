"""Constrained ad-hoc signing of one checksum-pinned Simulator export.

This never repairs the upstream archive or grants it a valid upstream signature.
All ordinary resources and every executable byte outside the documented signing
allocation fields/envelope remain exact. The normal strict consumer gates follow.
"""
import hashlib
import json
import plistlib
import platform
from pathlib import Path
import shutil
import stat
import struct
import sys

from framework_products import framework_closure
from framework_profile import sha256
from pbx_source import require

HERE = Path(__file__).resolve().parent
PROFILE = HERE / 'amplitude_simulator_signing.json'
NAME = 'AmplitudeCore.framework'
EXECUTABLE = 'AmplitudeCore'
MISSING = {
    'Modules/AmplitudeCore.swiftmodule/arm64-apple-ios-simulator.swiftmodule',
    'Modules/AmplitudeCore.swiftmodule/x86_64-apple-ios-simulator.swiftmodule',
}
ARCHITECTURES = [(0x01000007, 3, 14, 12, 292784),
                 (0x0100000c, 0, 14, 14, 307792)]

def digest(data):
    return hashlib.sha256(data).hexdigest()

def read_profile():
    value = json.loads(PROFILE.read_bytes())
    require(value.get('schema') == 1 and value.get('framework') == NAME
            and value.get('executable') == EXECUTABLE
            and value.get('package_identity') == 'amplitudecore-swift'
            and value.get('package_revision') == '13fd0eb0aa080816ffa409669758b2e8787322b2'
            and value.get('archive_sha256') == '2c0fbe60170efdf0b634ae73298803880098e1d352c9afef2baface15b45070c'
            and set(value.get('missing_sealed_members', [])) == MISSING
            and len(value.get('files', {})) == 13, 'Unreviewed Simulator signing profile')
    return value

def seal_members(files, expected_missing):
    seal = plistlib.loads(files['_CodeSignature/CodeResources'])
    missing, present, covered = set(), 0, set()
    require(isinstance(seal.get('files2'), dict), 'Missing modern resource seal')
    for table in ('files', 'files2'):
        for name, record in seal.get(table, {}).items():
            require(isinstance(name, str) and not Path(name).is_absolute()
                    and '..' not in Path(name).parts, 'Unsafe resource seal name')
            item = record if isinstance(record, dict) else {'hash': record}
            if name not in files:
                require(item.get('optional') is not True, 'Unexpected optional missing sealed member')
                missing.add(name)
                continue
            require('symlink' not in item, 'Unexpected symbolic resource seal')
            for field, algorithm in [('hash', 'sha1'), ('hash2', 'sha256')]:
                if field in item:
                    require(hashlib.new(algorithm, files[name]).digest() == item[field],
                            'Resource seal digest differs: ' + name)
                    present += 1
                    covered.add(name)
    require(missing == set(expected_missing), 'Wrong missing sealed resource set')
    required = set(files) - {EXECUTABLE, '_CodeSignature/CodeResources', 'Info.plist'}
    require(required <= covered, 'An ordinary framework resource is not sealed')
    return {'missing': sorted(missing), 'present_digests': present}

def pinned_closure(path, profile):
    path = Path(path)
    observed = framework_closure(path)
    expected_files = set(profile['files'])
    expected_dirs = {'.'}
    for name in expected_files:
        expected_dirs.update(parent.as_posix() for parent in Path(name).parents
                             if parent.as_posix() != '.')
    require(set(observed) == expected_files | expected_dirs,
            'Pinned framework closure has missing or extra members')
    require(all(row['kind'] == ('file' if name in expected_files else 'directory')
                for name, row in observed.items()), 'Pinned framework aliases or special files are forbidden')
    files = {}
    for name, expected in profile['files'].items():
        data = (path / name).read_bytes()
        row = observed[name]
        require(len(data) == expected['bytes'] and digest(data) == expected['sha256']
                and row['mode'] == expected['mode'], 'Pinned original framework bytes or mode differ: ' + name)
        files[name] = data
    info = plistlib.loads(files['Info.plist'])
    require(info.get('CFBundleExecutable') == EXECUTABLE
            and info.get('CFBundleIdentifier') == EXECUTABLE
            and info.get('CFBundlePackageType') == 'FMWK'
            and info.get('CFBundleSupportedPlatforms') == ['iPhoneSimulator']
            and info.get('DTPlatformName') == 'iphonesimulator',
            'This signing boundary is limited to the exact iOS Simulator product')
    seal_members(files, MISSING)
    read_macho(files[EXECUTABLE], files)
    return observed, files

def read_signature(thin, signature_offset, signature_size, files, *, previous_thin=None, expected_page=12):
    raw = thin[signature_offset:signature_offset + signature_size]
    require(len(raw) >= 12, 'Truncated signing envelope')
    magic, length, count = struct.unpack_from('>III', raw)
    require(magic == 0xfade0cc0 and 12 <= length <= len(raw)
            and count == 3 and 12 + 8 * count <= length,
            'Unexpected signing envelope shape')
    if previous_thin is None:
        require(not any(raw[length:]), 'Unexpected or nonzero signature allocation padding')
    else:
        # The actual modern allocator copies the original slice, resizes its
        # terminal signing allocation, and writes only the new SuperBlob.
        # Admit only the observed 18-byte slack, at its exact retained offset.
        end = signature_offset + signature_size
        require(signature_size % 16 == 0 and signature_size - length == 18,
                'Unexpected native signature allocation alignment or slack')
        require(end <= len(previous_thin)
                and raw[length:] == previous_thin[signature_offset + length:end],
                'Native signature allocation slack differs from the exact preimage')
    blobs, ranges = {}, []
    for index in range(count):
        slot, offset = struct.unpack_from('>II', raw, 12 + index * 8)
        require(slot not in blobs and 12 + 8 * count <= offset <= length - 8,
                'Malformed signing blob index')
        kind, size = struct.unpack_from('>II', raw, offset)
        require(size >= 8 and offset + size <= length, 'Malformed signing blob length')
        require(not any(offset < end and start < offset + size for start, end in ranges),
                'Overlapping signing blobs')
        ranges.append((offset, offset + size))
        blobs[slot] = raw[offset:offset + size]
    require(set(blobs) == {0, 2, 0x10000}, 'New entitlements or unexpected signature authority')
    require(blobs[2] == struct.pack('>III', 0xfade0c01, 12, 0)
            and blobs[0x10000] == struct.pack('>II', 0xfade0b01, 8),
            'Expected empty requirements and an empty ad-hoc CMS wrapper')
    directory = blobs[0]
    require(len(directory) >= 88 and struct.unpack_from('>I', directory)[0] == 0xfade0c02,
            'Missing original CodeDirectory shape')
    version, flags, hashes, identifier, special_count, code_count, code_limit = struct.unpack_from('>IIIIIII', directory, 8)
    hash_size, hash_type, platform, page = struct.unpack_from('>BBBB', directory, 36)
    require(version in {0x20400, 0x20500, 0x20600} and flags == 2
            and (hash_size, hash_type, platform, page) == (32, 2, 0, expected_page)
            and special_count == 3 and code_limit == signature_offset,
            'Ad-hoc signing semantics or executable code limit changed')
    require(struct.unpack_from('>I', directory, 44)[0] == 0
            and struct.unpack_from('>I', directory, 48)[0] == 0
            and struct.unpack_from('>Q', directory, 56)[0] in {0, code_limit},
            'Unexpected scatter, team or 64-bit code limit')
    require(88 <= identifier < len(directory)
            and directory[identifier:].split(bytes([0]), 1)[0] == EXECUTABLE.encode(),
            'Code signing identifier differs')
    page_bytes = 1 << expected_page
    require(code_count == (code_limit + page_bytes - 1) // page_bytes
            and hashes >= special_count * hash_size
            and hashes + code_count * hash_size <= len(directory),
            'Unexpected code-signing page coverage')
    for index in range(code_count):
        actual = hashlib.sha256(thin[index * page_bytes:min((index + 1) * page_bytes, code_limit)]).digest()
        require(directory[hashes + index * 32:hashes + (index + 1) * 32] == actual,
                'Executable signing page hash differs')
    for index, payload in [(1, files['Info.plist']), (2, blobs[2]), (3, files['_CodeSignature/CodeResources'])]:
        require(directory[hashes - index * 32:hashes - (index - 1) * 32] == hashlib.sha256(payload).digest(),
                'Special signing slot differs')
    return {'version': version, 'flags': flags, 'identifier': EXECUTABLE,
            'hash_type': hash_type, 'hash_size': hash_size, 'code_limit': code_limit,
            'code_pages': code_count, 'page_exponent': page, 'special_slots': special_count, 'entitlements': [],
            'superblob_bytes': length, 'allocated_signature_bytes': signature_size}

def read_macho(binary, files, *, previous_slices=None):
    require(len(binary) >= 48 and struct.unpack_from('>II', binary) == (0xcafebabe, 2),
            'Expected the exact two-architecture FAT32 executable')
    require(previous_slices is None or len(previous_slices) == 2, 'Missing original signing slices')
    slices, previous_end = [], 48
    for index, (cpu, subtype, alignment, vm_alignment, original_signature_offset) in enumerate(ARCHITECTURES):
        actual_cpu, actual_subtype, offset, size, actual_alignment = struct.unpack_from('>IIIII', binary, 8 + index * 20)
        require((actual_cpu, actual_subtype, actual_alignment) == (cpu, subtype, alignment)
                and offset == (previous_end + (1 << alignment) - 1) // (1 << alignment) * (1 << alignment)
                and 32 <= size <= len(binary) - offset
                and not any(binary[previous_end:offset]), 'FAT architecture, alignment or padding differs')
        thin = binary[offset:offset + size]
        magic, thin_cpu, thin_subtype, filetype, count, command_bytes, flags, reserved = struct.unpack_from('<IIIIIIII', thin)
        require((magic, thin_cpu, thin_subtype, filetype) == (0xfeedfacf, cpu, subtype, 6)
                and 0 < count <= 128 and 32 <= 32 + command_bytes <= len(thin),
                'Expected original little-endian MH_DYLIB header')
        cursor, commands, linkedit, signature, platform_commands = 32, [], None, None, []
        for _ in range(count):
            require(cursor + 8 <= 32 + command_bytes, 'Truncated load command')
            command, length = struct.unpack_from('<II', thin, cursor)
            require(length >= 8 and length % 8 == 0 and cursor + length <= 32 + command_bytes,
                    'Malformed load command')
            commands.append((command, length, cursor))
            if command == 0x19:
                require(length >= 72, 'Truncated segment command')
                name = thin[cursor + 8:cursor + 24].split(bytes([0]), 1)[0]
                vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<QQQQ', thin, cursor + 24)
                if name == b'__LINKEDIT':
                    require(linkedit is None and struct.unpack_from('<I', thin, cursor + 64)[0] == 0,
                            'Ambiguous or sectional LINKEDIT')
                    linkedit = {'command_offset': cursor, 'vmaddr': vmaddr, 'vmsize': vmsize,
                                'fileoff': fileoff, 'filesize': filesize}
            elif command == 0x1d:
                require(signature is None and length == 16, 'Ambiguous signature load command')
                dataoff, datasize = struct.unpack_from('<II', thin, cursor + 8)
                signature = {'command_offset': cursor, 'dataoff': dataoff, 'datasize': datasize}
            elif command in {0x25, 0x32}:
                platform_commands.append(thin[cursor:cursor + length])
            cursor += length
        require(cursor == 32 + command_bytes and linkedit is not None and signature is not None,
                'Incomplete original command closure')
        require(signature['dataoff'] == original_signature_offset
                and signature['datasize'] > 0
                and signature['dataoff'] + signature['datasize'] == len(thin)
                and linkedit['fileoff'] < signature['dataoff']
                and linkedit['fileoff'] + linkedit['filesize'] == len(thin)
                and linkedit['vmsize'] >= linkedit['filesize'],
                'Signature is not the exact terminal signing allocation')
        # x86 uses the original iOS minimum-version command; arm64 identifies
        # platform 7 (iOS Simulator) explicitly. Other load-command bytes are
        # compared in full below, including both original deployment values.
        require(len(platform_commands) == 1
                and ((cpu == 0x01000007 and struct.unpack_from('<I', platform_commands[0])[0] == 0x25)
                     or (cpu == 0x0100000c and struct.unpack_from('<II', platform_commands[0], 0)[0] == 0x32
                         and struct.unpack_from('<I', platform_commands[0], 8)[0] == 7)),
                'Original iOS Simulator platform command differs')
        prior = previous_slices[index] if previous_slices is not None else None
        if prior is not None:
            require((prior['cpu'], prior['subtype'], prior['signature']['dataoff'])
                    == (cpu, subtype, signature['dataoff']), 'Original signing slice identity differs')
        signature_proof = read_signature(
            thin, signature['dataoff'], signature['datasize'], files,
            previous_thin=prior['thin'] if prior is not None else None,
            expected_page=(14 if cpu == 0x0100000c else 12) if prior is not None else 12)
        slices.append({'cpu': cpu, 'subtype': subtype, 'offset': offset, 'size': size,
                       'fat_alignment': alignment, 'vm_alignment': vm_alignment,
                       'thin': thin, 'commands': commands, 'linkedit': linkedit,
                       'signature': signature, 'signature_proof': signature_proof})
        previous_end = offset + size
    require(previous_end == len(binary), 'Unexpected trailing FAT payload')
    return slices

def executable_preservation(before_files, after_files):
    before = read_macho(before_files[EXECUTABLE], before_files)
    after = read_macho(after_files[EXECUTABLE], after_files, previous_slices=before)
    proofs = []
    for old, new in zip(before, after):
        require(old['commands'] == new['commands'], 'Mach-O command shape changed')
        require(old['signature']['dataoff'] == new['signature']['dataoff'],
                'Signature movement or page-aligned string-table mutation is not admitted')
        old_link, new_link = old['linkedit'], new['linkedit']
        require(old_link['fileoff'] == new_link['fileoff'] and old_link['vmaddr'] == new_link['vmaddr'],
                'LINKEDIT address changed')
        require(new_link['filesize'] == len(new['thin']) - old_link['fileoff'],
                'LINKEDIT size is not exactly the new signature end')
        # Security's current codesign_alloc.cpp rounds both architectures to
        # 16 KiB, including shrinkage. This fixed export may not expand beyond
        # the original pinned LINKEDIT virtual range.
        expected_vm = (new_link['filesize'] + 16383) // 16384 * 16384
        require(new_link['vmsize'] == expected_vm
                and new_link['vmsize'] <= old_link['vmsize'],
                'Unexpected LINKEDIT virtual allocation')
        end = old['signature']['dataoff']
        left, right = bytearray(old['thin'][:end]), bytearray(new['thin'][:end])
        masks = [(old_link['command_offset'] + 32, 8),
                 (old_link['command_offset'] + 48, 8),
                 (old['signature']['command_offset'] + 12, 4)]
        for start, length in masks:
            left[start:start + length] = bytes(length)
            right[start:start + length] = bytes(length)
        require(left == right, 'Executable or nonsignature LINKEDIT bytes changed')
        proofs.append({'cpu': old['cpu'], 'subtype': old['subtype'],
                       'unchanged_signature_offset': end, 'masked_allocation_fields': masks,
                       'normalized_payload_sha256': digest(left),
                       'before': {k: v for k, v in old.items() if k not in {'thin', 'commands'}},
                       'after': {k: v for k, v in new.items() if k not in {'thin', 'commands'}}})
    return proofs

def retain_files(evidence, name, files):
    target = Path(evidence) / (name + '-attachments')
    require(not target.exists(), 'Refusing stale retained signing evidence')
    target.mkdir()
    for relative, data in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return target.name

def expected_original_failure(framework, root, evidence, name, command):
    arguments = ['codesign', '--verify', '--strict', '--verbose=4', str(framework)]
    try:
        command(arguments, root, evidence, name, 30)
    except ValueError as error:
        require(str(error) == 'Actual command failed: ' + name,
                'Unexpected verification failure boundary')
        receipt = json.loads((Path(evidence) / (name + '.command.json')).read_bytes())
        stderr = (Path(evidence) / (name + '.stderr.log')).read_bytes()
        stdout = (Path(evidence) / (name + '.stdout.log')).read_bytes()
        require(receipt.get('command') == arguments and receipt.get('returncode') == 1
                and receipt.get('timed_out') is False and receipt.get('timeout_seconds') == 30
                and receipt.get('stderr_sha256') == digest(stderr)
                and receipt.get('stdout_sha256') == digest(stdout)
                and b'a sealed resource is missing or invalid' in stderr,
                'The exact pinned upstream resource-seal failure was not observed')
        return receipt
    raise ValueError('The pinned upstream strict signature unexpectedly passed; no repair was authorized')

def prepare_amplitude_simulator_export(root, products, exported, evidence, command):
    require(platform.system() == 'Darwin', 'Native signing is limited to the actual Apple host')
    root, products, exported, evidence = map(Path, (root, products, exported, evidence))
    require(products.resolve().is_relative_to((root / 'build').resolve())
            and exported.resolve().is_relative_to((root / 'build').resolve())
            and evidence.resolve().is_relative_to((root / 'build').resolve()),
            'Simulator signing requires owned producer/export/evidence paths')
    require(products.resolve() != exported.resolve()
            and not products.resolve().is_relative_to(exported.resolve())
            and not exported.resolve().is_relative_to(products.resolve()),
            'The original producer must remain separate from the export')
    original, target = products / NAME, exported / 'Frameworks' / NAME
    require(original.resolve() != target.resolve(), 'Refusing to sign the original framework')
    profile = read_profile()
    package = json.loads((root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved').read_bytes())
    matching = [item for item in package['pins'] if item['identity'] == profile['package_identity']]
    require(len(matching) == 1 and matching[0]['state']['revision'] == profile['package_revision'],
            'The original locked package revision differs')
    source_metadata, source_files = pinned_closure(original, profile)
    before_metadata, before_files = pinned_closure(target, profile)
    require(source_files == before_files, 'Export differs from the exact pinned producer input')
    receipt = {'schema': 1, 'status': 'FAIL', 'scope': 'OWNED_SIMULATOR_EXPORT_ADHOC_TRANSFORMATION',
               'upstream_signature': 'INVALID_MISSING_SEALED_MEMBERS',
               'upstream_package_revision': profile['package_revision'],
               'upstream_archive_sha256': profile['archive_sha256'],
               'source': str(original), 'export': str(target),
               'missing_original_seal_members': sorted(MISSING),
               'before_source_metadata': source_metadata, 'before_export_metadata': before_metadata,
               'ordinary_resources_unchanged': False, 'nonsignature_executable_unchanged': False,
               'native_post_signature': 'NOT_RUN', 'consumer_qualification': 'NOT_GRANTED'}
    receipt['retained_original'] = retain_files(evidence, 'amplitude-original', source_files)
    receipt['retained_export_before'] = retain_files(evidence, 'amplitude-export-before', before_files)
    try:
        receipt['original_strict_failure'] = expected_original_failure(
            original, root, evidence, 'amplitude-original-strict-signature', command)
        receipt['export_strict_failure'] = expected_original_failure(
            target, root, evidence, 'amplitude-export-before-strict-signature', command)
        require(framework_closure(original) == source_metadata
                and framework_closure(target) == before_metadata,
                'Pinned inputs changed before signing')
        command(['codesign', '--force', '--sign', '-', '--timestamp=none', str(target)],
                root, evidence, 'amplitude-export-adhoc-sign', 30)
        after_metadata = framework_closure(target)
        require(set(after_metadata) == set(before_metadata), 'Signing changed framework membership')
        after_files = {}
        for relative, row in after_metadata.items():
            prior = before_metadata[relative]
            require(row['kind'] == prior['kind'] and row['resolved_kind'] == prior['resolved_kind']
                    and row['resolved_metadata'] == prior['resolved_metadata']
                    and all(row[key] == prior[key] for key in ['mode', 'uid', 'gid', 'flags', 'extended_attributes']),
                    'Signing changed non-content product metadata: ' + relative)
            if row['kind'] == 'file':
                after_files[relative] = (target / relative).read_bytes()
        receipt['retained_export_after'] = retain_files(evidence, 'amplitude-export-after', after_files)
        mutable = {EXECUTABLE, '_CodeSignature/CodeResources'}
        require(set(after_files) == set(before_files)
                and {name for name in after_files if after_files[name] != before_files[name]} == mutable,
                'Signing changed ordinary resources or did not replace exactly the signing content')
        receipt['resource_seal_after'] = seal_members(after_files, set())
        receipt['mach_o_preservation'] = executable_preservation(before_files, after_files)
        require(framework_closure(original) == source_metadata,
                'The original framework changed during export signing')
        command(['codesign', '--verify', '--strict', '--verbose=4', str(target)],
                root, evidence, 'amplitude-export-after-strict-signature', 30)
        require(framework_closure(target) == after_metadata
                and framework_closure(original) == source_metadata,
                'Signature verification changed the verified input closure')
        receipt.update(status='PASS_CONSTRAINED_SIMULATOR_EXPORT_SIGNATURE',
                       ordinary_resources_unchanged=True, nonsignature_executable_unchanged=True,
                       after_export_metadata=after_metadata, native_post_signature='PASS',
                       upstream_signature='INVALID_MISSING_SEALED_MEMBERS')
        return receipt
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        (Path(evidence) / 'amplitude-simulator-signing.json').write_text(
            json.dumps(receipt, indent=2, sort_keys=True) + '\n')
