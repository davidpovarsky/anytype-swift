"""Package only an actual qualified canonical read/cold receipt.

This script cannot manufacture a pass or publish any private account contents.
It is prepared locally while the native execution slot is storage-gated.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127')
EVIDENCE = Path('/var/lib/pinkha-w1-functional-migration-20261127')
BASE = '5235bf902f8820fdc41fe802265ff5444407b363'
BUILD = EVIDENCE / 'canonical-definition-components-attempt3'
DEST = ROOT / 'docs/validation/20261127-wave1-functional-migration/canonical-definition-supplement'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native-receipt', type=Path, required=True)
parser.add_argument('--native-receipt-sha', required=True)
args = parser.parse_args()
assert args.native_receipt.name == 'result.json'
assert args.native_receipt.parent.parent == EVIDENCE
assert re.fullmatch(r'[0-9a-f]{64}', args.native_receipt_sha)
NATIVE = args.native_receipt.parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_bytes())

assert subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip() == BASE
assert sha(BUILD / 'result.json') == 'd9bf1c3911219e2227c17db48726a8508030a20f7557f19934504f599b76c69b'
assert sha(args.native_receipt) == args.native_receipt_sha
b, n = read(BUILD / 'result.json'), read(args.native_receipt)
assert b['status'] == n['status'] == 'PASS'
assert b['compiled'] and b['sourceUnchanged'] and b['exitCode'] == 0 and b['ownedGroupAbsent']
assert len(b['startLines']) == len(b['passLines']) == 1 and not b['failLines'] and not b['errors']
assert b['qualification']['newlyExecutedMethods'] == 1
assert b['qualification']['retainedUnchangedMethods'] == 2
assert b['qualification']['totalQualifiedMethods'] == 3
assert b['qualification']['priorOverallFailurePreserved']
assert n['componentQualification'] == b['qualification']
assert not n['errors'] and n['allOwnedGroupsPositivelyAbsent']
assert n['sourceDefinitionsUnchanged'] and n['swiftSourcesUnchanged']
assert n['originalAccountAndAcceptedReceiptsUnchanged']
assert not n['sourceAdmissionPromoted'] and not n['wholeSpaceMigration']
assert not n['historicalPreservationReexecuted'] and not n['appleUIPresentationAccepted']
assert not n['originalHistoryValuesRestamped'] and not n['literalNativeIdentityEquivalenceClaim']
assert n['actualPreparedOperations'] == n['actualDomainWrites'] == 0
assert n['newCanonicalDefinitions'] == 8 and n['allDirectoryEntries'] == 21
assert n['unresolvedSourceDefinitions'] == 129
assert n['uniqueTestMethods'] == 1 and n['testInvocations'] == 2
assert len(n['processes']) == len(n['phases']) == len(n['testLaunches']) == 2
assert len({r['pid'] for r in n['processes']}) == 2
assert all(r['exitCode'] == 0 and r['groupPositivelyAbsent'] and r['outboundDeniedByOS'] for r in n['processes'])
assert all(r['result'] == 'PASS' and r['exitCode'] == 0 and r['testGroupPositivelyAbsent'] for r in n['phases'])
assert all(r['compiledProducts'] == b['compiledProducts'] for r in n['phases'])
assert n['swiftBuildReceiptSHA256'] == sha(BUILD / 'result.json')
assert n['measuredAllocationReceiptSHA256'] == '023e19116534d131b38553c979920602eb179be1d7d57b57e5b5e576816bb261'
assert n['resourcePolicy']['initialReserveMiB'] == 128
assert n['resourcePolicy']['liveRootEmergencyFloorMiB'] == 2048
assert n['minimumFreeBytes'] > 2 * 1024**3
assert n['minimumDevelopmentCacheFreeBytes'] >= 512 * 1024**2
assert n['cacheCustodyReceiptSHA256'] == 'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8'
assert sha(NATIVE / 'component/read-canonical.json') == sha(NATIVE / 'component/reopen-canonical.json') == n['comparisonSHA256']
assert n['retainedInput']['activeOriginalAccountProcesses'] == 0
assert n['retainedInput']['copyBytesAndModesEqual'] and n['retainedInput']['entries'] == 26
assert not n['retainedInput']['accountInitialized'] and not n['retainedInput']['spaceCreated']

code = {
    'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeImportedDefinitionDirectory.swift': 'bc0a444fa673bb1d5fb0494e73132462e080ed52b8ab3e95dd1cb7721509440c',
    'Modules/PinkhaAnyHost/Sources/PinkhaAnyHost/AnyNativeImportedDefinitionStore.swift': 'e209c44b174e3ec6a0a1c967135e5d8313a49600ac58161e08dd98969fd9c9c2',
    'Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/NativeCanonicalDefinitionSupplementTests.swift': 'e8a40030d0cca49e7978869e487ba1422bc135e65f88469ba61ee852a73b7319',
    'Modules/PinkhaAnyHost/Tests/PinkhaAnyHostTests/AnyDestinationNativeCanonicalSupplementTests.swift': 'fbd02a09f9e0be7ecc15932839f183fb55578d2b67d1ff416bd8d4c7f1eef418',
}
sources = read(BUILD / 'source-after.json')
assert sources == read(BUILD / 'source-before.json')
assert sources == read(NATIVE / 'swift-sources-before.json') == read(NATIVE / 'swift-sources-after.json')
for relative, digest in code.items():
    assert sha(ROOT / relative) == sources[relative] == digest
controllers = ROOT / 'Tools/AnyEngineValidation/native_canonical_definition'
assert sha(controllers / 'run_canonical_definition_components.py') == b['controllerSHA256']
assert sha(controllers / 'run_native_canonical_definition_linux.py') == n['controllerSources']['canonicalDefinitions']
contract = ROOT / 'docs/architecture/native-canonical-definition-supplement-contract-20261127.md'
assert sha(contract) == '34a9f52d9e2936c97b5b422373b7c6a1c18bebf09d4a3a2889a4084b7adf19d9'

assert not DEST.exists()
copies = []
for name in ['result.json', 'test.log', 'source-before.json', 'source-after.json', 'controller.py']:
    copies.append((BUILD / name, 'components/' + name))
for name in ['result.json', 'read-test.log', 'reopen-test.log', 'swift-sources-before.json', 'swift-sources-after.json', 'controller.py', 'allocation-measurement.json', 'cache-custody-result.json']:
    copies.append((NATIVE / name, 'native/' + name))
for name in ['accepted-canonical-inputs.json', 'read-result.json', 'reopen-result.json']:
    copies.append((NATIVE / 'component' / name, 'native/' + name))
for name in ['result.json', 'test.log', 'source-before.json', 'source-after.json', 'NativeCanonicalDefinitionSupplementTests.swift', 'run_canonical_definition_components.py']:
    copies.append((EVIDENCE / 'canonical-definition-components-attempt1' / name, 'failed-attempts/components-attempt1/' + name))
for name in ['result.json', 'dispatch-termination.json', 'test.log', 'source-before.json', 'source-after.json', 'controller.py']:
    copies.append((EVIDENCE / 'canonical-definition-components-attempt2' / name, 'failed-attempts/components-attempt2/' + name))
failure = EVIDENCE / 'canonical-definition-native-attempt1/result.json'
failed = read(failure)
assert failed['status'] == 'FAIL' and failed['processes'] == failed['testLaunches'] == []
assert failed['allOwnedGroupsPositivelyAbsent']
copies.append((failure, 'failed-attempts/native-attempt1/result.json'))
failed2 = EVIDENCE / 'canonical-definition-native-attempt2'
assert sha(failed2 / 'result.json') == 'e694ca01ea35c93c291de212b5de270e1cafb30099e6873fa9794ef7152dce40'
failure2 = read(failed2 / 'result.json')
assert failure2['status'] == 'FAIL' and failure2['testLaunches'] == []
assert failure2['allOwnedGroupsPositivelyAbsent']
assert [r['exitCode'] for r in failure2['processes']] == [-15]
for name in ['result.json', 'controller.py', 'copy-walk-variable-correction.diff', 'swift-sources-before.json', 'swift-sources-after.json']:
    copies.append((failed2 / name, 'failed-attempts/native-attempt2/' + name))
for name in ['result.json', 'previous-unexecuted-controller.py', 'controller.diff']:
    copies.append((EVIDENCE / 'canonical-native-allocation-measurement1' / name, 'allocation-measurement/' + name))
for name in ['prior-controller.py', 'controller.diff']:
    copies.append((EVIDENCE / 'canonical-native-cache-placement1' / name, 'cache-placement/' + name))
for directory, names in [
    ('swift-cache-relocation1', ['result.json', 'new-dispatch-name-collision.json']),
    ('swift-cache-relocation2', ['result.json', 'traceback.txt']),
    ('swift-cache-relocation-continuation1', ['result.json', 'staged-symlink-target-and-restored-atime.json']),
]:
    for name in names: copies.append((EVIDENCE / directory / name, 'cache-custody/' + directory + '/' + name))
copies.append((Path('/tmp/pinkha-w1-relocate-swift-cache-20261127.py'), 'cache-custody/name-collision-controller.py'))
copies.append((Path('/tmp/pinkha-w1-relocate-swift-cache-20261127-attempt2.py'), 'cache-custody/initial-copy-controller.py'))
copies.append((Path('/tmp/pinkha-w1-continue-swift-cache-relocation-20261127.py'), 'cache-custody/continuation-controller.py'))
assert sha(EVIDENCE / 'swift-cache-relocation2/result.json') == '4ef5b081ca0792d328ca4e570ebefbf57d9f964fd71e886c4fab3007582ff103'
assert sha(EVIDENCE / 'swift-cache-relocation-continuation1/result.json') == n['cacheCustodyReceiptSHA256']
assert all(source.is_file() and not source.is_symlink() for source, _ in copies)
assert len(set(relative for _, relative in copies)) == len(copies)
DEST.mkdir(parents=True)

copied = []
for source, relative in copies:
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    digest = sha(source)
    shutil.copyfile(source, target)
    target.chmod(0o644)
    assert sha(source) == sha(target) == digest
    copied.append({'path': relative, 'bytes': target.stat().st_size, 'sha256': digest})

readme = f'''# Eight original canonical definitions: native read and offline reopen

This milestone adds eight strictly source-bound canonical definition addresses
to the existing 13-entry native directory. It qualifies ordinary reads of their
exact native schema, with 21 directory entries and 129 source definitions still
explicitly unresolved. It does not execute or replace any of the accepted 182
migration operations.

## Actual evidence

The component qualification is one newly executed positive method plus two
unchanged negative passes retained from the first attempt. Their complete
method bodies, fixture helpers, production, dependency pins and original inputs
remain byte-identical. The overall first attempt remains FAIL, because its
positive expectation incorrectly omitted empty fields already included by the
established projection. The correction is confined to that expectation.

The native proof executed one new method in each of two fresh native processes,
with OS outbound TCP/UDP denial and zero peers in both phases. The exact eight
descriptors, original source identities and explicit value-meaning distinction
matched after a normal close and new-process reopen. Both normal closes
returned zero. All native and Swift test groups were positively absent.
Foreign Space and revoked Host-lease reads were refused. Original accounts,
accepted migration receipts, source members, native source/binary, Swift source
closure and the exact previously qualified Products remained unchanged.

The total is zero prepared operations and zero domain writes. The four native
author/clock properties describe destination events; source author/time values
remain original Heart metadata. Native ID, Space and Type addresses are
translated identities. No original history, literal cross-engine identity,
whole-Space source admission or current-value migration is inferred from schema
equivalence.

| Evidence | SHA-256 |
| --- | --- |
| Component result, one new plus two retained | `{sha(BUILD / 'result.json')}` |
| Native warm/cold result | `{args.native_receipt_sha}` |
| Equal private warm/cold descriptor bytes | `{n['comparisonSHA256']}` |
| Measured allocation budget | `{n['measuredAllocationReceiptSHA256']}` |
| Original unchanged 182-operation preservation | `f7f4a5b34465907c3285229a266a488229a92eb1c3a7c04c5b4cdd162ed1b32b` |

Native execution took {n['seconds']} seconds. Minimum observed root free space
was {n['minimumFreeBytes']} bytes. The explicit measured initial allowance was
128 MiB above the unchanged 2 GiB runtime emergency floor. The source account
copy bound was under 9 MiB. Separate account/WAL, log, receipt and whole-output
caps were enforced throughout. This allocation policy changed no semantic,
identity, permission, cold-process or lifecycle predicate.

## Retained unsuccessful attempts

Component attempt1 retains the actual failed positive method and two successful
negative methods. Attempt2's Sentinel dispatch timeout stopped provisioning
before any method; its raw RUNNING snapshot and separate external FAIL receipt
are both retained. Native attempt1 stopped at the initial storage guard with
1,850,232,832 free bytes, before account copy or native/test process launch.
Native attempt2 started an owned child, but a copy-allocation loop overwrote
the controller's HTTP base URL before readiness. There were zero Swift starts;
the child exited -15 with positive group absence. That remains FAIL. Renaming
only the measurement loop variable enabled the qualified attempt3; no product,
semantic assertion or lifecycle requirement changed.
The original unexecuted 256 MiB controller and exact allocation-policy delta
are preserved separately. No failed attempt is relabeled as successful.

## Exact cache custody

The inactive cache was relocated to
`/mnt/development/projects/caches/pinkha-w1-migration-swift-20261127`, retaining
`/tmp/pinkha-w1-migration-swift-20261127` as its stable symlink. All 6,906 entries,
file hashes, modes, owners, access/modification times, extended attributes and
link topology matched after durable copy and readback. The exact accepted
Products and three dependency pins were rechecked through the stable path.
Only then were the verified old duplicate bytes retired. No native, compiler,
dependency resolution or accepted component method was run for the move.

The earlier prepared relocation was kept intact. An exclusive evidence-name
collision stopped a new dispatch before any copy. The first actual copy
readback retained a FAIL because reading the `debug` symlink changed its access
time on the destination filesystem. All other rows and metadata matched.
Continuation reused that same copy, restored only the observed access-time
side effect, and used its exact lstat inode/ctime witness for subsequent target
checks without another readlink. Both failed and corrected receipts are here;
the complete private manifests remain at their paths named in those receipts.
Accepted custody SHA256: `{n['cacheCustodyReceiptSHA256']}`.

## Integration and remaining work

Consumer contract: `docs/architecture/native-canonical-definition-supplement-contract-20261127.md`.
This tranche follows `5235bf902f8820fdc41fe802265ff5444407b363` and uses the
existing native imported definition store unchanged. The shared root Engine
dependencies remain `6fdcabeff7a39bc206ce250b069cc076a1d29895`,
`4416ef1515dba0149a03d9a2f8441015d77e9da0` and
`e8e80bfd6b9ecdfddef41598dbf7e6a1446d0f6a`, each included once.

C remains open. All 129 unresolved definitions and 17 remaining Type-family
adapters retain their explicit boundaries. The exact original156 account
archive was recovered, but the unchanged application HistoryTree route still
requires its original account credential; archived encrypted device.key and
other-account wallets cannot supply that authority. Private original account
and descriptor material remains in the retained evidence roots. Published
files contain safe qualification metadata, source hashes and actual test logs.
'''
(DEST / 'README.md').write_text(readme)
copied.append({'path': 'README.md', 'bytes': (DEST / 'README.md').stat().st_size, 'sha256': sha(DEST / 'README.md')})
qualification = {
    'protocol': 'pinkha-native-canonical-definition-supplement-qualification-v1',
    'status': 'PASS_COMPONENT_AND_NATIVE_READ_COLD_REOPEN',
    'sourceCommitBeforeChanges': BASE,
    'componentQualification': b['qualification'],
    'componentResultSHA256': sha(BUILD / 'result.json'),
    'nativeResultSHA256': args.native_receipt_sha,
    'newCanonicalDefinitions': 8, 'allDirectoryEntries': 21, 'unresolvedSourceDefinitions': 129,
    'nativeUniqueMethods': 1, 'nativeInvocations': 2,
    'acceptedFailures': 0, 'acceptedSkips': 0,
    'preservedFailedComponentAttempts': 2, 'preservedFailedNativeAttempts': 2,
    'compiledProducts': b['compiledProducts'], 'code': code,
    'nativeControllerSHA256': n['controllerSources']['canonicalDefinitions'],
    'componentControllerSHA256': b['controllerSHA256'],
    'contractSHA256': sha(contract),
    'comparisonSHA256': n['comparisonSHA256'], 'resourcePolicy': n['resourcePolicy'],
    'maxObservedAllocationBytes': n['maxObservedAllocationBytes'], 'files': copied,
    'cacheCustodyReceiptSHA256': n['cacheCustodyReceiptSHA256'],
    'minimumDevelopmentCacheFreeBytes': n['minimumDevelopmentCacheFreeBytes'],
    'originalOperationsReexecuted': 0, 'actualPreparedOperations': 0, 'actualDomainWrites': 0,
    'originalHistoryValuesRestamped': False, 'literalNativeIdentityEquivalenceClaim': False,
    'fullSourceAdmission': False, 'wholeSpaceMigration': False, 'appleUIPresentationAccepted': False,
}
(DEST / 'qualification.json').write_text(json.dumps(qualification, sort_keys=True, indent=2) + '\n')
subprocess.run(['git', '-C', str(ROOT), 'diff', '--check'], check=True)
assert sha(args.native_receipt) == args.native_receipt_sha
for relative, digest in code.items():
    assert sha(ROOT / relative) == digest
print(json.dumps({'status': 'PACKAGED', 'path': str(DEST), 'qualificationSHA256': sha(DEST / 'qualification.json'), 'publicFiles': len(copied) + 1}))
