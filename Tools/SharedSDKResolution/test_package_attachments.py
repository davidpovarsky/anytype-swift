"""Two new admission controls for actual PBX owning attachment semantics."""
import copy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('package_attachment_resolution', HERE / 'resolve_packages.py')
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OriginalPackageAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.original = {'objects': {
            'P': {'isa': 'PBXProject', 'packageReferences': ['R']},
            'A': {'isa': 'PBXNativeTarget', 'name': 'OriginalApp', 'packageProductDependencies': ['D']},
            'B': {'isa': 'PBXNativeTarget', 'name': 'OtherTarget', 'packageProductDependencies': []},
            'R': {'isa': 'XCRemoteSwiftPackageReference', 'repositoryURL': 'https://example.invalid/original',
                  'requirement': {'kind': 'revision', 'revision': '1' * 40}},
            'D': {'isa': 'XCSwiftPackageProductDependency', 'package': 'R', 'productName': 'OriginalProduct'},
        }}
        self.before = MODULE.package_graph(self.original)
        MODULE.require_unchanged_package_graph(self.before, MODULE.package_graph(copy.deepcopy(self.original)))

    def test_retained_reference_objects_cannot_hide_project_attachment_removal(self):
        modified = copy.deepcopy(self.original)
        modified['objects']['P']['packageReferences'] = []
        after = MODULE.package_graph(modified)
        self.assertEqual(after['references'], self.before['references'])
        with self.assertRaisesRegex(RuntimeError, 'owning project/target attachments'):
            MODULE.require_unchanged_package_graph(self.before, after)

    def test_retained_product_objects_cannot_hide_reassignment_to_other_target(self):
        modified = copy.deepcopy(self.original)
        modified['objects']['A']['packageProductDependencies'] = []
        modified['objects']['B']['packageProductDependencies'] = ['D']
        after = MODULE.package_graph(modified)
        self.assertEqual(after['references'], self.before['references'])
        with self.assertRaisesRegex(RuntimeError, 'owning project/target attachments'):
            MODULE.require_unchanged_package_graph(self.before, after)


if __name__ == '__main__':
    unittest.main()
