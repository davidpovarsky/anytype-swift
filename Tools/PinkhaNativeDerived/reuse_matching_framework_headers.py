"""Preserve verified header timestamps when only Heart implementation changed.

No old binary is installed. Matching header/module-map/plist bytes may keep the
timestamps used by the cached Swift build; new native binaries keep their dates.
"""
import argparse
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tarfile

from build_custom_heart import digest, git

parser = argparse.ArgumentParser(__doc__)
parser.add_argument('--app-source', required=True, type=Path)
parser.add_argument('--previous-archive', required=True, type=Path)
parser.add_argument('--evidence', required=True, type=Path)
args = parser.parse_args()
app = args.app_source.resolve()
if git(app, 'branch', '--show-current') != 'codex/torah-native-derived-properties-20261103':
    raise RuntimeError('Wrong isolated branch')
accepted = json.loads((app/'docs/pinkha/torah-integration/evidence/universal-properties-r13/xcode-42740484502/custom-heart-build.json').read_text())
installed = app/'Dependencies/Middleware'
current = json.loads((installed/'PinkhaNativeHeartBuild.json').read_text())
if accepted['heart_sha'] != current['heart_sha'] or accepted['patch_sha256'] == current['patch_sha256']:
    raise RuntimeError('This helper requires the accepted base and a genuinely new native patch')
framework = installed/'Lib.xcframework'
before_binaries = {item['path']: digest(framework/item['path']) for item in current['artifacts']
                   if PurePosixPath(item['path']).name == 'Lib'}
old_hashes = {item['path']: item['sha256'] for item in accepted['artifacts']}
new_hashes = {item['path']: item['sha256'] for item in current['artifacts']}
if any(sha != new_hashes.get(path) for path, sha in before_binaries.items()):
    raise RuntimeError('A new native binary differs from its verified build receipt')
if not before_binaries or any(sha == old_hashes.get(path) for path, sha in before_binaries.items()):
    raise RuntimeError('An unchanged old native binary was supplied')
restored = []
with tarfile.open(args.previous_archive) as archive:
    members = archive.getmembers()
    receipt = next(item for item in members if PurePosixPath(item.name).name == 'PinkhaNativeHeartBuild.json')
    if json.load(archive.extractfile(receipt)) != accepted:
        raise RuntimeError('The prior archive is not the exact accepted revision-13 build')
    for member in members:
        relative = PurePosixPath(member.name)
        if not member.isfile() or not relative.parts or relative.parts[0] != 'Lib.xcframework':
            continue
        relative = PurePosixPath(*relative.parts[1:])
        if relative.suffix not in {'.h', '.modulemap', '.plist'}:
            continue
        path = framework/str(relative)
        if not path.is_file() or path.is_symlink():
            continue
        sha = digest(path)
        old_bytes = archive.extractfile(member).read()
        if sha != old_hashes.get(str(relative)) or hashlib.sha256(old_bytes).hexdigest() != sha:
            continue
        seconds = member.pax_headers.get('mtime', str(member.mtime))
        timestamp = int(Decimal(seconds)*Decimal(1_000_000_000))
        os.utime(path, ns=(path.stat().st_atime_ns, timestamp))
        restored.append(dict(path=str(relative), sha256=sha, mtime_ns=timestamp))
if not restored:
    raise RuntimeError('No byte-identical accepted framework headers were found')
if before_binaries != {path: digest(framework/path) for path in before_binaries}:
    raise RuntimeError('A new native binary changed during header timestamp restoration')
args.evidence.mkdir(parents=True, exist_ok=True)
(args.evidence/'header-input-reuse.json').write_text(json.dumps(dict(status='MATCHED_HEADERS_ONLY',
    previous_source_run_id=42740484502, previous_patch_sha256=accepted['patch_sha256'],
    new_patch_sha256=current['patch_sha256'], untouched_new_binaries=before_binaries,
    restored_headers=restored), indent=2)+'\n')
print(json.dumps(dict(restored_matching_headers=len(restored), new_binaries_unchanged=True)))
