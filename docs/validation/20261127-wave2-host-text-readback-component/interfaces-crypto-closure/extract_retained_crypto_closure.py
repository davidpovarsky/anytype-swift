"""Local extraction of fixed retained input records; no host, compiler or copy calls."""
from pathlib import Path
import hashlib
import json
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
def sha(raw): return hashlib.sha256(raw).hexdigest()
def read(relative, expected):
    path = ROOT / relative
    raw = path.read_bytes()
    assert sha(raw) == expected, relative
    return json.loads(raw), {'localPath': str(path), 'bytes': len(raw), 'sha256': expected}
def write(name, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    path = OUT / name
    if path.exists(): assert path.read_bytes() == raw, name
    else: path.write_bytes(raw)
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}

manifest, manifest_pin = read('execution-preparation/compiled-source-inputs.original.json', 'de642b7c2cc54367d1b767807443a38e4803bc8cba628beefa3cee819688f9bc')
context, context_pin = read('uploader-source-context.primary.json', 'edf32026e89c786ed21370ba73006379b528c43184d4f9be7e89ddd7df7e9d9f')
receipt, receipt_pin = read('uploader-components-attempt2.original.json', '4b24eb81b7e7fa6b108568ea619bf125148e8952b38879a71cc8091b55d101c5')
package = context['package']
raw_package = package['content'].encode()
assert len(raw_package) == 6317 and sha(raw_package) == package['sha256'] == 'c6fd6d65b5c80ad30ed2f22bd322114e1293afa516fb0d58785600145d76cf53'
assert manifest['isolatedCopies'][package['path']] == {'bytes': len(raw_package), 'sha256': sha(raw_package)}
assert receipt['compiledSourceInputs']['sha256'] == manifest_pin['sha256']
assert receipt['status'] == 'FAIL' and receipt['compiledSourceInputsUnchanged'] is True
assert receipt['admittedInputsUnchanged'] is True and manifest['noExistingProjectModuleImportDirectories'] is True
arrays = [json.loads(x) for x in re.findall(r'\.unsafeFlags\((\[[^\]]*\])\)', package['content'])]
assert len(arrays) == 7 and arrays[:6] == [arrays[0]] * 6
swift_flags, link_flags = arrays[0], arrays[-1]
physical_root = '/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127/'
alias_root = '/tmp/pinkha-w1-migration-swift-20261127/'
product_root = physical_root + 'out/Products/Debug-linux-aarch64/'
prior_root = '/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/components-attempt2/'
imports_root = prior_root + 'retained-crypto-imports/'
headers_root = prior_root + 'retained-crypto-headers/'
original = manifest['originalInputs']
copies = manifest['isolatedCopies']
imports = {p: x for p, x in copies.items() if p.startswith(imports_root)}
headers = {p: x for p, x in copies.items() if p.startswith(headers_root)}
assert len(imports) == 4 and len(headers) == 94
assert swift_flags == ['-I', imports_root[:-1], '-Xcc', '-fmodule-map-file=' + headers_root + 'CCryptoBoringSSL/include/module.modulemap', '-Xcc', '-I' + headers_root + 'CCryptoBoringSSL/include', '-Xcc', '-fmodule-map-file=' + headers_root + 'CCryptoBoringSSLShims/include/module.modulemap', '-Xcc', '-I' + headers_root + 'CCryptoBoringSSLShims/include']
objects = ['Crypto.o', 'CryptoBoringWrapper.o', 'CCryptoBoringSSL.o', 'CCryptoBoringSSLShims.o']
assert link_flags == [alias_root + 'out/Products/Debug-linux-aarch64/' + n for n in objects] + ['-lstdc++']
files = []
for category, values, isolated_root, original_root in [
    ('swift-import', imports, imports_root, product_root),
    ('c-header-or-module-map', headers, headers_root, physical_root + 'checkouts/swift-crypto/Sources/')
]:
    for copied_path, record in sorted(values.items()):
        relative = copied_path.removeprefix(isolated_root)
        physical = original_root + relative
        alias = alias_root + physical.removeprefix(physical_root)
        assert original[physical] == record and original[alias] == record
        files.append({'kind': category, 'relativePath': relative, 'originalManifestPath': physical, 'recordedHistoricalAliasPath': alias, 'isolatedManifestPath': copied_path, 'freshCopySourcePath': copied_path, **record, 'binding': 'Both physical original and historical alias manifest entries exactly equal the retained isolated-copy record; no current symlink resolution is inferred.'})
for index, name in enumerate(objects):
    physical = product_root + name
    alias = link_flags[index]
    record = original[physical]
    assert alias not in original
    files.append({'kind': 'aggregated-link-object', 'relativePath': name, 'originalManifestPath': physical, 'actualOriginalPackageLinkerPath': alias, 'isolatedManifestPath': None, 'freshCopySourcePath': physical, **record, 'binding': 'Exact aggregated Products object from originalInputs. The linker alias is retained from Package.swift but was not a separate object key in this manifest; resolve/verify before any alias use.'})
