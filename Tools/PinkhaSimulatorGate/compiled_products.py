"""Record actual native test products for later reviewed build-reuse decisions.

No build or test reuse is enabled by this inventory. Capture only after the
native build completed successfully, after execution returns or fails. Restored
or stale unrelated entries may remain: observing bytes is not build provenance.
Acceptance outcomes remain independent.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from validate_release import require, digest


def capture_products(derived, evidence, source_sha, build_flags):
    products = derived / 'Build/Products'
    require(products.is_dir(), 'Actual native build products are missing')
    target = Path(evidence) / 'compiled-products'
    require(not target.exists(), 'Refuse stale compiled product inventory')
    target.mkdir(parents=True)
    entries = {}
    for path in sorted(products.rglob('*')):
        relative = path.relative_to(products)
        # These are per-selection copies made by run_selection, not Xcode's
        # original build configuration; they are regenerated on each attempt.
        if relative.parent == Path('.') and relative.suffix == '.xctestrun' and relative.name.startswith('UI27-'):
            continue
        if path.is_symlink():
            entries[relative.as_posix()] = dict(kind='symlink', target=path.readlink().as_posix())
        elif path.is_file():
            with path.open('rb') as source:
                entries[relative.as_posix()] = dict(kind='file', bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(source, 'sha256').hexdigest())
    require(any(p.endswith('.xctestrun') for p in entries), 'Original Xcode test configuration missing')
    require(any('.xctest/' in p and Path(p).name == 'AnytypeTests' for p in entries), 'Actual native test executable missing')
    source_inputs = (derived / 'Build/PinkhaSourceInputs.json').read_bytes()
    inputs = json.loads(source_inputs)
    require(inputs.get('source_sha') == source_sha, 'Actual compiled source manifest identity differs')
    (target / 'source-inputs.json').write_bytes(source_inputs)
    manifest = dict(status='OBSERVED_PRODUCTS_INVENTORY_NOT_BUILD_PROVENANCE', source_sha=source_sha,
                    captured_at=datetime.now(timezone.utc).isoformat(), capture_phase='AFTER_EXECUTION_OR_FAILURE',
                    every_entry_build_origin_verified=False, build_reuse_enabled=False,
                    build_flags=build_flags, source_inputs_sha256=digest(source_inputs),
                    symlink_targets_require_separate_dependency_review=True, products=entries,
                    native_acceptance_reused=False, ui_acceptance_reused=False)
    data = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    (target / 'manifest.json').write_bytes(data)
    return dict(status=manifest['status'], manifest_path='compiled-products/manifest.json',
                manifest_sha256=digest(data), source_inputs_path='compiled-products/source-inputs.json',
                source_inputs_sha256=digest(source_inputs), entries=len(entries), build_reuse_enabled=False)
