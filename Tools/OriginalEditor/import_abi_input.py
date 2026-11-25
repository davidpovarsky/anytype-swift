"""Verify the locally produced original Import ABI before/after SDK compilation.

The receipt is pinned by the execution owner after the native producer, original
mobile bind and actual generated invocation link succeed. This adapter never
creates qualification, reruns a generator or credits compilation as editor UI.
"""
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re

from local_execution import require, sha
from reused_abi_history import history_proofs

LIB = 'Dependencies/Middleware/Lib.xcframework'
EXPORTS = {'ServiceAnnotationSchemaRegister', 'ServiceAnnotationImport', 'ServiceAnnotationImportCancel'}


def exact_file(root, row):
    relative = PurePosixPath(row['path'])
    require(not relative.is_absolute() and '..' not in relative.parts
            and str(relative) == row['path'] and '\\' not in row['path'],
            'ABI receipt contains a noncanonical member')
    path = root / row['path']
    require(path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
            and path.stat().st_size == row['bytes'] and sha(path) == row['sha256'],
            'ABI source/evidence member differs: ' + row['path'])
    return path


def verify(root, path, digest, source):
    root, path = Path(root).resolve(), Path(path)
    require(not path.is_symlink(), 'Aliased ABI receipt')
    path = path.resolve()
    require(path.is_relative_to(root / 'build') and path.is_file()
            and re.fullmatch(r'[0-9a-f]{64}', digest or '') and sha(path) == digest,
            'Exact owned Import ABI receipt is required')
    value = json.loads(path.read_bytes())
    if value.get('schema') == 'otzaria.original-import-donor-sdk-input/1':
        from donor_abi_input import verify as verify_donor
        return verify_donor(root, path, digest, source, value)
    require(value.get('schema') in ('otzaria.original-import-local-sdk-input/1',
                                   'otzaria.original-import-local-sdk-input/2')
            and value.get('status') == 'PASS' and value.get('producer_kind') == 'local-mac'
            and value.get('sdk_source_sha') == source['head_sha']
            and value.get('local_execution_sha256') == source['execution_identity']['local_execution_sha256']
            and value.get('generated_files_verified') == 733
            and value.get('generated_files_written') == 0
            and value.get('generators_replayed') == 0
            and value.get('full_sdk_accepted') is False and value.get('editor_ui_accepted') is False,
            'Local original ABI admission scope/source differs')
    pinned_wrapper = None
    if value['schema'].endswith('/2'):
        require(isinstance(value.get('pinned_wrapper'), dict),
                'Pinned-wrapper ABI requires its complete actual adapter observation')
        adapter = exact_file(path.parent, value['pinned_wrapper'])
        spec = importlib.util.spec_from_file_location('admitted_pinned_wrapper',
            root / 'Tools/OriginalEditor/ABIPinnedWrapper/pinned_wrapper.py')
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        pinned_wrapper = helper.verify(adapter, value['pinned_wrapper']['sha256'], root, source['head_sha'])
    else:
        require('pinned_wrapper' not in value,
                'The historical ABI schema cannot implicitly admit a wrapper adapter')
    native = value['native_qualification']
    require(re.fullmatch(r'[0-9a-f]{40}', native.get('source_sha', ''))
            and re.fullmatch(r'[0-9a-f]{40}', native.get('native_source_tree', ''))
            and re.fullmatch(r'[0-9a-f]{64}', native.get('execution_manifest_sha256', ''))
            and native.get('status') == 'PASS', 'Qualified native union identity is missing')
    counts = {'native9': 9, 'rpc9': 9, 'cancel_panic': 1, 'bundled_semantic': 6,
              'schema_closure': 11, 'relation_target_closure': 12,
              'imported_creation_date': 6, 'bounded_native_metadata': 12}
    require(all(type(number) is int for group in native.get('counts', {}).values()
                for number in group.values()), 'Native counts must be actual integer counts')
    require(native.get('counts') == {key: {'passes': count, 'failures': 0, 'skipped': 0, 'not_run': 0}
                                    for key, count in counts.items()},
            'Original native, RPC and relation acceptance is incomplete')
    require(native.get('source_module_link_stability') == 'PASS'
            and native.get('owned_command_groups_drained') is True,
            'Native producer did not close its source/process proof')
    require(set(value['qualification_receipts']) == {
                'generation_qualification', 'changed_swift_qualification', 'final_native_rpc_union'},
            'Separate original generation, changed Swift and final native receipts required')
    proofs = {name: json.loads(exact_file(path.parent, row).read_bytes())
              for name, row in value['qualification_receipts'].items()}
    historical = history_proofs(path.parent, value['historical_receipts'], exact_file)
    require(all(proofs[name] == item for name, item in historical.items()),
            'Historical qualification differs from authenticated original bytes')
    require(proofs['final_native_rpc_union'] == native, 'Native qualification body differs')
    generation, swift = proofs['generation_qualification'], proofs['changed_swift_qualification']
    require(generation.get('status') == 'PASS'
            and generation.get('output_counts') == {'native': 11, 'swift': 696, 'middleware': 37}
            and generation.get('aggregate_producer_outcome') == 'FAIL'
            and generation.get('generators_replayed_by_abi') == 0,
            'Original generation scope/history differs')
    require(swift.get('status') == 'PASS' and swift.get('primary_count') == 2
            and swift.get('input_files') == 689 and swift.get('typecheck_invocations') == 1
            and swift.get('generated_index_sha256') == generation.get('generated_index_sha256')
            and swift.get('generation_replayed') is False and swift.get('full_sdk_typechecked') is False,
            'Original changed-Swift scope differs')
    commands = value['commands']
    required = {'gomobile_bind', 'generated_invocation_link', 'ios_arm64_exports',
                'ios-simulator_arm64_exports', 'ios-simulator_x86_64_exports'}
    require(set(commands) == required, 'Incomplete original ABI build/link observations')
    for name, row in commands.items():
        command_path = exact_file(path.parent, row)
        command = json.loads(command_path.read_bytes())
        require(command.get('returncode') == 0 and command.get('timed_out') is False
                and command.get('owned_group_drained') is True
                and isinstance(command.get('command'), list) and command['command'],
                'Original ABI command did not succeed: ' + name)
        for stream in ('stdout', 'stderr'):
            exact_file(path.parent, command[stream])
    require(set(value['defined_exports']) >= EXPORTS
            and value.get('verified_architectures') == {
                'ios': ['arm64'], 'ios-simulator': ['arm64', 'x86_64']}
            and value.get('source_unchanged_after_bind') is True,
            'Original mobile ABI platform/export/source verification differs')
    require(value.get('owned_command_groups_drained') is True, 'ABI producer left an owned command group')
    lib = root / LIB
    rows = value['lib_files']
    names = [row['path'] for row in rows]
    require(names and len(names) == len(set(names))
            and all(name.startswith(LIB + '/') for name in names), 'Invalid Lib inventory')
    actual = sorted(p.relative_to(root).as_posix() for p in lib.rglob('*') if p.is_file())
    require(actual == sorted(names), 'Installed Lib has missing or additional files')
    require(not any(p.is_symlink() for p in lib.rglob('*')), 'Aliased Lib member')
    for row in rows:
        exact_file(root, row)
    return {'schema': value['schema'], 'status': 'PASS', 'receipt_sha256': digest,
            'app_source_sha': source['head_sha'], 'producer_kind': 'local-mac',
            'native_qualification': native, 'lib_files': rows,
            'generated_files_verified': 733, 'generated_files_written': 0,
            'full_sdk_accepted': False, 'editor_ui_accepted': False,
            **({'pinned_wrapper': pinned_wrapper} if pinned_wrapper is not None else {})}
