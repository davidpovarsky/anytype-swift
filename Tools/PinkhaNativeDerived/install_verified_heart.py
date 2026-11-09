"""Install only this task's exact, newly built and verified Heart artifact."""
import argparse
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from build_custom_heart import PIN, digest, git, verify_framework_slices

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--archive', required=True, type=Path)
parser.add_argument('--inventory', required=True, type=Path)
parser.add_argument('--patch', required=True, type=Path)
parser.add_argument('--app-source', required=True, type=Path)
parser.add_argument('--source-run-id', required=True)
parser.add_argument('--evidence', required=True, type=Path)
args = parser.parse_args()
inventory = json.loads(args.inventory.read_text())
patch_sha = digest(args.patch)
if patch_sha != inventory['patch_sha256']:
    raise RuntimeError('Current source inventory does not match its exact patch')
if git(args.app_source, 'branch', '--show-current') != 'codex/torah-native-derived-properties-20261103':
    raise RuntimeError('Wrong application branch')
with tempfile.TemporaryDirectory(prefix='pinkha-verified-heart-') as directory:
    staging = Path(directory)
    with tarfile.open(args.archive) as archive:
        archive.extractall(staging, filter='data')
    if {p.name for p in staging.iterdir()} != {'Lib.xcframework', 'PinkhaNativeHeartBuild.json'}:
        raise RuntimeError('Unexpected artifact payload')
    framework = staging / 'Lib.xcframework'
    receipt = json.loads((staging / 'PinkhaNativeHeartBuild.json').read_text())
    marker = 'pinkha-native-derived-v1-' + patch_sha
    if (receipt.get('status') != 'PASS' or receipt.get('target') != 'ios' or
        receipt.get('heart_sha') != PIN or receipt.get('patch_sha256') != patch_sha or
        receipt.get('marker') != marker or receipt.get('files') != inventory['files']):
        raise RuntimeError('Artifact is not the exact current native source revision')
    actual_paths = {str(p.relative_to(framework)) for p in framework.rglob('*') if p.is_file()}
    if actual_paths != {entry['path'] for entry in receipt['artifacts']}:
        raise RuntimeError('Framework file inventory differs')
    for entry in receipt['artifacts']:
        if digest(framework / entry['path']) != entry['sha256']:
            raise RuntimeError('Framework content differs: ' + entry['path'])
    actual_slices = verify_framework_slices(framework, marker)
    slice_key = lambda entry: (entry['path'], entry['architecture'])
    if sorted(actual_slices, key=slice_key) != sorted(receipt.get('binary_slices', []), key=slice_key):
        raise RuntimeError('Framework thin-architecture proof differs')
    destination = args.app_source / 'Dependencies/Middleware'
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / 'Lib.xcframework').exists() or (destination / 'PinkhaNativeHeartBuild.json').exists():
        raise RuntimeError('Refusing to overwrite an existing middleware installation')
    shutil.copytree(framework, destination / 'Lib.xcframework')
    shutil.copyfile(staging / 'PinkhaNativeHeartBuild.json', destination / 'PinkhaNativeHeartBuild.json')
    args.evidence.mkdir(parents=True, exist_ok=True)
    (args.evidence / 'custom-heart-build.json').write_text(json.dumps(receipt, indent=2) + '\n')
    installation = dict(status='PASS', source_run_id=args.source_run_id,
                        archive_sha256=digest(args.archive), patch_sha256=patch_sha,
                        app_source_sha=git(args.app_source, 'rev-parse', 'HEAD'),
                        original_build_app_sha=receipt.get('app_base_sha'), marker=marker)
    (args.evidence / 'heart-installation.json').write_text(json.dumps(installation, indent=2) + '\n')
    print(json.dumps(installation))
