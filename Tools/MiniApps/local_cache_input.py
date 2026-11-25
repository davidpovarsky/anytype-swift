"""Admit only the completed owned 36a recovery cache for a source-equivalent continuation.

This preserves the original immutable product export and compiler identity.
The caller must still run both original xcodebuild commands and every postgate.
No foreign cache, failed build or changed application source is admitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

from local_execution import PRIVATE_ROOT, digest, write, require

SOURCE = '36a138dda50d2fb0b874f0b1635a80bb4b33fe5c'
APP = PRIVATE_ROOT / 'source'
DERIVED = PRIVATE_ROOT / 'DerivedData-36a138dd-01'
PREVIOUS = PRIVATE_ROOT / 'evidence/build-36a138dd-01'
DESCRIPTOR_SHA256 = '5f06e1778bef72b54ddf9e2a0d8ac3f76f8887b0498c9772b248588594ff7cf2'
BUILD_SHA256 = '21ef0b6799dc6689f65d4f2aba211c335afc3e768dfc07cfe1b6199abf31290f'
RESULT_SHA256 = 'a2674db8e8adaef3d06661223a9dbb7bd3958b3a6157273e37ab06e15055fdfb'
MANIFEST_SHA256 = 'd21f19741add2c02198651581176fce314959764ea116c23cdee6a64203bf28c'
ARCHIVE_SHA256 = 'b05ff68134fc410d59419c17676faa12b3b9d8e6b1f34fb328ed78171a55af6c'
CACHE_PATHS = ('Build', 'MiniAppsCurrentModuleCache.noindex')
# These are downstream execution metadata/controllers, never app source or tests.
CONTROL_ONLY_PATHS = {
    'Tools/Hanlin/source.json', 'Tools/MiniApps/producer.json',
    'Tools/MiniApps/producer-preparation-fe3f75d0.json',
    'Tools/MiniApps/local_cache_input.py', 'Tools/MiniApps/test_local_cache_input.py',
    'Tools/MiniApps/run_local_native_acceptance.py',
    'Tools/MiniApps/run_native_acceptance.py', 'Tools/MiniApps/local_execution.py',
    'Tools/MiniApps/test_local_runtime_selection.py',
    'docs/miniapps-cross-app/evidence/20261125-cache-continuation/CONTRACT.json',
    'docs/miniapps-cross-app/evidence/20261125-fe3-producer-source/REVIEW.json',
    'docs/miniapps-cross-app/CUSTOM_RESULTS_AND_RECEIPT_BOUNDARY_20261125.md',
    'docs/miniapps-cross-app/evidence/20261125-recovered-producer04/REVIEW.json',
    'docs/miniapps-cross-app/evidence/20261125-recovered36-cache/CONTRACT.json',
}


def git(app, *args):
    return subprocess.check_output(['git', '-c', 'gc.auto=0', '-C', str(app), *args],
                                   text=True).strip()


def compiled_source_tree(app, revision):
    raw = subprocess.check_output(['git', '-c', 'gc.auto=0', '-C', str(app),
                                   'ls-tree', '-rz', revision])
    result = {}
    for entry in raw.split(b'\0'):
        if not entry:
            continue
        meta, name = entry.split(b'\t', 1)
        name = name.decode()
        if name not in CONTROL_ONLY_PATHS:
            result[name] = meta.decode()
    require(result, 'Empty original compilation source tree')
    return result


def cache_inventory(derived, prefixes=CACHE_PATHS):
    result = {}
    for prefix in prefixes:
        start = derived / prefix
        require(start.is_dir() and not start.is_symlink(), 'Owned compiled cache is absent or aliased')
        for directory, dirs, files in os.walk(start, followlinks=False):
            for name in sorted(dirs + files):
                p = Path(directory) / name
                relative = p.relative_to(derived).as_posix()
                value = p.lstat()
                row = {'mode': stat.S_IMODE(value.st_mode)}
                if stat.S_ISLNK(value.st_mode):
                    row.update(kind='symlink', target=os.readlink(p))
                elif stat.S_ISDIR(value.st_mode):
                    row.update(kind='directory')
                else:
                    require(stat.S_ISREG(value.st_mode), 'Special filesystem object in owned compiler cache')
                    row.update(kind='file', bytes=value.st_size, sha256=digest(p))
                result[relative] = row
    require(result, 'Empty completed compiler cache')
    return result


def exact_json(path, expected):
    require(path.is_file() and not path.is_symlink() and digest(path) == expected,
            'Original completed build receipt changed: ' + str(path))
    return json.loads(path.read_text())


def previous_build():
    descriptor = exact_json(PREVIOUS / 'local-execution.json', DESCRIPTOR_SHA256)
    build = exact_json(PREVIOUS / 'miniapps-build.json', BUILD_SHA256)
    terminal = exact_json(PREVIOUS / 'local-execution-result.json', RESULT_SHA256)
    require(descriptor['source_sha'] == SOURCE and descriptor['source_root'] == str(APP)
            and descriptor['derived'] == str(DERIVED)
            and descriptor['configuration'] == 'Debug-MiniAppsOwner'
            and descriptor['execution_origin'] == 'local-mac' and descriptor['github_run_id'] is None
            and terminal['status'] == 'BUILD_PASS_ORIGINAL_FIVE_NOT_RUN'
            and terminal['source_sha'] == SOURCE and terminal['run_id'] == descriptor['run_id']
            and build['source_sha'] == SOURCE and build['run_id'] == descriptor['run_id']
            and build['status'] == 'BUILD_PASS_TESTS_NOT_RUN'
            and build['native_build_succeeded'] is True and build['ui_build_succeeded'] is True
            and build['final_entitlement_admission']['status'] == 'ORIGINAL_SIMULATOR_SIGNATURE_AND_ENTITLEMENTS_VERIFIED'
            and build['standalone_runtime_boundary']['status'] == 'PASS',
            'Only the actual completed original owner build can donate this cache')
    for name in ['resolve-native-packages', 'build-native', 'resolve-ui-packages', 'build-ui']:
        path = PREVIOUS / (name + '.command.json')
        row = json.loads(path.read_text())
        require(row['returncode'] == 0 and row['timed_out'] is False
                and row['owned_group_drained'] is True and row['cwd'] == str(APP)
                and row['log_sha256'] == digest(PREVIOUS / (name + '.log'))
                and row['arguments'] == build['completed_build_commands'][name]['arguments']
                and row['log_sha256'] == build['completed_build_commands'][name]['log_sha256'],
                'Original cache donor command or complete output differs: ' + name)
    exported = build['complete_early_products']
    manifest = exact_json(Path(exported['manifest']), MANIFEST_SHA256)
    require(exported['manifest_sha256'] == MANIFEST_SHA256
            and manifest['source_sha'] == SOURCE and manifest['run_id'] == descriptor['run_id']
            and manifest['configuration'] == 'Debug-MiniAppsOwner'
            and exported['archive_sha256'] == manifest['archive_sha256'] == ARCHIVE_SHA256
            and digest(Path(exported['archive'])) == ARCHIVE_SHA256
            and Path(exported['archive']).stat().st_size == manifest['archive_bytes']
            and digest(Path(exported['manifest']).parent / 'original-build-receipt.json')
                == manifest['original_build_receipt_sha256'] == exported['original_build_receipt_sha256'],
            'Immutable complete original application product archive differs')
    return descriptor, build, manifest


def qualified_hanlin(app):
    sys.path.insert(0, str(app / 'Tools/Hanlin'))
    import prepare_sdk
    require(Path(prepare_sdk.__file__).resolve() == app / 'Tools/Hanlin/prepare_sdk.py',
            'Shared SDK verifier was imported from another application root')
    return prepare_sdk.verify(app / 'Dependencies/Hanlin')


def seal(app, derived, output):
    require(app == APP and derived == DERIVED and app.resolve() == app and derived.resolve() == derived,
            'Only the already owned original source/cache paths may be sealed')
    require(git(app, 'rev-parse', 'HEAD') == SOURCE and not git(app, 'diff', '--name-only', 'HEAD')
            and not output.exists() and output.is_relative_to(PRIVATE_ROOT / 'evidence'),
            'Seal must observe the actual clean original source before any continuation checkout')
    descriptor, build, manifest = previous_build()
    from export_products import product_closure
    _, entries, _, _ = product_closure(derived / 'Build/Products',
        [Path(build['native_configuration']), Path(build['ui_configuration'])])
    require(entries == manifest['files'], 'Actual completed app/test products differ from their immutable export')
    source = compiled_source_tree(app, SOURCE)
    shared = qualified_hanlin(app)
    value = {'schema': 'miniapps.completed-owned-compiler-cache/1',
        'status': 'SEALED_ACTUAL_COMPLETE_BUILD_CACHE_NOT_ACCEPTANCE',
        'source_sha': SOURCE, 'source_root': str(app), 'derived': str(derived),
        'prior_run_id': descriptor['run_id'], 'prior_descriptor_sha256': DESCRIPTOR_SHA256,
        'prior_build_sha256': BUILD_SHA256, 'prior_result_sha256': RESULT_SHA256,
        'prior_complete_manifest_sha256': MANIFEST_SHA256,
        'prior_complete_archive_sha256': ARCHIVE_SHA256,
        'compiler_source_tree': source,
        'hanlin_snapshot': shared,
        'cache': cache_inventory(derived),
        'native_or_ui_credit': 0}
    require(git(app, 'rev-parse', 'HEAD') == SOURCE
            and compiled_source_tree(app, SOURCE) == source
            and not git(app, 'diff', '--name-only', 'HEAD'), 'Source changed during cache sealing')
    write(output, value)
    return {'path': str(output), 'sha256': digest(output), 'cache_members': len(value['cache']),
            'source_members': len(source), 'prior_run_id': descriptor['run_id']}


def admit(app, derived, evidence, snapshot, expected_sha256):
    require(app == APP and derived == DERIVED and app.resolve() == app and derived.resolve() == derived
            and snapshot is not None and expected_sha256 is not None,
            'Existing compiler inputs require an exact owned-cache snapshot')
    path = Path(snapshot)
    require(path.is_relative_to(PRIVATE_ROOT / 'evidence') and path.resolve() == path,
            'Unowned or aliased compiler-cache snapshot')
    value = exact_json(path, expected_sha256)
    descriptor, build, manifest = previous_build()
    require(value.get('schema') == 'miniapps.completed-owned-compiler-cache/1'
            and value.get('status') == 'SEALED_ACTUAL_COMPLETE_BUILD_CACHE_NOT_ACCEPTANCE'
            and value.get('source_sha') == SOURCE and value.get('source_root') == str(app)
            and value.get('derived') == str(derived)
            and value.get('prior_run_id') == descriptor['run_id']
            and value.get('prior_descriptor_sha256') == DESCRIPTOR_SHA256
            and value.get('prior_build_sha256') == BUILD_SHA256
            and value.get('prior_result_sha256') == RESULT_SHA256
            and value.get('prior_complete_manifest_sha256') == MANIFEST_SHA256
            and value.get('prior_complete_archive_sha256') == ARCHIVE_SHA256
            and value.get('native_or_ui_credit') == 0,
            'Unknown, failed, foreign or relabelled compiler-cache donor')
    require(subprocess.run(['git', '-c', 'gc.auto=0', '-C', str(app),
                            'merge-base', '--is-ancestor', SOURCE, 'HEAD']).returncode == 0,
            'Current source is not a continuation of the actual build')
    current = compiled_source_tree(app, 'HEAD')
    require(current == value['compiler_source_tree'] == compiled_source_tree(app, SOURCE),
            'Application, tests, native source, resource, project, capability or dependency bytes changed')
    shared = qualified_hanlin(app)
    require(shared['files'] == value['hanlin_snapshot']['files'],
            'A materialized shared SDK package changed since the actual completed build')
    require(cache_inventory(derived) == value['cache'],
            'Owned compiler/module/product bytes changed after the completed snapshot')
    result = {'status': 'ADMITTED_SAME_PATH_SOURCE_IDENTICAL_OWNED_COMPILER_CACHE',
        'snapshot_path': str(path), 'snapshot_sha256': expected_sha256,
        'prior_source_sha': SOURCE, 'current_source_sha': git(app, 'rev-parse', 'HEAD'),
        'prior_run_id': descriptor['run_id'], 'module_cache': str(derived / 'MiniAppsCurrentModuleCache.noindex'),
        'prior_hanlin_source_sha': value['hanlin_snapshot']['revision'],
        'current_hanlin_source_sha': shared['revision'],
        'complete_hanlin_file_set_sha256': hashlib.sha256(json.dumps(
            shared['files'], sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
        'source_members': len(current), 'cache_members': len(value['cache']),
        'old_products_remain_in_immutable_archive': ARCHIVE_SHA256,
        'new_native_or_ui_credit': 0, 'both_actual_compiler_commands_and_postgates_required': True}
    write(evidence / 'owned-compiler-cache-admission.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--seal', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(seal(APP, DERIVED, args.seal)))
