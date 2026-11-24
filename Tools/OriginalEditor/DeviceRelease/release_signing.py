"""Seal only newly owned Release exports, preserving all non-signature bytes."""
import hashlib
from pathlib import Path
import plistlib
import struct

from release_contract import require
from product_inventory import inventory


def thin_layout(raw, executable, platform_name):
    require(len(raw) >= 32, 'Truncated Release image')
    header = struct.unpack_from('<8I', raw)
    magic, cpu, subtype, kind, count, size, flags, reserved = header
    require((magic, cpu, subtype, kind) == (0xfeedfacf, 0x0100000c, 0, 6)
            and 0 < count <= 128 and 32 + size <= len(raw),
            'Expected a generated thin arm64 Release dynamic framework')
    cursor, signature, linkedit, platforms, names, commands = 32, None, None, [], [], []
    for _ in range(count):
        require(cursor + 8 <= 32 + size, 'Truncated Release load command')
        code, length = struct.unpack_from('<II', raw, cursor)
        require(length >= 8 and length % 8 == 0 and cursor + length <= 32 + size,
                'Invalid Release load command bounds')
        if code == 0x19:
            require(length >= 72, 'Truncated Release segment')
            if raw[cursor + 8:cursor + 24].split(b'\0', 1)[0] == b'__LINKEDIT':
                require(linkedit is None and struct.unpack_from('<I', raw, cursor + 64)[0] == 0,
                        'Ambiguous or sectional Release LINKEDIT')
                vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<4Q', raw, cursor + 24)
                linkedit = {'command': cursor, 'vmaddr': vmaddr, 'vmsize': vmsize,
                            'fileoff': fileoff, 'filesize': filesize}
        elif code == 0x1d:
            require(signature is None and length == 16, 'Ambiguous Release code signature')
            offset, allocated = struct.unpack_from('<II', raw, cursor + 8)
            signature = {'command': cursor, 'offset': offset, 'allocated': allocated}
        elif code in {0x24, 0x25, 0x2f, 0x30, 0x32}:
            require(code == 0x32 and length >= 24, 'Unreviewed Release build platform command')
            platforms.append(struct.unpack_from('<I', raw, cursor + 8)[0])
        elif code == 0xd:
            start = struct.unpack_from('<I', raw, cursor + 8)[0]
            require(length >= 24 and 24 <= start < length, 'Invalid Release install name')
            names.append(raw[cursor + start:cursor + length].split(b'\0', 1)[0])
        commands.append((code, length, cursor))
        cursor += length
    require(cursor == 32 + size and platforms == [7 if platform_name == 'iphonesimulator' else 2]
            and names == [('@rpath/' + executable + '.framework/' + executable).encode()]
            and linkedit is not None
            and linkedit['fileoff'] + linkedit['filesize'] == len(raw),
            'Release platform/install-name/LINKEDIT closure differs')
    if signature is not None:
        require(signature['allocated'] > 0 and signature['offset'] > linkedit['fileoff']
                and signature['offset'] + signature['allocated'] == len(raw),
                'Release signature is not a terminal allocation')
    return {'header': header, 'commands': commands, 'linkedit': linkedit, 'signature': signature}


