"""Explicit declaration-boundary fixture for pre-existing driver controls, never native source."""
import json
from pathlib import Path

from clang_product_closure import MANIFEST, declaration_inventory
from framework_profile import sha256


def write_clang_fixture(exported, source, lock_sha256):
    exported = Path(exported)
    header = exported / 'Clang/Packages/EXPLICIT_DECLARATION_FIXTURE/include/EXPLICIT.h'
    header.parent.mkdir(parents=True)
    header.write_bytes(b'/* Explicit orchestration boundary fixture, not a native API. */\n')
    modulemap = header.with_name('module.modulemap')
    modulemap.write_bytes(b'module EXPLICIT_DECLARATION_FIXTURE { header "EXPLICIT.h" export * }\n')
    relative = modulemap.relative_to(exported).as_posix()
    proof = {'schema': 1, 'status': 'ORIGINAL_CLANG_DECLARATIONS_EXPORTED_NOT_QUALIFIED',
             'source_sha': source['head_sha'], 'run_id': source['run_id'], 'run_attempt': source['run_attempt'],
             'original_package_lock_sha256': lock_sha256, 'compiler_line_sha256': 'e' * 64,
             'module_maps': [relative], 'header_search_paths': [header.parent.relative_to(exported).as_posix()],
             'module_map_provenance': [{'path': relative, 'exported_sha256': sha256(modulemap),
                                        'transformation': 'EXACT_ORIGINAL_TRACKED_BYTES',
                                        'scope': 'EXPLICIT_DECLARATION_BOUNDARY_FIXTURE_NOT_UPSTREAM'}],
             'files': declaration_inventory(exported),
             'implementation_translation_units_exported_or_added': False,
             'consumer_or_native_qualification': False,
             'scope': 'EXPLICIT_DECLARATION_BOUNDARY_FIXTURE_NO_NATIVE_COMPILATION'}
    manifest = exported / MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(proof, sort_keys=True) + '\n')
    identity = {key: proof[key] for key in ('source_sha', 'run_id', 'run_attempt', 'original_package_lock_sha256')}
    identity['manifest_sha256'] = sha256(manifest)
    return proof, identity
