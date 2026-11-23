"""Admit the original producer's static/DYLIB partition without rebuilding."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from framework_products import inventory


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def header_role(raw, binary):
    require(isinstance(raw, bytes) and 0 < len(raw) <= 2 * 1024**2,
            'Missing or oversized original framework header')
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as error:
        raise RuntimeError('Original framework header is not UTF-8') from error
    rows, locations, archives = [], [], 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(('MH_', 'FAT_')):
            row = re.fullmatch(
                r'MH_MAGIC(?:_64)?\s+\S+\s+\S+\s+0x[0-9a-fA-F]+\s+(\S+)\s+\d+\s+\d+(?:\s+.*)?',
                stripped)
            require(row is not None, 'Unknown original Mach-O header row')
            rows.append(row.group(1))
        if line.startswith('Archive : '):
            archives += 1
            location = line.removeprefix('Archive : ')
            locations.append(location)
        elif line.startswith('/'):
            locations.append(line)
    require(rows and locations, 'Original framework header has no typed image')
    require(all(location == binary + ':' or location.startswith(binary + ' (architecture ')
                or location.startswith(binary + '(') for location in locations),
            'Original framework header names a different binary')
    kinds = set(rows)
    if kinds == {'DYLIB'} and archives == 0:
        role = 'DYLIB_EMBED'
    elif kinds == {'OBJECT'} and archives > 0:
        role = 'STATIC_ARCHIVE_DISTRIBUTION_ONLY'
    else:
        raise RuntimeError('Unknown or mixed original framework image kinds')
    require(bool(re.search(r'\bDYLIB\b', text)) == (role == 'DYLIB_EMBED'),
            'Header classification differs from original producer selection')
    return role, len(rows), archives


def derive_original_framework_roles(read_member, exported, retained_consumer):
    """read_member must read the already digest-authenticated original archive."""
    frameworks = exported['frameworks']
    files = exported['files']
    require(isinstance(frameworks, list) and frameworks
            and len(frameworks) == len(set(frameworks)), 'Duplicate or missing original frameworks')
    require(all(isinstance(name, str) and re.fullmatch(r'[A-Za-z0-9_.+-]+\.framework', name)
                for name in frameworks), 'Invalid original framework name')
    file_frameworks = {path.split('/')[1] for path in files if path.startswith('Frameworks/')}
    require(file_frameworks == set(frameworks), 'Original declared distribution framework set differs')
    rows = []
    for index, name in enumerate(frameworks):
        stem = 'framework-header-' + str(index)
        try:
            raw_command = read_member(stem + '.command.json')
            stdout = read_member(stem + '.stdout.log')
            stderr = read_member(stem + '.stderr.log')
        except (KeyError, FileNotFoundError) as error:
            raise RuntimeError('Missing original framework header receipt: ' + name) from error
        command = json.loads(raw_command)
        argv = command.get('command')
        executable = name.removesuffix('.framework')
        require(isinstance(argv, list) and len(argv) == 3 and argv[:2] == ['otool', '-hv']
                and isinstance(argv[2], str) and PurePosixPath(argv[2]).is_absolute()
                and PurePosixPath(argv[2]).parts[-4:] == ('distribution', 'Frameworks', name, executable),
                'Original header command index/name/binary differs: ' + name)
        require('Frameworks/' + name + '/' + executable in files
                and 'Frameworks/' + name + '/Info.plist' in files,
                'Original header executable is absent from the admitted distribution')
        require(type(command.get('returncode')) is int and command['returncode'] == 0
                and command.get('timed_out') is False, 'Original header command did not succeed')
        require(hashlib.sha256(stdout).hexdigest() == command.get('stdout_sha256')
                and hashlib.sha256(stderr).hexdigest() == command.get('stderr_sha256'),
                'Original header command stream commitment differs')
        role, image_count, archive_count = header_role(stdout, argv[2])
        rows.append({
            'name': name, 'original_index': index, 'executable': executable, 'role': role,
            'command_sha256': hashlib.sha256(raw_command).hexdigest(),
            'stdout_sha256': command['stdout_sha256'], 'stderr_sha256': command['stderr_sha256'],
            'image_count': image_count, 'archive_count': archive_count,
            'command_exit_code': 0, 'timed_out': False,
        })
    dynamic = sorted(row['name'] for row in rows if row['role'] == 'DYLIB_EMBED')
    static = sorted(row['name'] for row in rows if row['role'] == 'STATIC_ARCHIVE_DISTRIBUTION_ONLY')
    require('AnytypeOriginalEditor.framework' in dynamic, 'Original dynamic editor is absent')
    directories = retained_consumer['directories']
    original_app_dirs = sorted(path.removeprefix('Frameworks/') for path in directories
                               if path.startswith('Frameworks/') and path.count('/') == 1)
    original_app_file_dirs = {path.split('/')[1] for path in retained_consumer['file_modes']
                             if path.startswith('Frameworks/')}
    require(original_app_dirs == dynamic and original_app_file_dirs == set(dynamic),
            'Original signed consumer membership differs from the original DYLIB selection')
    return {
        'schema': 'otzaria.original-producer.framework-roles/1',
        'frameworks': frameworks, 'dynamic_embeds': dynamic, 'static_distribution_only': static,
        'original_header_receipts': rows, 'original_signed_app_directories': original_app_dirs,
        'scope': 'Authenticated original producer role partition; no runtime qualification',
    }


def verify_embedded_frameworks(app, distribution, exported, roles):
    """Keep complete byte equality for every genuine dynamic embed."""
    app, distribution = Path(app), Path(distribution)
    frameworks = exported['frameworks']
    require(roles.get('schema') == 'otzaria.original-producer.framework-roles/1'
            and roles['frameworks'] == frameworks, 'Original role proof belongs to a different distribution')
    dynamic, static = roles['dynamic_embeds'], roles['static_distribution_only']
    require(len(dynamic) == len(set(dynamic)) and len(static) == len(set(static))
            and set(dynamic).isdisjoint(static) and set(dynamic) | set(static) == set(frameworks),
            'Original role proof has missing, duplicate or extra frameworks')
    require(len(roles['original_header_receipts']) == len(frameworks)
            and [row['name'] for row in roles['original_header_receipts']] == frameworks,
            'Original role proof lost its indexed command binding')
    require(dynamic == sorted(row['name'] for row in roles['original_header_receipts']
                              if row['role'] == 'DYLIB_EMBED')
            and static == sorted(row['name'] for row in roles['original_header_receipts']
                                 if row['role'] == 'STATIC_ARCHIVE_DISTRIBUTION_ONLY'),
            'Original role partition differs from its authenticated header rows')
    app_root, distribution_root = app / 'Frameworks', distribution / 'Frameworks'
    require(app_root.is_dir() and not app_root.is_symlink()
            and distribution_root.is_dir() and not distribution_root.is_symlink(),
            'Original framework roots are absent or aliased')
    app_entries, distribution_entries = list(app_root.iterdir()), list(distribution_root.iterdir())
    require(all(path.is_dir() and not path.is_symlink() for path in app_entries + distribution_entries),
            'Unknown non-directory or aliased framework entry')
    require(sorted(path.name for path in app_entries) == dynamic,
            'Signed app has a missing, extra or static framework embed')
    require(sorted(path.name for path in distribution_entries) == sorted(frameworks),
            'Restored complete distribution framework set differs')
    checked = {}
    for name in frameworks:
        source_files = inventory(distribution_root / name)
        expected_files = {path.removeprefix('Frameworks/' + name + '/'): value
                          for path, value in exported['files'].items()
                          if path.startswith('Frameworks/' + name + '/')}
        require(source_files and source_files == expected_files,
                'Restored framework bytes differ from the complete original inventory: ' + name)
        if name in static:
            require(not (app_root / name).exists(), 'Original static archive was embedded into the signed app')
            continue
        app_files = inventory(app_root / name)
        require(app_files == source_files, 'Signed dynamic framework inventory differs: ' + name)
        checked[name] = {'files': len(app_files), 'bytes': sum(row['bytes'] for row in app_files.values())}
    return {
        'schema': 'otzaria.original-producer.dynamic-embed-binding/1',
        'status': 'EXACT_ORIGINAL_DYNAMIC_EMBED_SET_AND_BYTES_PASS',
        'dynamic_frameworks': checked, 'static_distribution_only': static,
        'complete_distribution_frameworks_checked': len(frameworks),
        'runtime_execution': False, 'binary_mutations': 0,
    }
