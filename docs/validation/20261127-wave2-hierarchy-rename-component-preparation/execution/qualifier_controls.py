#!/usr/bin/env python3
"""Pure local result-qualifier controls; never imports or executes the runner."""
from pathlib import Path
import ast
import hashlib
import json
import re
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUNNER = HERE / 'inputs/run_component.py'
G04 = ROOT / 'wave2-reader-audit/component/actual-run/attempt1/stdout.original.log'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


raw = RUNNER.read_bytes()
tree = ast.parse(raw)
constants = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
        if node.targets[0].id in ('METHODS', 'SUITE'):
            constants[node.targets[0].id] = ast.literal_eval(node.value)
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'swift_testing_result')
assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(function))
namespace = {'re': re, **constants}
exec(compile(ast.Module(body=[function], type_ignores=[]), '<exact AST-extracted result qualifier>', 'exec'), namespace)
qualify = namespace['swift_testing_result']

original = G04.read_text()
first_name = 'newerSelectionRejectsLateProviderCompletion'
start = original.index('◇ Test ' + first_name + '(providerFails:) started.')
end_token = '✔ Test ' + first_name + '(providerFails:) with 2 test cases passed after 0.007 seconds.'
end = original.index(end_token) + len(end_token)
block = original[start:end]
blocks = [block.replace(first_name, method).replace('(providerFails:)', '(_:)')
          .replace('argument providerFails → false (Swift.Bool)', 'argument example → latin (HierarchyRawTitleExample)')
          .replace('argument providerFails → true (Swift.Bool)', 'argument example → hebrew (HierarchyRawTitleExample)')
          for method in constants['METHODS']]
suite = 'Hierarchy rename preserves exact requested title bytes'
positive = '\n'.join(['◇ Test run started.',
    '◇ Suite "' + suite + '" (aka \'' + constants['SUITE'] + '\') started.', *blocks,
    '✔ Suite "' + suite + '" (aka \'' + constants['SUITE'] + '\') passed after 0.030 seconds.',
    '✔ Test run with 4 tests in 1 suite passed after 0.031 seconds.']) + '\n'
first = constants['METHODS'][0]
cases = [
    ('four_methods_eight_paired_argument_cases', positive, True),
    ('missing_one_argument_pass', positive.replace('✔ Test case passing 1 argument example → hebrew (HierarchyRawTitleExample) to ' + first + '(_:) passed after 0.003 seconds.\n', '', 1), False),
    ('same_argument_repeated_instead_of_second', positive.replace('example → hebrew (HierarchyRawTitleExample)', 'example → latin (HierarchyRawTitleExample)'), False),
    ('old_method_execution_even_with_fixed_summary', positive.replace('✔ Test run with ', '◇ Test originalOldHierarchyMethod() started.\n✔ Test run with ', 1), False),
    ('zero_test_footer_is_not_acceptance', positive.replace('Test run with 4 tests in 1 suite', 'Test run with 0 tests in 0 suites'), False),
    ('duplicate_selected_method_event', positive.replace('✔ Test run with ', '◇ Test ' + first + '(_:) started.\n✔ Test run with ', 1), False),
]
results = []
started = time.monotonic()
for name, text, expected in cases:
    try:
        value = qualify(text)
        accepted = True
        details = {'methods': value['actualMethodCount'], 'argumentCases': value['actualPassedArgumentCaseCount']}
    except AssertionError as error:
        accepted = False
        details = {'refusal': str(error)}
    assert accepted == expected, name
    results.append({'name': name, 'syntheticLogSHA256': sha(text.encode()), 'expectedAccept': expected,
                    'observedAccept': accepted, 'controlStatus': 'PASS', **details})
report = {'schema': 'pinkha-hierarchy-rename-pure-result-controls/v1',
          'status': 'SIX_SYNTHETIC_QUALIFIER_CONTROLS_PASS', 'seconds': round(time.monotonic() - started, 6),
          'runnerSHA256': sha(raw), 'exactFunctionASTExtracted': function.name,
          'actualG04FormatSource': {'path': str(G04), 'sha256': sha(G04.read_bytes())},
          'syntheticConstruction': 'Four copies of one actual G04 two-argument event block, with explicitly synthetic source-specific method/enum/suite labels. Not actual hierarchy output.',
          'controls': results, 'runnerImportedOrInvoked': False, 'processManagerInvoked': False,
          'compilerInvocations': 0, 'SwiftTestsExecuted': 0, 'HTTPNativeOrHostCalls': 0,
          'newActualResultOrCompiledEnumeration': None}
out = HERE / 'qualifier-controls-result.json'
assert not out.exists(), 'Retain original control attempt; no silent replay/overwrite.'
out.write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
print(json.dumps({'result': str(out), 'sha256': sha(out.read_bytes()), 'status': report['status'], 'seconds': report['seconds']}))
