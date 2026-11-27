"""Receipt/cache controls only; no Apple product build or test is executed."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location('warm', ROOT / 'wave3_warm_retry.py')
warm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(warm)
adapter = warm.load_adapter(ROOT / 'wave3_shared_build.py')


def example():
    value = json.loads((ROOT / 'wave3_build_admission.template.json').read_text())
    value.update(readyForBuild=True, appSourceSHA='1' * 40, buildRoot=warm.FAILED_ROOT + '-retry-fixture')
    value['sourceStaging']['sha256'] = '2' * 64
    value['cacheQualification']['sha256'] = '3' * 64
    value['pins']['sdkMaterializationReceiptSHA256'] = warm.SDK_MARKER_SHA
    value['warmRetry'] = {'schema': 'pinkha-terminal-failure-warm-retry-v1',
                          'priorFailedSourceCommit': warm.FAILED_SOURCE, 'priorBuildRoot': warm.FAILED_ROOT,
                          'failedPreservation': {'path': warm.FAILED_ROOT + '/failed-preservation1/receipt.json',
                                                 'sha256': warm.PRESERVATION_SHA},
                          'concurrentGrowthAllowanceBytes': 2 * 1024 ** 3}
    return value


class WarmRetryControls(unittest.TestCase):
    def test_complete_inverse_and_original_runtime_compiler_gates_remain(self):
        original_path = ROOT / 'build_wave2_app16_compiler_qualified.py'
        original = (original_path.read_text() if original_path.exists() else
                    subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show',
                                             adapter.BASE_COMMIT + ':Tools/PinkhaDualEngineRuntime/build_wave2_app16_compiler_qualified.py'], text=True))
        candidate, proof = warm.expand(original, example(), Path('/approved.json'), '8' * 64, adapter, '9' * 64)
        inverse = candidate
        for change in reversed(proof['changes']):
            inverse = inverse.replace(change['new'], change['old'])
        self.assertEqual(inverse, original)
        for name in ('run_phase', 'source_state'):
            self.assertEqual(adapter.function_source(candidate, name), adapter.function_source(original, name))
        for required in ('w3_native_proof()', 'w3_ui_after(ui_snapshot,ui_source,ui_project)',
                         'verify_dependencies("after-ui")', '"sourceUnchanged":True', '"products-all.json"',
                         'wr_validate_cache(cache,staging)', 'CONCURRENT_GROWTH=2147483648'):
            self.assertIn(required, candidate)
        self.assertNotIn('assert cache["protocol"]=="app16-observed-cache-requalification-v1"', candidate)

    def test_historical_rerun_wrong_preservation_changed_sdk_or_reduced_budget_rejected(self):
        for mutation in ('old-source', 'old-output', 'preservation', 'SDK', 'native', 'concurrent'):
            with self.subTest(mutation=mutation):
                value = example()
                if mutation == 'old-source': value['appSourceSHA'] = warm.FAILED_SOURCE
                if mutation == 'old-output': value['buildRoot'] = warm.FAILED_ROOT
                if mutation == 'preservation': value['warmRetry']['failedPreservation']['sha256'] = '0' * 64
                if mutation == 'SDK': value['pins']['sdkMaterializationReceiptSHA256'] = '0' * 64
                if mutation == 'native': value['pins']['nativeSourceManifestSHA256'] = '0' * 64
                if mutation == 'concurrent': value['warmRetry']['concurrentGrowthAllowanceBytes'] = 0
                with self.assertRaises(ValueError): warm.validate_retry(value)

    def test_actual_prebuild_absence_receipt_cannot_be_relabelled_as_warm(self):
        # These exact original cache fields caused the concrete continuation gap.
        cache = {'protocol': 'app16-observed-cache-requalification-v1', 'sourceCommit': '1' * 40,
                 'originalIntermediatesAndPackagePathsReused': False}
        with patch.object(warm, 'WAVE3_ADMISSION', example(), create=True), patch.object(warm, 'EXPECTED', '1' * 40, create=True):
            with self.assertRaisesRegex(ValueError, 'Fresh post-failure'):
                warm.wr_validate_cache(cache, {})

    def checkout_fixture(self, root):
        source, derived = root / 'source', root / 'derived'
        checkout = derived / 'SourcePackages/checkouts/original'
        checkout.mkdir(parents=True)
        git = ['/usr/bin/git', '-C', str(checkout)]
        subprocess.run(git + ['init', '-q'], check=True)
        (checkout / 'Package.swift').write_text('// exact original package\n')
        subprocess.run(git + ['add', 'Package.swift'], check=True)
        subprocess.run(git + ['-c', 'user.name=Control fixture', '-c', 'user.email=fixture@example.invalid',
                              'commit', '-qm', 'Original package'], check=True)
        head = subprocess.check_output(git + ['rev-parse', 'HEAD'], text=True).strip()
        lock = source / 'Anytype.xcodeproj/project.xcworkspace/xcshareddata/swiftpm/Package.resolved'
        lock.parent.mkdir(parents=True)
        state = {'revision': head}
        lock.write_text(json.dumps({'pins': [{'identity': 'original', 'state': state}]}))
        dependencies = [{'packageRef': {'identity': 'original'}, 'state': {'name': 'sourceControlCheckout', 'checkoutState': state}, 'subpath': 'original'}]
        for name in ('hanlinagentsdk', 'hanlinminiappsbridge', 'hanlinplatform', 'hanlinpresentationsdk'):
            path = source / 'Dependencies/Hanlin/Packages' / name
            path.mkdir(parents=True)
            dependencies.append({'packageRef': {'identity': name}, 'state': {'name': 'fileSystem', 'path': str(path)}})
        workspace = derived / 'SourcePackages/workspace-state.json'
        workspace.write_text(json.dumps({'object': {'dependencies': dependencies}}))
        return source, derived, checkout, workspace, dependencies

    def test_real_git_head_and_dirty_tracked_bytes_are_checked(self):
        with tempfile.TemporaryDirectory() as directory:
            source, derived, checkout, workspace, dependencies = self.checkout_fixture(Path(directory))
            result = warm.wr_packages(source, derived)
            self.assertEqual(set(result['checkouts']), {'original'})
            (checkout / 'Package.swift').write_text('// changed cached dependency\n')
            with self.assertRaisesRegex(ValueError, 'Actual pinned'):
                warm.wr_packages(source, derived)

    def test_untracked_swift_source_in_pinned_checkout_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source, derived, checkout, workspace, dependencies = self.checkout_fixture(Path(directory))
            admitted = warm.wr_packages(source, derived)
            additional = checkout / 'Sources/Unexpected.swift'
            additional.parent.mkdir()
            additional.write_text('public let unexpectedCompiledSource = true\n')
            # The pinned HEAD remains exact while SwiftPM could compile this
            # extra source. A tracked-files-only status check would miss it.
            head = subprocess.check_output(['/usr/bin/git', '-C', str(checkout), 'rev-parse', 'HEAD'], text=True).strip()
            self.assertEqual(head, admitted['checkouts']['original']['revision'])
            with self.assertRaisesRegex(ValueError, 'Actual pinned'):
                warm.wr_packages(source, derived)

    def test_missing_pin_duplicate_checkout_and_foreign_local_sdk_rejected(self):
        for mutation in ('missing', 'duplicate', 'foreign-local'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                source, derived, checkout, workspace, dependencies = self.checkout_fixture(Path(directory))
                if mutation == 'missing': dependencies.pop(0)
                elif mutation == 'duplicate': dependencies.append(copy.deepcopy(dependencies[0]))
                else: dependencies[-1]['state']['path'] = str(checkout)
                workspace.write_text(json.dumps({'object': {'dependencies': dependencies}}))
                with self.assertRaises(ValueError): warm.wr_packages(source, derived)


if __name__ == '__main__':
    unittest.main()
