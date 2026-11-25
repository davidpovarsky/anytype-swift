#!/usr/bin/env python3
"""Read-only actual failed-device interval admission controls; no build credit."""
import argparse
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import resume_release_postbuild as resume


class ActualPostbuildAdmissionControls(unittest.TestCase):
    evidence = work = root = driver = None

    def test_exact_original_terminal_failure_is_admitted(self):
        resume.admit_terminal(json.loads((self.evidence / 'execution.json').read_text()))

    def test_every_changed_terminal_ownership_or_success_fact_is_refused(self):
        original = json.loads((self.evidence / 'execution.json').read_text())
        changes = {'status': 'PASS', 'phase': 'OTHER', 'error': 'another failure',
            'error_type': 'TimeoutExpired', 'source_sha': '0' * 40, 'control_sha': '1' * 40,
            'platform': 'iphonesimulator', 'configuration': 'Debug-Anytype',
            'original_framework_build': 'NOT_RUN', 'external_consumer_build': 'PASS',
            'strict_dependency_resolution': 'SKIPPED', 'owned_command_groups_drained': False,
            'owned_simulator_cleanup': {'status': 'FAIL'}, 'final_observation_error': 'changed',
            'cleanup_error': 'changed'}
        for key, value in changes.items():
            with self.subTest(field=key):
                changed = copy.deepcopy(original); changed[key] = value
                with self.assertRaises(RuntimeError):
                    resume.admit_terminal(changed)

    def test_all_actual_command_bytes_and_compiler_flags_are_admitted(self):
        value = resume.verify_commands(self.evidence, self.root, self.work)
        self.assertEqual(set(value), resume.REQUIRED_COMMANDS)

    def test_original_complete_postbuild_body_is_pinned(self):
        code, digest = resume.original_postbuild(self.driver)
        self.assertEqual(len(digest), 64)
        self.assertIn('verify_ownership', code.co_names)
        self.assertIn('verify_public_surface', code.co_names)
        self.assertIn('consumer_project', code.co_names)
        self.assertIn('verify_abi', code.co_names)

    def test_changed_postbuild_driver_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'run_release.py'
            path.write_bytes(self.driver.read_bytes() + b'\n')
            with self.assertRaises(RuntimeError):
                resume.original_postbuild(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ['evidence', 'work', 'root', 'driver']:
        parser.add_argument('--' + name, type=Path, required=True)
    args, remaining = parser.parse_known_args()
    for name in ['evidence', 'work', 'root', 'driver']:
        setattr(ActualPostbuildAdmissionControls, name, getattr(args, name))
    unittest.main(argv=[sys.argv[0], *remaining])
