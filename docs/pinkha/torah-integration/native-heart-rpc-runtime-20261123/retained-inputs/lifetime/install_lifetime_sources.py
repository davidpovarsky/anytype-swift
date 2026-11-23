"""Install only the reviewed eight-file original application-lifetime overlay.

The preceding twenty-file owned importer closure must already match exactly.
All source/preimage/path validation completes before the first write. This
installer starts no app, import, schema, compiler or test, and changes no module.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ORIGINAL = 'd98420b1113536afd08cde6de9a5816f6d27ffff'
EXPECTED_PATHS = {
    'core/application/account_create.go',
    'core/application/account_create_from_export.go',
    'core/application/account_move.go',
    'core/application/account_select.go',
    'core/application/account_stop.go',
    'core/application/application.go',
    'core/application/owned_import_admission.go',
    'core/block/import/owned_import_operation.go',
}


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def install(root, packet, output):
    root, packet = Path(root).resolve(), Path(packet).resolve()
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], check=True,
                          capture_output=True, timeout=30).stdout.decode().strip()
    require(head == ORIGINAL, 'The original native checkout differs')
    manifest = json.loads((packet / 'SOURCE_MANIFEST.json').read_bytes())
    require(len(manifest) == len(EXPECTED_PATHS) and {row['path'] for row in manifest} == EXPECTED_PATHS,
            'The eight-file lifetime source inventory differs')
    preceding = json.loads((packet / 'PRECEDING_COMPILED_CLOSURE.json').read_bytes())
    require(preceding['run_id'] == 45056548826 and preceding['source_commit'] == '3d58f04f938f743b9c3b737cdfedcc10610cbffc'
            and len(preceding['product_hashes']) == 20, 'The preceding native compile commitment differs')
    for relative, expected in preceding['product_hashes'].items():
        target = root / relative
        require(target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(root)
                and hashlib.sha256(target.read_bytes()).hexdigest() == expected,
                'Preceding compiled native source differs: ' + relative)
    pending = []
    for row in manifest:
        relative = Path(row['path'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'Unsafe source path')
        source, target = packet / 'native' / relative, root / relative
        require(source.is_file() and not source.is_symlink() and source.resolve().is_relative_to(packet), 'Aliased packet source')
        require(target.parent.resolve().is_relative_to(root), 'Aliased native target parent')
        data = source.read_bytes()
        require(identity(data) == {key: row[key] for key in ['bytes', 'sha256', 'git_blob']}, 'Packet source changed: ' + str(relative))
        if row['preimage'] is None:
            require(not target.exists() and not target.is_symlink(), 'New native source already exists: ' + str(relative))
        else:
            require(target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(root), 'Missing or aliased original native source')
            require(identity(target.read_bytes()) == row['preimage'], 'Original native preimage differs: ' + str(relative))
        pending.append((target, data, row))
    receipt = {'status': 'INSTALLED_REVIEWED_LIFETIME_SOURCE_ONLY', 'original_commit': ORIGINAL,
               'preceding_compile_run': preceding['run_id'], 'preceding_twenty_inputs_verified': True,
               'files': [], 'tests_executed': 0, 'native_imports_executed': 0,
               'scope': 'Eight source afterimages only. Full original application-package compilation, native lifecycle execution and production route remain separate gates.'}
    for target, data, row in pending:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        require(identity(target.read_bytes()) == identity(data), 'Native source write verification failed')
        receipt['files'].append({'path': row['path'], 'before_sha256': row['preimage']['sha256'] if row['preimage'] else None,
                                 'after_sha256': row['sha256']})
    Path(output).write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--packet', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    arguments = parser.parse_args()
    install(arguments.root, arguments.packet, arguments.output)
