import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import subprocess

from framework_profile import TARGET, blob, sha256
from pbx_source import require
from product_inventory import inventory

MANIFEST = 'SourceProvenance/ClangImportContext.json'
HEADER_SUFFIXES = {'.h', '.hh', '.hpp', '.hxx', '.inc', '.def', '.ipp', '.tpp'}
TRANSLATION_SUFFIXES = {'.c', '.cc', '.cpp', '.cxx', '.m', '.mm', '.swift', '.s'}
PATH_TOKEN = re.compile(r'(?:[A-Za-z0-9_.+-]+/)*[A-Za-z0-9_.+-]+')
DIRECTIVE = re.compile(
    rb'(?P<prefix>\b(?:(?:private|textual|exclude)[ \t]+)*'
    rb'(?:umbrella(?:[ \t]+header)?|header)[ \t]+)"(?P<path>[^"\r\n]+)"')


def command(root, *arguments):
    result = subprocess.run(['git', '-C', str(root), *arguments], capture_output=True, timeout=60)
    require(result.returncode == 0, 'Cannot verify original Clang package Git input')
    return result.stdout


def relative_path(value):
    require(isinstance(value, str) and PATH_TOKEN.fullmatch(value)
            and not any(part in {'', '.', '..'} for part in value.split('/')),
            'Unsafe relative Clang declaration path')
    return PurePosixPath(value)


def unaliased(path, root, directory):
    path, root = Path(path), Path(root)
    require(path.is_absolute() and path.is_relative_to(root) and '..' not in path.parts,
            'Clang input escapes its owned root')
    current = root
    for part in path.relative_to(root).parts:
        current /= part
        mode = current.lstat().st_mode
        require(not stat.S_ISLNK(mode), 'Clang input has an unexpected alias')
        if current != path:
            require(stat.S_ISDIR(mode), 'Clang input has a non-directory ancestor')
    require(path.is_dir() if directory else path.is_file(), 'Clang input has the wrong kind')
    return path


def stable_bytes(path):
    path = Path(path)
    before = path.stat()
    raw = path.read_bytes()
    after = path.stat()
    identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    require(identity(before) == identity(after) and len(raw) == before.st_size,
            'Clang declaration changed during read')
    return raw


def write_new(path, raw):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not os.path.lexists(path), 'Refusing an existing Clang declaration output')
    with path.open('xb') as stream:
        stream.write(raw)


def clang_arguments(arguments):
    require(isinstance(arguments, list) and all(isinstance(item, str) for item in arguments),
            'Malformed actual original compiler arguments')
    values = []
    index = 0
    while index < len(arguments):
        if arguments[index] == '-Xcc':
            require(index + 1 < len(arguments), 'Missing original Clang compiler argument')
            values.append(arguments[index + 1])
            index += 1
        index += 1
    maps, includes = [], []
    index = 0
    while index < len(values):
        value = values[index]
        if value.startswith('-fmodule-map-file='):
            maps.append(Path(value.split('=', 1)[1]))
        elif value == '-I':
            require(index + 1 < len(values), 'Missing original Clang include directory')
            includes.append(Path(values[index + 1]))
            index += 1
        elif value.startswith('-I'):
            includes.append(Path(value[2:]))
        index += 1
    require(maps and len(maps) == len(set(maps)) and len(includes) == len(set(includes)),
            'Missing or duplicate original Clang declaration inputs')
    require(all(path.is_absolute() and '..' not in path.parts for path in maps + includes),
            'Original Clang inputs must use exact absolute paths')
    return maps, includes


