#!/usr/bin/env python3
"""Offhost, pure result-scope controls. Does not import or invoke the runner."""
from pathlib import Path
import ast
import contextlib
import hashlib
import io
import json
import re
import time
import unittest

HERE = Path(__file__).resolve().parent
raw = (HERE / 'inputs/run_component.py').read_bytes()
assert hashlib.sha256(raw).hexdigest() == '66f09e18e07cca8a2056d0c8b51ffa318433f28bf9cb7f255f7a0c9bd9db9ea8'
tree = ast.parse(raw.decode())
constants = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ('METHODS', 'SUITE'):
        constants[node.targets[0].id] = ast.literal_eval(node.value)
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'xctest_result')
namespace = {'re': re, **constants}
exec(compile(ast.Module(body=[function], type_ignores=[]), '<exact-frozen-result-qualifier>', 'exec'), namespace)
qualify = namespace['xctest_result']
methods = constants['METHODS']


def event(name, outcome='passed', suite='NativePropertyStoreTests'):
    return "Test Case '" + suite + '.' + name + "' started at 00:00:00\nTest Case '" + suite + '.' + name + "' " + outcome + ' (0.001 seconds).\n'


def log(names=methods):
    return ''.join(event(name) for name in names) + 'Executed 4 tests, with 0 failures (0 unexpected) in 0.004 seconds\n'


class SelectionScope(unittest.TestCase):
    def test_exact_four_events_are_the_only_positive_scope(self):
        result = qualify(log())
        self.assertEqual(result['actualXCTestMethods'], list(methods))
        self.assertEqual(result['XCTestCases'], 4)
        self.assertEqual(result['oldMethodsExecuted'], 0)
        self.assertEqual(result['HTTPFixturesInvoked'], 0)

    def test_original_property_or_host_method_cannot_be_added(self):
        for old, suite in [('testRawUnknownNamespacesAndNativeDerivedMetadataSurviveProjection', 'NativePropertyStoreTests'),
                           ('testExactUnicodeTextReadbackRetainsVerifiedReceiptAndExactInverse', 'NativeTextEditReadbackHTTPTests')]:
            with self.subTest(old=old), self.assertRaises(AssertionError):
                qualify(log() + event(old, suite=suite))

    def test_missing_duplicate_failed_and_skipped_events_are_not_pass(self):
        variants = [log(methods[:-1]), log((methods[0], methods[0], *methods[2:])),
                    log().replace(event(methods[1]), event(methods[1], 'failed')),
                    log().replace(event(methods[1]), event(methods[1], 'skipped'))]
        for index, value in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(AssertionError):
                qualify(value)

    def test_swift_testing_footer_or_summary_without_events_is_not_authority(self):
        for value in ['Test run with 0 tests passed after 0.001 seconds.\n',
                      'Executed 4 tests, with 0 failures\n']:
            with self.subTest(value=value), self.assertRaises(AssertionError):
                qualify(value)


stream = io.StringIO(); started = time.monotonic()
result = unittest.TextTestRunner(stream=stream, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SelectionScope))
stdout = stream.getvalue().encode()
folder = HERE / 'portable-selection-controls1'
folder.mkdir()
(folder / 'stdout.original.log').write_bytes(stdout)
receipt = {'status': 'PASS_SOURCE_ONLY_SELECTION_CONTROLS' if result.wasSuccessful() else 'FAIL',
    'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'seconds': round(time.monotonic() - started, 6),
    'runnerSHA256': hashlib.sha256(raw).hexdigest(),
    'controlSourceSHA256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'stdoutSHA256': hashlib.sha256(stdout).hexdigest(), 'stdoutBytes': len(stdout),
    'scope': 'Synthetic event strings passed only to the exact AST-extracted result qualifier; these are not Swift/XCTest/component outcomes.',
    'runnerImportedOrInvoked': False, 'compilerInvocations': 0, 'hostCalls': 0, 'networkCalls': 0,
    'processHelperInvocations': 0, 'oldControlsReplayed': 0}
(folder / 'result.json').write_text(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
print(json.dumps(receipt, sort_keys=True))
raise SystemExit(0 if result.wasSuccessful() else 1)
