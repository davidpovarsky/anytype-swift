"""Execute only the new failure wrapper extracted from the real driver AST."""
import ast
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest

PACKET = Path(__file__).resolve().parents[1]
DRIVER = PACKET / 'candidate/Tools/OriginalEditor/run_framework_acceptance.py'


def actual_failure_wrapper():
    module = ast.parse(DRIVER.read_text())
    execute = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'execute')
    languages = next(node for node in execute.body if isinstance(node, ast.For)
                     and isinstance(node.target, ast.Name) and node.target.id == 'language')
    wrapper = [node for node in languages.body if isinstance(node, ast.Try)]
    assert len(wrapper) == 1
    function = ast.parse('def invoke():\n    pass\n').body[0]
    function.body = wrapper
    return ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))


class OriginalFailure(Exception):
    pass


class DiagnosticFailure(Exception):
    pass


class FailureIntegrationControls(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.output = self.root / 'actual-observation.json'
        self.output.write_text('{"fixture": "EXPLICIT_OBSERVATION_BOUNDARY"}')
        self.calls = []
        self.writes = []
        self.failure = None
        self.diagnostic_failure = False
        self.original = OriginalFailure('original command or validator failure')
        self.receipt = {'verified_runtime_observations': []}
        self.environment = {
            'command': self.command, 'launch': ['EXPLICIT_LAUNCH_ARGV_BOUNDARY'], 'root': self.root,
            'evidence': self.root, 'name': 'consumer-en', 'output': self.output, 'time': types.SimpleNamespace(monotonic=lambda: 0),
            'require': lambda condition, message: None if condition else (_ for _ in ()).throw(ValueError(message)),
            'json': json, 'verify_observation': self.verify, 'nonce': 'EXPLICIT_NONCE', 'language': 'en',
            'installed': 'EXPLICIT_INSTALLED_CONTAINER', 'oracle': {'EXPLICIT_RESOURCE_ORACLE': True},
            'derived': self.root / 'absent-original-build-path', 'receipt': self.receipt, 'write': self.write,
            'sys': sys, 'capture_request': self.root / 'REQUEST.json'}
        exec(compile(actual_failure_wrapper(), str(DRIVER), 'exec'), self.environment)

    def command(self, argv, root, evidence, name, timeout):
        self.calls.append({'argv': argv, 'name': name, 'timeout': timeout})
        if name.endswith('-launch') and self.failure == 'launch':
            raise self.original
        if name.endswith('-failure-capture') and self.diagnostic_failure:
            raise DiagnosticFailure('separate diagnostic error')
        return ''

    def verify(self, raw, nonce, language, installed, oracle):
        self.assertEqual((nonce, language, installed, oracle),
                         ('EXPLICIT_NONCE', 'en', 'EXPLICIT_INSTALLED_CONTAINER', {'EXPLICIT_RESOURCE_ORACLE': True}))
        if self.failure == 'observation':
            raise self.original
        return {'scope': 'EXPLICIT_VALIDATOR_DOUBLE_NO_NATIVE_RUNTIME', 'language': language}

    def write(self, path, value):
        self.writes.append((path, dict(value)))

    def test_success_keeps_original_validator_and_never_invokes_failure_capture(self):
        self.environment['invoke']()
        self.assertEqual([x['name'] for x in self.calls], ['consumer-en-launch'])
        self.assertEqual(self.calls[0]['timeout'], 30)
        self.assertEqual(len(self.receipt['verified_runtime_observations']), 1)
        self.assertEqual((self.root / 'consumer-en-observation.json').read_bytes(), self.output.read_bytes())

    def test_launch_error_is_rethrown_after_one_bounded_capture(self):
        self.failure = 'launch'
        with self.assertRaises(OriginalFailure) as caught:
            self.environment['invoke']()
        self.assertIs(caught.exception, self.original)
        self.assertEqual([x['name'] for x in self.calls], ['consumer-en-launch', 'consumer-en-failure-capture'])
        self.assertEqual(self.calls[1]['timeout'], 15)
        self.assertEqual(self.calls[1]['argv'], [sys.executable, str(self.root / 'Tools/OriginalEditor/consumer_failure_capture.py'),
                                               '--capture-failure', str(self.root / 'REQUEST.json')])
        self.assertEqual(self.receipt['verified_runtime_observations'], [])

    def test_failed_diagnostic_does_not_replace_original_launch_error(self):
        self.failure, self.diagnostic_failure = 'launch', True
        with self.assertRaises(OriginalFailure) as caught:
            self.environment['invoke']()
        self.assertIs(caught.exception, self.original)
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.writes[0][0].name, 'consumer-en-failure-capture-error.json')
        self.assertEqual(self.writes[0][1]['error_type'], 'DiagnosticFailure')
        self.assertTrue(self.writes[0][1]['primary_launch_or_observation_error_preserved'])

    def test_original_observation_failure_is_rethrown_without_runtime_credit(self):
        self.failure = 'observation'
        with self.assertRaises(OriginalFailure) as caught:
            self.environment['invoke']()
        self.assertIs(caught.exception, self.original)
        self.assertEqual([x['name'] for x in self.calls], ['consumer-en-launch', 'consumer-en-failure-capture'])
        self.assertEqual(self.receipt['verified_runtime_observations'], [])
        self.assertEqual((self.root / 'consumer-en-observation.json').read_bytes(), self.output.read_bytes())


    def test_failed_diagnostic_error_recorder_preserves_original_error(self):
        self.failure, self.diagnostic_failure = 'launch', True
        def unavailable_recorder(path, value):
            raise OSError('EXPLICIT_DIAGNOSTIC_STORAGE_FAILURE')
        self.environment['write'] = unavailable_recorder
        with self.assertRaises(OriginalFailure) as caught:
            self.environment['invoke']()
        self.assertIs(caught.exception, self.original)
        self.assertEqual([x['name'] for x in self.calls], ['consumer-en-launch', 'consumer-en-failure-capture'])
        self.assertEqual(self.receipt['verified_runtime_observations'], [])


class RecordedResult(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        print('START ' + test.id(), flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        print('PASS ' + test.id(), flush=True)


if __name__ == '__main__':
    unittest.main(verbosity=2, testRunner=unittest.TextTestRunner(resultclass=RecordedResult, verbosity=2))
