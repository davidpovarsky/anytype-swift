"""Use the pinned original install-name reader for the exact Release platform.

The qualified Simulator helper stays byte-identical. Its complete parser,
file-opening checks, install-name/rpath and consumer reachability checks are
reused in an isolated namespace. Only its final platform predicate (and the
matching diagnostic) is specialized for a genuine device Release image.
No Mach-O input bytes, observed platform value or prefix digest are rewritten.
"""
import ast
import copy
import hashlib
from pathlib import Path
import types

ORIGINAL_HELPER_SHA256 = 'a5555c17dd7609558577a622e4df25424e9dea16d01e7f354600e62a21b483f9'
PLATFORMS = {'iphoneos': 2, 'iphonesimulator': 7}
ORIGINAL_PLATFORM_CHECK = """require(
    len(result['build_versions']) == 1 and result['build_versions'][0]['platform'] == 7,
    'Actual load-command image is not uniquely an iOS Simulator binary')"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def original_reader(source_root, platform_name):
    require(isinstance(platform_name, str) and platform_name in PLATFORMS,
            'Release install-name reader requires an explicit supported platform')
    root = Path(source_root)
    require(root.is_absolute() and root.resolve(strict=True) == root,
            'Original reader source root must be exact and unaliased')
    path = root / 'Tools/OriginalEditor/framework_install_names.py'
    require(path.is_file() and not path.is_symlink() and path.resolve(strict=True) == path,
            'Original reader source must be a regular unaliased file')
    raw = path.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == ORIGINAL_HELPER_SHA256,
            'Qualified original install-name reader changed')
    tree = ast.parse(raw, filename=str(path))
    original_ast = ast.dump(tree, include_attributes=False)
    functions = [node for node in tree.body
                 if isinstance(node, ast.FunctionDef) and node.name == 'parse_load_commands']
    require(len(functions) == 1, 'Original parser identity differs')
    parser = functions[0]
    check = ast.parse(ORIGINAL_PLATFORM_CHECK).body[0]
    require(ast.dump(parser.body[-2], include_attributes=False)
            == ast.dump(check, include_attributes=False),
            'Original exact platform predicate differs')
    if platform_name == 'iphoneos':
        adapted = copy.deepcopy(check)
        adapted.value.args[0].values[1].comparators[0] = ast.Constant(value=2)
        adapted.value.args[1] = ast.Constant(
            value='Actual load-command image is not uniquely an iOS device binary')
        parser.body[-2] = adapted
    adapted_ast = ast.dump(tree, include_attributes=False)
    # Mechanically prove that every other original AST node remains intact.
    restored = copy.deepcopy(tree)
    restored_parser = next(node for node in restored.body
                           if isinstance(node, ast.FunctionDef) and node.name == 'parse_load_commands')
    restored_parser.body[-2] = copy.deepcopy(check)
    require(ast.dump(restored, include_attributes=False) == original_ast,
            'Platform specialization changed unrelated original validation')
    module = types.ModuleType('_qualified_original_release_install_names')
    module.__file__ = str(path)
    exec(compile(ast.fix_missing_locations(tree), str(path), 'exec'), module.__dict__)
    admission = {'source_path': str(path), 'source_sha256': ORIGINAL_HELPER_SHA256,
                 'original_ast_sha256': hashlib.sha256(original_ast.encode()).hexdigest(),
                 'effective_ast_sha256': hashlib.sha256(adapted_ast.encode()).hexdigest(),
                 'requested_platform': platform_name, 'required_macho_platform': PLATFORMS[platform_name],
                 'only_specialization': ('final platform predicate7->2 and diagnostic'
                                        if platform_name == 'iphoneos' else 'none'),
                 'original_file_unchanged': True, 'binary_bytes_rewritten': 0}
    return module, admission


def parse_load_commands(prefix, file_bytes, platform_name, *, source_root):
    reader, _ = original_reader(source_root, platform_name)
    return reader.parse_load_commands(prefix, file_bytes)


def verify_framework_install_name(binary, platform_name, *, source_root):
    reader, admission = original_reader(source_root, platform_name)
    result = reader.verify_framework_install_name(binary)
    result['release_platform_admission'] = admission
    return result


def verify_consumer_install_name(app, platform_name, *, source_root):
    reader, admission = original_reader(source_root, platform_name)
    result = reader.verify_consumer_install_name(app)
    result['release_platform_admission'] = admission
    return result
