"""Seal six exact generated exports observed failing strict signing in v8.

The original producer and nested resource bundles stay byte/metadata identical.
Only the owning export's signature allocation and new root resource seal may
change. No recursive signing, wildcard products, consumer or editable credit.
"""
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import struct
import subprocess

from amplitude_simulator_signing import retain_files
from anycrypto_simulator_signing import (SEAL, executable_preservation,
                                       expected_unsealed_failure, layout)
from framework_products import framework_closure
from pbx_source import require


OBSERVED_RUN = '44946489804'
OBSERVED_SOURCE = '4ba0c82d22948a414aaf70873b69de9771fbd252'
OBSERVED_ARTIFACT_SHA256 = '1a45863adb5c3d45bfcc290536bda759fa3842b25f3888bf14c7b0d1a681243b'
PROFILES = {
    'AppTarget_-256A0C750C206F_PackageProduct.framework': {
        'label': 'app-target', 'identifier': 'apptarget.AppTarget',
        'module': 'Modules/AppTarget', 'tree': 'd5aaab9b2e9f4cf07bb5c0003b733ff91ecd0691'},
    'BigInt_175F1397B99A03_PackageProduct.framework': {
        'label': 'bigint', 'identifier': 'bigint.BigInt', 'package': 'bigint',
        'revision': 'd013a2b66ee468aade6da1f26c6d55cb6cd2e9ad'},
    'Crypto_17A3B1FFC41E47_PackageProduct.framework': {
        'label': 'crypto', 'identifier': 'swift-crypto.Crypto', 'package': 'swift-crypto',
        'revision': 'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed',
        'resource_bundle': 'swift-crypto_Crypto.bundle',
        'privacy_sha256': '42fb8a30dd8d7ba0900e1bf17fe64ed8c12cfdb8a9c791ab6b4e1eceb0f299c0'},
    'Factory_32A9B87E1196645F_PackageProduct.framework': {
        'label': 'factory', 'identifier': 'factory.Factory', 'package': 'factory',
        'revision': '8ca11a7bd1ede031e8e6d7a912bb116e2e43961b'},
    'NotificationsCore_5AD5AD79262EBF4_PackageProduct.framework': {
        'label': 'notifications-core', 'identifier': 'notificationscore.NotificationsCore',
        'module': 'Modules/NotificationsCore', 'tree': 'ac0029fe20559cf289045213fe0d37bcc776bd4c'},
    'SwiftProtobuf_7CEE9AB92C12BC6B_PackageProduct.framework': {
        'label': 'swift-protobuf', 'identifier': 'swift-protobuf.SwiftProtobuf', 'package': 'swift-protobuf',
        'revision': 'c6fe6442e6a64250495669325044052e113e990c',
        'resource_bundle': 'SwiftProtobuf_SwiftProtobuf.bundle',
        'privacy_sha256': 'a07418e5fe128e224cd37964bc21c503b7aa2f575e7b4927468478ad873214fe'},
}
RESOURCE_FILES = {'Info.plist', 'PrivacyInfo.xcprivacy', '_CodeSignature/CodeDirectory',
                  '_CodeSignature/CodeRequirements', '_CodeSignature/CodeResources',
                  '_CodeSignature/CodeSignature'}


def git_bytes(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], timeout=30)


