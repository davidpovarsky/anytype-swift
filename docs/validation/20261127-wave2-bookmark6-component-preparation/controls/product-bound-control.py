#!/usr/bin/env python3
"""One synthetic size-bound control of the exact two AST call sites; no runner import."""
from pathlib import Path
import ast
import hashlib
import json
import time

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'inputs/run_component.py'
raw = SOURCE.read_bytes()
tree = ast.parse(raw)
compiler = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'compiler_inputs')
physical = next(node for node in compiler.body if isinstance(node, ast.FunctionDef) and node.name == 'physical')
calls = [node for node in ast.walk(compiler) if isinstance(node, ast.Assign)
         and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
         and node.value.func.id == 'physical' and len(node.value.keywords) == 1
         and node.value.keywords[0].arg == 'maximum' and isinstance(node.value.keywords[0].value, ast.IfExp)]
assert len(calls) == 2
assert all(ast.unparse(node.value.keywords[0].value) == 'ALLOCATION_CAP if path in product_modules else 16 * 1024 ** 2' for node in calls)


class LengthOnlyBytes:
    """Synthetic read result; represents length only and allocates no large payload."""
    def __init__(self, size):self.size = size
    def __len__(self):return self.size


class SyntheticPhysicalPath(str):
    sizes = {}
    def is_relative_to(self, root):return self.startswith(str(root) + '/')
    def resolve(self, strict=True):return self
    def is_file(self):return True
    def is_symlink(self):return False
    def read_bytes(self):return LengthOnlyBytes(self.sizes[str(self)])


root = '/synthetic/bookmark6'
aggregate = root + '/build/out/Products/Debug-linux-aarch64/PinkhaAnyHost.o'
test_product = root + '/build/out/Products/Debug-linux-aarch64/PinkhaAnyHostTests.so'
crypto = root + '/retained-crypto-objects/Crypto.o'
source = root + '/component/Sources/PinkhaAnyHost/AnyNativePropertyStore.swift'
unlisted_product = root + '/build/out/Products/Debug-linux-aarch64/Unlisted.so'
cap = 256 * 1024**2
default = 16 * 1024**2
rows = [
    ('expected-aggregate-over-default', aggregate, default + 1, True),
    ('expected-test-product-over-default', test_product, default + 1, True),
    ('expected-product-at-existing-cap', test_product, cap, True),
    ('expected-product-above-existing-cap', test_product, cap + 1, False),
    ('crypto-over-default', crypto, default + 1, False),
    ('source-over-default', source, default + 1, False),
    ('unlisted-product-over-default', unlisted_product, default + 1, False),
    ('nonproduct-at-original-default', source, default, True),
]
observations = []
started = time.monotonic()
for index, call in enumerate(calls):
    exact_module = ast.Module(body=[physical, call], type_ignores=[])
    code = compile(exact_module, str(SOURCE) + ':AST-product-read-site-' + str(index + 1), 'exec')
    for name, path, size, expected in rows:
        SyntheticPhysicalPath.sizes = {path: size}
        namespace = {'Path': SyntheticPhysicalPath, 'ROOT': root, 'ALLOCATION_CAP': cap,
                     'product_modules': {aggregate: 'PinkhaAnyHost', test_product: 'PinkhaAnyHostTests'}, 'path': path}
        accepted = False
        try:
            exec(code, namespace)
            assert len(namespace['raw']) == size
            accepted = True
        except AssertionError:
            pass
        assert accepted == expected, (index + 1, name, accepted, expected)
        observations.append({'callSite': index + 1, 'case': name, 'syntheticBytes': size,
                             'expectedAcceptance': expected, 'actualAcceptance': accepted})
result = {'schema': 'pinkha-bookmark6-product-read-bound-control/v1',
          'status': 'PASS_SYNTHETIC_BOUNDARY_CONTROL_ONLY', 'controlMethods': 1,
          'syntheticBoundaryRows': len(observations), 'controllerSHA256': hashlib.sha256(raw).hexdigest(),
          'controlSourceSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'seconds': round(time.monotonic() - started, 6), 'observations': observations,
          'actualLargeProductObserved': False, 'largeFilesAllocated': False,
          'runnerImportedOrMainInvoked': False, 'SwiftOrHostOrRuntimeInvocations': 0,
          'scope': 'Exact AST physical helper and both corrected call-site expressions; length-only synthetic read values, not compiler artifact evidence.'}
out = BASE / 'product-bound-controls1'
out.mkdir(exist_ok=False)
(out / 'result.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
stdout = json.dumps({'status': result['status'], 'controlMethods': 1, 'rows': len(observations),
                     'controllerSHA256': result['controllerSHA256'], 'seconds': result['seconds'],
                     'SwiftOrHostOrRuntimeInvocations': 0}, sort_keys=True) + '\n'
(out / 'stdout.original.log').write_text(stdout)
print(stdout, end='')
