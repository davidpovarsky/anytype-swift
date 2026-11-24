"""Focused synthetic controls; these do not claim Mac, ABI or editor acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import uuid

import local_execution as execution


class LocalExecutionControls(unittest.TestCase):
    def setUp(self):
        self.root = Path('/Users/m1/builds/anytype-source-sdk')
        self.host = {'system': 'Darwin', 'architecture': 'arm64', 'hostname': 'test-mac'}
        self.head, self.tree = '1' * 40, '2' * 40
        self.record = {'schema': execution.SCHEMA, 'repository': execution.REPOSITORY,
                       'execution_id': 'local-' + str(uuid.uuid4()),
                       'source_sha': self.head, 'source_tree': self.tree,
                       'head_branch': execution.LOCAL_BRANCH, 'root': str(self.root),
                       'host': self.host, 'acceptance': 'PROVENANCE_ONLY_NOT_ACCEPTANCE'}

    def check(self, record):
        return execution.validate_record(record, self.root, self.head, self.tree,
                                          execution.LOCAL_BRANCH, self.host)

    def test_exact_local_identity_is_distinct_from_actions(self):
        self.assertEqual(self.check(self.record), self.record)
        with self.assertRaises(ValueError):
            self.check({**self.record, 'execution_id': '45269355714'})

    def test_source_tree_branch_and_checkout_must_all_match(self):
        for key, value in [('source_sha', '3' * 40), ('source_tree', '4' * 40),
                           ('head_branch', 'develop'), ('root', '/Users/m1/other')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check({**self.record, key: value})

    def test_other_machine_and_nonapple_are_rejected(self):
        for key, value in [('hostname', 'other-mac'), ('architecture', 'x86_64'),
                           ('system', 'Linux')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check({**self.record, 'host': {**self.host, key: value}})

    def test_identity_cannot_claim_acceptance(self):
        with self.assertRaises(ValueError):
            self.check({**self.record, 'acceptance': 'PASS'})

    def test_local_and_actions_context_cannot_mix(self):
        with self.assertRaisesRegex(ValueError, 'cannot be mixed'):
            execution.read_identity({'OTZARIA_LOCAL_EXECUTION': '/not-read',
                                     'OTZARIA_LOCAL_EXECUTION_SHA256': 'a' * 64,
                                     'GITHUB_RUN_ID': '12345'})

    def test_descriptor_digest_is_required_before_parse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'identity.json'
            path.write_text(json.dumps(self.record))
            with self.assertRaisesRegex(ValueError, 'bytes differ'):
                execution.read_identity({'OTZARIA_LOCAL_EXECUTION': str(path),
                                         'OTZARIA_LOCAL_EXECUTION_SHA256': 'a' * 64})


if __name__ == '__main__':
    unittest.main()
