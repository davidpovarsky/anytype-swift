"""Pure mapping controls; no compiled-source or native acceptance credit."""
import hashlib
import os
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent), str(HERE.parent / 'SharedRuntime')]
from test_release_continuation_roots import RootContinuationControls
from release_quarantine_mapping import original_reader, ORIGINAL_HELPER_SHA256


class ContinuedGitMappingControls(unittest.TestCase):
    def setUp(self):
        fixture = RootContinuationControls()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture = fixture
        fixture.quarantine()
        helper = fixture.root / 'Tools/OriginalEditor/SharedRuntime/verify_framework_ownership.py'
        helper.parent.mkdir(parents=True)
        # Read the exact reviewed SDK helper even in a sparse control checkout.
        raw = subprocess.check_output([
            'git', '-c', 'safe.directory=' + str(HERE.parents[2]), '-C', str(HERE.parents[2]),
            'show', '8ae85a6490c4fb763fcd01d5f93345f7e071db92:'
            'Tools/OriginalEditor/SharedRuntime/verify_framework_ownership.py'])
        helper.write_bytes(raw)
        self.assertEqual(hashlib.sha256(helper.read_bytes()).hexdigest(), ORIGINAL_HELPER_SHA256)
        self.helper = helper
        self.checkouts = fixture.exported.parent / 'producer-derived-preserved/SourcePackages/checkouts'
        self.directory = self.checkouts / 'exact-dependency'
        self.original_checkouts = fixture.derived / 'SourcePackages/checkouts'
        alternate = self.directory / '.git/objects/info/alternates'
        alternate.parent.mkdir(parents=True)
        alternate.write_text(str(self.original_checkouts.parent / 'repositories/exact-dependency-123/objects') + '\n')
        self.alternate = alternate
        self.objects = self.checkouts.parent / 'repositories/exact-dependency-123/objects'
        self.objects.mkdir(parents=True)

    def reader(self):
        f = self.fixture
        return original_reader(f.root, f.derived, f.exported, f.collection, f.source)

    def resolve(self, directory=None, checkouts=None, original=None):
        reader, admission = self.reader()
        env, resolution = reader.retained_git_objects(
            directory or self.directory, checkouts or self.checkouts,
            original or self.original_checkouts)
        return env, resolution, admission

    def test_exact_move_uses_original_alternate_without_any_metadata_write(self):
        before = self.alternate.read_bytes()
        env, result, admission = self.resolve()
        self.assertEqual(env['GIT_ALTERNATE_OBJECT_DIRECTORIES'], str(self.objects))
        self.assertEqual(result['retained_objects'], str(self.objects))
        self.assertEqual(self.alternate.read_bytes(), before)
        self.assertTrue(admission['whole_original_ast_restores_exactly'])
        self.assertFalse(admission['git_metadata_modified'])

    def test_aliased_dependency_directory_is_refused(self):
        alias = self.checkouts / 'aliased-dependency'
        alias.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.resolve(directory=alias)

    def test_changed_qualified_helper_is_refused(self):
        self.helper.write_bytes(self.helper.read_bytes() + b'\n')
        with self.assertRaises(ValueError):
            self.reader()

    def test_other_original_root_is_refused_even_if_it_is_absent(self):
        other = self.fixture.root / 'build/foreign/producer-derived/SourcePackages/checkouts'
        with self.assertRaises(ValueError):
            self.resolve(original=other)

    def test_other_retained_root_with_same_suffix_is_refused(self):
        other = self.fixture.root / 'build/foreign/producer-derived-preserved/SourcePackages/checkouts'
        directory = other / 'exact-dependency'
        directory.mkdir(parents=True)
        with self.assertRaises(ValueError):
            self.resolve(directory=directory, checkouts=other)

    def test_foreign_alternate_is_refused(self):
        self.alternate.write_text('/foreign/repositories/exact-dependency-123/objects\n')
        with self.assertRaises(ValueError):
            self.resolve()

    def test_multiple_alternates_are_refused(self):
        self.alternate.write_bytes(self.alternate.read_bytes() * 2)
        with self.assertRaises(ValueError):
            self.resolve()

    def test_recreated_original_compiler_directory_is_refused(self):
        self.fixture.derived.mkdir()
        with self.assertRaises(ValueError):
            self.resolve()

    def test_transitively_redirected_object_store_is_refused(self):
        path = self.objects / 'info/alternates'
        path.parent.mkdir()
        path.write_text('/somewhere/else\n')
        with self.assertRaises(ValueError):
            self.resolve()

    def test_external_primary_object_override_is_refused(self):
        with patch.dict(os.environ, {'GIT_OBJECT_DIRECTORY': '/foreign/objects'}):
            with self.assertRaises(ValueError):
                self.resolve()

    def test_missing_or_changed_root_proof_is_refused_before_any_git_read(self):
        self.fixture.collection.pop('collection_continuation')
        with self.assertRaises(ValueError):
            self.reader()


if __name__ == '__main__':
    unittest.main(verbosity=2)
