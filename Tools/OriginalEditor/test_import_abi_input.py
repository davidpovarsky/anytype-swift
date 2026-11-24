"""Synthetic admission controls, not genuine native or mobile ABI execution."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from import_abi_input import EXPORTS, LIB, verify
from local_execution import sha


class ImportABIInputControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.evidence = self.root / 'build/abi'
        self.evidence.mkdir(parents=True)
        self.source = {'head_sha': '1' * 40,
                       'execution_identity': {'local_execution_sha256': '2' * 64}}
        self.value = {'schema': 'otzaria.original-import-local-sdk-input/1',
                      'status': 'PASS', 'producer_kind': 'local-mac',
                      'sdk_source_sha': self.source['head_sha'], 'local_execution_sha256': '2' * 64,
                      'generated_files_verified': 733, 'generated_files_written': 0,
                      'generators_replayed': 0, 'full_sdk_accepted': False, 'editor_ui_accepted': False,
                      'defined_exports': sorted(EXPORTS),
                      'verified_architectures': {'ios': ['arm64'], 'ios-simulator': ['arm64', 'x86_64']},
                      'source_unchanged_after_bind': True, 'owned_command_groups_drained': True}
        native = {'source_sha': '3' * 40, 'native_source_tree': '4' * 40,
                  'execution_manifest_sha256': '5' * 64, 'status': 'PASS',
                  'source_module_link_stability': 'PASS', 'owned_command_groups_drained': True,
                  'counts': {name: {'passes': count, 'failures': 0, 'skipped': 0, 'not_run': 0}
                             for name, count in [('native9', 9), ('rpc9', 9), ('cancel_panic', 1),
                                                 ('bundled_semantic', 6), ('schema_closure', 11),
                                                 ('relation_target_closure', 12),
                                                 ('imported_creation_date', 6), ('bounded_native_metadata', 12)]}}
        self.value['native_qualification'] = native
        proofs = {'generation_qualification': {'status': 'PASS', 'output_counts': {
                    'native': 11, 'swift': 696, 'middleware': 37}, 'aggregate_producer_outcome': 'FAIL',
                    'generators_replayed_by_abi': 0, 'generated_index_sha256': '6' * 64},
                  'changed_swift_qualification': {'status': 'PASS', 'primary_count': 2,
                    'input_files': 689, 'typecheck_invocations': 1, 'generated_index_sha256': '6' * 64,
                    'generation_replayed': False, 'full_sdk_typechecked': False},
                  'final_native_rpc_union': native}
        # These controls isolate admission after history authentication. Actual
        # historical hashes are separately checked against retained real bytes.
        self.value['historical_receipts'] = {}
        self.history = patch('import_abi_input.history_proofs', return_value={
            name: proof for name, proof in proofs.items() if name != 'final_native_rpc_union'})
        self.history.start()
        self.value['qualification_receipts'] = {
            name: self.file(self.evidence, name + '.json', json.dumps(proof))
            for name, proof in proofs.items()}
        commands = {}
        for name in ('gomobile_bind', 'generated_invocation_link', 'ios_arm64_exports',
                     'ios-simulator_arm64_exports', 'ios-simulator_x86_64_exports'):
            command = {'command': ['synthetic-test-command', name], 'returncode': 0, 'timed_out': False,
                       'owned_group_drained': True,
                       'stdout': self.file(self.evidence, name + '.stdout', 'synthetic'),
                       'stderr': self.file(self.evidence, name + '.stderr', '')}
            commands[name] = self.file(self.evidence, name + '.json', json.dumps(command))
        self.value['commands'] = commands
        self.value['lib_files'] = [self.file(self.root, LIB + '/fixture', 'SYNTHETIC_NOT_A_BINARY')]
        self.receipt = self.evidence / 'ABI.json'

    def tearDown(self):
        self.history.stop()
        self.temporary.cleanup()

    @staticmethod
    def file(root, name, content):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return {'path': name, 'bytes': path.stat().st_size, 'sha256': sha(path)}

    def check(self):
        self.receipt.write_text(json.dumps(self.value))
        return verify(self.root, self.receipt, sha(self.receipt), self.source)

    def test_complete_control_metadata_is_admitted_without_sdk_credit(self):
        result = self.check()
        self.assertFalse(result['full_sdk_accepted'])
        self.assertFalse(result['editor_ui_accepted'])

    def test_new_schema_cannot_omit_actual_adapter_proof(self):
        self.value['schema'] = 'otzaria.original-import-local-sdk-input/2'
        with self.assertRaisesRegex(ValueError, 'complete actual adapter observation'):
            self.check()

    def test_old_schema_cannot_silently_admit_adapter_outputs(self):
        self.value['pinned_wrapper'] = {'path': 'unadmitted.json'}
        with self.assertRaisesRegex(ValueError, 'historical ABI schema'):
            self.check()

    def test_new_schema_authenticates_actual_adapter_bytes_before_loading(self):
        self.value['schema'] = 'otzaria.original-import-local-sdk-input/2'
        self.value['pinned_wrapper'] = self.file(self.evidence, 'pinned-wrapper/RESULT.json', '{}')
        (self.evidence / 'pinned-wrapper/RESULT.json').write_text('{"tampered":true}')
        with self.assertRaisesRegex(ValueError, 'ABI source/evidence member differs'):
            self.check()

    def test_partial_native_counts_and_changed_source_are_rejected(self):
        for name, count in [('native9', 9), ('imported_creation_date', 6), ('bounded_native_metadata', 12)]:
            self.value['native_qualification']['counts'][name]['passes'] = count - 1
            with self.assertRaisesRegex(ValueError, 'acceptance is incomplete'):
                self.check()
            self.value['native_qualification']['counts'][name]['passes'] = count
        self.value['sdk_source_sha'] = '7' * 40
        with self.assertRaisesRegex(ValueError, 'scope/source differs'):
            self.check()

    def test_installed_binary_mutation_is_rejected(self):
        (self.root / LIB / 'fixture').write_text('CHANGED')
        with self.assertRaisesRegex(ValueError, 'member differs'):
            self.check()

    def test_failed_command_or_changed_stream_is_rejected(self):
        (self.evidence / 'gomobile_bind.stdout').write_text('CHANGED')
        with self.assertRaisesRegex(ValueError, 'member differs'):
            self.check()

    def test_missing_simulator_architecture_is_rejected(self):
        self.value['verified_architectures']['ios-simulator'] = ['arm64']
        with self.assertRaisesRegex(ValueError, 'platform/export/source'):
            self.check()

    def test_receipt_alias_and_wrong_digest_are_rejected(self):
        self.check()
        alias = self.evidence / 'alias.json'
        alias.symlink_to(self.receipt.name)
        with self.assertRaisesRegex(ValueError, 'Aliased'):
            verify(self.root, alias, sha(self.receipt), self.source)
        with self.assertRaisesRegex(ValueError, 'Exact owned'):
            verify(self.root, self.receipt, '8' * 64, self.source)


if __name__ == '__main__':
    unittest.main()
