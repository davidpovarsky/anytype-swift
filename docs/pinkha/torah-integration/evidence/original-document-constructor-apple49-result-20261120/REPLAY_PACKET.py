#!/usr/bin/env python3
"""Reconstruct retained Apple49 inputs and replay their original result validators."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile


def safe_extract(archive, destination):
    with zipfile.ZipFile(archive) as z:
        names = set()
        if z.testzip() is not None:
            raise ValueError('ZIP CRC mismatch')
        for item in z.infolist():
            name = Path(item.filename)
            if (item.filename in names or name.is_absolute() or '..' in name.parts
                    or '\\' in item.filename or (item.external_attr >> 16) & 0o170000 == 0o120000):
                raise ValueError('Unsafe ZIP member')
            names.add(item.filename)
            target = destination / name
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as f:
                    f.write(z.read(item))


def main():
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    packet = Path(__file__).resolve().parent
    index = json.loads((packet / 'PACKET_INDEX.json').read_text())
    for item in index['files']:
        f = packet / item['path']
        raw = f.read_bytes()
        if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('Packet input differs: ' + item['path'])
    output = args.output.resolve()
    if output.exists():
        raise ValueError('Use a new owned output directory; do not overwrite evidence')
    output.mkdir(parents=True)
    for kind in ['api', 'source']:
        for path in (packet / kind).rglob('*.gz'):
            target = output / kind / path.relative_to(packet / kind).with_suffix('')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(gzip.decompress(path.read_bytes()))
    archive = output / 'raw/apple49-44791343024-attempt1.zip'
    archive.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(packet / 'raw' / archive.name, archive)
    safe_extract(archive, output / 'extracted')
    safe_extract(output / 'extracted/Pinkha-Native-Derived-Evidence.zip', output / 'raw/evidence')
    shutil.copyfile(packet / 'VERIFY_RESULT.py', output / 'VERIFY_RESULT.py')
    subprocess.run([sys.executable, '-B', str(output / 'VERIFY_RESULT.py'), '--root', str(output)], check=True)
    print('Replayed retained result validation only; no Swift, XCTest, CI or control test rerun.')


if __name__ == '__main__':
    main()
