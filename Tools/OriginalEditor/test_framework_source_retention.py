"""Original input-list validator plus original evidence packager, synthetic inputs."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
import zipfile

from framework_profile import HERE, TARGET
from run_framework_acceptance import source_file_proof


class OriginalRawCompilerEvidenceControls(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'source'
        self.derived = self.root / 'build/producer-derived'
        self.evidence = Path(self.temporary.name) / 'evidence'
        self.evidence.mkdir()
        self.sources = ['Anytype/Sources/Original.swift', 'Anytype/Sources/ApplicationLayer/AppScene.swift']
        self.expected = [self.root / self.sources[0], self.root / 'Anytype/Resources/AssetConstants.swift',
                         self.root / 'OriginalEditorFramework/AnytypeOriginalEditorModule.swift']
        self.generated = self.derived / 'Build/Generated/Input.swift'
        for path in [*self.expected, self.root / self.sources[1], self.generated]:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'// EXPLICIT_SYNTHETIC_SOURCE_BOUNDARY_NOT_COMPILED\n')
        self.file_list = self.derived / 'Build/Intermediates' / (TARGET + '.build') / 'Inputs.SwiftFileList'
        self.file_list.parent.mkdir(parents=True)
        self.write_list([*self.expected, self.generated])
        self.accessors = []
        for name in ['Assets', 'Loc', 'DesignKit']:
            path = self.derived / 'Build/Intermediates' / (name + '.build') / 'resource_bundle_accessor.swift'
            path.parent.mkdir(parents=True)
            path.write_bytes(('// SYNTHETIC_GENERATED_ACCESSOR_' + name + '\n').encode())
            self.accessors.append(path)

    def write_list(self, values):
        self.file_list.write_bytes(('\n'.join(shlex.quote(str(p)) for p in values) + '\n').encode())

    def proof(self):
        return source_file_proof(self.root, self.derived, {
            'source_files': self.sources,
            'framework_facade_sources': ['OriginalEditorFramework/AnytypeOriginalEditorModule.swift']}, self.evidence)

    def test_original_packager_retains_all_four_exact_raw_proofs_as_text(self):
        value = self.proof()
        self.assertEqual(value['complete_original_swift_input_count'], 3)
        self.assertEqual(value['generated_swift_input_count'], 1)
        originals = {str(p): p.read_bytes() for p in [self.file_list, *self.accessors]}
        retained = value['lists'] + value['generated_bundle_accessors']
        self.assertEqual(len(retained), 4)
        for row in retained:
            self.assertIn('evidence_path', row)
            self.assertTrue(row['evidence_path'].endswith('.txt'))
            actual = (self.evidence / row['evidence_path']).read_bytes()
            self.assertEqual(actual, originals[row['path']])
            self.assertEqual(hashlib.sha256(actual).hexdigest(), row['sha256'])
            self.assertEqual(len(actual), row['bytes'])
        packager = HERE.parents[1] / 'Tools/PinkhaNativeDerived/package_evidence.py'
        result = subprocess.run([sys.executable, str(packager), str(self.evidence)],
                                capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr.decode())
        with zipfile.ZipFile(self.evidence / 'Pinkha-Native-Derived-Evidence.zip') as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {'actual-framework-source-inputs.json',
                                                     *[row['evidence_path'] for row in retained]})
            for row in retained:
                self.assertEqual(archive.read(row['evidence_path']), originals[row['path']])
        self.assertEqual({str(p): p.read_bytes() for p in [self.file_list, *self.accessors]}, originals)

    def test_missing_original_input_still_fails(self):
        self.write_list([*self.expected[1:], self.generated])
        with self.assertRaises(ValueError): self.proof()

    def test_foreign_unowned_source_still_fails(self):
        foreign = Path(self.temporary.name) / 'Foreign.swift'
        foreign.write_bytes(b'// not an admitted source')
        self.write_list([*self.expected, self.generated, foreign])
        with self.assertRaises(ValueError): self.proof()

    def test_original_app_entrypoint_still_fails(self):
        self.write_list([*self.expected, self.generated, self.root / self.sources[1]])
        with self.assertRaises(ValueError): self.proof()

    def test_missing_generated_bundle_accessor_still_fails(self):
        self.accessors[0].unlink()
        with self.assertRaises(ValueError): self.proof()

    def test_duplicate_generated_bundle_accessor_still_fails(self):
        extra = self.derived / 'Other/Assets.build/resource_bundle_accessor.swift'
        extra.parent.mkdir(parents=True)
        extra.write_bytes(self.accessors[0].read_bytes())
        with self.assertRaises(ValueError): self.proof()

    def test_malformed_original_source_line_still_fails(self):
        self.file_list.write_bytes(b'one.swift two.swift\n')
        with self.assertRaises(ValueError): self.proof()


if __name__ == '__main__':
    unittest.main()
