"""One local filesystem boundary control; never import or run the controller."""
from pathlib import Path
import ast
import hashlib
import json
import os
import time

BASE = Path(__file__).resolve().parent
OUT = BASE / 'alias-control1'
source = (BASE / 'inputs/run_component.py').read_bytes()
tree = ast.parse(source)
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'allocated_bytes')
namespace = {'os': os}
exec(compile(ast.Module(body=[function], type_ignores=[]), 'exact-allocated-bytes-only', 'exec'), namespace)
assert not OUT.exists(), 'Keep each original control attempt'
OUT.mkdir()
root = OUT / 'owned-root'
target = root / 'xdg-cache/org.swift.swiftpm'
target.mkdir(parents=True)
(target / 'local-control-only').write_bytes(b'not a Swift cache or runtime artifact\n')
alias = root / 'xdg-config/swiftpm/cache'
alias.parent.mkdir(parents=True)
namespace['ROOT'] = root
started = time.monotonic()
observations = []

alias.symlink_to(target)
observed = namespace['allocated_bytes']()
assert isinstance(observed, int) and observed > 0
observations.append({'case': 'exact_owned_alias', 'status': 'PASS_ACCEPTED_LOCAL_CONTROL'})

outside = OUT / 'outside-owned-root'
outside.mkdir()
alias.unlink()
alias.symlink_to(outside)
try:
    namespace['allocated_bytes']()
except AssertionError:
    observations.append({'case': 'same_alias_foreign_target', 'status': 'PASS_REJECTED_LOCAL_CONTROL'})
else:
    raise AssertionError('Foreign alias target was accepted')

alias.unlink()
alias.symlink_to(target)
extra = alias.parent / 'unlisted-alias'
extra.symlink_to(target)
try:
    namespace['allocated_bytes']()
except AssertionError:
    observations.append({'case': 'unlisted_alias_same_owned_target', 'status': 'PASS_REJECTED_LOCAL_CONTROL'})
else:
    raise AssertionError('Unlisted alias path was accepted')

receipt = {'schema': 'host2-specific-xdg-alias-control/v1', 'status': 'PASS_LOCAL_GUARD_CONTROL_ONLY',
           'controllerSHA256': hashlib.sha256(source).hexdigest(), 'cases': observations,
           'seconds': time.monotonic() - started, 'driverImported': False, 'driverExecuted': False,
           'selectedFunction': 'allocated_bytes', 'actualCompilerOrRuntimeAcceptance': False,
           'historicalPIDProbes': 0, 'OracleCalls': 0, 'NativeCalls': 0, 'SwiftCompilerCalls': 0,
           'HTTPServerCalls': 0, 'XCTestCalls': 0}
(OUT / 'result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps(receipt))
