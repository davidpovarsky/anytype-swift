#!/usr/bin/env python3
"""Local docs-only packet assembly. No Git writes, remote calls or runtime."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
WORK = HERE.parent
SOURCE = WORK / 'wave2-hierarchy-rename-component'
EXECUTION = SOURCE / 'execution-preparation'
STAGING = SOURCE / 'staging-preparation'
PRIOR = WORK / 'wave2-property-unicode-audit/component-preparation'
PRODUCT = WORK / 'interfaces_work/hierarchy-title-exact/publication'
PACKET = HERE / 'packet'
PREFIX = 'docs/validation/20261127-wave2-hierarchy-rename-component-preparation'
BASE = '9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce'
TREE = 'c8466a2e97f13d5708213f4275bb4f30ac96cc22'
BRANCH = 'codex/chatgpt-wave15-wave2-hierarchy-rename-component-20261127'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': sha(raw)}


provenance = []


def save(relative, raw, original=None):
    if isinstance(raw, str):
        raw = raw.encode()
    target = PACKET / PREFIX / relative
    assert not target.exists(), str(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    target.chmod(0o644)
    if original is not None:
        provenance.append({'packetPath': relative, 'originalLocal': pin(original), 'byteIdentical': True})


def emit(relative, value):
    save(relative, json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + '\n')


def copy(path, relative, expected=None):
    assert path.is_file() and not path.is_symlink(), str(path)
    raw = path.read_bytes()
    if expected is not None:
        assert sha(raw) == expected, str(path)
    save(relative, raw, path)


assert not PACKET.exists(), 'Do not overwrite a prepared packet.'
input_packet = json.loads((EXECUTION / 'input-packet.json').read_bytes())
assert sha((EXECUTION / 'input-packet.json').read_bytes()) == 'ed3ef9bfce4119bc199934d4740a09f5e0e621abd0806a45e831f392cf043df6'
assert input_packet['productCommit'] == BASE and input_packet['fileCount'] == 61 and input_packet['bytes'] == 781373
assert input_packet['runtimeReady'] is False and input_packet['runtimeSlotGranted'] is False
expected = {row['path']: (row['bytes'], row['sha256']) for row in input_packet['files']}
actual = {}
for path in sorted((EXECUTION / 'inputs').rglob('*')):
    assert not path.is_symlink(), str(path)
    if path.is_file():
        raw = path.read_bytes(); relative = path.relative_to(EXECUTION / 'inputs').as_posix()
        actual[relative] = (len(raw), sha(raw))
        copy(path, 'execution/inputs/' + relative)
assert actual == expected

for source, relative, expected_hash in [
    (SOURCE / 'whole-source-intake.json', 'intake/whole-source-intake.json', '280877ebf3b83c3f642c5da94ea4f74b17a7fd4b9f490775d9e6586a026c2d13'),
    (SOURCE / 'whole-source-imports.json', 'intake/whole-source-imports.json', '547eba1455cdb2528ef80cbe66f563e910ad8dcf7ea767effed773ca7772249c'),
    (SOURCE / 'review-handoff.json', 'intake/review-handoff.original.json', '31507d0f24b91ad9815b6db4b1b2d62eb3a63b85390e1120396bf22016b7e42f'),
    (SOURCE / 'README.md', 'intake/author-README.original.md', '9916220b8c2ee4d9bdd9539b653eeeb9fe93cd101fd88f81730f44ceb0a7a7e9'),
    (SOURCE / 'root-independent-execution-review.json', 'reviews/root-independent-execution-review.json', 'e152db9ef0e57c44206497b73b2bdfb726e5d83fe942ec3f4f8bb369a968aab8'),
    (STAGING / 'root-stager-review.json', 'reviews/root-stager-review.json', '7f6673a03092391cb9fe35e01dde1ca55a6f7d3509e67b9f1db7fcbadd9d9e79'),
]:
    copy(source, relative, expected_hash)

for name in ('input-packet.json', 'controller-derivative.json', 'controller-derivative.patch',
             'package-derivative.patch', 'generated-source-format-proof.json',
             'expected-generated-test-entry-point.swift', 'qualifier_controls.py', 'qualifier-controls-result.json'):
    copy(EXECUTION / name, 'execution/' + name)
for name in ('README.md', 'materialize_and_exec.py', 'hierarchy-rename-inputs.json.gz',
             'hierarchy-rename-inputs.json.gz.base64', 'source.patch', 'stager-derivation.json',
             'transport-manifest.json', 'one-shot-invocation.json', 'payload-readback.json'):
    copy(STAGING / name, 'staging/' + name)
for name in ('prepare_intake.py', 'prepare_execution.py', 'prepare_staging.py', 'swift_testing_result.fragment.py'):
    copy(SOURCE / name, 'generation/' + name)
for name in ('kit-package.swift', 'engine-package.swift', 'integration-package.swift'):
    copy(SOURCE / 'reference' / name, 'reference/original-packages/' + name)

intake = json.loads((SOURCE / 'whole-source-intake.json').read_bytes())
bindings = []
raw_receipts = {}
for row in intake['files']:
    source = EXECUTION / 'inputs/component' / row['path']
    raw = source.read_bytes()
    assert (len(raw), sha(raw), blob(raw)) == (row['bytes'], row['sha256'], row['gitBlob'])
    receipt_path = Path(row['currentPrimary']['path'])
    receipt_raw = receipt_path.read_bytes()
    assert sha(receipt_raw) == row['currentPrimary']['sha256']
    value = json.loads(receipt_raw)['structuredContent']
    record = {'repository': row['repository'], 'repositoryPath': row['repositoryPath'],
              'sourceCommit': row['sourceCommit'], 'publishedAppCommit': BASE,
              'gitBlob': row['gitBlob'], 'sha256': row['sha256'], 'bytes': row['bytes'],
              'packetWholeSource': 'execution/inputs/component/' + row['path'],
              'originalPrimaryReceipt': pin(receipt_path),
              'immutableBodyURL': 'https://github.com/' + row['repository'] + '/blob/' + row['sourceCommit'] + '/' + row['repositoryPath']}
    if value.get('encoding') == 'utf-8':
        assert value['content'].encode() == raw and value['sha'] == row['gitBlob']
        record['observedPrimaryKind'] = 'full_body'
        record['originalPrimaryURL'] = value['display_url']
    else:
        entries = json.loads(value['content'])
        matched = [entry for entry in entries if entry['path'] == row['repositoryPath']]
        assert len(matched) == 1
        entry = matched[0]
        assert entry['type'] == 'file' and entry['sha'] == row['gitBlob'] and entry['size'] == len(raw)
        assert '?ref=' + row['sourceCommit'] in entry['url']
        record['observedPrimaryKind'] = 'immutable_directory_entry_plus_exact_recomputed_body_git_blob'
        record['observedDirectoryEntry'] = {key: entry[key] for key in ('name','path','sha','size','url','html_url','git_url','type')}
    raw_receipts[str(receipt_path)] = pin(receipt_path)
    bindings.append(record)
emit('primary/source-authorities.json', {
    'schema': 'pinkha-hierarchy-component-primary-source-bindings/v1',
    'status': 'DERIVED_EXACT_BINDING_INDEX_OF_RETAINED_PRIMARY_RECEIPTS',
    'base': intake['base'], 'productCommit': BASE, 'coreDependencyCommit': intake['coreDependencyCommit'],
    'files': bindings, 'rawPrimaryReceipts': list(raw_receipts.values()),
    'bodyCustody': 'All55 complete Swift bodies occur once in execution/inputs/component; each independently reproduces its observed immutable Git blob.',
    'noClaimOfNewAPIResponse': True,
    'rawEnvelopePolicy': 'Raw original API envelopes remain at their exact retained paths/hashes. This explicit derived index preserves all selected observed entries, exact body hashes and immutable URLs without duplicating full source bodies.',
    'compiledClosureObserved': False})

product_receipt = json.loads((PRODUCT / 'publication-result.json').read_bytes())
commit_raw = json.loads((PRODUCT / 'api/final-commit.original.json').read_bytes())
commit = json.loads(commit_raw['structuredContent']['content'])
assert commit['sha'] == BASE and commit['tree']['sha'] == TREE
assert [row['sha'] for row in commit['parents']] == [intake['base']]
assert product_receipt['allOtherOriginalLeavesAndModesPreserved'] and product_receipt['all24PrimaryBodyReadbacksExact']
copy(PRODUCT / 'publication-result.json', 'primary/product-publication-result.original.json')
merkle_path = PRODUCT / 'api/complete-merkle-proof.json'
merkle = json.loads(merkle_path.read_bytes())
assert merkle['newTree'] == TREE and merkle['allOtherOriginalLeavesAndModesRetained']
emit('primary/product-lineage-binding.json', {
    'schema': 'pinkha-hierarchy-component-source-lineage-excerpt/v1',
    'status': 'EXPLICIT_DERIVED_EXCERPT_OF_RETAINED_PRIMARY_AND_FULL_TREE_PROOF',
    'originalCommitResponse': pin(PRODUCT / 'api/final-commit.original.json'),
    'originalCompleteMerkleProof': pin(merkle_path), 'publicationReceipt': pin(PRODUCT / 'publication-result.json'),
    'commit': BASE, 'tree': TREE, 'parents': [row['sha'] for row in commit['parents']],
    'sourceChanges': product_receipt['readbacks'][:2],
    'originalProofStatus': merkle['status'], 'unchangedSubtreeOrLeafEntries': len(merkle['unchangedSubtreeOrLeafEntries']),
    'treeComparisonCount': len(merkle['treeComparisons']),
    'allOtherOriginalLeavesAndModesRetained': True,
    'bodyBasis': 'Current9f body bindings are inherited by the exact single-child9e4 commit; only the two explicitly published repository/test bodies change. Both full new bodies were independently fetched again for this component.',
    'excerptIsNotANewFullTreeProof': True})

g04 = WORK / 'wave2-reader-audit/component/actual-run/attempt1'
g04_publication = WORK / 'wave2-reader-audit/component-evidence-publication/root-api-publication/publication-result.json'
copy(g04 / 'stdout.original.log', 'reference/g04-stdout.original.log')
copy(g04_publication, 'reference/g04-evidence-publication.original.json', '9a6721f120d9ff6e216bb597d62faacbe5898287c6e680a4c9afd0fa5708125e')
property_publication = WORK / 'interfaces_work/property4-component-publication/publication-result.json'
copy(property_publication, 'reference/property4-preparation-publication.original.json')

property_prefix = 'docs/validation/20261127-wave2-property4-component-preparation'
property_commit = '7e2c09a81434e287b2f3b434ccb1be141a1f1b99'
g04_prefix = 'docs/validation/20261127-reader-document-lifetime/component/actual-run/attempt1'
g04_commit = 'e77c9d448882b74ddcf6c3d30622708ae25a21ba'
references = []
for path, repository, commit_id, published_path, purpose in [
    (PRIOR / 'execution-preparation/inputs/run_component.py', 'davidpovarsky/anytype-swift', property_commit, property_prefix + '/execution/inputs/run_component.py', 'Exact66f donor; full inverse retained in this packet.'),
    (PRIOR / 'execution-preparation/inputs/component/Package.swift', 'davidpovarsky/anytype-swift', property_commit, property_prefix + '/execution/inputs/component/Package.swift', 'Exact25f Package donor; full inverse retained in this packet.'),
    (PRIOR / 'staging-preparation/materialize_and_exec.py', 'davidpovarsky/anytype-swift', property_commit, property_prefix + '/staging/materialize_and_exec.py', 'Exact2a7 stager donor; full inverse retained in this packet.'),
    (g04 / 'stdout.original.log', 'davidpovarsky/TorahInspectorKit', g04_commit, g04_prefix + '/stdout.original.log', 'Actual Swift Testing event grammar only; G04 six/nine not replayed.'),
    (g04 / 'receipt.json', 'davidpovarsky/TorahInspectorKit', g04_commit, g04_prefix + '/receipt.json', 'Original G04 actual receipt, remains separate.'),
    (g04 / 'compiler-filelists/test_entry_point.swift', 'davidpovarsky/TorahInspectorKit', g04_commit, g04_prefix + '/compiler-filelists/test_entry_point.swift', 'Actual G04 generated input; complete two-literal inverse from expected source retained here.'),
]:
    references.append({'original': pin(path), 'repository': repository, 'publishedCommit': commit_id,
                       'publishedPath': published_path, 'URL': 'https://github.com/' + repository + '/blob/' + commit_id + '/' + published_path,
                       'purpose': purpose})

host2 = WORK / 'torah-acceptance-prep/native-text-readback/execution-preparation'
failure_refs = []
for path, reason in [
    (host2 / 'actual-source2/originals/attempt1/receipt.json', 'Original failed source2 qualifier receipt remains immutable; later actual completion does not rewrite it.'),
    (host2 / 'actual-source2/completion-result.original.json', 'Later read-only completion records actual ROOT compiler working-directory evidence; not new hierarchy execution.'),
    (PRIOR / 'execution-preparation/review-v1-metadata/input-packet.json', 'Original4e17 metadata predecessor, preserved by Property4 publication.'),
    (PRIOR / 'execution-preparation/historical-footprint-precision.json', 'Explicit4e17 to66d0 historical-footprint precision, not capacity forecast.'),
]:
    assert path.exists(), str(path)
    failure_refs.append({'original': pin(path), 'preservation': reason})
emit('reference/original-evidence-index.json', {
    'schema': 'pinkha-hierarchy-component-original-evidence-index/v1',
    'status': 'RETAINED_REFERENCES_NO_PRIOR_RUNTIME_REPLAY', 'references': references,
    'priorFailureAndCorrectionReferences': failure_refs,
    'priorProperty4PersistentHistoryRoot': 'https://github.com/davidpovarsky/anytype-swift/tree/' + property_commit + '/' + property_prefix,
    'originalCryptoFailureRetainedInsideExactInputManifest': {'path': 'execution/inputs/retained-crypto-closure.json', 'sha256': '10c98c4192acba640c401586fb84ef9aa227e6d52bdde7198f251a0498146c2c'},
    'allOriginalsRemainUnchanged': True,
    'newHierarchyRuntimeResult': None,
    'scope': 'No bulky prior controller/production/body/history copies are duplicated. Exact full inverses, original immutable references and original failure metadata remain available.'})

copy(HERE / 'prepare_packet.py', 'generation/prepare_publication_packet.py')
emit('custody/copied-originals.json', {'schema': 'pinkha-hierarchy-component-packet-original-custody/v1',
     'status': 'EXACT_BYTE_COPIES_FROM_FROZEN_LOCAL_ARTIFACTS', 'files': provenance,
     'localPathsAreHistoricalProvenance': True, 'publishedPathMapping': 'packetPath is relative to this docs prefix.'})

emit('publication-scope.json', {
    'schema': 'pinkha-hierarchy-component-docs-publication-scope/v1',
    'status': 'SOURCE_PREPARATION_ONLY_RUNTIME_NOT_ADMITTED', 'repository': 'davidpovarsky/anytype-swift',
    'parent': BASE, 'parentTree': TREE, 'branch': BRANCH, 'docsPrefix': PREFIX,
    'existingSourcePathsChanged': [], 'newProductOrTestSourcePaths': [],
    'allOriginalPackagePBXGatesAppSourcesAndTestsMustRemainUnchanged': True,
    'inputCopies': 61, 'inputBytes': 781373, 'sourceFiles': 55, 'sourceBytes': 526737,
    'selectedSourceSuite': 'AnyHierarchyRawTitleTests', 'selectedNewMethods': 4, 'declaredArgumentCases': 8,
    'old23MethodsSelected': 0, 'compiledEnumeration': None, 'actualRuntimeResult': None,
    'runtimeReady': False, 'slotGranted': False, 'upload': False,
    'schedulingNoticeOnly': {'asanaStory': '1220961913615252', 'executionGrant': False, 'mustNotBeUsedAsCoordinationGrant': True},
    'requiredBeforeRuntime': 'Separate explicit W1 owner release/grant, root coordination, exact upload/readback and original fresh source/dependency/resource predicates.',
    'sourceBodyPolicy': 'One ordinary copy per61 input files. Deterministic gzip/base64 transport encodes those same inputs; no duplicate local55-file source tree or older complete source bodies.',
    'generators': 'Verbatim local-only assembly sources with historical layout/path provenance, not promised to execute from relocated publication paths.',
    'GitMutationBeforePacketApproval': False})

readme = '''# Hierarchy rename4/8 — reviewed component preparation

This is a docs-only preparation packet for the exact source published in `9e4aa3f1b88d8f6bfec27cdf2cb47d07ffd416ce`. **No hierarchy compiler/test attempt, upload, host/cache access or runtime-slot reservation has occurred.** Root accepted the runner and stager source; those reviews do not grant execution.

## Exact review entry points

- `execution/input-packet.json`:61 exact input files,781,373 bytes, frozen `ed3ef9bf…`.
- `execution/inputs/run_component.py`: frozen `f63adbdf…`, one owned Swift command with the retained resource/cleanup machinery.
- `reviews/root-independent-execution-review.json`: root review `e152db9e…`.
- `staging/transport-manifest.json`: exact stager `b3cfea8a…`, gzip `b4ef0e16…`, raw JSON `ec0c1a2e…`.
- `reviews/root-stager-review.json`: root review `7f6673a0…`.
- `primary/source-authorities.json`: all55 full input bodies bound to exact original Git blobs, immutable commits, observed primary metadata and current package dependency pins.
- `intake/author-README.original.md` and `staging/README.md`: complete preparation decisions and current limitations.

The full source closure is54 whole production files plus the complete27-method `AnyHierarchyTests.swift`,526,737 source bytes. Core8 is at the actual app-pinned Kit26beca; Kit12, Engine15 and Integration19 are exact current bodies. The real protocol-owning HTTP store files are included whole. No declarations are extracted and no production stub or removed guard substitutes for a dependency.

## Only four methods / eight declared argument cases

The fixed original target is `PinkhaAnyIntegrationTests` and the fixed suite filter is `AnyHierarchyRawTitleTests`. Its methods are:

1. `canonicallyEquivalentRequestedRenameReachesTheOriginalStore`
2. `canonicallyEquivalentStaleExpectedTitleRefusesBeforeDispatch`
3. `canonicallyEquivalentSuccessfulReadbackCannotCertifyRename`
4. `canonicallyEquivalentReadbackPreservesTheOriginalWriteError`

Each uses the source enum's Latin/Hebrew arguments. The full original23-method prefix is compiled but excluded from selection. Source names are not claimed compiled IDs. Acceptance would require all four actual method passes and eight distinct paired argument-case passes, a matching suite/summary, and the full actual compiler/source/object closure. These are controlled-store Integration tests; no HTTP/Native/account/mounted-UI claim is made.

The six finite AST-only synthetic qualifier controls are retained in `execution/qualifier-controls-result.json`; they are not Swift test execution. Their event grammar is derived from the original G04 actual stdout retained under `reference/`. The expected generated entrypoint is explicitly an expectation, not an observed artifact of this new attempt. Unknown actual output fails qualification without automatic widening.

## Original execution boundaries remain

The runner is a complete byte-invertible derivative of Property4 `66f09e18…`, with11 original functions and the exact58624 owned helper unchanged. The stager inverts to proven2a7, with all six helper bodies unchanged. Both inverses and the local generator sources are retained. Every original source/reference remains unchanged; historical local paths in copied reports identify original provenance, while this README and the custody index locate the published copies.

The future root is `/mnt/development/projects/evidence/pinkha-wave2-hierarchy-rename-20261127`. Staging refuses any existing root/path, validates the exact payload and complete new file set, preserves original dependencies, and establishes actual ROOT cwd/PWD before the original exec transition. The runner then retains its one owned Swift child and original terminal-group handling. No historical group is queried by this preparation.

Limits remain300 seconds/jobs2,256MiB whole-owned containment including1MiB final reserve,2GiB root floor+32MiB admission margin,512MiB Development stop floor plus cap/margin at admission, and512MiB available memory. These are strict limits, not a prediction of peak usage. The Crypto102 physical originals/copies/aliases and current capacity must be freshly qualified within the real owner window; no warmness is assumed.

**Asana story1220961913615252 is a scheduling notice only. It is not an execution grant and must not be used as the one-shot coordination grant.** `staging/one-shot-invocation.json` deliberately has a null coordination story. Root owns future publication/upload and any separately granted W1 window. No automatic retry, new source namespace or resource-limit increase is supplied.

## Publication and retained history

This packet adds only its new docs prefix to single parent9e4. All original product/test/Package/PBX/gate/workflow bodies must remain unchanged, qualified by a complete finite Merkle comparison at publication. Root's packet approval and actual publication receipt will be retained externally so the frozen packet does not change.

The61 ordinary input files are copied once. The gzip and base64 are explicit encodings of that same frozen tuple. The duplicate local55-file source directory and bulky earlier runtime/source bodies are excluded. Exact original G04/Property4 URLs, hashes, full inverse maps and failure/correction references remain in `reference/original-evidence-index.json`; the unchanged Crypto manifest also retains its original failed-result boundary. No previous accepted suite is replayed or counted as hierarchy acceptance.
'''
save('README.md', readme)

files = []
for path in sorted(PACKET.rglob('*')):
    assert not path.is_symlink(), str(path)
    if path.is_file():
        raw = path.read_bytes()
        files.append({'path': path.relative_to(PACKET).as_posix(), 'mode': '100644', 'type': 'blob',
                      'bytes': len(raw), 'sha256': sha(raw), 'gitBlob': blob(raw)})
manifest = {'schema': 'pinkha-hierarchy-rename-component-docs-packet/v1',
            'status': 'FROZEN_FOR_ROOT_PACKET_REVIEW', 'repository': 'davidpovarsky/anytype-swift',
            'parent': BASE, 'parentTree': TREE, 'branch': BRANCH, 'docsPrefix': PREFIX,
            'filesExcludingThisManifest': len(files), 'bytesExcludingThisManifest': sum(row['bytes'] for row in files),
            'files': files, 'productSourceFilesChanged': 0, 'inputCopies': 61,
            'runtimeExecuted': False, 'uploaded': False, 'slotGranted': False}
emit('packet-manifest.json', manifest)
manifest_path = PACKET / PREFIX / 'packet-manifest.json'
raw = manifest_path.read_bytes()
files.append({'path': manifest_path.relative_to(PACKET).as_posix(), 'mode': '100644', 'type': 'blob',
              'bytes': len(raw), 'sha256': sha(raw), 'gitBlob': blob(raw)})
files.sort(key=lambda row: row['path'])
assert all(row['path'].startswith(PREFIX + '/') for row in files)
target = {'schema': 'pinkha-hierarchy-rename-component-owned-publication-target/v1',
          'status': 'FROZEN_PENDING_ROOT_PACKET_REVIEW_NO_GIT_WRITES', 'repo': 'davidpovarsky/anytype-swift',
          'parent': BASE, 'parentTree': TREE, 'branch': BRANCH, 'docsPrefix': PREFIX,
          'packetRoot': str(PACKET), 'packetManifestPath': str(manifest_path), 'packetManifestSHA256': sha(raw),
          'totalFilesIncludingManifest': len(files), 'totalBytesIncludingManifest': sum(row['bytes'] for row in files),
          'expectedFiles': files, 'newProductOrTestSourcePaths': [], 'changedExistingSourcePaths': [],
          'runtimeExecuted': False, 'publicationPerformed': False, 'freshRemoteChecksRequired': True,
          'expectedRuntimeInputPacketSHA256': 'ed3ef9bfce4119bc199934d4740a09f5e0e621abd0806a45e831f392cf043df6',
          'expectedStagerSHA256': 'b3cfea8a789c4abae7f2f2b8aa3202dc7cf2725a5fae2438eb5c5c9d6342f7eb'}
target_path = HERE / 'publication-target.json'
assert not target_path.exists()
target_path.write_text(json.dumps(target, sort_keys=True, indent=2) + '\n')
print(json.dumps({'target': pin(target_path), 'manifest': pin(manifest_path), 'files': len(files),
                  'bytes': target['totalBytesIncludingManifest'], 'originalInputTupleUnchanged': True}, indent=2))
