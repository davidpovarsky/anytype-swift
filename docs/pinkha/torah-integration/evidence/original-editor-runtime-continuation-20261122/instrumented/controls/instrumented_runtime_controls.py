"""New helper boundaries only; process replies and codesign receipt are fixtures.

ZIP bytes, hidden files, modes and actual helper functions execute locally.
No Apple command, simulator, framework build or old control body is executed.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import plistlib
import stat
import sys
import tempfile
import time
import unittest
import zipfile

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / 'candidate/Tools/OriginalEditor'
ORIGINAL = BASE.parent / 'sdk_runtime_continuation/original/Tools/OriginalEditor'
PROCESS = BASE.parent / 'sdk_runtime_continuation/candidate/Tools/OriginalEditor'
sys.path[:0] = [str(SOURCE), str(ORIGINAL), str(PROCESS)]
import runtime_continuation_observation as subject


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


class RecordedReplies:
    """Explicit command boundary fixture, never a claim of native execution."""
    def __init__(self, evidence, environment=None, deadline=None, responses=None):
        self.evidence = Path(evidence)
        self.evidence.mkdir(parents=True, exist_ok=True)
        self.responses = responses or {}
        self.items = []
        self.owned_groups_drained = True
        self.environment, self.deadline = environment, deadline

    def run(self, label, argv, root, seconds):
        item = {'label': label, 'argv': argv, 'requested_timeout_seconds': seconds}
        reply = self.responses.get(label, {})
        self.owned_groups_drained = reply.get('drained', True)
        item.update(effective_returncode=reply.get('code', 0), timed_out=reply.get('code') == 124)
        self.items.append(item)
        if reply.get('interrupt'):
            raise KeyboardInterrupt('explicit command-boundary fixture')
        output = self.evidence / (label + '.stdout')
        error = self.evidence / (label + '.stderr')
        raw = reply.get('raw', encoded(reply.get('json', {'devices': {'runtime': []}})))
        output.write_bytes(raw)
        error.write_bytes(b'')
        return item['effective_returncode'], output, error


class InstrumentedRuntimeBoundaries(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='otzaria-runtime-observation-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.evidence = self.root / 'evidence'
        self.evidence.mkdir()
        self.identifier = 'C7858FF8-04DA-4515-A009-7F8F2503008A'
        self.name = 'Otzaria-Original-Editor-Continuation-fixture-1'
        self.device = {'identifier': 'reviewed-fixture-device'}
        self.runtime = {'identifier': 'reviewed-fixture-runtime', 'buildversion': 'fixture'}
        self.owned = {'udid': self.identifier, 'name': self.name, 'device': self.device, 'runtime': self.runtime}

    def cleanup(self, responses=None, owned=None, original=None):
        commands = RecordedReplies(self.evidence / 'cleanup', responses=responses)
        value = subject.cleanup_owned_simulator(commands, self.root, owned or self.owned,
            self.name, self.device, self.runtime, original or set())
        return value, commands

    def app(self):
        app = self.root / 'OriginalEditorConsumer.app'
        app.mkdir()
        (app / 'empty').mkdir()
        (app / '.gitattributes').write_bytes(b'original hidden fixture\r\n')
        (app / 'OriginalEditorConsumer').write_bytes(b'unit fixture, not a Mach-O executable\0')
        (app / 'OriginalEditorConsumer').chmod(0o755)
        (app / 'Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier': 'org.otzaria.fixture'}))
        inventory = subject.inventory(app)
        signature = {'label': 'external-consumer-signature', 'argv': ['codesign', '--verify', '--strict', str(app)],
                     'status': 'TERMINAL', 'returncode': 0, 'effective_returncode': 0, 'timed_out': False}
        return app, inventory, signature

    def retain(self, app, inventory, signature):
        return subject.retain_signed_consumer(app, inventory, signature, self.root / 'retained',
            {'control_sha': 'fixture-control', 'run_id': 'fixture'},
            {'source_sha': 'fixture-framework', 'run_id': 'old-fixture'}, 'a' * 64, 'b' * 64, time.time() + 120)

    def test_ordinary_context_is_preserved_without_any_credential_or_child_override(self):
        environment = {key: 'value-' + key for key in subject.ENVIRONMENT_KEYS}
        environment.update(GH_TOKEN='sentinel-fixture-secret', GITHUB_TOKEN='other-secret',
                           ACTIONS_RUNTIME_TOKEN='runtime-secret', SIMCTL_CHILD_GH_TOKEN='child-secret')
        actual = subject.runtime_environment(environment)
        self.assertEqual(set(actual), set(subject.ENVIRONMENT_KEYS))
        self.assertTrue(all(actual[key] == environment[key] for key in actual))
        self.assertNotIn('secret', json.dumps(actual))

    def test_diagnostics_reject_unapproved_environment_before_any_command(self):
        with self.assertRaisesRegex(RuntimeError, 'Unapproved diagnostic environment'):
            subject.observe_runtime(self.evidence, 'before-boot', self.root, {'GH_TOKEN': 'secret'},
                                    time.time() + 120, self.owned, RecordedReplies)
        self.assertFalse((self.evidence / 'diagnostics').exists())

    def test_diagnostics_are_bounded_readonly_and_bind_owned_state_and_plist(self):
        plist = self.root / 'Library/Developer/CoreSimulator/Devices' / self.identifier / 'device.plist'
        plist.parent.mkdir(parents=True)
        plist.write_bytes(plistlib.dumps({'UDID': self.identifier, 'name': self.name, 'state': 3}))
        created = []
        def factory(evidence, environment, deadline):
            instance = RecordedReplies(evidence, environment, deadline, {'devices-observed': {'json':
                {'devices': {'runtime': [{'udid': self.identifier, 'state': 'Booting'},
                                         {'udid': 'UNRELATED', 'state': 'Shutdown'}]}}}})
            created.append(instance)
            return instance
        started = time.time()
        result = subject.observe_runtime(self.evidence, 'before-boot', self.root, {'HOME': str(self.root)},
                                         started + 120, self.owned, factory)
        self.assertLessEqual(created[0].deadline, time.time() + 35)
        self.assertEqual(len(created[0].items), 5)
        self.assertTrue(all(row['requested_timeout_seconds'] == 8 for row in created[0].items))
        self.assertEqual(created[0].items[-1]['argv'], ['xcrun', 'simctl', 'list', 'devices', '-j'])
        self.assertEqual(created[0].items[3]['argv'], ['ps', '-axo', 'pid=,ppid=,pgid=,comm='])
        self.assertEqual(result['owned_device_state'], {'udid': self.identifier, 'state': 'Booting'})
        self.assertEqual(result['device_plist']['represented_fields']['state'], 3)
        self.assertTrue(result['owned_groups_drained'])

    def test_an_undrained_diagnostic_stops_later_commands_and_reports_incomplete_ownership(self):
        created = []
        def factory(evidence, environment, deadline):
            instance = RecordedReplies(evidence, environment, deadline, {'host-resources': {'code': 124, 'drained': False}})
            created.append(instance)
            return instance
        result = subject.observe_runtime(self.evidence, 'after-runtime-failure', self.root, {}, time.time() + 120,
                                         self.owned, factory)
        self.assertFalse(result['owned_groups_drained'])
        self.assertEqual(len(created[0].items), 1)
        self.assertTrue(result['remaining_commands_not_started'])

    def test_interrupted_diagnostic_preserves_undrained_state_and_stops(self):
        def factory(evidence, environment, deadline):
            return RecordedReplies(evidence, environment, deadline,
                {'host-resources': {'interrupt': True, 'drained': False}})
        result = subject.observe_runtime(self.evidence, 'before-boot', self.root, {}, time.time() + 120,
                                         self.owned, factory)
        self.assertTrue(result['interrupted'])
        self.assertFalse(result['owned_groups_drained'])
        self.assertEqual(len(result['commands']), 1)

    def test_drained_shutdown_timeout_still_deletes_and_proves_actual_absence(self):
        value, commands = self.cleanup({'shutdown-owned-simulator': {'code': 124}})
        self.assertEqual([c['label'] for c in commands.items],
            ['shutdown-owned-simulator', 'delete-owned-simulator', 'devices-after-cleanup'])
        self.assertEqual([c['requested_timeout_seconds'] for c in commands.items], [60, 60, 30])
        self.assertEqual(value['shutdown']['effective_returncode'], 124)
        self.assertTrue(value['completed'])
        self.assertTrue(value['owned_device_proven_absent'])
        self.assertEqual(commands.items[1]['argv'], ['xcrun', 'simctl', 'delete', self.identifier])

    def test_failed_delete_still_observes_state_and_cannot_complete_cleanup(self):
        value, commands = self.cleanup({'delete-owned-simulator': {'code': 124}})
        self.assertEqual(commands.items[-1]['label'], 'devices-after-cleanup')
        self.assertTrue(value['owned_device_proven_absent'])
        self.assertFalse(value['completed'])

    def test_remaining_owned_device_cannot_complete_cleanup(self):
        value, _ = self.cleanup({'devices-after-cleanup': {'json': {'devices':
            {'runtime': [{'udid': self.identifier, 'state': 'Shutdown'}]}}}})
        self.assertFalse(value['owned_device_proven_absent'])
        self.assertFalse(value['completed'])

    def test_undrained_shutdown_prevents_later_mutation_and_false_absence(self):
        value, commands = self.cleanup({'shutdown-owned-simulator': {'code': 124, 'drained': False}})
        self.assertEqual(len(commands.items), 1)
        self.assertFalse(value['completed'])
        self.assertFalse(value['owned_device_proven_absent'])
        self.assertIn('NOT_ATTEMPTED', value['delete']['status'])

    def test_unowned_or_preexisting_identity_cannot_receive_cleanup_commands(self):
        for owned, original in [({**self.owned, 'name': 'unrelated'}, set()), (self.owned, {self.identifier})]:
            commands = RecordedReplies(self.evidence / 'cleanup')
            with self.assertRaises(RuntimeError):
                subject.cleanup_owned_simulator(commands, self.root, owned, self.name, self.device, self.runtime, original)
            self.assertFalse(commands.items)

    def test_malformed_poststate_is_unknown_and_cannot_complete_cleanup(self):
        value, _ = self.cleanup({'devices-after-cleanup': {'json': {'devices': {'runtime': [{}]}}}})
        self.assertFalse(value['completed'])
        self.assertFalse(value['owned_device_proven_absent'])
        self.assertEqual(value['post_state']['error_type'], 'RuntimeError')

    def test_retention_keeps_hidden_bytes_empty_directories_and_executable_modes_unqualified(self):
        app, inventory, signature = self.app()
        value = self.retain(app, inventory, signature)
        self.assertFalse(value['runtime_qualified'])
        self.assertFalse(value['restore_as_original_sdk_allowed'])
        self.assertEqual(value['consumer_producer']['control_sha'], 'fixture-control')
        self.assertEqual(value['framework_producer']['source_sha'], 'fixture-framework')
        archive = self.root / 'retained/consumer-app.zip'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), value['archive_sha256'])
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(zipped.read('OriginalEditorConsumer.app/.gitattributes'), (app / '.gitattributes').read_bytes())
            self.assertTrue(zipped.getinfo('OriginalEditorConsumer.app/empty/').is_dir())
            self.assertEqual(stat.S_IMODE(zipped.getinfo('OriginalEditorConsumer.app/OriginalEditorConsumer').external_attr >> 16), 0o755)
            for path, row in inventory.items():
                self.assertEqual(hashlib.sha256(zipped.read('OriginalEditorConsumer.app/' + path)).hexdigest(), row['sha256'])

    def test_failed_signature_cannot_create_a_retained_consumer_receipt(self):
        app, inventory, signature = self.app()
        signature['effective_returncode'] = 124
        with self.assertRaisesRegex(RuntimeError, 'successful actual consumer signature'):
            self.retain(app, inventory, signature)
        self.assertFalse((self.root / 'retained').exists())

    def test_changed_signed_input_cannot_be_archived_as_the_observed_consumer(self):
        app, inventory, signature = self.app()
        (app / 'Info.plist').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'Signed consumer inventory differs'):
            self.retain(app, inventory, signature)
        self.assertFalse((self.root / 'retained').exists())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--result', required=True, type=Path)
    arguments = parser.parse_args()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(InstrumentedRuntimeBoundaries)
    expected = [test.id().split('.')[-1] for test in suite]
    started, passed = [], []
    class Results(unittest.TextTestResult):
        def startTest(self, test):
            started.append(test.id().split('.')[-1])
            super().startTest(test)
        def addSuccess(self, test):
            passed.append(test.id().split('.')[-1])
            super().addSuccess(test)
    result = unittest.TextTestRunner(verbosity=2, resultclass=Results).run(suite)
    inputs = [Path(__file__), SOURCE / 'runtime_continuation_observation.py', SOURCE / 'run_runtime_continuation.py',
              PROCESS / 'runtime_continuation_process.py', ORIGINAL / 'product_inventory.py',
              ORIGINAL / 'framework_profile.py', ORIGINAL / 'pbx_source.py']
    record = {'status': 'PASS_NEW_INSTRUMENTED_RUNTIME_BOUNDARIES' if result.wasSuccessful() else 'FAIL',
        'tests_run': result.testsRun, 'expected_ids': expected, 'started_ids': started, 'passed_ids': passed,
        'failures': [test.id() for test,_ in result.failures], 'errors': [test.id() for test,_ in result.errors],
        'skipped': [test.id() for test,_ in result.skipped],
        'source_inputs': [{'path': str(path.resolve()), 'bytes': path.stat().st_size,
                           'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path in inputs],
        'scope': 'Actual new helper with explicit command/signature fixtures and actual archive byte/mode IO.',
        'old_control_bodies_replayed': 0, 'apple_commands_executed': 0, 'runtime_qualification': False}
    arguments.result.parent.mkdir(parents=True, exist_ok=True)
    arguments.result.write_bytes(encoded(record))
    raise SystemExit(0 if result.wasSuccessful() else 1)
