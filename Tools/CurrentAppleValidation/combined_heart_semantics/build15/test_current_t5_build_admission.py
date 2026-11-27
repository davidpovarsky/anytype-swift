import copy
import plistlib
from pathlib import Path
import tempfile
import unittest

import current_t5_build_admission as gate


class CurrentT5OriginTests(unittest.TestCase):
    def setUp(self):
        self.contract = {'source': {'commit': '1' * 40}, 'build': {'receipt': {'sha256': '2' * 64}}}
        self.proof = {'inputs': {'nativeSourceManifestSHA256': gate.NATIVE_MANIFEST,
                                 'nativeSHA256': gate.NATIVE_BINARY}}
        self.fixture = {'appSourceSHA': gate.FIXTURE_SOURCE, 'runID': 'original-run',
                        'token': 'original-disposable-token', 'spaceID': 'original-space'}

    def test_current_product_keeps_preparation_origin_and_native(self):
        origin = gate.compiled_origin(self.contract, self.proof)
        receipt = dict(self.fixture, currentCompiledBuild=origin)
        result = gate.verify_ui_origin([receipt, copy.deepcopy(receipt)], origin, self.fixture)
        self.assertEqual(result['receiptCount'], 2)
        self.assertEqual(receipt['appSourceSHA'], gate.FIXTURE_SOURCE)
        self.assertNotEqual(receipt['currentCompiledBuild']['compiledAppAndUISourceSHA'], gate.FIXTURE_SOURCE)
        self.assertEqual(origin['acceptanceScope'], 'current-product-with-retained-fixture-preparation')

    def test_changed_native_old_product_and_invalid_receipt_are_rejected(self):
        for key in ('nativeSourceManifestSHA256', 'nativeSHA256'):
            proof = copy.deepcopy(self.proof)
            proof['inputs'][key] = '3' * 64
            with self.subTest(key=key), self.assertRaises(ValueError):
                gate.compiled_origin(self.contract, proof)
        for value in (gate.FIXTURE_SOURCE, 'unknown-source'):
            contract = copy.deepcopy(self.contract)
            contract['source']['commit'] = value
            with self.subTest(source=value), self.assertRaises(ValueError):
                gate.compiled_origin(contract, self.proof)
        contract = copy.deepcopy(self.contract)
        contract['build']['receipt']['sha256'] = '2' * 63
        with self.assertRaises(ValueError):
            gate.compiled_origin(contract, self.proof)

    def test_missing_or_rewritten_compiled_and_fixture_origins_are_rejected(self):
        origin = gate.compiled_origin(self.contract, self.proof)
        valid = dict(self.fixture, currentCompiledBuild=origin)
        invalid = []
        missing = copy.deepcopy(valid)
        del missing['currentCompiledBuild']
        invalid.append(missing)
        for key in origin:
            value = copy.deepcopy(valid)
            value['currentCompiledBuild'][key] = 'other'
            invalid.append(value)
        for key in self.fixture:
            value = copy.deepcopy(valid)
            value[key] = 'other'
            invalid.append(value)
        for index, value in enumerate(invalid):
            with self.subTest(mutation=index), self.assertRaises(ValueError):
                gate.verify_ui_origin([value], origin, self.fixture)

    def test_original_descriptor_selection_requires_exact_blueprints(self):
        native = {'__xctestrun_metadata__': {'FormatVersion': 2}, 'TestConfigurations': [
            {'TestTargets': [{'BlueprintName': 'AnytypeTests', 'OnlyTestIdentifiers': ['Original/testA']}]}]}
        ui = {'__xctestrun_metadata__': {'FormatVersion': 1}, 'PinkhaStage1AcceptanceUITests':
              {'OnlyTestIdentifiers': ['Original/testUI']}}
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'original.xctestrun'
            for kind, value in (('app', native), ('ui', ui)):
                path.write_bytes(plistlib.dumps(value))
                self.assertEqual(len(gate.product_selection(path, kind)), 1)
            invalid = copy.deepcopy(native)
            invalid['TestConfigurations'][0]['TestTargets'].append(copy.deepcopy(invalid['TestConfigurations'][0]['TestTargets'][0]))
            path.write_bytes(plistlib.dumps(invalid))
            with self.assertRaises(ValueError):
                gate.product_selection(path, 'app')
            invalid = copy.deepcopy(ui)
            invalid['PinkhaStage1AcceptanceUITests']['OnlyTestIdentifiers'] *= 2
            path.write_bytes(plistlib.dumps(invalid))
            with self.assertRaises(ValueError):
                gate.product_selection(path, 'ui')


if __name__ == '__main__':
    unittest.main()