assert len(files) == 102 and len({x['freshCopySourcePath'] for x in files}) == 102
coverage = []
for module, count in [('CCryptoBoringSSL', 92), ('CCryptoBoringSSLShims', 2)]:
    prefix = module + '/include/'
    retained = {p.removeprefix(headers_root): v for p, v in headers.items() if p.startswith(headers_root + prefix)}
    physical_prefix = physical_root + 'checkouts/swift-crypto/Sources/'
    recorded = {p.removeprefix(physical_prefix): v for p, v in original.items() if p.startswith(physical_prefix + prefix)}
    assert retained == recorded and len(retained) == count
    assert prefix + 'module.modulemap' in retained
    coverage.append({'module': module, 'files': count, 'bytes': sum(x['bytes'] for x in retained.values()), 'allOriginalManifestIncludeNamespaceEntriesRetainedExactly': True})
summary = {category: {'files': sum(x['kind'] == category for x in files), 'bytes': sum(x['bytes'] for x in files if x['kind'] == category)} for category in ['swift-import', 'c-header-or-module-map', 'aggregated-link-object']}
total = sum(x['bytes'] for x in files)
assert total == 19775715
swift_commands = [x for x in receipt['commands'] if x['argv'][0].endswith('/usr/bin/swift')]
assert len(swift_commands) == 1 and swift_commands[0]['argv'][0] == '/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift'
closure = {
    'schema': 'pinkha-retained-crypto-input-closure-v1',
    'status': 'LOCAL_SOURCE_RECORD_EXTRACTION_COMPLETE_FRESH_COPY_AND_RUNTIME_NOT_RUN',
    'authoritativeInputs': [manifest_pin, context_pin, receipt_pin],
    'originalPackage': {k: package[k] for k in ['path', 'bytes', 'sha256']},
    'originalSwiftFlagArraysCount': 6, 'originalSwiftFlags': swift_flags,
    'originalLinkerFlags': link_flags,
    'aggregateProductObjectAuthority': product_root,
    'files': files, 'summary': summary, 'includeNamespaceCoverage': coverage,
    'resource': {'totalFiles': len(files), 'logicalCopyInputBytes': total, 'sumEachFileRoundedTo4096Bytes': sum((x['bytes'] + 4095) // 4096 * 4096 for x in files), 'roundingIsNotAnObservedAllocation': True, 'sourceBytesOnlyNotFullBuildBudget': True, 'freshDestinationFilesystemMetadataAndActualCapacityStillRequired': True},
    'originalResultBoundary': {'receiptSHA256': receipt_pin['sha256'], 'status': receipt['status'], 'originalSwiftCommandExitCode': swift_commands[0]['exitCode'], 'compiledSourceInputsUnchanged': True, 'admittedInputsUnchanged': True, 'W1ReportedPassedMethods': 23, 'reportedMethodCountIndependentlyRecountedHere': False, 'reportedMethodCountIsNotOverallPASSOrReuseAuthority': True, 'actualNewHostMethodsRun': 0},
    'toolchainBoundary': {'originalCommandExecutable': swift_commands[0]['argv'][0], 'originalOuterJobs': 2, 'originalImportTarget': 'aarch64-unknown-linux-gnu', 'actualOriginalVersionCommandOrBinaryHashReadHere': False, 'freshToolchainAndTargetBindingRequired': True, 'compiledSwiftModulesAreNotClaimedPortableAcrossCompilersOrPlatforms': True},
    'preExecutionChecks': [
        'Under the coordinated owner slot, no-follow physical source/open/stat/hash checks must match every exact size and SHA256. The /mnt/development Products object records are authoritative; never substitute similarly named Intermediates/Modules objects.',
        'The recorded /tmp linker paths are historical argument strings, not current alias-resolution receipts. If any alias is used, resolve it and prove exact physical object identity. A fresh owned package may instead link only the independently copied, pinned Products objects; record that path-only argument transformation.',
        'Copy into a fresh W2-owned DEV namespace; verify complete file set, path confinement, modes/ownership, original-to-copy byte equality and source stability before and after. No shared cache mutation or full historical import directory reuse.',
        'Bind the actual Swift6.4.3 binary/version/target and compatible C/system linker environment to the compiled Swift modules and objects. Retained path spelling alone is not a toolchain identity receipt.',
        'Preserve the complete94-file retained include/module-map set and both import module directories. Retain -I and explicit -fmodule-map-file flags with exact fresh-root substitutions, original object order and -lstdc++.',
        'Retain the new actual compiler/linker inputs, exact original-source project compilation, selected Host XCTest enumeration/results, lifecycle and resource receipts. This input extraction does not open an execution gate or prove a full build.'
    ],
    'excluded': {'intermediatesModulesObjects': True, 'otherProjectCompiledModuleDirectories': True, 'unselectedOldTestsOrNativeRuns': True},
    'actions': {'remoteCalls': 0, 'copies': 0, 'cacheMutations': 0, 'compilerOrTests': 0, 'historicalProcessProbes': 0},
    'fullBuildEquivalenceClaim': False,
}
proof = write('retained-crypto-closure.json', closure)
print(json.dumps({'manifest': proof, 'summary': summary, 'resource': closure['resource']}))
