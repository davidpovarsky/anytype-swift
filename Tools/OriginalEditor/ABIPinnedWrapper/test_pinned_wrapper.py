#!/usr/bin/env python3
"""Focused controls for the real module-promotion/refusal boundary."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import pinned_wrapper as p


class ModuleControls(unittest.TestCase):
    def setUp(self):
        self.heart = Path('/owned/heart')
        self.source = Path('/owned/tmp/gomobile-work-1/ios/src-arm64')
        self.original = [
            {'Path': p.HEART, 'Main': True, 'Dir': str(self.heart)},
            {'Path': 'example.org/direct', 'Version': 'v1.3.1'},
            {'Path': 'example.org/replaced', 'Version': 'v1.2.0',
             'Replace': {'Path': 'example.org/fork', 'Version': 'v1.1.7'}},
            {'Path': 'example.org/pruned', 'Version': 'v0.8.0'}]
        self.actual = [
            {'Path': 'gobind', 'Main': True, 'Dir': str(self.source)},
            {'Path': p.HEART, 'Version': p.LOCAL_VERSION,
             'Replace': {'Path': str(self.heart), 'Dir': str(self.heart)}},
            *copy.deepcopy(self.original[1:3])]
        self.mod = {'Module': {'Path': p.HEART}, 'Go': '1.26.5',
                    'Require': [{'Path': 'example.org/direct', 'Version': 'v1.3.1'},
                                {'Path': 'example.org/replaced', 'Version': 'v1.2.0', 'Indirect': True}],
                    'Replace': [{'Old': {'Path': 'example.org/replaced'},
                                 'New': {'Path': 'example.org/fork', 'Version': 'v1.1.7'}}],
                    'Exclude': None, 'Retract': None, 'Tool': None, 'Ignore': None}

    def rewritten(self):
        result = copy.deepcopy(self.mod)
        result['Module']['Path'] = 'gobind'
        result['Require'].append({'Path': p.HEART, 'Version': p.LOCAL_VERSION})
        result['Replace'].append({'Old': {'Path': p.HEART}, 'New': {'Path': str(self.heart)}})
        return result

    def test_original_selected_subset_and_wildcard_roots_pass(self):
        p.check_modules(self.actual, self.original, self.heart, self.source)
        p.check_retained_roots(self.rewritten(), self.mod, self.heart)

    def test_original_generator_boundary_is_checked_before_replacement(self):
        generated = {'Module': {'Path': 'gobind'}, 'Go': '1.26.5',
                     'Require': [copy.deepcopy(self.original[1]), copy.deepcopy(self.original[3])],
                     'Replace': [{'Old': {'Path': p.HEART}, 'New': {'Path': str(self.heart)}},
                                 {'Old': {'Path': 'example.org/replaced', 'Version': 'v1.2.0'},
                                  'New': {'Path': 'example.org/fork', 'Version': 'v1.1.7'}}]}
        p.check_generated_boundary(generated, self.original)
        generated['Require'].append({'Path': 'example.org/foreign', 'Version': 'v9.0.0'})
        with self.assertRaisesRegex(RuntimeError, 'promotion boundary'):
            p.check_generated_boundary(generated, self.original)

    def test_three_observed_version_drifts_are_refused(self):
        for name, old, new in (('github.com/gogo/googleapis', 'v1.3.1', 'v1.4.1'),
                              ('go.opentelemetry.io/otel/sdk/metric', 'v1.44.0', 'v1.46.0'),
                              ('golang.org/x/arch', 'v0.8.0', 'v0.10.0')):
            with self.subTest(name=name), self.assertRaisesRegex(RuntimeError, 'selection differs'):
                p.check_modules(self.actual + [{'Path': name, 'Version': new}],
                    self.original + [{'Path': name, 'Version': old}], self.heart, self.source)

    def test_promoting_pruned_modules_to_roots_is_refused(self):
        value = self.rewritten()
        value['Require'].append({'Path': 'example.org/pruned', 'Version': 'v0.8.0'})
        with self.assertRaisesRegex(RuntimeError, 'root requirements'):
            p.check_retained_roots(value, self.mod, self.heart)

    def test_version_scoped_replacement_cannot_replace_original_wildcard(self):
        value = self.rewritten()
        value['Replace'][0]['Old']['Version'] = 'v1.2.0'
        with self.assertRaisesRegex(RuntimeError, 'root requirements'):
            p.check_retained_roots(value, self.mod, self.heart)

    def test_wrong_local_heart_and_changed_replacement_are_refused(self):
        for change in ('heart', 'replacement'):
            actual = copy.deepcopy(self.actual)
            if change == 'heart':
                actual[1]['Replace']['Dir'] = '/foreign/heart'
            else:
                actual[3]['Replace']['Version'] = 'v1.1.8'
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                p.check_modules(actual, self.original, self.heart, self.source)

    def test_repeated_and_new_modules_are_refused(self):
        for extra in (self.actual[-1], {'Path': 'example.org/new', 'Version': 'v1.0.0'}):
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                p.check_modules(self.actual + [extra], self.original, self.heart, self.source)

    def test_actual_archive_command_has_only_explicit_readonly_delta(self):
        with tempfile.TemporaryDirectory() as temporary:
            retained = Path(temporary)
            source = retained / 'ios/src-arm64'
            args = ['build', '-tags', ','.join(p.TAGS.split()), '-x', '-ldflags', 'exact-ldflags',
                    '-work', '-buildmode=c-archive', '-o', str(retained / 'Lib-ios-arm64.a'), './gobind']
            actual, archive = p.build_argv(args, source, retained, {'ldflags': 'exact-ldflags'})
            self.assertEqual(actual, ['build', '-mod=readonly', *args[1:]])
            with self.assertRaises(RuntimeError):
                p.build_argv(args + ['-mod=mod'], source, retained, {'ldflags': 'exact-ldflags'})
            archive.write_bytes(b'rejected archive')
            with self.assertRaisesRegex(RuntimeError, 'repeated'):
                p.build_argv(args, source, retained, {'ldflags': 'exact-ldflags'})

    def test_parent_escape_and_foreign_target_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            top = Path(temporary).resolve()
            config = {'temporary': str(top / 'tmp')}
            for suffix in ('foreign/gomobile-work-1/ios/src-arm64', 'tmp/gomobile-work-1/android/src-arm64'):
                path = top / suffix
                path.mkdir(parents=True)
                with self.subTest(suffix=suffix), self.assertRaises(RuntimeError):
                    p.target_context(path, config, {})

    def test_only_read_queries_are_forwarded_to_original_tool(self):
        for args in (['version'], ['env', '-json', 'GOMOD', 'GOROOT'],
                     ['list', '-e', '-json', '-compiled=true', '-deps=true', './core']):
            p.query_argv(args)
        for args in (['env', '-w', 'GOPROXY=foreign'], ['clean', '-modcache'], ['build', './...'],
                     ['list', '-mod=mod', './core'], ['list', '-modfile=/foreign/go.mod', './core'],
                     ['list', '-toolexec=/foreign/compiler', './core']):
            with self.subTest(args=args), self.assertRaises(RuntimeError):
                p.query_argv(args)

    def test_historical_verification_does_not_extend_execution_deadline_or_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            executable = p.row(Path(sys.executable).resolve())
            value = {'schema': p.SCHEMA, 'deadline': 1, 'inputs': [], 'go': executable,
                     'python': executable, 'root': str(root), 'control_sha': 'a' * 40}
            path = root / 'CONFIG.json'
            path.write_text(json.dumps(value))
            before = path.read_bytes()
            with mock.patch.object(p.subprocess, 'check_output', return_value='a' * 40 + '\n'):
                with self.assertRaisesRegex(RuntimeError, 'expired'):
                    p.validate_config(path, p.sha(path), require_live=True)
                self.assertEqual(p.validate_config(path, p.sha(path), require_live=False), value)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
