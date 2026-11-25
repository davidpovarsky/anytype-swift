"""Compiler-cache source and byte-refusal controls; no Apple acceptance."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import local_cache_input as cache


class CacheSourceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git('init', '-q')
        for path, value in {
            'Anytype/Sources/Editor.swift': 'original editor',
            'PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift': 'all six original methods',
            'Anytype/Anytype.entitlements': 'all original groups',
            'Anytype.xcodeproj/project.pbxproj': 'all original targets',
            'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved': 'exact pins',
            'Tools/MiniApps/producer.json': 'historical producer',
        }.items():
            p = self.root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(value)
        self.commit()
        self.original = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'user.name=Integrity Control',
            '-c', 'user.email=control@example.invalid', '-C', str(self.root), *args], text=True)

    def commit(self):
        self.git('add', '.'); self.git('commit', '-qm', 'Synthetic integrity fixture, no native proof')

    def changed(self, path):
        p = self.root / path; p.parent.mkdir(parents=True, exist_ok=True); p.write_text('changed')
        self.commit()
        return cache.compiled_source_tree(self.root, self.original) != cache.compiled_source_tree(self.root, 'HEAD')

    def test_reviewed_producer_metadata_keeps_compiled_source_tree(self):
        self.assertFalse(self.changed('Tools/MiniApps/producer.json'))

    def test_original_application_source_change_is_not_metadata(self):
        self.assertTrue(self.changed('Anytype/Sources/Editor.swift'))

    def test_original_ui_objective_change_is_not_metadata(self):
        self.assertTrue(self.changed('PinkhaStage1Acceptance/Tests/MiniAppsNativeAcceptanceUITests.swift'))

    def test_native_capability_change_is_not_metadata(self):
        self.assertTrue(self.changed('Anytype/Anytype.entitlements'))

    def test_original_project_change_is_not_metadata(self):
        self.assertTrue(self.changed('Anytype.xcodeproj/project.pbxproj'))

    def test_dependency_change_is_not_metadata(self):
        self.assertTrue(self.changed('Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'))

    def test_an_unreviewed_file_below_tools_is_not_whitelisted(self):
        self.assertTrue(self.changed('Tools/MiniApps/NewRuntime.swift'))


class CacheBytesControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'Build').mkdir()
        (self.root / 'MiniAppsCurrentModuleCache.noindex').mkdir()
        (self.root / 'Build/Compiled.o').write_bytes(b'actual-byte-shape-fixture')
        (self.root / 'MiniAppsCurrentModuleCache.noindex/Module.pcm').write_bytes(b'pcm-shape-fixture')

    def test_changed_compiler_bytes_are_detected(self):
        before = cache.cache_inventory(self.root)
        (self.root / 'Build/Compiled.o').write_bytes(b'changed')
        self.assertNotEqual(before, cache.cache_inventory(self.root))

    def test_changed_module_bytes_are_detected(self):
        before = cache.cache_inventory(self.root)
        (self.root / 'MiniAppsCurrentModuleCache.noindex/Module.pcm').write_bytes(b'changed')
        self.assertNotEqual(before, cache.cache_inventory(self.root))

    def test_changed_alias_target_is_detected(self):
        p = self.root / 'Build/alias'; p.symlink_to('Compiled.o')
        before = cache.cache_inventory(self.root)
        p.unlink(); p.symlink_to('Other.o')
        self.assertNotEqual(before, cache.cache_inventory(self.root))

    def test_missing_cache_is_refused(self):
        (self.root / 'MiniAppsCurrentModuleCache.noindex/Module.pcm').unlink()
        (self.root / 'MiniAppsCurrentModuleCache.noindex').rmdir()
        with self.assertRaises(RuntimeError):
            cache.cache_inventory(self.root)

    def test_foreign_cache_path_is_refused_before_any_build_input_is_read(self):
        with self.assertRaises(RuntimeError):
            cache.admit(cache.APP, self.root, self.root, None, None)


if __name__ == '__main__':
    unittest.main(verbosity=2)
