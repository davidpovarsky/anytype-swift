"""Inspect Xcode's simulator Mach-O identity without changing its signature.

Layout: apple-oss-distributions/xnu EXTERNAL_HEADERS/mach-o/loader.h.
The actual Xcode27 link log puts Anytype.app-Simulated.xcent in this section;
codesign's device-style entitlements alone do not describe that carrier.
"""
import mmap
import plistlib
import struct

from validate_release import digest, require


def inspect_simulator_entitlements(data):
    require(len(data) >= 32 and data[:4] == b'\xcf\xfa\xed\xfe', 'Expected actual thin 64-bit simulator Mach-O')
    require(struct.unpack_from('<I', data, 4)[0] == 0x0100000c, 'Expected actual ARM64 simulator executable')
    commands, size = struct.unpack_from('<II', data, 16)
    end = 32 + size
    require(0 < commands <= 16384 and end <= len(data), 'Invalid Mach-O load command bounds')
    cursor = 32
    found = []
    builds = []
    for _ in range(commands):
        require(cursor + 8 <= end, 'Truncated Mach-O load command')
        command, length = struct.unpack_from('<II', data, cursor)
        require(length >= 8 and cursor + length <= end, 'Invalid Mach-O load command length')
        if command == 0x32:
            require(length >= 24, 'Truncated Mach-O build version')
            platform, minimum, sdk, tools = struct.unpack_from('<IIII', data, cursor + 8)
            require(24 + tools * 8 <= length, 'Invalid Mach-O build tool bounds')
            builds.append(dict(platform=platform, minimum=minimum, sdk=sdk))
        if command == 0x19:
            require(length >= 72, 'Truncated 64-bit segment')
            count = struct.unpack_from('<I', data, cursor + 64)[0]
            require(72 + count * 80 <= length, 'Invalid Mach-O section bounds')
            for index in range(count):
                section = cursor + 72 + index * 80
                name, segment = struct.unpack_from('<16s16s', data, section)
                if name.rstrip(b'\0') != b'__entitlements' or segment.rstrip(b'\0') != b'__TEXT':
                    continue
                section_size = struct.unpack_from('<Q', data, section + 40)[0]
                offset = struct.unpack_from('<I', data, section + 48)[0]
                require(0 < section_size < 1024 ** 2 and offset >= end and offset + section_size <= len(data),
                        'Invalid actual simulator entitlement section range')
                raw = bytes(data[offset:offset + section_size])
                value = plistlib.loads(raw if raw.startswith(b'bplist00') else raw.rstrip(b'\0'))
                require(isinstance(value, dict), 'Simulator entitlements must be an actual plist dictionary')
                found.append(dict(entitlements=value, section_sha256=digest(raw), offset=offset, bytes=section_size))
        cursor += length
    require(cursor == end and len(found) == 1, 'One actual __TEXT,__entitlements section is required')
    require(len(builds) == 1 and builds[0]['platform'] == 7 and builds[0]['sdk'] >> 16 == 27,
            'Actual application Mach-O must target iOS Simulator SDK27')
    return dict(**found[0], build_version=builds[0])


def verify_simulator_keychain_identity(result):
    identifier = result['entitlements'].get('application-identifier', '')
    require(identifier.endswith('.io.anytype.app') and identifier.partition('.')[0],
            'Actual simulator Mach-O lacks the expected application identity')
    groups = result['entitlements'].get('keychain-access-groups', [])
    require(isinstance(groups, list) and all(isinstance(group, str) and group for group in groups),
            'Actual simulator Mach-O has invalid Keychain access groups')
    # SeedService supplies no explicit access group. Apple's documented default
    # is the first listed group, or the application identifier when none exist.
    require((groups[0] if groups else identifier) == identifier,
            'Actual simulator Mach-O selects an unexpected default Keychain access group')
    return identifier


def read_simulator_entitlements(path):
    with path.open('rb') as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as data:
        return inspect_simulator_entitlements(data)


def verify_simulator_shared_app_group(result, info, *, application_prefix, compilation_condition):
    """Bind the actual group entitlement to the original runtime target selection.

    CoreEnvironment reads CompilationCondition from the built bundle; DEBUG and
    RELEASE_NIGHTLY use TargetsConstants' existing development group.
    This checks metadata only; native preparation checks container availability.
    """
    condition = info.get('CompilationCondition')
    require(condition in {'DEBUG', 'RELEASE_NIGHTLY', 'RELEASE_ANYTYPE'},
            'Actual simulator bundle has an unsupported compilation condition')
    require(condition == compilation_condition,
            'Actual simulator app and extension compilation conditions differ')
    bundle = info.get('CFBundleIdentifier')
    require(bundle in {'io.anytype.app', 'io.anytype.app.AnytypeShareExtension',
                       'io.anytype.app.AnytypeNotificationExtension'},
            'Unexpected actual shared-group simulator bundle identity')
    expected = 'group.io.anytype.app' + ('' if condition == 'RELEASE_ANYTYPE' else '.dev')
    require(result['entitlements'].get('application-identifier') == application_prefix + '.' + bundle,
            'Actual shared-group simulator application identity differs')
    require(result['entitlements'].get('com.apple.security.application-groups') == [expected],
            'Actual simulator app group differs from the original runtime target selection')
    return dict(bundle_identifier=bundle, compilation_condition=condition,
                application_group=expected, entitlement_section_sha256=result['section_sha256'])
