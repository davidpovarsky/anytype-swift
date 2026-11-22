"""New source-preflight controls only; no Apple/product tests are executed."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

import continue_native_acceptance as admission
import native_continuation_sources as sources
import hanlin_fixture_ci as fixture

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / 'docs/validation/20261122-any-continuation-preflight'
ORIGINAL_ZIP_SHA = '57a39e9b4fb7e7550f7a32806cb32217f4bea06450bf9ecebaf1a2671cca995a'


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, stderr=subprocess.PIPE)


def original_checkout(root):
    data = (PROOF / 'original-source.zip').read_bytes()
    if hashlib.sha256(data).hexdigest() != ORIGINAL_ZIP_SHA:
        raise ValueError('exact original source archive required')
    records = json.loads((PROOF / 'ORIGINAL_SOURCE_MANIFEST.json').read_bytes())
    assert records['commit'] == 'edf1545f2ebcd1a71d307735a645c779cb9dc3bb'
    rows = {row['path']: row for row in records['files']}
    assert len(rows) == 12
    with zipfile.ZipFile(PROOF / 'original-source.zip') as archive:
        assert set(archive.namelist()) == set(rows)
        for name, row in rows.items():
            relative = PurePosixPath(name)
            assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in name
            value = archive.read(name)
            assert len(value) == row['bytes'] and hashlib.sha256(value).hexdigest() == row['sha256']
            assert hashlib.sha1(b'blob ' + str(len(value)).encode() + b'\0' + value).hexdigest() == row['gitBlob']
            path = root.joinpath(*relative.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(value)
    git(root, 'init', '--quiet')
    git(root, 'add', '--', *sorted(rows))
    git(root, '-c', 'user.name=Source Preflight Control', '-c', 'user.email=preflight@invalid',
        'commit', '--quiet', '-m', 'Exact isolated original source fixture')


class NativeContinuationPreflightTests(unittest.TestCase):
    def test_exact_original_imports_create_untracked_bytecode_and_workflow_prevents_it(self):
        workflow = (ROOT / '.github/workflows/pinkha-any-engine-port.yml').read_text()
        env_block = workflow.split('  ios-native-runtime:\n', 1)[1].split('    steps:\n', 1)[0]
        self.assertEqual(env_block.count('      PYTHONDONTWRITEBYTECODE: "1"\n'), 1)
        for protected in (False, True):
            with self.subTest(bytecode_prevented=protected), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                original_checkout(root)
                env = dict(os.environ)
                env.pop('PYTHONDONTWRITEBYTECODE', None)
                env.pop('PYTHONPYCACHEPREFIX', None)
                if protected:
                    env['PYTHONDONTWRITEBYTECODE'] = '1'
                result = subprocess.run([sys.executable, 'Tools/AnyEnginePort/continue_native_acceptance.py', '--help'],
                                        cwd=root, env=env, capture_output=True, timeout=45)
                self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
                self.assertFalse(git(root, 'diff', '--name-only', 'HEAD', '--'))
                unknown = git(root, 'ls-files', '--others', '--exclude-standard', '-z', '--', 'Tools/AnyEnginePort')
                paths = [value.decode() for value in unknown.split(b'\0') if value]
                if protected:
                    self.assertEqual(paths, [])
                    sources.verify_worktree(root)
                else:
                    self.assertGreaterEqual(len(paths), 6)
                    self.assertTrue(all(path.startswith('Tools/AnyEnginePort/__pycache__/') and path.endswith('.pyc') for path in paths))
                    with self.assertRaisesRegex(ValueError, 'consumer_source_worktree_not_clean') as error:
                        sources.verify_worktree(root)
                    diagnostic = json.loads(str(error.exception).split(' ', 1)[1])
                    self.assertEqual(diagnostic['untracked'], paths)

    def test_dirty_tracked_and_unknown_sources_are_still_refused_with_actual_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original_checkout(root)
            sources.verify_worktree(root)
            source_path = root / 'Tools/AnyEnginePort/continue_native_acceptance.py'
            source_path.write_bytes(source_path.read_bytes() + b'\n# unreviewed modification\n')
            extra = root / 'Modules/Unexpected/New.swift'
            extra.parent.mkdir(parents=True)
            extra.write_text('let unreviewed = true\n')
            with self.assertRaisesRegex(ValueError, 'consumer_source_worktree_not_clean') as error:
                sources.verify_worktree(root)
            diagnostic = json.loads(str(error.exception).split(' ', 1)[1])
            self.assertEqual(diagnostic, {'trackedCount': 1, 'untrackedCount': 1,
                'tracked': ['Tools/AnyEnginePort/continue_native_acceptance.py'],
                'untracked': ['Modules/Unexpected/New.swift']})

    def test_consumer_scope_allows_only_two_exact_work_branches(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'simulator.json').write_text('{}\n')
            (root / 'xcode-version.txt').write_text('fixture only; no Apple execution\n')
            env = {'GITHUB_REPOSITORY': admission.REPOSITORY, 'GITHUB_RUN_ATTEMPT': '1'}
            with mock.patch.object(fixture, 'github_context', return_value=('999999', 'a' * 40, root)), \
                 mock.patch.object(fixture, 'verify_simulator', return_value=('controlled-udid', {}, None)), \
                 mock.patch.dict(os.environ, env):
                for branch in (admission.BRANCH, admission.CONTINUATION_BRANCH):
                    with mock.patch.dict(os.environ, {'GITHUB_REF': 'refs/heads/' + branch}):
                        context, _ = admission.context(root)
                        self.assertEqual(context['consumerCommit'], 'a' * 40)
                for ref in ('', 'refs/heads/main', 'refs/heads/' + admission.CONTINUATION_BRANCH + '-other',
                            'refs/tags/' + admission.BRANCH, 'refs/pull/1/merge'):
                    with mock.patch.dict(os.environ, {'GITHUB_REF': ref}):
                        with self.assertRaisesRegex(ValueError, 'consumer_run_scope_mismatch'):
                            admission.context(root)


if __name__ == '__main__':
    unittest.main()
