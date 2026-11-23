#!/usr/bin/env python3
"""Execute only the six new source controls; no Apple/native runtime."""
import hashlib
import importlib
import json
from pathlib import Path
import sys
import time
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[6]
PACKET = Path(__file__).resolve().parent
OUT = PACKET / 'controls-run-1'
OUT.mkdir(exist_ok=False)
sys.path.insert(0, str(ROOT / 'Tools/OriginalEditor'))
module = importlib.import_module('test_signed_consumer_framework_roles')
names = unittest.defaultTestLoader.getTestCaseNames(module.OriginalFrameworkRolesTests)
expected = ['test_signed_consumer_framework_roles.OriginalFrameworkRolesTests.' + name for name in names]

class ObservedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.started_ids = []
        self.passed_ids = []
    def startTest(self, test):
        self.started_ids.append(test.id())
        super().startTest(test)
    def addSuccess(self, test):
        self.passed_ids.append(test.id())
        super().addSuccess(test)

started = time.time()
with (OUT / 'unittest.stderr.log').open('w') as stream:
    result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=ObservedResult).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(module.OriginalFrameworkRolesTests))
(OUT / 'unittest.stdout.log').write_bytes(b'')
source_paths = [
    ROOT / 'Tools/OriginalEditor/run_signed_consumer_continuation.py',
    ROOT / 'Tools/OriginalEditor/signed_consumer_framework_roles.py',
    ROOT / 'Tools/OriginalEditor/test_signed_consumer_framework_roles.py',
    ROOT / 'Tools/OriginalEditor/framework_products.py',
    PACKET / 'run_controls.py', PACKET / 'DIAGNOSIS.json',
    PACKET / 'original-framework-distribution.json', PACKET / 'original-consumer-retention.json',
    *sorted((PACKET / 'original-headers').iterdir()),
]
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
report = {
    'status': 'PASS' if result.wasSuccessful() and result.testsRun == len(expected) == 6
                      and sorted(result.started_ids) == sorted(result.passed_ids) == sorted(expected) else 'FAIL',
    'scope': 'AUTHENTIC_ORIGINAL_ROLE_RECEIPTS_AND_SYNTHETIC_FILESYSTEM_INVENTORY_SOURCE_CONTROLS_ONLY',
    'tests_run': result.testsRun, 'expected_ids': expected,
    'started_ids': result.started_ids, 'passed_ids': result.passed_ids,
    'failed': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped),
    'expected_failures': len(result.expectedFailures), 'unexpected_successes': len(result.unexpectedSuccesses),
    'native_tests_executed': 0, 'prior_controls_reexecuted': False,
    'authentic_original_header_receipts': 17, 'synthetic_filesystem_fixtures': True,
    'elapsed_seconds': time.time() - started,
    'source_sha256': {p.relative_to(ROOT).as_posix(): digest(p) for p in source_paths},
    'log_sha256': {p.relative_to(PACKET).as_posix(): digest(p) for p in sorted(OUT.iterdir()) if p.is_file()},
}
(PACKET / 'FRAMEWORK_ROLE_CONTROLS.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in [
    'status', 'tests_run', 'failed', 'errors', 'skipped', 'native_tests_executed', 'elapsed_seconds'
]}, indent=2))
sys.exit(0 if report['status'] == 'PASS' else 1)