def preserve_thin(before, after, executable, platform_name):
    old, new = thin_layout(before, executable, platform_name), thin_layout(after, executable, platform_name)
    require(new['signature'] is not None, 'Owned Release export is still unsigned')
    old_commands = [v for v in old['commands'] if v[0] != 0x1d]
    new_commands = [v for v in new['commands'] if v[0] != 0x1d]
    require(old_commands == new_commands, 'Release signing changed existing command positions')
    a, b = old['linkedit'], new['linkedit']
    require(a['command'] == b['command'] and a['fileoff'] == b['fileoff'] and a['vmaddr'] == b['vmaddr']
            and b['vmsize'] == (b['filesize'] + 16383) // 16384 * 16384,
            'Release signing changed LINKEDIT placement or allocation rounding')
    new_signature = new['signature']
    if old['signature']:
        require(old['commands'] == new['commands']
                and old['signature']['offset'] == new_signature['offset'],
                'Existing signature moved during Release signing')
        end = old['signature']['offset']
        masks = [(a['command'] + 32, 8), (a['command'] + 48, 8),
                 (old['signature']['command'] + 12, 4)]
        left, right = bytearray(before[:end]), bytearray(after[:end])
    else:
        # codesign may add exactly one command in pre-existing zero header
        # padding. No original load command, code, resource or linkedit data is
        # dropped; only terminal zero alignment before the new signature exists.
        command_offset = 32 + old['header'][5]
        require(new_signature['command'] == command_offset
                and new['commands'][-1] == (0x1d, 16, command_offset)
                and new['header'][4] == old['header'][4] + 1
                and new['header'][5] == old['header'][5] + 16
                and before[command_offset:command_offset + 16] == bytes(16)
                and new_signature['offset'] == (len(before) + 15) // 16 * 16,
                'New Release signature changed nonempty header/code storage')
        end = new_signature['offset']
        left = bytearray(before + bytes(end - len(before)))
        right = bytearray(after[:end])
        masks = [(16, 8), (a['command'] + 32, 8), (a['command'] + 48, 8), (command_offset, 16)]
    for offset, length in masks:
        left[offset:offset + length] = right[offset:offset + length] = bytes(length)
    require(left == right, 'Release signing modified original executable or nonsignature data')
    signature = after[end:]
    require(len(signature) >= 12 and struct.unpack_from('>I', signature)[0] == 0xfade0cc0,
            'Missing native code-signing SuperBlob')
    return {'status': 'ALL_NONSIGNATURE_BYTES_PRESERVED',
            'normalized_payload_sha256': hashlib.sha256(left).hexdigest(),
            'signature_offset': end, 'added_signature_command': old['signature'] is None,
            'masked_signature_allocation_fields': masks, 'before': old, 'after': new}


def seal_framework(root, exported, name, platform_name, evidence, command):
    from framework_products import framework_closure
    framework = exported / 'Frameworks' / name
    require(framework.is_dir() and not framework.is_symlink()
            and framework.resolve().is_relative_to(exported.resolve()), 'Unowned Release signature target')
    info = plistlib.loads((framework / 'Info.plist').read_bytes())
    executable = info['CFBundleExecutable']
    require(isinstance(executable, str) and Path(executable).name == executable, 'Invalid Release executable')
    before = inventory(framework)
    before_metadata = framework_closure(framework)
    before_bytes = {p: (framework / p).read_bytes() for p in before}
    label = 'release-seal-' + name.removesuffix('.framework')
    command(['codesign', '--force', '--sign', '-', '--timestamp=none', str(framework)],
            root, evidence, label, 60)
    command(['codesign', '--verify', '--strict', str(framework)], root, evidence, label + '-verify', 30)
    details = command(['codesign', '-d', '--verbose=4', str(framework)], root, evidence, label + '-identity', 30)
    # codesign diagnostic details normally go to stderr, retain and inspect both.
    details += (evidence / (label + '-identity.stderr.log')).read_text(errors='replace')
    require('Signature=adhoc' in details and 'Authority=' not in details,
            'Release prerequisite sealing acquired an unexpected signing authority')
    after = inventory(framework)
    after_metadata = framework_closure(framework)
    allowed = {executable, '_CodeSignature/CodeResources'}
    require(set(after) == set(before) | {'_CodeSignature/CodeResources'}
            and {p for p in before if before[p] != after[p]} <= allowed,
            'Release signing changed resource/module membership or bytes')
    require(set(after_metadata) <= set(before_metadata) | {'_CodeSignature', '_CodeSignature/CodeResources'},
            'Release signing added unowned filesystem members')
    for path, previous in before_metadata.items():
        require(path in after_metadata
                and {k: v for k, v in previous.items() if k not in {'bytes', 'sha256'}}
                == {k: v for k, v in after_metadata[path].items() if k not in {'bytes', 'sha256'}},
                'Release signing changed source permissions, aliases or extended attributes')
    raw_after = (framework / executable).read_bytes()
    if before_bytes[executable][:4] == bytes.fromhex('cafebabe'):
        require(name == 'AmplitudeCore.framework' and platform_name == 'iphonesimulator',
                'Unreviewed universal framework signing transform')
        from amplitude_simulator_signing import executable_preservation
        preservation = executable_preservation(before_bytes, {p: (framework / p).read_bytes() for p in after})
    else:
        preservation = preserve_thin(before_bytes[executable], raw_after, executable, platform_name)
    return {'status': 'OWNED_RELEASE_ADHOC_SEAL_VERIFIED_NO_DEVICE_ACCEPTANCE',
            'framework': name, 'platform': platform_name,
            'before': before, 'after': after, 'original_filesystem_metadata_preserved': True,
            'executable_preservation': preservation}
