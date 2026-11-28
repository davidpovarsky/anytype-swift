#!/usr/bin/env python3
"""Synthetic boundary controls only; never imports or launches the component runner."""
from pathlib import Path
import ast
import hashlib
import io
import json
import re
import shlex
import tempfile
import time
import unittest

BASE = Path(__file__).resolve().parent
SOURCE = BASE / 'inputs/run_component.py'
RAW = SOURCE.read_bytes()
TREE = ast.parse(RAW)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def literal(name):
    node = next(n for n in TREE.body if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
    return ast.literal_eval(node.value)


def extracted(name, **overrides):
    node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    namespace = {'Path': Path, 're': re, 'shlex': shlex, 'json': json, 'sha': sha,
                 'XCTEST_METHODS': literal('XCTEST_METHODS'),
                 'SWIFT_TESTING_METHODS': literal('SWIFT_TESTING_METHODS'),
                 'SOURCE_PINS': literal('SOURCE_PINS'),
                 'GENERATED_ENTRY_SHA256': literal('GENERATED_ENTRY_SHA256'),
                 'SWIFT': Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift'),
                 'ALLOCATION_CAP': 268435456, **overrides}
    exec(compile(module, str(SOURCE) + ':AST-only-' + name, 'exec'), namespace)
    return namespace[name]


def mixed_fixture(empty=False):
    xctest = literal('XCTEST_METHODS')
    swift = literal('SWIFT_TESTING_METHODS')
    lines = ["Test Suite 'Selected tests' started at 2026-11-27 00:00:00.000",
             "Test Suite 'NativeBookmarkPresentationTests' started at 2026-11-27 00:00:00.000"]
    for name in xctest:
        lines += [f"Test Case 'NativeBookmarkPresentationTests.{name}' started at 2026-11-27 00:00:00.000",
                  f"Test Case 'NativeBookmarkPresentationTests.{name}' passed (0.001 seconds)"]
    lines += ["Test Suite 'NativeBookmarkPresentationTests' passed at 2026-11-27 00:00:00.004",
              ' Executed 4 tests, with 0 failures (0 unexpected) in 0.004 (0.004) seconds',
              "Test Suite 'Selected tests' passed at 2026-11-27 00:00:00.004",
              ' Executed 4 tests, with 0 failures (0 unexpected) in 0.004 (0.004) seconds']
    if empty:
        lines += ["Test Suite 'Selected tests' started at 2026-11-27 00:00:00.005",
                  "Test Suite 'Selected tests' passed at 2026-11-27 00:00:00.005",
                  ' Executed 0 tests, with 0 failures (0 unexpected) in 0.000 (0.000) seconds',
                  '◇ Test run started.', '✔ Test run with 0 tests passed after 0.001 seconds.']
    lines += ['◇ Test run started.', '◇ Suite "Native wiki hierarchy preserves the original tree domain" (aka \'AnyHierarchyTests\') started.']
    for name in swift:
        lines += [f'◇ Test {name}() started.', f'✔ Test {name}() passed after 0.001 seconds.']
    lines += ['✔ Suite "Native wiki hierarchy preserves the original tree domain" (aka \'AnyHierarchyTests\') passed after 0.002 seconds.',
              '✔ Test run with 2 tests in 1 suite passed after 0.003 seconds.']
    return '\n'.join(lines)


class CompilerFixture:
    def __init__(self, root):
        self.root = root
        self.component = root / 'component'
        self.build = root / 'build'
        self.project = self.build / 'out/Intermediates.noindex/BookmarkCreationProof.build/Debug-linux-aarch64'
        self.products = self.build / 'out/Products/Debug-linux-aarch64'
        self.swift = Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift')
        self.prod = ('TorahInspectorCore', 'PinkhaKit', 'PinkhaAnyEngine', 'PinkhaAnyIntegration', 'PinkhaAnyHost')
        self.tests = ('PinkhaAnyHostTests', 'PinkhaAnyIntegrationTests')
        self.runners = {name + '_test_runner': name for name in self.tests}
        self.groups = {}
        self.log = ['Swift version 6.4.3 (swift-6.4.3-RELEASE)', 'Target: aarch64-unknown-linux-gnu']
        self.product_paths = {name: self.products / (name + '.o') for name in self.prod}
        self.product_paths.update({name: self.products / (name + '.so') for name in self.tests})
        self.product_paths.update({runner: self.products / (name + '-test-runner') for runner, name in self.runners.items()})
        for relative in literal('SOURCE_PINS'):
            parts = Path(relative).parts
            if len(parts) == 3 and parts[0] in ('Sources', 'Tests') and relative.endswith('.swift'):
                path = self.component / relative
                self.write(path, (BASE / 'inputs/component' / relative).read_bytes())
                self.groups.setdefault(parts[1], set()).add(path)
        for name in self.tests:
            anchor = self.project / (name + '-p.build/DerivedSources/test_anchor.swift')
            entry = self.project / (name + '-test-runner.build/DerivedSources/test_entry_point.swift')
            self.write(anchor, ('public func __test_anchor_' + name + '() {}').encode())
            self.write(entry, (BASE / ('expected-generated/' + name + '-test_entry_point.swift')).read_bytes())
            self.groups[name].add(anchor)
            self.groups[name + '_test_runner'] = {entry}
            self.log.append(shlex.join(['write-file', str(anchor)]))
            self.log.append(shlex.join(['builtin-generateTestEntryPoint', '--output', str(entry), '--discover-tests',
                '--test-anchor-module', name, '--linker-file-list-format', 'unixShellQuotedNewlineSeparated',
                '--index-store-library-path', str(self.swift.parent.parent / 'lib/libIndexStore.so'),
                '--index-store', str(self.build / 'out'), '--index-unit-base-path', str(self.build / 'out/Intermediates.noindex'),
                '--linker-filelist', str(self.project / (name + '-p.build/Objects-normal/aarch64/' + name + '.LinkFileList'))]))
        crypto = [str(root / 'retained-crypto-objects' / (name + '.o')) for name in
                  ('Crypto', 'CryptoBoringWrapper', 'CCryptoBoringSSL', 'CCryptoBoringSSLShims')]
        for name in crypto:
            self.write(Path(name), b'SYNTHETIC CRYPTO OBJECT; NOT A REAL DEPENDENCY')
        for name, expected in sorted(self.groups.items()):
            if name in self.runners:
                stem = self.runners[name] + '-test-runner'; target = stem + '.build'
            else:
                stem = name; target = name + ('-p.build' if name in self.tests else '-t.build')
            objroot = self.project / target / 'Objects-normal/aarch64'
            source_list = objroot / (stem + '.SwiftFileList')
            self.write(source_list, self.list_text(expected))
            objects = {source: objroot / (source.stem + '.o') for source in expected}
            output_map = {str(source): {'object': str(obj)} for source, obj in objects.items()}
            output_map[''] = {}
            map_path = objroot / (stem + '-OutputFileMap.json')
            self.write(map_path, json.dumps(output_map).encode())
            module = objroot / 'Modules' / (name + '.swiftmodule')
            module_object = objroot / 'Modules' / (name + '.o')
            self.write(module, b'SYNTHETIC MODULE');self.write(module_object, b'SYNTHETIC MODULE OBJECT')
            for obj in objects.values():
                self.write(obj, b'SYNTHETIC SOURCE OBJECT')
            self.log.append(shlex.join(['builtin-SwiftDriver', '--', str(self.swift.with_name('swiftc')),
                '-module-name', name, '@' + str(source_list), '-output-file-map', str(map_path),
                '-target', 'aarch64-unknown-linux-gnu', '-swift-version', '5' if name in self.runners else '6',
                '-working-directory', str(root), '-j2', '-c', '-enable-testing', '-emit-module-path', str(module)]))
            linked = set(objects.values()) | {module_object}
            if name in self.tests:
                linked |= {self.product_paths[n] for n in (self.prod if name == 'PinkhaAnyHostTests' else self.prod[:-1])}
            link_list = objroot / (stem + '.LinkFileList');self.write(link_list, self.list_text(linked))
            if name in self.prod:
                argv = [str(self.swift.with_name('clang')), '-target', 'aarch64-unknown-linux-gnu', '-r', '-nostdlib', '@' + str(link_list)]
            else:
                autolink = objroot / (name + '-swiftbuild.autolink');self.write(autolink, b'-lFoundation\n')
                argv = [str(self.swift.with_name('swiftc')), '-target', 'aarch64-unknown-linux-gnu',
                        '-emit-executable' if name in self.runners else '-emit-library', '@' + str(link_list), '@' + str(autolink)]
                if name in self.tests:
                    argv += ['-Xlinker', '-soname', '-Xlinker', name + '.so']
                argv += crypto + ['-lstdc++']
                if name in self.runners:
                    argv.append(str(self.product_paths[self.runners[name]]))
            argv += ['-o', str(self.product_paths[name])]
            self.write(self.product_paths[name], b'SYNTHETIC PRODUCT; NOT COMPILED')
            self.log.append(shlex.join(argv))
        self.function = extracted('compiler_inputs', ROOT=root, COMPONENT=self.component)

    @staticmethod
    def write(path, raw):
        path.parent.mkdir(parents=True, exist_ok=True);path.write_bytes(raw)

    @staticmethod
    def list_text(paths):
        return ('\n'.join(shlex.quote(str(path)) for path in sorted(paths)) + '\n').encode()

    def text(self):
        return '\n'.join(self.log)


class BoundaryControls(unittest.TestCase):
    def test_both_positive_frameworks_and_bounded_empty_outputs(self):
        fn = extracted('mixed_test_result')
        for empty in (False, True):
            result = fn(mixed_fixture(empty))
            self.assertEqual((result['actualXCTestCaseCount'], result['actualSwiftTestingCaseCount']), (4, 2))

    def test_missing_duplicate_old_or_unknown_events_cannot_pass(self):
        fn = extracted('mixed_test_result');valid = mixed_fixture()
        name = literal('SWIFT_TESTING_METHODS')[0]
        mutations = {
            'missing-framework': valid[:valid.index('◇ Test run started.')],
            'old-method': valid + "\nTest Case 'NativeBookmarkPresentationTests.testBookmarkPreservesItsNativeTypeURLRoleAndUnrelatedContent' started at now",
            'duplicate-pass': valid + '\n✔ Test ' + name + '() passed after 0.001 seconds.',
            'wrong-count': valid.replace('Test run with 2 tests in 1 suite', 'Test run with 0 tests in 1 suite'),
            'unknown-case': valid + '\n◇ Test case passing 1 argument x → false (Swift.Bool) to ' + name + '() started.',
        }
        for reason, text in mutations.items():
            with self.subTest(reason=reason), self.assertRaises(AssertionError):fn(text)

    def test_compiler_requires_both_target_products_and_root_cwd(self):
        with tempfile.TemporaryDirectory(prefix='bookmark6-synthetic-', dir=BASE) as tmp:
            fixture = CompilerFixture(Path(tmp))
            result = fixture.function(fixture.text())
            self.assertEqual(len(result), 9)
            self.assertEqual(sum(len(row['objects']) for row in result), 88)
            self.assertEqual(sum(len(row['generatedInputs']) for row in result), 4)
            with self.assertRaises(AssertionError):
                fixture.function(fixture.text().replace('-working-directory ' + str(fixture.root), '-working-directory ' + str(fixture.component), 1))
            with self.assertRaises(AssertionError):
                fixture.function('\n'.join(line for line in fixture.log if not (line.startswith('builtin-SwiftDriver') and '-module-name PinkhaAnyHostTests_test_runner ' in line)))

    def test_link_and_generated_source_drift_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='bookmark6-synthetic-', dir=BASE) as tmp:
            fixture = CompilerFixture(Path(tmp));valid = fixture.text()
            # Appending a duplicate dependency at the actual link command must fail.
            line = next(line for line in fixture.log if '-emit-executable ' in line)
            crypto = str(fixture.root / 'retained-crypto-objects/Crypto.o')
            with self.assertRaises(AssertionError):fixture.function(valid.replace(line, line + ' ' + crypto))
            extra = fixture.build / 'unlisted.swift';extra.write_bytes(b'// not admitted\n')
            with self.assertRaises(AssertionError):fixture.function(valid)
            extra.unlink()
            source = fixture.component / 'Tests/PinkhaAnyHostTests/NativeBookmarkPresentationTests.swift'
            source.write_bytes(source.read_bytes() + b'\n// changed\n')
            with self.assertRaises(AssertionError):fixture.function(valid)


if __name__ == '__main__':
    out = BASE / 'portable-controls1';out.mkdir(exist_ok=False)
    capture = io.StringIO();started = time.monotonic()
    result = unittest.TextTestRunner(stream=capture, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BoundaryControls))
    raw = capture.getvalue().encode();(out / 'stdout.original.log').write_bytes(raw)
    receipt = {'status': 'PASS_PORTABLE_SYNTHETIC_CONTROLS_ONLY' if result.wasSuccessful() else 'FAIL_PORTABLE_CONTROL',
        'controllerSHA256': sha(RAW), 'controlSourceSHA256': sha(Path(__file__).read_bytes()),
        'methodsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'seconds': round(time.monotonic() - started, 6), 'stdoutSHA256': sha(raw), 'stdoutBytes': len(raw),
        'runnerModuleImported': False, 'runnerMainInvoked': False, 'compilerInvocations': 0,
        'runtimeCommands': 0, 'HTTPOrNativeCalls': 0, 'syntheticCompilerProductsAreNotRuntimeEvidence': True}
    (out / 'result.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)
