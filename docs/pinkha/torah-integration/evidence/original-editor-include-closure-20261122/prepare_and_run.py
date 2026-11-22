import ast
from datetime import datetime, timezone
import difflib
import hashlib
import importlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest

ROOT = Path(__file__).resolve().parent
REL = Path('Tools/OriginalEditor')
candidate = ROOT / 'candidate' / REL
preimage = ROOT / 'preimage' / REL
harness = ROOT / 'harness' / REL
evidence = ROOT / 'evidence'
evidence.mkdir(exist_ok=True)

def test_methods(path):
    return {
        (node.name, method.name): ast.dump(method, include_attributes=False)
        for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef)
        for method in node.body if isinstance(method, ast.FunctionDef)
        and method.name.startswith('test_')
    }

before = test_methods(preimage / 'test_clang_product_closure.py')
after = test_methods(candidate / 'test_clang_product_closure.py')
assert all(after.get(key) == value for key, value in before.items())
new = sorted('test_clang_product_closure.' + '.'.join(key) for key in after.keys() - before.keys())
assert len(new) == 6
gate = preimage / 'run_source_controls.py'
source = gate.read_text()
assignment = next(node for node in ast.parse(source).body
                  if isinstance(node, ast.Assign) and node.targets[0].id == 'EXPECTED_IDS')
old_ids = ast.literal_eval(assignment.value)
assert len(old_ids) == len(set(old_ids)) == 239
expected = sorted([*old_ids, *new])
assert len(expected) == len(set(expected)) == 245
lines = source.splitlines(keepends=True)
replacement = 'EXPECTED_IDS = (\n' + ''.join('    ' + json.dumps(name) + ',\n' for name in expected) + ')\n'
lines[assignment.lineno - 1:assignment.end_lineno] = [replacement]
source = ''.join(lines).replace('EXPECTED_COUNT = 239', 'EXPECTED_COUNT = 245')
(candidate / 'run_source_controls.py').write_text(source)
for name in ['clang_product_closure.py', 'test_clang_product_closure.py', 'run_source_controls.py']:
    shutil.copyfile(candidate / name, harness / name)

sys.path.insert(0, str(harness))
gate_module = importlib.import_module('run_source_controls')
discovered = sorted(test.id() for test in gate_module.cases(
    unittest.defaultTestLoader.discover(str(harness), pattern='test_*.py')))
assert discovered == expected
audit = {
    'schema': 1, 'baseline': 'a9aa64bb8556ba5504ed0f5fe528cd1ce5f91efc',
    'old_gate_identities_retained': len(old_ids), 'new_identities': new,
    'new_expected_count': 245, 'discovered_ids': discovered,
    'prior_clang_test_method_ast_unchanged': len(before),
    'discovery_executed_test_bodies': 0,
    'source_files': {name: {'sha256': hashlib.sha256((candidate / name).read_bytes()).hexdigest()}
                     for name in ['clang_product_closure.py', 'test_clang_product_closure.py', 'run_source_controls.py']},
}
(ROOT / 'DISCOVERY_AND_PRESERVATION.json').write_text(json.dumps(audit, indent=2, sort_keys=True) + '\n')
diff = ''.join(''.join(difflib.unified_diff(
    (preimage / name).read_text().splitlines(keepends=True),
    (candidate / name).read_text().splitlines(keepends=True),
    fromfile='a/' + str(REL / name), tofile='b/' + str(REL / name)))
    for name in ['clang_product_closure.py', 'test_clang_product_closure.py', 'run_source_controls.py'])
(ROOT / 'SOURCE.diff').write_text(diff)

assert not (evidence / 'RESULT.json').exists(), 'Refusing to replay the focused execution'
started = datetime.now(timezone.utc).isoformat()
stream = io.StringIO()
result = unittest.TextTestRunner(verbosity=2, stream=stream,
                               resultclass=gate_module.ObservedResult).run(
    unittest.defaultTestLoader.loadTestsFromNames(new))
raw = stream.getvalue().encode()
(evidence / 'focused-controls.stderr.log').write_bytes(raw)
receipt = {
    'schema': 1, 'scope': 'New real Git/filesystem source controls only; no Apple or native execution',
    'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
    'python': sys.version, 'command': [sys.executable, str(Path(__file__).resolve())],
    'expected_ids': new, 'started_ids': result.started_ids, 'passed_ids': result.passed_ids,
    'tests_run': result.testsRun,
    'failures': [{'id': test.id(), 'traceback': text} for test, text in result.failures],
    'errors': [{'id': test.id(), 'traceback': text} for test, text in result.errors],
    'skipped': [{'id': test.id(), 'reason': text} for test, text in result.skipped],
    'prior_test_bodies_replayed': 0,
    'raw_log_sha256': hashlib.sha256(raw).hexdigest(), 'source_files': audit['source_files'],
}
receipt['status'] = ('PASS' if result.wasSuccessful() and result.testsRun == 6
                     and sorted(result.started_ids) == new and sorted(result.passed_ids) == new
                     and not result.skipped else 'FAIL')
(evidence / 'RESULT.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: receipt[k] for k in ['status', 'tests_run', 'started_at', 'finished_at',
                                      'prior_test_bodies_replayed', 'failures', 'errors', 'skipped']}))
raise SystemExit(0 if receipt['status'] == 'PASS' else 1)
