import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from framework_products import inventory
from signed_consumer_framework_roles import (
    derive_original_framework_roles, header_role, verify_embedded_frameworks,
)


PACKET = Path(__file__).resolve().parents[2] / (
    'docs/pinkha/torah-integration/evidence/'
    'original-editor-signed-consumer-20261123/framework-role-admission'
)


class OriginalFrameworkRolesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.exported = json.loads((PACKET / 'original-framework-distribution.json').read_bytes())
        cls.retained = json.loads((PACKET / 'original-consumer-retention.json').read_bytes())
        cls.members = {path.name: path.read_bytes() for path in (PACKET / 'original-headers').iterdir()
                       if path.is_file()}
        cls.roles = derive_original_framework_roles(cls.members.__getitem__, cls.exported, cls.retained)

    def fixture(self, root):
        # Deliberate tiny UNIT files, never original products or runtime evidence.
        distribution, app = root / 'distribution', root / 'consumer.app'
        (distribution / 'Frameworks').mkdir(parents=True)
        (app / 'Frameworks').mkdir(parents=True)
        for name in self.exported['frameworks']:
            directory = distribution / 'Frameworks' / name
            directory.mkdir()
            (directory / name.removesuffix('.framework')).write_bytes(('UNIT_BINARY:' + name).encode())
            (directory / 'Info.plist').write_bytes(('UNIT_INFO:' + name).encode())
            (directory / '_CodeSignature').mkdir()
            (directory / '_CodeSignature/CodeResources').write_bytes(('UNIT_RESOURCE_SEAL:' + name).encode())
            if name in self.roles['dynamic_embeds']:
                shutil.copytree(directory, app / 'Frameworks' / name)
        exported = {'frameworks': list(self.exported['frameworks']), 'files': inventory(distribution)}
        return app, distribution, exported

    def test_authentic_original_headers_select_exact_retained_signed_app(self):
        self.assertEqual(len(self.roles['frameworks']), 17)
        self.assertEqual(len(self.roles['dynamic_embeds']), 15)
        self.assertEqual(self.roles['static_distribution_only'], ['Lib.framework', 'Sentry.framework'])
        self.assertEqual(self.roles['original_signed_app_directories'], self.roles['dynamic_embeds'])
        self.assertEqual([r['original_index'] for r in self.roles['original_header_receipts']], list(range(17)))
        self.assertTrue(all(r['command_exit_code'] == 0 and r['timed_out'] is False
                            for r in self.roles['original_header_receipts']))
        with tempfile.TemporaryDirectory(prefix='otzaria-framework-role-unit-') as directory:
            app, distribution, exported = self.fixture(Path(directory))
            result = verify_embedded_frameworks(app, distribution, exported, self.roles)
            self.assertEqual(len(result['dynamic_frameworks']), 15)
            self.assertEqual(result['complete_distribution_frameworks_checked'], 17)
            self.assertFalse(result['runtime_execution'])

    def test_tampered_missing_failed_or_misbound_original_receipts_rejected(self):
        stem = 'framework-header-0'
        changes = []
        for stream in ['stdout', 'stderr']:
            members = dict(self.members)
            members[stem + '.' + stream + '.log'] += b'altered'
            changes.append(members)
        for key, value in [('returncode', 1), ('returncode', False), ('timed_out', True)]:
            members = dict(self.members)
            command = json.loads(members[stem + '.command.json'])
            command[key] = value
            members[stem + '.command.json'] = json.dumps(command).encode()
            changes.append(members)
        members = dict(self.members)
        command = json.loads(members[stem + '.command.json'])
        command['command'][2] = '/other/distribution/Frameworks/Lib.framework/Lib'
        members[stem + '.command.json'] = json.dumps(command).encode()
        changes.append(members)
        members = dict(self.members)
        del members[stem + '.stdout.log']
        changes.append(members)
        members = dict(self.members)
        members[stem + '.command.json'] = members['framework-header-1.command.json']
        changes.append(members)
        for number, members in enumerate(changes):
            with self.subTest(mutation=number), self.assertRaises(RuntimeError):
                derive_original_framework_roles(members.__getitem__, self.exported, self.retained)
        duplicate = copy.deepcopy(self.exported)
        duplicate['frameworks'].append(duplicate['frameworks'][0])
        with self.assertRaises(RuntimeError):
            derive_original_framework_roles(self.members.__getitem__, duplicate, self.retained)

    def test_unknown_mixed_or_nonarchive_object_headers_rejected(self):
        command = json.loads(self.members['framework-header-3.command.json'])
        binary = command['command'][2]
        dynamic = self.members['framework-header-3.stdout.log']
        object_row = b'MH_MAGIC_64 ARM64 ALL 0x00 OBJECT 1 32 0x00\n'
        invalid = [
            b'', b'\xff', dynamic.replace(b'DYLIB', b'BUNDLE'),
            dynamic + object_row, b'Archive : ' + binary.encode() + b'\n' + dynamic,
            dynamic.replace(b'DYLIB', b'OBJECT'),
            dynamic.replace(binary.encode(), b'/wrong/framework/binary'),
        ]
        for raw in invalid:
            with self.subTest(header_sha256=hashlib.sha256(raw).hexdigest()), self.assertRaises(RuntimeError):
                header_role(raw, binary)

    def test_missing_extra_or_static_signed_app_embeds_rejected(self):
        for mutation in ['missing', 'extra', 'Lib.framework', 'Sentry.framework']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix='otzaria-framework-role-unit-') as directory:
                app, distribution, exported = self.fixture(Path(directory))
                if mutation == 'missing':
                    shutil.rmtree(app / 'Frameworks' / self.roles['dynamic_embeds'][0])
                elif mutation == 'extra':
                    (app / 'Frameworks/Unexpected.framework').mkdir()
                else:
                    shutil.copytree(distribution / 'Frameworks' / mutation, app / 'Frameworks' / mutation)
                with self.assertRaises(RuntimeError):
                    verify_embedded_frameworks(app, distribution, exported, self.roles)

    def test_dynamic_byte_size_member_and_resource_changes_rejected(self):
        for mutation in ['same-size-bytes', 'size', 'missing-info', 'resource-seal']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix='otzaria-framework-role-unit-') as directory:
                app, distribution, exported = self.fixture(Path(directory))
                framework = app / 'Frameworks/AnytypeOriginalEditor.framework'
                binary = framework / 'AnytypeOriginalEditor'
                if mutation == 'same-size-bytes':
                    raw = binary.read_bytes()
                    binary.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
                elif mutation == 'size':
                    binary.write_bytes(binary.read_bytes() + b'changed')
                elif mutation == 'missing-info':
                    (framework / 'Info.plist').unlink()
                else:
                    (framework / '_CodeSignature/CodeResources').write_bytes(b'altered-unit-seal')
                with self.assertRaises(RuntimeError):
                    verify_embedded_frameworks(app, distribution, exported, self.roles)

    def test_static_inventory_role_name_and_alias_changes_rejected(self):
        for mutation in ['static-bytes', 'static-missing', 'missing-role', 'forged-role', 'duplicate-role', 'alias']:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(prefix='otzaria-framework-role-unit-') as directory:
                app, distribution, exported = self.fixture(Path(directory))
                roles = copy.deepcopy(self.roles)
                if mutation == 'static-bytes':
                    (distribution / 'Frameworks/Lib.framework/Lib').write_bytes(b'changed-unit-static')
                elif mutation == 'static-missing':
                    shutil.rmtree(distribution / 'Frameworks/Sentry.framework')
                elif mutation == 'missing-role':
                    roles['frameworks'] = roles['frameworks'][:-1]
                elif mutation == 'forged-role':
                    roles['static_distribution_only'].remove('Lib.framework')
                    roles['dynamic_embeds'].append('Lib.framework')
                    roles['dynamic_embeds'].sort()
                elif mutation == 'duplicate-role':
                    roles['dynamic_embeds'].append(roles['dynamic_embeds'][0])
                else:
                    target = app / 'Frameworks' / roles['dynamic_embeds'][0]
                    shutil.rmtree(target)
                    target.symlink_to(distribution / 'Frameworks' / roles['dynamic_embeds'][0], target_is_directory=True)
                with self.assertRaises(RuntimeError):
                    verify_embedded_frameworks(app, distribution, exported, roles)


if __name__ == '__main__':
    unittest.main()