class Package:
    def __init__(self, identity, revision, checkout, output, producer):
        self.identity, self.revision = identity, revision
        self.checkout = unaliased(checkout, producer, True)
        self.output = output
        require(command(checkout, 'rev-parse', 'HEAD').decode().strip() == revision,
                'Clang package revision differs from its original pin')
        require(not command(checkout, 'diff', '--name-only', 'HEAD').strip()
                and not command(checkout, 'ls-files', '--others', '-z'),
                'Clang package contains modified or untracked inputs')
        self.entries = {}
        for record in command(checkout, 'ls-tree', '-rz', '--full-tree', revision).split(b'\0'):
            if not record:
                continue
            metadata, name = record.split(b'\t', 1)
            mode, kind, object_id = metadata.decode().split()
            name = name.decode('utf-8')
            require(name not in self.entries, 'Duplicate tracked Clang input')
            self.entries[name] = (mode, kind, object_id)
        self.records = {}
        self.exported_bytes = 0

    def read(self, name, ancestors=()):
        relative_path(name)
        require(name in self.entries and name not in ancestors and len(ancestors) < 32,
                'Missing, excessive or cyclic tracked Clang input')
        mode, kind, object_id = self.entries[name]
        require(kind == 'blob' and mode in {'100644', '100755', '120000'},
                'Clang declaration is not a tracked regular file or header alias')
        source = self.checkout / name
        unaliased(source.parent, self.checkout, True)
        if mode == '120000':
            require(source.is_symlink(), 'Tracked Clang header alias was replaced')
            literal = os.readlink(source)
            require(blob(os.fsencode(literal)) == object_id, 'Tracked Clang alias bytes differ')
            require(not Path(literal).is_absolute() and '\\' not in literal,
                    'Clang header alias has an absolute or ambiguous target')
            target_name = posixpath.normpath(posixpath.join(posixpath.dirname(name), literal))
            relative_path(target_name)
            require(Path(target_name).suffix.lower() in HEADER_SUFFIXES,
                    'Clang header alias does not target a declaration')
            raw, target_record = self.read(target_name, (*ancestors, name))
            row = {'git_blob': object_id, 'git_mode': mode, 'literal_alias': literal,
                   'materialized_target': target_name, 'target_provenance': target_record}
        else:
            unaliased(source, self.checkout, False)
            raw = stable_bytes(source)
            require(blob(raw) == object_id, 'Tracked original Clang declaration bytes differ')
            row = {'git_blob': object_id, 'git_mode': mode}
        require(len(raw) <= 8 * 1024 * 1024, 'Oversized original Clang declaration')
        return raw, {**row, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

    def export(self, name):
        if name in self.records:
            return
        raw, provenance = self.read(name)
        require(self.exported_bytes + len(raw) <= 32 * 1024 * 1024,
                'Original package declaration closure exceeds the size bound')
        write_new(self.output / name, raw)
        self.exported_bytes += len(raw)
        self.records[name] = provenance

    def headers(self):
        names = [name for name in self.entries if Path(name).suffix.lower() in HEADER_SUFFIXES]
        require(names and len(names) <= 5000, 'Missing or excessive original package declarations')
        for name in sorted(names):
            self.export(name)


def modulemap_declarations(raw):
    masked = bytearray(raw)
    tokens = re.compile(rb'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', re.DOTALL)
    for match in tokens.finditer(raw):
        if match[0].startswith((b'//', b'/*')):
            for offset in range(match.start(), match.end()):
                if masked[offset] not in (10, 13):
                    masked[offset] = 32
    masked = bytes(masked)
    declarations = list(DIRECTIVE.finditer(masked))
    strings = list(re.finditer(rb'"(?:\\.|[^"\\])*"', masked))
    require([(item.start() + 1, item.end() - 1) for item in strings]
            == [item.span('path') for item in declarations],
            'Module map has an unsupported quoted directive or escaped path')
    return declarations


def relocate_modulemap(raw, source, destination, map_path):
    substitutions, pieces, offset = [], [], 0
    for match in modulemap_declarations(raw):
        literal = match['path'].decode('utf-8')
        old_path = Path(literal)
        resolved = old_path if old_path.is_absolute() else source.parent / old_path
        target = map_path(resolved)
        require(target.is_file() or target.is_dir(), 'Original module map target was not exported')
        replacement = Path(os.path.relpath(target, destination.parent)).as_posix().encode('utf-8')
        require(b'"' not in replacement and b'\\' not in replacement,
                'Unsafe relocated module map declaration')
        start, finish = match.span('path')
        pieces.extend((raw[offset:start], replacement))
        substitutions.append({'start': start, 'finish': finish,
                              'original': literal, 'replacement': replacement.decode('utf-8')})
        offset = finish
    require(substitutions, 'Generated module map has no recognized header or umbrella declaration')
    pieces.append(raw[offset:])
    relocated = b''.join(pieces)
    inverse, offset = [], 0
    matches = modulemap_declarations(relocated)
    require(len(matches) == len(substitutions), 'Module map declaration count changed')
    for match, item in zip(matches, substitutions):
        require(match['path'].decode('utf-8') == item['replacement'], 'Module map relocation differs')
        start, finish = match.span('path')
        inverse.extend((relocated[offset:start], item['original'].encode('utf-8')))
        offset = finish
    inverse.append(relocated[offset:])
    require(b''.join(inverse) == raw, 'Module map changed outside exact declaration paths')
    return relocated, substitutions


def export_clang_declarations(derived, exported, collection, source, lock_path):
    derived, exported = Path(derived), Path(exported)
    require(not derived.is_symlink() and not exported.is_symlink(),
            'Producer or exported Clang root is an alias')
    derived, exported = derived.resolve(strict=True), exported.resolve(strict=True)
    require(derived.name == 'producer-derived' and exported.name == 'distribution'
            and derived.parent == exported.parent, 'Unowned Clang declaration export root')
    require(collection.get('status') == 'ACTUAL_COMPILER_FULL_GRAPHS_COLLECTED_SURFACE_NOT_YET_VERIFIED'
            and collection.get('module') == TARGET
            and collection.get('target') == 'arm64-apple-ios27.0-simulator'
            and all(collection.get(key) == source[other] for key, other in
                    [('source_sha', 'head_sha'), ('run_id', 'run_id'), ('run_attempt', 'run_attempt')]),
            'Original Clang compiler receipt identity differs')
    maps, includes = clang_arguments(collection['compiler_arguments'])
    package_root = unaliased(derived / 'SourcePackages/checkouts', derived, True)
    generated = unaliased(derived / 'Build/Intermediates.noindex/GeneratedModuleMaps-iphonesimulator', derived, True)
    product_include = derived / 'Build/Products/Debug-Anytype-iphonesimulator/include'
    target_build = derived / ('Build/Intermediates.noindex/Anytype.build/'
                              'Debug-Anytype-iphonesimulator/' + TARGET + '.build')
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
    write_new(exported / MANIFEST, (json.dumps(result, indent=2, sort_keys=True) + '\n').encode())
    return result


def declaration_inventory(exported):
    result = {}
    for name in ('Clang', 'Include'):
        directory = exported / name
        if not os.path.lexists(directory):
            continue
        unaliased(directory, exported, True)
        for relative, item in inventory(directory).items():
            relative_path(relative)
            require(Path(relative).suffix.lower() not in TRANSLATION_SUFFIXES,
                    'Implementation translation unit in exported Clang declarations')
            result[name + '/' + relative] = item
    return result


def read_clang_imports(exported, expected_identity):
    exported = Path(exported)
    require(not exported.is_symlink(), 'Exported Clang root is an alias')
    exported = exported.resolve(strict=True)
    manifest = unaliased(exported / MANIFEST, exported, False)
    raw = stable_bytes(manifest)
    require(len(raw) <= 32 * 1024 * 1024, 'Oversized Clang declaration manifest')
    identity_fields = ('source_sha', 'run_id', 'run_attempt', 'original_package_lock_sha256')
    require(isinstance(expected_identity, dict)
            and set(expected_identity) == {*identity_fields, 'manifest_sha256'}
            and all(isinstance(value, str) for value in expected_identity.values())
            and re.fullmatch(r'[0-9a-f]{40}', expected_identity['source_sha'])
            and re.fullmatch(r'[1-9][0-9]*', expected_identity['run_id'])
            and re.fullmatch(r'[1-9][0-9]*', expected_identity['run_attempt'])
            and re.fullmatch(r'[0-9a-f]{64}', expected_identity['original_package_lock_sha256'])
            and re.fullmatch(r'[0-9a-f]{64}', expected_identity['manifest_sha256']),
            'Missing externally admitted Clang producer identity')
    require(hashlib.sha256(raw).hexdigest() == expected_identity['manifest_sha256'],
            'Clang manifest differs from its externally admitted digest')
    result = json.loads(raw)
    require(isinstance(result, dict) and result.get('schema') == 1
            and result.get('status') == 'ORIGINAL_CLANG_DECLARATIONS_EXPORTED_NOT_QUALIFIED',
            'Unsupported Clang declaration manifest')
    require(all(result.get(key) == expected_identity[key] for key in identity_fields),
            'Clang manifest producer identity differs')
    require(result.get('implementation_translation_units_exported_or_added') is False
            and result.get('consumer_or_native_qualification') is False,
            'Clang declarations cannot claim consumer or native qualification')
    require(isinstance(result.get('files'), dict) and 1 <= len(result['files']) <= 40000,
            'Missing or excessive exported Clang input inventory')
    for relative, expected in result['files'].items():
        relative_path(relative)
        require(relative.startswith(('Clang/', 'Include/')), 'Clang inventory escapes its export namespace')
        require(isinstance(expected, dict) and set(expected) == {'bytes', 'sha256'}
                and type(expected['bytes']) is int and 0 <= expected['bytes'] <= 8 * 1024 * 1024
                and isinstance(expected['sha256'], str) and re.fullmatch(r'[0-9a-f]{64}', expected['sha256']),
                'Invalid Clang declaration file commitment')
        path = unaliased(exported / relative, exported, False)
        require(path.stat().st_size == expected['bytes'] and sha256(path) == expected['sha256'],
                'Exported Clang declaration differs')
    require(sum(item['bytes'] for item in result['files'].values()) <= 64 * 1024 * 1024,
            'Original Clang declaration closure exceeds reviewed size bound')
    require(declaration_inventory(exported) == result['files'],
            'Clang declaration membership or exact bytes changed')
    maps, roots = result.get('module_maps'), result.get('header_search_paths')
    require(isinstance(maps, list) and 1 <= len(maps) <= 128
            and all(isinstance(item, str) for item in maps) and len(maps) == len(set(maps))
            and isinstance(roots, list) and 1 <= len(roots) <= 256
            and all(isinstance(item, str) for item in roots) and len(roots) == len(set(roots)),
            'Missing or duplicate exported Clang import roots')
    provenance = result.get('module_map_provenance')
    require(isinstance(provenance, list) and len(provenance) == len(maps)
            and all(isinstance(item, dict) for item in provenance)
            and [item.get('path') for item in provenance] == maps,
            'Clang module map provenance differs from the exact import order')
    for relative in maps:
        relative_path(relative)
        require(relative in result['files'] and relative.endswith('.modulemap'),
                'Unrecorded exported Clang module map')
    for item in provenance:
        require(item.get('exported_sha256') == result['files'][item['path']]['sha256']
                and item.get('transformation') in {'EXACT_ORIGINAL_TRACKED_BYTES',
                                                  'EXACT_DECLARATION_PATH_RELOCATION'},
                'Clang module map bytes or transformation differ')
    for relative in roots:
        relative_path(relative)
        require(relative == 'Include' or relative.startswith('Clang/Packages/'),
                'Clang include root escapes the original declaration closure')
        unaliased(exported / relative, exported, True)
    return {'module_maps': maps, 'header_search_paths': roots}
