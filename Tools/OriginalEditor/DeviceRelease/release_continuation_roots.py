"""Bind relocated postbuild outputs to their original actual compiler roots."""
import hashlib
import json
import os
from pathlib import Path
import uuid
from clang_product_closure import stable_bytes
from pbx_source import require
from release_contract import identity


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def exact_path(path, *, directory):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts
            and path.resolve(strict=True) == path and not path.is_symlink(),
            'Aliased or nonabsolute continuation ownership path')
    require(path.is_dir() if directory else path.is_file(),
            'Unexpected continuation ownership path type')
    return path


def admit_roots(derived, exported, collection, source, *, quarantined=False):
    derived, exported = Path(derived), Path(exported)
    require(derived.name == 'producer-derived' and exported.name == 'distribution',
            'Unowned Clang declaration export root')
    # Preserve the original direct-build relationship. A distinct pair is
    # accepted only through the actual source-bound continuation proof below.
    if derived.parent == exported.parent:
        return None
    old_work = exact_path(derived.parent, directory=True)
    work = exact_path(exported.parent, directory=True)
    exact_path(exported, directory=True)
    proof = collection.get('collection_continuation')
    require(isinstance(proof, dict), 'Different compiler/export roots require original continuation proof')
    evidence = exact_path(Path(collection['output_directory']).parent, directory=True)
    require(Path(collection['output_directory']) == evidence / 'actual-public-symbol-graphs',
            'Foreign graph collection output directory')
    collection_path = exact_path(evidence / 'compiler-symbolgraph-collection.json', directory=False)
    require(json.loads(stable_bytes(collection_path)) == collection,
            'Clang ownership must use the exact actual graph collection receipt')
    continuation_path = exact_path(evidence / 'continuation.json', directory=False)
    continuation_raw = stable_bytes(continuation_path)
    continuation = json.loads(continuation_raw)
    compiler_evidence = exact_path(proof['compiler_evidence_root'], directory=True)
    descriptor = exact_path(compiler_evidence / 'release-execution.json', directory=False)
    descriptor_raw = stable_bytes(descriptor)
    execution = json.loads(descriptor_raw)
    root = exact_path(execution['root'], directory=True)
    build_root = exact_path(root / 'build', directory=True)
    for candidate in [old_work, work, evidence, compiler_evidence]:
        require(candidate.is_relative_to(build_root) and candidate != build_root,
                'Compiler/continuation root escapes original source build directory')
    require(not old_work.is_relative_to(work) and not work.is_relative_to(old_work)
            and not evidence.is_relative_to(work) and not work.is_relative_to(evidence)
            and not evidence.is_relative_to(compiler_evidence)
            and not compiler_evidence.is_relative_to(evidence),
            'Original compiler and continuation roots overlap')
    continuation_id = continuation.get('execution_id', '')
    require(continuation.get('schema') == 'otzaria.original-editor.release-postbuild-continuation/1'
            and continuation_id.startswith('local-')
            and str(uuid.UUID(continuation_id[6:])) == continuation_id[6:]
            and continuation_id != execution['execution_id']
            and continuation.get('compiler_executions') == 0
            and continuation.get('previous_evidence') == str(compiler_evidence)
            and continuation.get('previous_work') == str(old_work)
            and continuation.get('evidence_root') == str(evidence)
            and continuation.get('work_root') == str(work)
            and continuation.get('source_sha') == execution['source_sha'] == source['head_sha']
            and continuation.get('build_run_id') == execution['execution_id'] == source['run_id']
            and execution.get('work_root') == str(old_work)
            and execution.get('evidence_root') == str(compiler_evidence)
            and source['execution_identity'] == identity(execution, descriptor)
            and proof.get('execution_id') == continuation_id
            and proof.get('original_compiler_execution_id') == execution['execution_id']
            and proof.get('compiler_descriptor_path') == str(descriptor)
            and proof.get('compiler_descriptor_sha256') == continuation.get('previous_descriptor_sha256') == digest(descriptor_raw)
            and proof.get('continuation_sha256') == digest(continuation_raw)
            and proof.get('compiler_executions') == 0
            and proof.get('original_evidence_rewritten') is False,
            'Distinct Clang roots are not bound to the actual original compiler and continuation')
    original_terminal = exact_path(compiler_evidence / 'execution.json', directory=False)
    require(digest(stable_bytes(original_terminal)) == continuation['previous_execution_sha256'],
            'Original compiler terminal receipt changed')
    if quarantined:
        retained = exact_path(work / 'producer-derived-preserved', directory=True)
        move_path = exact_path(evidence / 'producer-build-path-absent.json', directory=False)
        move = json.loads(stable_bytes(move_path))
        require(not os.path.lexists(derived)
                and move == {'original': str(derived), 'preserved_at': str(retained),
                             'original_path_exists': False, 'deleted': False},
                'Original compiler path must remain absent with its exact retained move recorded')
    else:
        exact_path(derived, directory=True)
    return {'status': 'EXACT_ORIGINAL_COMPILER_AND_FRESH_CONTINUATION_ROOTS',
            'original_derived': str(derived), 'continuation_distribution': str(exported),
            'compiler_descriptor_sha256': digest(descriptor_raw),
            'graph_collection_sha256': digest(stable_bytes(collection_path)),
            'continuation_sha256': digest(continuation_raw),
            'original_compiler_run_id': execution['execution_id'],
            'continuation_id': continuation_id, 'producer_quarantined': quarantined}
