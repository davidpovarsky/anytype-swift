"""Synthetic JSON/control checks only. These never execute a native test binary."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from unittest.mock import Mock

import run_pairs


class PairControlTests(unittest.TestCase):
    def fixture(self, role='new', phase='new-upgrade'):
        identity = dict(heart_sha=run_pairs.PIN, patch_sha256=run_pairs.PATCHES[role],
                        fixture_sha256='f' * 64, runtime_capability=int(role == 'new'))
        report = dict(protocol=run_pairs.PROTOCOL, phase=phase, nonce='current-nonce', pid=123,
                      database_path=str(Path('synthetic/database')), space_id='test', closed=True, test_passed=True,
                      export_status='NOT_RUN_COMPONENT_NO_RPC', swift_pairing_status='NOT_RUN',
                      required_swift_fallback='UNAVAILABLE_FROM_RUNTIME_CAPABILITY',
                      canonical_sha256={key: 'a' * 64 for key in ['pair-manifest', 'pair-document', 'pair-block']},
                      public_sha256={key: 'b' * 64 for key in ['pair-document', 'pair-block']},
                      cache_sha256={key: 'c' * 64 for key in ['pair-document', 'pair-block']},
                      public_members=['pair-document'], ready={'pair-document': True, 'pair-block': True},
                      private_versions={'pair-document': 1, 'pair-block': 1}, recovery_complete=True, recomputed=3,
                      private_members=['pair-block', 'pair-document'], private_index_used=True,
                      private_query_status='EXECUTED', **identity)
        if role == 'old':
            report.update(private_members=[], private_index_used=False,
                          private_query_status='NOT_ATTEMPTED_RUNTIME_UNAVAILABLE')
        return identity, report

    def validate(self, identity, report, baseline=None, previous=None):
        role = 'new' if identity['runtime_capability'] else 'old'
        return run_pairs.validate_phase(report, report['phase'], role, identity, 'current-nonce',
                                        Path('synthetic/database'), 123, baseline, previous)

    def test_complete_synthetic_control_report_validates_without_native_execution(self):
        identity, report = self.fixture()
        self.validate(identity, report)
        self.assertEqual(report['export_status'], 'NOT_RUN_COMPONENT_NO_RPC')
        self.assertEqual(report['swift_pairing_status'], 'NOT_RUN')

    def test_stale_private_version_one_never_grants_old_runtime_capability(self):
        identity, report = self.fixture('old', 'old-edit')
        self.validate(identity, report)
        self.assertEqual(report['private_versions']['pair-document'], 1)
        self.assertEqual(report['runtime_capability'], 0)
        report['runtime_capability'] = 1
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'):
            self.validate(identity, report)

    def test_wrong_identity_nonce_pid_database_or_open_handles_fail(self):
        identity, report = self.fixture()
        for field, value in [('nonce', 'old-attempt'), ('pid', 999), ('heart_sha', 'other'),
                             ('patch_sha256', '0' * 64), ('fixture_sha256', '0' * 64),
                             ('database_path', 'another/database'), ('space_id', 'private'),
                             ('closed', False), ('test_passed', False), ('protocol', 'unknown')]:
            with self.subTest(field=field):
                candidate = dict(report, **{field: value})
                with self.assertRaises(RuntimeError):
                    self.validate(identity, candidate)

    def test_component_report_cannot_claim_export_or_swift_pass(self):
        identity, report = self.fixture()
        for field in ['export_status', 'swift_pairing_status']:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(identity, dict(report, **{field: 'PASS'}))

    def test_missing_canonical_public_cache_or_malformed_digest_fail(self):
        identity, report = self.fixture()
        for field in ['canonical_sha256', 'public_sha256', 'cache_sha256']:
            candidate = copy.deepcopy(report)
            candidate[field].pop(next(iter(candidate[field])))
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(identity, candidate)
        report['canonical_sha256']['pair-document'] = 'not-a-sha256'
        with self.assertRaisesRegex(RuntimeError, 'digest'):
            self.validate(identity, report)

    def test_canonical_or_public_change_between_revisions_fails(self):
        identity, report = self.fixture()
        for field in ['canonical_sha256', 'public_sha256']:
            candidate = copy.deepcopy(report)
            candidate[field]['pair-document'] = 'd' * 64
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'data changed'):
                self.validate(identity, candidate, baseline=report)

    def test_revision_transition_requires_recovery_and_changed_cache_proofs(self):
        identity, report = self.fixture()
        with self.assertRaisesRegex(RuntimeError, 'did not change'):
            self.validate(identity, report, previous=report)
        previous = copy.deepcopy(report)
        previous['cache_sha256'] = {key: 'd' * 64 for key in previous['cache_sha256']}
        self.validate(identity, report, previous=previous)
        for field, value in [('recovery_complete', False), ('recomputed', 1)]:
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, 'recovery'):
                self.validate(identity, dict(report, **{field: value}), previous=previous)

    def test_widened_public_or_missing_new_private_index_version_readiness_fail(self):
        identity, report = self.fixture()
        for field, value in [('public_members', ['pair-block', 'pair-document']),
                             ('private_members', ['pair-document']), ('private_index_used', False),
                             ('private_versions', {'pair-document': True, 'pair-block': True}),
                             ('private_query_status', 'NOT_RUN'), ('ready', {})]:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(identity, dict(report, **{field: value}))

    def test_old_runtime_expanded_query_or_missing_fallback_contract_fails(self):
        identity, report = self.fixture('old', 'old-edit')
        for field, value in [('private_query_status', 'EXECUTED'), ('required_swift_fallback', 'NORMAL_EMPTY')]:
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                self.validate(identity, dict(report, **{field: value}))

    def test_fresh_preflight_failure_saves_current_fail_without_invoking_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.object(run_pairs, 'execute', side_effect=RuntimeError('missing actual artifacts')) as execute:
                with contextlib.redirect_stdout(io.StringIO()):
                    code = run_pairs.main(['--manifest', str(root / 'missing.json'), '--workspace', str(root / 'attempt')])
            self.assertEqual(code, 1)
            execute.assert_not_called()  # Missing manifest fails before any execution.
            receipt = json.loads((root / 'attempt/result.json').read_text())
            self.assertEqual(receipt['status'], 'FAIL')
            self.assertEqual(receipt['full_F10'], 'NOT_PROVEN')
            self.assertIn('finished_at', receipt)
            self.assertEqual(receipt['client_enablement'], 'DISABLED_PENDING_RUNTIME_COMPATIBILITY_PROOF')

    def test_existing_workspace_is_refused_and_old_pass_receipt_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            receipt = root / 'result.json'
            original = '{"status":"COMPONENT_STORE_PAIR_PASS","run_id":"historical"}'
            receipt.write_text(original)
            with self.assertRaises(FileExistsError):
                run_pairs.main(['--manifest', 'missing', '--workspace', str(root)])
            self.assertEqual(receipt.read_text(), original)

    def test_artifact_preflight_pins_immutable_inventory_before_using_its_file_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary, source, inventory, patch_file = [root / name for name in ['binary', 'source', 'inventory.json', 'patch']]
            binary.write_bytes(b'control fixture, never executable')
            source.mkdir()
            inventory.write_text(json.dumps({'heart_sha': run_pairs.PIN, 'patch_sha256': run_pairs.PATCHES['new'], 'files': []}))
            patch_file.write_text('control fixture')
            with self.assertRaisesRegex(RuntimeError, 'immutable source inventory'):
                run_pairs.verify_artifact('new', dict(binary=str(binary), source=str(source), inventory=str(inventory), patch=str(patch_file)))

    def test_relative_artifact_paths_are_refused_before_any_file_is_opened(self):
        with self.assertRaisesRegex(RuntimeError, 'Absolute'):
            run_pairs.verify_artifact('new', dict(binary='relative', source='relative', inventory='relative', patch='relative'))

    def test_report_from_another_phase_cannot_advance_the_expected_sequence(self):
        identity, report = self.fixture()
        report['phase'] = 'new-recover'
        with self.assertRaisesRegex(RuntimeError, 'phase/protocol'):
            run_pairs.validate_phase(report, 'new-upgrade', 'new', identity, 'current-nonce',
                                     Path('synthetic/database'), 123, None, None)

    def process_control(self, root, child, exists=False, free=None, times=None):
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(run_pairs, 'EXECUTION_PLATFORM', 'posix'))
        popen = stack.enter_context(patch.object(run_pairs.subprocess, 'Popen', return_value=child))
        stack.enter_context(patch.object(run_pairs, 'group_exists', return_value=exists))
        stop = stack.enter_context(patch.object(run_pairs, 'stop_group'))
        stack.enter_context(patch.object(run_pairs.shutil, 'disk_usage', return_value=Mock(free=free or run_pairs.RESERVE)))
        if times:
            stack.enter_context(patch.object(run_pairs.time, 'monotonic', side_effect=times))
        return popen, stop

    def test_process_control_waits_for_exit_and_empty_group_without_launching_native(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = Mock(pid=123)
            child.poll.return_value = 0
            child.wait.return_value = 0
            popen, stop = self.process_control(root, child)
            self.assertEqual(run_pairs.run_process(['nonexistent-control-binary'], {}, root / 'control.log', root), 123)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            stop.assert_not_called()
            self.assertGreaterEqual(child.wait.call_count, 2)

    def test_process_control_fails_and_cleans_up_lingering_descendants(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = Mock(pid=123)
            child.poll.return_value = 0
            child.wait.return_value = 0
            _, stop = self.process_control(root, child, exists=True)
            with self.assertRaisesRegex(RuntimeError, 'descendant'):
                run_pairs.run_process(['nonexistent-control-binary'], {}, root / 'control.log', root)
            stop.assert_called_once_with(123)

    def test_process_control_deadline_and_disk_guards_stop_own_group(self):
        for reason in ['deadline', 'disk']:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                child = Mock(pid=123)
                child.poll.return_value = None
                child.wait.return_value = 0
                _, stop = self.process_control(root, child,
                    free=run_pairs.RESERVE - 1 if reason == 'disk' else None,
                    times=[0, 1000] if reason == 'deadline' else [0, 1])
                with self.assertRaisesRegex(RuntimeError, 'deadline|reserve'):
                    run_pairs.run_process(['nonexistent-control-binary'], {}, root / 'control.log', root)
                stop.assert_called_once_with(123)

    def test_process_control_nonzero_exit_cannot_advance_sequence(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            child = Mock(pid=123)
            child.poll.return_value = 1
            child.wait.return_value = 1
            _, stop = self.process_control(root, child)
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                run_pairs.run_process(['nonexistent-control-binary'], {}, root / 'control.log', root)
            stop.assert_called_once_with(123)


if __name__ == '__main__':
    unittest.main()