def source_identity(root, profile):
    if 'package' in profile:
        lock = root / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
        pins = json.loads(lock.read_bytes())['pins']
        matched = [p for p in pins if p['identity'] == profile['package']]
        require(len(matched) == 1 and matched[0]['state']['revision'] == profile['revision'],
                'Observed generated product package revision differs')
        return {key: profile[key] for key in ['package', 'revision']}
    module = root / profile['module']
    require(not module.is_symlink() and module.resolve().is_relative_to(root.resolve()),
            'Aliased original local module')
    actual = git_bytes(root, 'rev-parse', 'HEAD:' + profile['module']).decode().strip()
    require(actual == profile['tree'], 'Observed generated product local module tree differs')
    records = {}
    for item in git_bytes(root, 'ls-tree', '-rz', 'HEAD:' + profile['module']).split(b'\0'):
        if not item:
            continue
        entry, relative = item.split(b'\t', 1)
        mode, kind, expected = entry.decode().split()
        name = relative.decode()
        path = module / name
        require(mode in {'100644', '100755'} and kind == 'blob' and path.is_file()
                and not path.is_symlink() and path.resolve().is_relative_to(module.resolve()),
                'Missing or aliased original local module input')
        raw = path.read_bytes()
        actual_blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(actual_blob == expected, 'Original local module bytes differ from its pinned tree')
        records[name] = {'git_blob': expected, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    require(records and {p.relative_to(module).as_posix() for p in module.rglob('*') if p.is_file()} == set(records),
            'Unreviewed original local module files')
    return {'module': profile['module'], 'tree': actual, 'files': records}


def observe(path, name, profile, *, sealed=False):
    executable = name[:-len('.framework')]
    metadata = framework_closure(path)
    directories = {'.'} | ({'_CodeSignature'} if sealed else set())
    files = {executable, 'Info.plist'} | ({SEAL} if sealed else set())
    bundle = profile.get('resource_bundle')
    if bundle:
        directories |= {bundle, bundle + '/_CodeSignature'}
        files |= {bundle + '/' + relative for relative in RESOURCE_FILES}
    require(set(metadata) == files | directories
            and all(row['kind'] == ('directory' if relative in directories else 'file')
                    for relative, row in metadata.items()),
            'Unexpected observed generated product members or aliases')
    payload = {relative: (path / relative).read_bytes() for relative in files}
    info = plistlib.loads(payload['Info.plist'])
    require(info.get('CFBundleExecutable') == executable and info.get('CFBundleIdentifier') == profile['identifier']
            and info.get('CFBundlePackageType') == 'FMWK'
            and info.get('CFBundleSupportedPlatforms') == ['iPhoneSimulator'],
            'Observed generated product identity or platform differs')
    if bundle:
        require(hashlib.sha256(payload[bundle + '/PrivacyInfo.xcprivacy']).hexdigest() == profile['privacy_sha256'],
                'Original pinned privacy resource differs')
    layout(payload[executable], executable)
    return metadata, payload


def signing_identifier(binary, executable):
    start = layout(binary, executable)['signature']['offset']
    raw = binary[start:]
    count = struct.unpack_from('>I', raw, 8)[0]
    rows = [struct.unpack_from('>II', raw, 12 + i * 8) for i in range(count)]
    offset = next(offset for slot, offset in rows if slot == 0)
    size = struct.unpack_from('>I', raw, offset + 4)[0]
    relative = struct.unpack_from('>I', raw, offset + 20)[0]
    require(44 <= relative < size, 'Malformed signed generated product identifier')
    end = raw.find(b'\0', offset + relative, offset + size)
    require(end >= 0, 'Unterminated signed generated product identifier')
    return raw[offset + relative:end].decode()


def prepare_observed_package_simulator_export(root, products, exported, evidence, name, command):
    require(name in PROFILES, 'Unreviewed generated product cannot be sealed')
    require(platform.system() == 'Darwin', 'Native export sealing requires an actual Apple host')
    root, products, exported, evidence = map(Path, (root, products, exported, evidence))
    profile = PROFILES[name]
    executable = name[:-len('.framework')]
    label = 'observed-' + profile['label']
    build = (root / 'build').resolve()
    require(all(p.resolve().is_relative_to(build) for p in [products, exported, evidence])
            and products.resolve() != exported.resolve()
            and not products.resolve().is_relative_to(exported.resolve())
            and not exported.resolve().is_relative_to(products.resolve()), 'Unowned or overlapping export paths')
    original, target = products / 'PackageFrameworks' / name, exported / 'Frameworks' / name
    require(not original.parent.is_symlink() and not target.parent.is_symlink()
            and original.resolve().is_relative_to(products.resolve())
            and target.resolve().is_relative_to(exported.resolve())
            and original.resolve() != target.resolve(), 'Refusing an aliased or original signing target')
    provenance = source_identity(root, profile)
    source_metadata, source_files = observe(original, name, profile)
    before_metadata, before_files = observe(target, name, profile)
    require(source_files == before_files, 'Export differs from the actual original producer')
    receipt = {'schema': 1, 'status': 'FAIL', 'scope': 'OWNED_OBSERVED_GENERATED_SIMULATOR_EXPORT_SEAL',
               'observed_run': OBSERVED_RUN, 'observed_source': OBSERVED_SOURCE,
               'observed_artifact_sha256': OBSERVED_ARTIFACT_SHA256,
               'framework': name, 'source': str(original), 'export': str(target), 'provenance': provenance,
               'before_source_metadata': source_metadata, 'before_export_metadata': before_metadata,
               'native_post_signature': 'NOT_RUN', 'consumer_qualification': 'NOT_GRANTED',
               'editable_mount': 'NOT_EXPOSED', 'native_editor_ui_tests': 0}
    receipt['retained_original'] = retain_files(evidence, label + '-original', source_files)
    receipt['retained_export_before'] = retain_files(evidence, label + '-export-before', before_files)
    try:
        for phase, path in [('original', original), ('export-before', target)]:
            receipt[phase + '_strict_failure'] = expected_unsealed_failure(
                path, root, evidence, label + '-' + phase + '-strict-signature', command)
            if profile.get('resource_bundle'):
                command(['codesign', '--verify', '--strict', str(path / profile['resource_bundle'])],
                        root, evidence, label + '-' + phase + '-nested-resource-strict', 30)
        require(framework_closure(original) == source_metadata and framework_closure(target) == before_metadata
                and source_identity(root, profile) == provenance, 'Inputs changed before export sealing')
        command(['codesign', '--force', '--sign', '-', '--timestamp=none', str(target)],
                root, evidence, label + '-export-adhoc-sign', 30)
        after_metadata, after_files = observe(target, name, profile, sealed=True)
        require(all(after_files[relative] == payload for relative, payload in before_files.items()
                    if relative != executable), 'Signing changed original resource or nested signature bytes')
        for relative, previous in before_metadata.items():
            require({k: v for k, v in after_metadata[relative].items() if k not in {'bytes', 'sha256'}}
                    == {k: v for k, v in previous.items() if k not in {'bytes', 'sha256'}},
                    'Signing changed original filesystem metadata: ' + relative)
        receipt['mach_o_preservation'] = executable_preservation(
            before_files[executable], after_files[executable], executable)
        require(signing_identifier(after_files[executable], executable) == profile['identifier'],
                'Signed generated product identifier differs from the original Info.plist')
        require(framework_closure(original) == source_metadata
                and source_identity(root, profile) == provenance, 'Signing changed the original producer or module')
        command(['codesign', '--verify', '--strict', str(target)],
                root, evidence, label + '-export-after-strict-signature', 30)
        if profile.get('resource_bundle'):
            command(['codesign', '--verify', '--strict', str(target / profile['resource_bundle'])],
                    root, evidence, label + '-export-after-nested-resource-strict', 30)
        require(framework_closure(target) == after_metadata and framework_closure(original) == source_metadata
                and source_identity(root, profile) == provenance, 'Verification changed the original or exported input closure')
        receipt.update(status='PASS_CONSTRAINED_GENERATED_SIMULATOR_EXPORT_SIGNATURE', native_post_signature='PASS',
                       original_producer_unchanged=True, original_resources_and_nested_signatures_unchanged=True,
                       original_metadata_unchanged=True, nonsignature_executable_unchanged=True)
        return receipt
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error))
        raise
    finally:
        retention_error = None
        try:
            observed = framework_closure(target)
            receipt['after_export_metadata'] = observed
            receipt['retained_export_after'] = retain_files(evidence, label + '-export-after',
                {relative: (target / relative).read_bytes() for relative, row in observed.items() if row['kind'] == 'file'})
        except BaseException as observation_error:
            receipt['after_observation_error'] = {'type': type(observation_error).__name__, 'message': str(observation_error)}
            if receipt['status'] != 'FAIL':
                receipt['status'] = 'FAIL'
                retention_error = observation_error
        (evidence / (label + '-simulator-signing.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        if retention_error is not None:
            raise retention_error
