#!/usr/bin/env python3
"""Preserve completed hierarchy build evidence without duplicating binaries."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--repo-root', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    p.add_argument('--build-dir', type=Path, action='append', required=True)
    a = p.parse_args()
    root = a.repo_root.resolve()
    out = a.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    manifest = {'scope': 'Byte-exact completed hierarchy build evidence; binaries and object files remain in their original task-owned build directories.', 'files': [], 'builds': []}
    allowed_suffixes = {'.json', '.log', '.py', '.swift', '.LinkFileList'}
    for directory in a.build_dir:
        directory = directory.resolve()
        receipt = directory / 'result.json'
        proof = json.loads(receipt.read_text(encoding='utf-8'))
        if proof.get('status') not in {'FAIL', 'PASS_EXACT_SOURCE_COMPONENT_BUILD'}:
            raise RuntimeError('completed_build_receipt_required')
        destination = out / directory.name
        destination.mkdir()
        manifest['builds'].append({'originalPath': str(directory), 'status': proof['status'], 'receiptSHA256': sha256(receipt), 'sourceStable': proof.get('sourceStable')})
        for source in sorted(directory.rglob('*')):
            if not source.is_file() or source.suffix not in allowed_suffixes:
                continue
            relative = source.relative_to(directory)
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            before = sha256(source)
            shutil.copyfile(source, target)
            if sha256(source) != before or sha256(target) != before:
                raise RuntimeError('source_changed_during_evidence_archive')
            manifest['files'].append({'source': str(source), 'archivedPath': target.relative_to(root).as_posix(), 'sha256': before, 'bytes': source.stat().st_size})
    final = out / 'archive.json'
    final.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'PASS_BYTE_EXACT_ARCHIVE', 'files': len(manifest['files']), 'builds': len(manifest['builds']), 'archiveSHA256': sha256(final)}))


if __name__ == '__main__':
    main()
