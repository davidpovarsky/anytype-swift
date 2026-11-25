"""Release path variant of the exact original Clang declaration export.

All package, declaration, traversal, relocation, source and inventory checks use
the unchanged original helpers. Only actual build platform/configuration vary.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from framework_profile import TARGET
from pbx_source import require
from release_continuation_roots import admit_roots
from clang_product_closure import (MANIFEST, clang_arguments, unaliased, stable_bytes,
    relative_path, Package, modulemap_declarations, write_new, relocate_modulemap,
    declaration_inventory)

def export_clang_declarations(derived, exported, collection, source, lock_path, platform_name):
    require(platform_name in {'iphoneos', 'iphonesimulator'}, 'Unreviewed Clang Release platform')
    target = 'arm64-apple-ios27.0' + ('-simulator' if platform_name == 'iphonesimulator' else '')
    derived, exported = Path(derived), Path(exported)
    require(not derived.is_symlink() and not exported.is_symlink(),
            'Producer or exported Clang root is an alias')
    derived, exported = derived.resolve(strict=True), exported.resolve(strict=True)
    roots = admit_roots(derived, exported, collection, source)
    require(collection.get('status') == 'ACTUAL_COMPILER_FULL_GRAPHS_COLLECTED_SURFACE_NOT_YET_VERIFIED'
            and collection.get('module') == TARGET
            and collection.get('target') == target
            and collection.get('configuration') == 'Release-Anytype'
            and collection.get('platform') == platform_name
            and all(collection.get(key) == source[other] for key, other in
                    [('source_sha', 'head_sha'), ('run_id', 'run_id'), ('run_attempt', 'run_attempt')]),
            'Original Clang compiler receipt identity differs')
    maps, includes = clang_arguments(collection['compiler_arguments'])
    package_root = unaliased(derived / 'SourcePackages/checkouts', derived, True)
    generated = unaliased(derived / ('Build/Intermediates.noindex/GeneratedModuleMaps-' + platform_name), derived, True)
    product_include = derived / ('Build/Products/Release-Anytype-' + platform_name + '/include')
    target_build = derived / ('Build/Intermediates.noindex/Anytype.build/'
                              'Release-Anytype-' + platform_name + '/' + TARGET + '.build')
    lock_raw = stable_bytes(lock_path)
    pins = {item['identity'].lower(): item['state']['revision'] for item in json.loads(lock_raw)['pins']}
    workspace = json.loads(stable_bytes(derived / 'SourcePackages/workspace-state.json'))
    actual = {}
    for item in workspace['object']['dependencies']:
        identity = item['packageRef']['identity'].lower()
        if item['state'].get('name') in {'local', 'fileSystem'}:
            continue
        require(identity in pins and item['state'].get('checkoutState', {}).get('revision') == pins[identity],
                'Clang checkout is not locked to the original graph')
        subpath = item['subpath']
        relative_path(subpath)
        require('/' not in subpath and subpath not in actual, 'Ambiguous Clang checkout root')
        actual[subpath] = (identity, pins[identity])
    source_packages = set()
    exported_includes, excluded, absent_product_includes = [], [], []
    for path in maps:
        if path.is_relative_to(package_root):
            source_packages.add(path.relative_to(package_root).parts[0])
        else:
            require(path.parent == generated, 'Original module map is outside the package/build closure')
            unaliased(path, generated, False)
    for path in includes:
        if path.is_relative_to(package_root):
            source_packages.add(path.relative_to(package_root).parts[0])
            unaliased(path, package_root, True)
            exported_includes.append('Clang/Packages/' + path.relative_to(package_root).as_posix())
        elif path == product_include:
            unaliased(path.parent, derived, True)
            if os.path.lexists(path):
                unaliased(path, derived, True)
                require((exported / 'Include').is_dir(), 'Original product include directory was not exported')
                unaliased(exported / 'Include', exported, True)
                exported_includes.append('Include')
            else:
                # Xcode can name this conventional search directory without
                # creating it. Preserve that observed absence; no declaration
                # or consumer search root is invented for a nonexistent input.
                require(not os.path.lexists(exported / 'Include'),
                        'An absent original product include root has an unowned export')
                absent_product_includes.append(path)
        else:
            require(path.is_relative_to(target_build)
                    and (path.suffix == '.hmap' or 'DerivedSources' in path.relative_to(target_build).parts
                         or 'DerivedSources-normal' in path.relative_to(target_build).parts),
                    'Unreviewed non-package Clang include root')
            excluded.append(str(path))
    require(source_packages and source_packages <= actual.keys(), 'Unpinned Clang package root')
    closure_root = exported / 'Clang'
    require(not os.path.lexists(closure_root), 'Refusing a stale Clang declaration export')
    closure_root.mkdir()
    packages = {}
    for subpath in sorted(source_packages):
        identity, revision = actual[subpath]
        package = Package(identity, revision, package_root / subpath,
                          closure_root / 'Packages' / subpath, derived)
        package.headers()
        packages[subpath] = package

    def mapped(path):
        require(path.is_absolute() and '..' not in path.parts, 'Ambiguous module map declaration path')
        if path.is_relative_to(package_root):
            relative = path.relative_to(package_root)
            require(relative.parts[0] in packages, 'Module map borrows an unrecorded package')
            return exported / 'Clang/Packages' / relative
        if path.is_relative_to(product_include):
            return exported / 'Include' / path.relative_to(product_include)
        raise ValueError('Module map declaration escapes the original Clang closure')

    map_records = []
    for source_map in maps:
        if source_map.is_relative_to(package_root):
            relative = source_map.relative_to(package_root)
            package = packages[relative.parts[0]]
            name = PurePosixPath(*relative.parts[1:]).as_posix()
            require(source_map.suffix == '.modulemap', 'Unexpected original module map suffix')
            package.export(name)
            destination = exported / 'Clang/Packages' / relative
            raw = stable_bytes(destination)
            for match in modulemap_declarations(raw):
                header = Path(match['path'].decode('utf-8'))
                require(not header.is_absolute(), 'Original tracked module map has an absolute declaration')
                original_target = source_map.parent / header
                target = mapped(original_target)
                require(target.is_file() or target.is_dir(), 'Tracked module map header was not exported')
            map_records.append({'path': destination.relative_to(exported).as_posix(),
                                'source': str(source_map), 'original_sha256': hashlib.sha256(raw).hexdigest(),
                                'exported_sha256': hashlib.sha256(raw).hexdigest(),
                                'transformation': 'EXACT_ORIGINAL_TRACKED_BYTES'})
        else:
            raw = stable_bytes(source_map)
            require(len(raw) <= 65536, 'Oversized original generated module map')
            write_new(exported / 'SourceProvenance/OriginalClangModuleMaps' / (source_map.name + '.txt'), raw)
            destination = closure_root / 'GeneratedModuleMaps' / source_map.name
            relocated, changes = relocate_modulemap(raw, source_map, destination, mapped)
            require(str(derived).encode() not in relocated, 'Generated module map still uses producer paths')
            write_new(destination, relocated)
            map_records.append({'path': destination.relative_to(exported).as_posix(),
                                'source': str(source_map), 'original_sha256': hashlib.sha256(raw).hexdigest(),
                                'exported_sha256': hashlib.sha256(relocated).hexdigest(),
                                'original_utf8': raw.decode('utf-8'),
                                'transformation': 'EXACT_DECLARATION_PATH_RELOCATION',
                                'path_substitutions': changes})
    for relative in exported_includes:
        require((exported / relative).is_dir(), 'Original Clang include root was not retained')
    for path in absent_product_includes:
        require(not os.path.lexists(path) and not os.path.lexists(exported / 'Include'),
                'An absent original product include root changed during export')
    files = declaration_inventory(exported)
    require(sum(item['bytes'] for item in files.values()) <= 64 * 1024 * 1024,
            'Original Clang declaration closure exceeds reviewed size bound')
    result = {'schema': 1, 'status': 'ORIGINAL_CLANG_DECLARATIONS_EXPORTED_NOT_QUALIFIED',
              'source_sha': source['head_sha'], 'run_id': source['run_id'], 'run_attempt': source['run_attempt'],
              'compiler_line_sha256': collection['compiler_line_sha256'],
              'original_package_lock_sha256': hashlib.sha256(lock_raw).hexdigest(),
              'module_maps': [item['path'] for item in map_records],
              'header_search_paths': exported_includes, 'module_map_provenance': map_records,
              'packages': {name: {'identity': package.identity, 'revision': package.revision,
                                  'original_tracked_declarations': package.records}
                           for name, package in packages.items()},
              'excluded_original_target_header_roots': excluded,
              'absent_original_product_header_roots': [
                  {'path': str(path), 'observation': 'LEXISTS_FALSE_BEFORE_AND_AFTER_DECLARATION_EXPORT'}
                  for path in absent_product_includes],
              'files': files, 'implementation_translation_units_exported_or_added': False,
              'consumer_or_native_qualification': False}
    if roots is not None:
        result['compiler_root_continuation'] = roots
    if source.get('execution_identity', {}).get('producer_kind') == 'local-mac':
        result.update(producer_kind='local-mac',
                      local_execution_sha256=source['execution_identity']['local_execution_sha256'])
    write_new(exported / MANIFEST, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    return result
