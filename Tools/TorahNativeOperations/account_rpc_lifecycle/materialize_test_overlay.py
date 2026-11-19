"""Prepare a Go compile overlay after the original pinned account-RPC composition.

This is an explicit future build input, not a dispatcher or a product writer.
Existing production files are read and hash checked, never overwritten. A fresh
empty package directory permits Go to discover the separately overlaid helper.
"""
from pathlib import Path
import argparse
import hashlib
import json

HERE = Path(__file__).resolve().parent
sha = lambda data: hashlib.sha256(data).hexdigest()


def prepare(heart: Path, existing: Path, output: Path) -> dict:
    heart, existing, output = heart.resolve(strict=True), existing.resolve(strict=True), output.resolve()
    assert not output.exists(), 'Refusing to replace an existing build overlay'
    manifest = json.loads((HERE / 'candidate.json').read_text())
    assert manifest['app_sha'] == '16b7493fa05bdc3abbae190c6e6c364c81874eea'
    assert manifest['heart_sha'] == 'd98420b1113536afd08cde6de9a5816f6d27ffff'
    assert manifest['scope'] == 'TEST_COMPILE_OVERLAYS_ONLY_NOT_SHIPPED_PRODUCT'
    assert sha((HERE / 'test-composition.patch').read_bytes()) == manifest['patch_sha256']
    original = json.loads(existing.read_text())
    assert set(original) == {'Replace'} and isinstance(original['Replace'], dict)
    replacements = dict(original['Replace'])
    added = {}
    for entry in manifest['instrumented']:
        target = heart / entry['path']
        source = HERE / 'overlay' / entry['path']
        assert target.is_file() and not target.is_symlink()
        assert sha(target.read_bytes()) == entry['before_sha256'], 'Wrong composed native input: ' + entry['path']
        assert source.is_file() and not source.is_symlink() and sha(source.read_bytes()) == entry['after_sha256']
        assert str(target) not in replacements, 'Test overlays cannot hide an existing replacement'
        added[str(target)] = str(source)
    for target_name, entry in manifest['added'].items():
        target, source = heart / target_name, HERE / entry['fixture']
        assert not target.exists() and not target.is_symlink()
        assert source.is_file() and not source.is_symlink() and sha(source.read_bytes()) == entry['sha256']
        assert str(target) not in replacements
        added[str(target)] = str(source)
    helper_package = heart / 'util/pinkhat2test'
    assert not helper_package.exists(), 'Expected a fresh test-only helper package'
    helper_package.mkdir()
    replacements.update(added)
    output.write_text(json.dumps({'Replace': replacements}, indent=2, sort_keys=True) + '\n')
    return {'scope': manifest['scope'], 'candidate_sha256': sha((HERE / 'candidate.json').read_bytes()),
            'original_overlay_sha256': sha(existing.read_bytes()), 'composed_overlay_sha256': sha(output.read_bytes()),
            'added_overlay_entries': len(added), 'product_source_mutations': 0, 'native_execution': 'NOT_RUN'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--heart', type=Path, required=True)
    parser.add_argument('--existing-overlay', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.heart, args.existing_overlay, args.output)))
