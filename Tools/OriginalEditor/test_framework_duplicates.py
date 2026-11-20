"""Whole-exporter controls for the two observed Lib locations; no Apple credit."""
import hashlib
import ctypes
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import unittest
from unittest.mock import patch

import framework_products as products_module
import test_framework as original_controls


class DarwinXattrBoundaryDouble:
    """Explicit ABI double; it is not a Darwin filesystem execution."""
    class Function:
        def __init__(self, call): self.call = call
        def __call__(self, *arguments): return self.call(*arguments)

    def __init__(self):
        self.names = b'user.payload\0user.empty\0'
        self.values = {b'user.payload': b'a\x00b', b'user.empty': b''}
        self.calls = []
        self.list_probe = self.list_result = self.get_probe = self.get_result = None
        self.listxattr = self.Function(self.listing)
        self.getxattr = self.Function(self.reading)

    def transfer(self, value, buffer, size, probe, result):
        if buffer is None:
            return len(value) if probe is None else probe
        if result is not None:
            return result
        if size < len(value):
            return -1
        ctypes.memmove(buffer, value, len(value))
        return len(value)

    def listing(self, path, buffer, size, options):
        self.calls.append(('list', path, buffer is None, size, options))
        return self.transfer(self.names, buffer, size, self.list_probe, self.list_result)

    def reading(self, path, name, buffer, size, position, options):
        self.calls.append(('get', path, name, buffer is None, size, position, options))
        return self.transfer(self.values[name], buffer, size, self.get_probe, self.get_result)


