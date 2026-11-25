"""Retain the original dependency verifier across an admitted compiler move.

Only the original sibling-root equality is specialized. The exact original
checker, Git-alternate restrictions, source/blob checks and inventory logic run
in an isolated namespace; qualified SDK files and Git metadata stay unchanged.
"""
import ast
import copy
import hashlib
from pathlib import Path
import types

from pbx_source import require
from release_continuation_roots import admit_roots

ORIGINAL_HELPER_SHA256 = '7b95b4c34d282402645d28741c6a87fd0fc368a9d06f7d7745388b83a02b3544'
ORIGINAL_MAPPING_CHECK = """require(
    checkouts.parts[-3:] == ('producer-derived-preserved', 'SourcePackages', 'checkouts')
    and original_checkouts == checkouts.parents[2] / 'producer-derived/SourcePackages/checkouts',
    'Unreviewed producer quarantine mapping')"""


def original_reader(root, derived, distribution, collection, source):
    root, derived, distribution = map(Path, (root, derived, distribution))
    require(root.is_absolute() and root.resolve(strict=True) == root,
            'Original ownership helper root must be exact and unaliased')
    roots = admit_roots(derived, distribution, collection, source, quarantined=True)
    require(roots is not None and roots['producer_quarantined'] is True,
            'Relocated ownership requires an actual distinct-root continuation')
    helper = root / 'Tools/OriginalEditor/SharedRuntime/verify_framework_ownership.py'
    require(helper.is_file() and not helper.is_symlink()
            and helper.resolve(strict=True) == helper,
            'Original ownership helper must be an unaliased regular file')
    raw = helper.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ORIGINAL_HELPER_SHA256,
            'Qualified original shared ownership verifier changed')
    tree = ast.parse(raw, filename=str(helper))
    original_ast = ast.dump(tree, include_attributes=False)
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == 'retained_git_objects']
    require(len(functions) == 1, 'Original retained Git resolver identity differs')
    resolver = functions[0]
    original_check = ast.parse(ORIGINAL_MAPPING_CHECK).body[0]
    matches = [index for index, node in enumerate(resolver.body)
               if ast.dump(node, include_attributes=False)
               == ast.dump(original_check, include_attributes=False)]
    require(len(matches) == 1, 'Original exact quarantine mapping guard differs')
    position = matches[0]
    adapted = copy.deepcopy(original_check)
    adapted.value.args[0].values[1] = ast.parse(
        'original_checkouts == _continued_original_checkouts', mode='eval').body
    adapted.value.args[0].values.append(ast.parse(
        'checkouts == _continued_retained_checkouts', mode='eval').body)
    resolver.body[position] = adapted
    adapted_ast = ast.dump(tree, include_attributes=False)
    restored = copy.deepcopy(tree)
    restored_resolver = next(node for node in restored.body
                             if isinstance(node, ast.FunctionDef) and node.name == 'retained_git_objects')
    restored_resolver.body[position] = copy.deepcopy(original_check)
    require(ast.dump(restored, include_attributes=False) == original_ast,
            'Continuation mapping changed unrelated original ownership checks')
    module = types.ModuleType('_qualified_original_continued_shared_ownership')
    module.__file__ = str(helper)
    module.__dict__.update(
        _continued_original_checkouts=derived / 'SourcePackages/checkouts',
        _continued_retained_checkouts=distribution.parent / 'producer-derived-preserved/SourcePackages/checkouts')
    exec(compile(ast.fix_missing_locations(tree), str(helper), 'exec'), module.__dict__)
    require(hashlib.sha256(helper.read_bytes()).hexdigest() == ORIGINAL_HELPER_SHA256,
            'Original ownership helper changed while loading')
    admission = {
        'status': 'EXACT_CONTINUED_QUARANTINE_MAPPING_ORIGINAL_CHECKS_RETAINED',
        'original_helper': str(helper), 'original_helper_sha256': ORIGINAL_HELPER_SHA256,
        'original_ast_sha256': hashlib.sha256(original_ast.encode()).hexdigest(),
        'effective_ast_sha256': hashlib.sha256(adapted_ast.encode()).hexdigest(),
        'only_specialization': 'sibling-root equality becomes two exact source-bound original/retained path equalities',
        'whole_original_ast_restores_exactly': True,
        'compiler_root_continuation': roots,
        'original_checkouts': str(derived / 'SourcePackages/checkouts'),
        'retained_checkouts': str(distribution.parent / 'producer-derived-preserved/SourcePackages/checkouts'),
        'original_helper_modified': False, 'git_metadata_modified': False,
    }
    return module, admission


def dependency_inventory(root, checkouts, contract, original_checkouts,
                         distribution, collection, source):
    original_checkouts = Path(original_checkouts)
    derived = original_checkouts.parents[1]
    reader, admission = original_reader(root, derived, distribution, collection, source)
    require(Path(checkouts) == Path(admission['retained_checkouts'])
            and original_checkouts == Path(admission['original_checkouts']),
            'Dependency inventory differs from admitted original/retained roots')
    observed = reader.dependency_source_inventory(
        Path(checkouts), contract, original_checkouts=original_checkouts)
    return observed, admission
