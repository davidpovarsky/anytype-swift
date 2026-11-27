#!/usr/bin/env python3
"""Apply the pinned bounded node/LAN progress overlay to an isolated SDK source export."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(root):
    values = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '.git' in relative.parts:
            continue
        if path.is_symlink():
            raise RuntimeError(f'source symlink is not admitted: {relative}')
        if path.is_file():
            if path.stat().st_nlink != 1:
                raise RuntimeError(f'source hard link is not admitted: {relative}')
            values[str(relative)] = sha(path)
    return values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-source', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root = args.sdk_source
    if not root.is_absolute() or root.resolve() != root or not root.is_dir():
        raise RuntimeError('SDK source must be an absolute, independent source directory')
    immutable = [Path('/var/lib/pinkha-root-t2-linux-20261126/build1/current/source'), Path('/var/lib/pinkha-c-filesv2-20261126/acl-refresh-native1/source'), Path('/var/lib/pinkha-c-filesv2-20261126/acl-refresh-overlay1/sdk-source'), Path('/var/lib/pinkha-c-filesv2-20261126/lan-progress-unit2/sdk-source')]
    if any(root == retained or retained in root.parents for retained in immutable):
        raise RuntimeError('the retained qualified source is immutable; use an isolated copy')
    here = Path(__file__).resolve().parent
    manifest = json.loads((here / 'manifest.json').read_text())
    patch = here / 'sdk-lan-progress.patch'
    if sha(patch) != manifest['patchSHA256']:
        raise RuntimeError('patch bytes differ from the reviewed manifest')
    if not (root / 'go.mod').read_text().startswith('module github.com/anyproto/any-sync-sdk\n'):
        raise RuntimeError('target is not the SDK module')
    before = inventory(root)
    for name, expected in manifest['requiredSourcePins'].items():
        if before.get(name) != expected:
            raise RuntimeError(f'previous qualified ACL patch is absent or changed: {name}')
    changes = manifest['changes']
    if all(before.get(row['path']) == row['afterSHA256'] for row in changes):
        print(json.dumps({'status': 'ALREADY_APPLIED_SOURCE_ONLY', 'patchSHA256': sha(patch), 'runtimeAcceptance': False}))
        return
    for row in changes:
        if before.get(row['path']) != row['beforeSHA256']:
            raise RuntimeError(f"unreviewed target source: {row['path']}")
    subprocess.run(['git', 'apply', '--check', '--', str(patch)], cwd=root, check=True)
    if args.check_only:
        print(json.dumps({'status': 'PATCH_APPLICABLE_SOURCE_ONLY', 'patchSHA256': sha(patch), 'runtimeAcceptance': False}))
        return
    subprocess.run(['git', 'apply', '--', str(patch)], cwd=root, check=True)
    after = inventory(root)
    changed = {name for name in before.keys() | after.keys() if before.get(name) != after.get(name)}
    if changed != {row['path'] for row in changes}:
        raise RuntimeError('unexpected source delta')
    for row in changes:
        if after.get(row['path']) != row['afterSHA256']:
            raise RuntimeError(f"applied bytes differ: {row['path']}")
    print(json.dumps({'status': 'APPLIED_SOURCE_ONLY', 'patchSHA256': sha(patch), 'changedFiles': sorted(changed), 'runtimeAcceptance': False}))


if __name__ == '__main__':
    main()
