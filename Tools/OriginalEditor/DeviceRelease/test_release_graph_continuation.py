"""Compiler-provenance continuation refusal controls; no Apple build/UI credit."""
import copy
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_release_controls as original
import collect_release_graphs as collector
from release_contract import current_build_context, write


class ContinuationGraphControls(unittest.TestCase):
    write_build = original.ReleaseGraphControls.write_build

    def setUp(self):
        original.ReleaseGraphControls.setUp(self)
        self.execution.update(root=str(self.root), evidence_root=str(self.evidence))
        write(self.descriptor, self.execution)
        self.context = current_build_context(self.before, self.execution, self.descriptor)
        write(self.evidence / 'execution.json', {'status': 'FAIL',
              'scope': 'SYNTHETIC_COMPILER_PROVENANCE_CONTROL_NO_NATIVE_CREDIT'})
        self.current = self.root / 'build/continuation'
        self.current.mkdir()
        self.output = self.current / 'actual-public-symbol-graphs'
        self.continuation = {
            'schema': 'otzaria.original-editor.release-postbuild-continuation/1',
            'execution_id': 'local-33333333-3333-4333-8333-333333333333',
            'previous_evidence': str(self.evidence), 'evidence_root': str(self.current),
            'source_sha': self.before['head_sha'], 'build_run_id': self.execution['execution_id'],
            'previous_descriptor_sha256': collector.sha256(self.descriptor),
            'previous_execution_sha256': collector.sha256(self.evidence / 'execution.json'),
            'compiler_executions': 0}
        write(self.current / 'continuation.json', self.continuation)

    def collect(self, compiler_evidence=None):
        return collector.collect(self.root, self.derived, self.current, self.sdk,
            self.output, 'iphonesimulator', self.context,
            compiler_evidence=self.evidence if compiler_evidence is None else compiler_evidence)

    def test_original_compiler_uuid_paths_bytes_and_full_graphs_are_preserved(self):
        before = {p.name: p.read_bytes() for p in self.evidence.iterdir() if p.is_file()}
        result = self.collect()
        self.assertEqual(result['run_id'], self.execution['execution_id'])
        self.assertEqual(result['collection_continuation']['execution_id'],
                         self.continuation['execution_id'])
        self.assertEqual(result['collection_continuation']['compiler_descriptor_path'], str(self.descriptor))
        self.assertEqual(result['collection_continuation']['compiler_executions'], 0)
        self.assertFalse((self.current / 'release-execution.json').exists())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.evidence.iterdir() if p.is_file()})
        self.assertEqual({p.name: p.read_bytes() for p in self.graphs.iterdir()},
                         {p.name: p.read_bytes() for p in self.output.iterdir()})

    def test_changed_continuation_binding_is_refused(self):
        changes = {'schema': 'other', 'previous_evidence': str(self.current),
            'evidence_root': str(self.evidence), 'compiler_executions': 1,
            'execution_id': self.execution['execution_id'], 'source_sha': '9' * 40,
            'build_run_id': self.continuation['execution_id'],
            'previous_descriptor_sha256': '0' * 64, 'previous_execution_sha256': '0' * 64}
        for key, value in changes.items():
            with self.subTest(key=key):
                changed = dict(self.continuation); changed[key] = value
                write(self.current / 'continuation.json', changed)
                with self.assertRaises(ValueError):
                    self.collect()
        write(self.current / 'continuation.json', self.continuation)

    def test_missing_continuation_is_refused(self):
        (self.current / 'continuation.json').unlink()
        with self.assertRaises(FileNotFoundError):
            self.collect()

    def test_changed_original_descriptor_is_refused(self):
        self.descriptor.write_bytes(self.descriptor.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.collect()

    def test_changed_original_failure_receipt_is_refused(self):
        p = self.evidence / 'execution.json'; p.write_bytes(p.read_bytes() + b' ')
        with self.assertRaises(ValueError):
            self.collect()

    def test_relabelled_result_bundle_path_is_refused(self):
        p = self.evidence / 'framework-build.command.json'
        value = json.loads(p.read_text())
        index = value['command'].index('-resultBundlePath')
        value['command'][index + 1] = str(self.current / 'framework-build.xcresult')
        write(p, value)
        with self.assertRaises(ValueError):
            self.collect()

    def test_continuation_uuid_cannot_replace_the_original_compiler_context(self):
        self.context['run_id'] = self.continuation['execution_id']
        with self.assertRaises(ValueError):
            self.collect()

    def test_changed_original_compiler_output_is_refused(self):
        p = self.evidence / 'framework-build.stdout.log'
        p.write_text(p.read_text() + 'changed compiler output')
        with self.assertRaises(ValueError):
            self.collect()

    def test_changed_source_or_old_graph_timestamp_is_refused(self):
        with patch.object(collector, 'source_observation', return_value={'head_sha': '9' * 40}):
            with self.assertRaises(ValueError):
                self.collect()
        for path in self.graphs.iterdir():
            os.utime(path, (1, 1))
        with self.assertRaises(ValueError):
            self.collect()

    def test_aliased_compiler_evidence_is_refused(self):
        alias = self.root / 'build/alias'; alias.symlink_to(self.evidence, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.collect(alias)


if __name__ == '__main__':
    unittest.main(verbosity=2)