class DarwinAttributeBoundaryControls(unittest.TestCase):
    def setUp(self):
        self.library = DarwinXattrBoundaryDouble()

    def read(self, follow=True):
        with patch.object(products_module.sys, 'platform', 'darwin'), \
                patch('ctypes.CDLL', return_value=self.library) as load:
            result = products_module.framework_extended_attributes('/explicit/synthetic/path', follow)
        load.assert_called_once_with(None, use_errno=True)
        return result

    def test_darwin_typed_abi_reads_binary_and_empty_attributes(self):
        value = self.read()
        self.assertEqual(value, {name.decode(): {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                                 for name, raw in self.library.values.items()})
        self.assertEqual(self.library.listxattr.argtypes,
                         [ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int])
        self.assertEqual(self.library.getxattr.argtypes,
                         [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p,
                          ctypes.c_size_t, ctypes.c_uint32, ctypes.c_int])
        self.assertIs(self.library.listxattr.restype, ctypes.c_ssize_t)
        self.assertIs(self.library.getxattr.restype, ctypes.c_ssize_t)
        self.assertTrue(all(call[-1] == 0x20 for call in self.library.calls))
        self.assertTrue(all(call[-2] == 0 for call in self.library.calls if call[0] == 'get'))

    def test_darwin_nofollow_inspects_link_attributes(self):
        self.read(follow=False)
        self.assertTrue(all(call[-1] == 0x21 for call in self.library.calls))

    def test_darwin_genuine_empty_list_is_empty_without_skipping_the_api(self):
        self.library.names = b''
        self.assertEqual(self.read(), {})
        self.assertEqual([call[0] for call in self.library.calls], ['list', 'list'])

    def test_darwin_unreadable_list_fails_closed(self):
        self.library.list_probe = -1
        with self.assertRaises(ValueError): self.read()

    def test_darwin_oversized_list_fails_before_allocation(self):
        self.library.list_probe = 16 * 1024 * 1024 + 1
        with self.assertRaises(ValueError): self.read()
        self.assertEqual(len(self.library.calls), 1)

    def test_darwin_list_changed_between_probe_and_read_fails(self):
        self.library.list_result = -1
        with self.assertRaises(ValueError): self.read()

    def test_darwin_missing_nul_terminator_fails(self):
        self.library.names = b'user.payload'
        with self.assertRaises(ValueError): self.read()

    def test_darwin_duplicate_name_fails(self):
        self.library.names = b'user.payload\0user.payload\0'
        with self.assertRaises(ValueError): self.read()

    def test_darwin_unreadable_attribute_fails(self):
        self.library.get_probe = -1
        with self.assertRaises(ValueError): self.read()

    def test_darwin_attribute_changed_between_probe_and_read_fails(self):
        self.library.get_result = -1
        with self.assertRaises(ValueError): self.read()


class KnownLibDuplicateControls(unittest.TestCase):
    def setUp(self):
        original_controls.RealFilesystemExportControls.setUp(self)
        self.first = (self.products / 'Lib.framework').resolve()
        self.second = (self.products / 'PackageFrameworks/Lib.framework').resolve()
        self.first.mkdir()
        (self.first / 'Lib').write_bytes(b'EXPLICIT_SYNTHETIC_LIB_NOT_AN_APPLE_BINARY')
        (self.first / 'Lib').chmod(0o755)
        for name, data in [('Info.plist', b'synthetic info'),
                           ('Headers/Lib.h', b'synthetic header'),
                           ('Modules/module.modulemap', b'synthetic module'),
                           ('Resources/item.bin', b'synthetic resource'),
                           ('_CodeSignature/CodeResources', b'synthetic signature')]:
            path = self.first / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.second.parent.mkdir()
        shutil.copytree(self.first, self.second, symlinks=True)

    def export(self):
        return products_module.export_products(self.products, self.exported, self.producer)

    def denied(self):
        with self.assertRaises(ValueError):
            self.export()

    def test_exact_known_pair_preserves_complete_equal_inputs_and_exports_one_lib(self):
        value = self.export()
        self.assertEqual(value['frameworks'], ['AnytypeOriginalEditor.framework', 'Lib.framework'])
        proof, = value['verified_known_duplicates']
        self.assertEqual(proof['selected'], 'Lib.framework')
        self.assertEqual(set(proof['source_closures']), {'Lib.framework', 'PackageFrameworks/Lib.framework'})
        first, second = (proof['source_closures'][p] for p in ['Lib.framework', 'PackageFrameworks/Lib.framework'])
        self.assertEqual(first, second)
        self.assertIn('.', first)
        self.assertIn('_CodeSignature/CodeResources', first)
        self.assertEqual(first['Lib']['mode'], 0o755)
        self.assertEqual(first['Lib']['sha256'], hashlib.sha256((self.first / 'Lib').read_bytes()).hexdigest())
        self.assertEqual(proof['materialized_export_closure']['Lib']['sha256'], first['Lib']['sha256'])
        self.assertEqual((self.first / 'Lib').read_bytes(), (self.second / 'Lib').read_bytes())

    def test_different_binary_byte_fails_without_choosing_the_first(self):
        (self.second / 'Lib').write_bytes(b'DIFFERENT_SYNTHETIC_LIB')
        self.denied()

    def test_different_signature_byte_fails(self):
        (self.second / '_CodeSignature/CodeResources').write_bytes(b'different signature')
        self.denied()

    def test_missing_resource_fails(self):
        (self.second / 'Resources/item.bin').unlink()
        self.denied()

    def test_different_relative_filename_with_same_bytes_fails(self):
        (self.second / 'Resources/item.bin').rename(self.second / 'Resources/other.bin')
        self.denied()

    def test_additional_empty_directory_fails(self):
        (self.second / 'additional').mkdir()
        self.denied()

    def test_different_file_mode_fails(self):
        (self.second / 'Lib').chmod(0o644)
        self.denied()

    def test_different_directory_mode_fails(self):
        (self.second / 'Resources').chmod(0o700)
        self.denied()

    def test_different_extended_attribute_fails(self):
        if sys.platform == 'darwin':
            subprocess.run(['/usr/bin/xattr', '-w', 'user.otzaria_export_fixture', 'changed',
                            str(self.second / 'Lib')], check=True, capture_output=True, timeout=10)
        else:
            os.setxattr(self.second / 'Lib', 'user.otzaria_export_fixture', b'changed')
        self.denied()

    def test_equal_internal_file_alias_is_materialized(self):
        for root in [self.first, self.second]:
            (root / 'LibraryAlias').symlink_to('Lib')
        value = self.export()
        proof, = value['verified_known_duplicates']
        self.assertEqual(proof['source_closures']['Lib.framework']['LibraryAlias']['link_target'], 'Lib')
        target = self.exported / 'Frameworks/Lib.framework/LibraryAlias'
        self.assertFalse(target.is_symlink())
        self.assertEqual(target.read_bytes(), (self.first / 'Lib').read_bytes())

    def test_equal_versioned_directory_aliases_preserve_all_resolved_members(self):
        for root in [self.first, self.second]:
            (root / 'Versions/A').mkdir(parents=True)
            (root / 'Versions/A/data').write_bytes(b'explicit versioned fixture')
            (root / 'Versions/Current').symlink_to('A', target_is_directory=True)
            (root / 'Current').symlink_to('Versions/Current', target_is_directory=True)
        value = self.export()
        proof, = value['verified_known_duplicates']
        self.assertIn('Current/data', proof['source_closures']['Lib.framework'])
        self.assertEqual((self.exported / 'Frameworks/Lib.framework/Current/data').read_bytes(),
                         b'explicit versioned fixture')

    def test_different_literal_symlink_target_fails_even_with_same_resolved_bytes(self):
        (self.first / 'Alias').symlink_to('Lib')
        (self.second / 'Alias').symlink_to('./Lib')
        self.denied()

    def test_product_alias_to_owned_but_other_framework_fails(self):
        for root in [self.first, self.second]:
            (root / 'Alias').symlink_to(self.products / 'AnytypeOriginalEditor.framework/AnytypeOriginalEditor')
        self.denied()

    def test_cyclic_internal_directory_alias_fails(self):
        for root in [self.first, self.second]:
            (root / 'Cycle').symlink_to('.', target_is_directory=True)
        self.denied()

    def test_broken_alias_fails(self):
        for root in [self.first, self.second]:
            (root / 'Broken').symlink_to('missing')
        self.denied()

    def test_special_fifo_fails_without_reading_it(self):
        for root in [self.first, self.second]:
            os.mkfifo(root / 'fifo')
        self.denied()

    def test_unexpected_third_lib_location_fails(self):
        shutil.copytree(self.first, self.products / 'Other/Lib.framework')
        self.denied()

    def test_same_pair_under_unreviewed_parent_fails(self):
        self.second.parent.rename(self.products / 'OtherPackageFrameworks')
        self.denied()

    def test_duplicate_original_editor_framework_still_fails(self):
        shutil.copytree(self.products / 'AnytypeOriginalEditor.framework',
                        self.products / 'PackageFrameworks/AnytypeOriginalEditor.framework')
        self.denied()

    def test_missing_original_editor_framework_still_fails(self):
        shutil.rmtree(self.products / 'AnytypeOriginalEditor.framework')
        self.denied()

    def test_root_framework_alias_is_not_an_independent_known_product(self):
        shutil.rmtree(self.second)
        self.second.symlink_to(self.first, target_is_directory=True)
        self.denied()

    def test_only_timestamps_may_differ(self):
        os.utime(self.second / 'Lib', (1, 1))
        self.assertEqual(self.export()['frameworks'], ['AnytypeOriginalEditor.framework', 'Lib.framework'])

    def test_whole_exporter_darwin_path_does_not_require_linux_os_xattr(self):
        class WithoutLinuxXattr:
            def __getattr__(self, name):
                if name in {'listxattr', 'getxattr'}:
                    raise AttributeError('Darwin CPython has no Linux os xattr API')
                return getattr(os, name)
        library = DarwinXattrBoundaryDouble()
        library.names = b''
        with patch.object(products_module, 'os', WithoutLinuxXattr()), \
                patch.object(sys, 'platform', 'darwin'), \
                patch('ctypes.CDLL', return_value=library):
            value = self.export()
        self.assertEqual(value['frameworks'], ['AnytypeOriginalEditor.framework', 'Lib.framework'])
        self.assertTrue(library.calls)

    def test_known_input_changed_during_copy_cannot_publish_success(self):
        real = products_module.copy_product
        mutations = []
        def changed(source, target, producer):
            real(source, target, producer)
            if Path(source) == self.first:
                (self.second / 'Lib').write_bytes(b'changed after admitted comparison')
                mutations.append(self.second / 'Lib')
        with patch.object(products_module, 'copy_product', changed):
            self.denied()
        self.assertEqual(mutations, [self.second / 'Lib'])
        self.assertEqual((self.second / 'Lib').read_bytes(), b'changed after admitted comparison')

    def test_changed_materialized_output_cannot_publish_success(self):
        real = products_module.copy_product
        mutations = []
        def changed(source, target, producer):
            real(source, target, producer)
            if Path(source) == self.first:
                (Path(target) / 'Lib').write_bytes(b'changed exported file')
                mutations.append(Path(target) / 'Lib')
        with patch.object(products_module, 'copy_product', changed):
            self.denied()
        self.assertEqual(mutations, [(self.exported / 'Frameworks/Lib.framework/Lib').resolve()])
        self.assertEqual(mutations[0].read_bytes(), b'changed exported file')


if __name__ == '__main__':
    unittest.main()
