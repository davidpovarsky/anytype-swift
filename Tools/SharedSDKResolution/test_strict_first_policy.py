"""Portable command-policy probes; explicit runner doubles are never Apple evidence."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('strict_first_resolution', HERE / 'resolve_packages.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
STALE = ('xcodebuild: error: Could not resolve package dependencies:\n'
         'an out-of-date resolved file was detected at example/Package.resolved, which is not allowed '
         'when automatic dependency resolution is disabled; Running resolver because requirements have changed.')


class StrictFirstPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='strict-first-policy-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / 'evidence'
        self.output.mkdir()
        self.active = self.root / 'Workspace.resolved'
        self.canonical = self.root / 'Project.resolved'
        self.lock = {'version': 2, 'pins': [{'identity': 'explicit-fixture', 'kind': 'remoteSourceControl',
                     'location': 'https://example.invalid/explicit-fixture', 'state': {'revision': '1' * 40}}]}
        self.original = json.dumps(self.lock).encode()
        self.active.write_bytes(self.original)
        self.canonical.write_bytes(self.original)
        self.expected = MODULE.pin_map(self.lock)
        self.calls = []

    def runner(self, results):
        def explicit_runner_double(argv, root, output, name, timeout, **kwargs):
            self.calls.append(list(argv))
            row = results[len(self.calls) - 1]
            if row.get('raises'):
                raise row['raises']
            if 'replacement' in row:
                self.active.write_bytes(json.dumps(row['replacement']).encode())
            MODULE.write(output / (name + '.command.json'), {'returncode': row['code'], 'timed_out': False})
            (output / (name + '.stdout.log')).write_text('')
            (output / (name + '.stderr.log')).write_text(row.get('stderr', ''))
            return ''
        return explicit_runner_double

    def invoke(self, results):
        return MODULE.resolve_strict_first(['xcodebuild', '-resolvePackageDependencies'], self.root, self.output,
            self.active, self.canonical, self.expected, runner=self.runner(results))

    def test_existing_strict_success_stops_after_one_command(self):
        raw, receipt = self.invoke([{'code': 0}])
        self.assertEqual(raw, self.original)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(receipt['automatic_resolution_invocations'], 0)
        self.assertIn('-onlyUsePackageVersionsFromResolvedFile', self.calls[0])

    def test_successful_strict_metadata_output_needs_no_second_pass(self):
        actual_output_fixture = dict(self.lock, version=3, originHash='a' * 64)
        raw, receipt = self.invoke([{'code': 0, 'replacement': actual_output_fixture}])
        self.assertEqual(json.loads(raw), actual_output_fixture)
        self.assertEqual(self.canonical.read_bytes(), raw)
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(receipt['automatic_resolution_invocations'], 0)

    def test_observed_stale_lock_diagnostic_permits_one_resolve_then_strict_replay(self):
        actual_output_fixture = dict(self.lock, version=3, originHash='b' * 64)
        raw, receipt = self.invoke([{'code': 74, 'stderr': STALE},
                                   {'code': 0, 'replacement': actual_output_fixture}, {'code': 0}])
        self.assertEqual(len(self.calls), 3)
        self.assertEqual(['-onlyUsePackageVersionsFromResolvedFile' in x for x in self.calls], [True, False, True])
        self.assertEqual(receipt['automatic_resolution_invocations'], 1)
        self.assertEqual(self.canonical.read_bytes(), raw)

    def test_network_failure_does_not_trigger_automatic_resolution(self):
        with self.assertRaisesRegex(RuntimeError, 'not admitted'):
            self.invoke([{'code': 74, 'stderr': 'Could not resolve package dependencies: failed to clone: TLS error'}])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.canonical.read_bytes(), self.original)

    def test_timeout_does_not_trigger_automatic_resolution(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            self.invoke([{'raises': subprocess.TimeoutExpired(['xcodebuild'], 1800)}])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.canonical.read_bytes(), self.original)

    def test_automatic_pin_drift_is_preserved_as_failure_before_strict_replay(self):
        wrong = copy.deepcopy(self.lock)
        wrong['pins'][0]['state']['revision'] = '2' * 40
        with self.assertRaisesRegex(RuntimeError, 'changed an original pin'):
            self.invoke([{'code': 74, 'stderr': STALE}, {'code': 0, 'replacement': wrong}])
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.canonical.read_bytes(), self.original)
        self.assertEqual(json.loads(self.active.read_bytes()), wrong)


if __name__ == '__main__':
    unittest.main()
