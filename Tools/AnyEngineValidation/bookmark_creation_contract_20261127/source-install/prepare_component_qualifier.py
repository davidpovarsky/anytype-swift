"""Compose a source-only Bookmark27 successor of the retained uploader qualifier."""
from pathlib import Path
import ast
import difflib
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'ordinary-upload-engine'
OUT = HERE / 'qualification'
OUT.mkdir(exist_ok=True)

def identity(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def save(name, data):
    raw = data.encode() if isinstance(data, str) else data
    (OUT / name).write_bytes(raw)
    return identity(raw)

old_manifest = json.loads((OLD / 'upload-component-inputs.json').read_bytes())
manifest = {key: old_manifest[key] for key in (
    'dependencySourcePins', 'originalCoreCommit', 'originalCoreFiles',
    'originalCoreRoot', 'originalProjectCommit', 'originalProjectFiles',
    'originalProjectRoot', 'retainedCryptoProducer')}
manifest.update(schema=1, scope='ISOLATED_BOOKMARK_CREATION_COMPONENT_SOURCE_CLOSURE_ONLY',
    sourceOnlyUntilActualControllerReceipt=True, noNativeStorageOrCloudDurabilityClaim=True,
    noOriginalAccountOpen=True, excludedNativeMethods={}, preparedSources=[], methods={})
for entry in old_manifest['preparedSources']:
    if entry['kind'] == 'production' and not entry['path'].endswith('/AnyNativeObjectCreator.swift'):
        row = dict(entry, sourceBase='retained-upload-prepared3')
        manifest['preparedSources'].append(row)
for name in ('AnyNativeObjectCreator.swift', 'AnyNativeBookmarkCreationFrame.swift'):
    raw = (HERE / 'Sources' / name).read_bytes()
    manifest['preparedSources'].append(dict(path='Sources/' + name, kind='production',
        target='PinkhaAnyHost', sourceBase='bookmark-prepared1', **identity(raw)))
for name in ('AnyNativeObjectCreationExactValueTests.swift', 'AnyNativeBookmarkCreationFrameTests.swift',
             'AnyNativeFileAttachmentPostCloseTests.swift'):
    raw = (HERE / 'Tests' / name).read_bytes()
    names = re.findall(r'^    func (test\w+)\(', raw.decode(), re.M)
    assert len(names) == len(set(names))
    manifest['methods'][name[:-6]] = names
    manifest['preparedSources'].append(dict(path='Tests/' + name, kind='test',
        target='BookmarkCreationTests', sourceBase='bookmark-prepared1', **identity(raw)))
assert [len(v) for v in manifest['methods'].values()] == [7, 20, 4]
frame_test = (HERE / 'Tests/AnyNativeBookmarkCreationFrameTests.swift').read_text()
script = frame_test.split('    private static let server = #"""\n', 1)[1].split('\n"""#', 1)[0].encode()
ast.parse(script)
manifest['fixtureScript'] = identity(script)
manifest['expectedCounts'] = dict(methods=31, exactValueMethods=7, frameMethods=20, postCloseMethods=4,
    httpBearingMethods=10, nonHTTPMethods=21, httpFixtureInstances=17,
    httpRequests=76, httpGETs=66, readOnlyFramePOSTs=10, objectCreatePOSTs=0,
    originalProjectReadFiles=20, originalProjectCompiledFiles=19,
    originalCoreCompiledFiles=8, preparedProductionCompiledFiles=6,
    productionCompiledFiles=33, compiledTestFiles=3, excludedNativeMethods=0)
manifest['controllerPredecessor'] = dict(path=str(OLD / 'run_upload_components.py'),
    **identity((OLD / 'run_upload_components.py').read_bytes()),
    originalMethodsReplayed=0, reusedScope='unchanged process, resource and complete source admission logic')
manifest['retainedUploadSourceRoot'] = '/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/prepared3'
manifest['status'] = 'SOURCE_ONLY_NOT_INSTALLED_OR_COMPILED_OR_RUN'
manifest_sha = save('bookmark-component-inputs.json', json.dumps(manifest, sort_keys=True, indent=2) + '\n')['sha256']

wrapper_old = (OLD / 'qualify_upload_crypto_c3.py').read_text()
wrapper = wrapper_old.replace('ordinary-upload consumer', 'Bookmark and recovery consumer').replace(
    "'CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_ORDINARY_UPLOAD_COMPONENTS_ONLY'",
    "'CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_BOOKMARK_COMPONENTS_ONLY'").replace(
    "'none; all35 ordinary-upload component methods remain mandatory'",
    "'none; all31 new Bookmark and recovery component methods remain mandatory'")
wrapper_sha = save('qualify_bookmark_crypto_c3.py', wrapper)['sha256']
save('crypto-wrapper.review.patch', ''.join(difflib.unified_diff(wrapper_old.splitlines(True), wrapper.splitlines(True), fromfile='qualified-uploader-wrapper.py', tofile='bookmark-label-only-wrapper.py')))
for name in ('qualify_current_c3_crypto.py', 'owned_swift_commands.py', 'crypto-header-source-manifest.json'):
    save(name, (OLD / name).read_bytes())

old = (OLD / 'run_upload_components.py').read_text()
assert identity(old.encode())['sha256'] == 'ee54cf07a4f21b53e6a9edec65145e621477c8f51017a54c589a4eccdd116b7e'
source = old
def once(before, after):
    global source
    assert source.count(before) == 1, (before[:100], source.count(before))
    source = source.replace(before, after)

once('35 ordinary-upload component methods', '27 new Bookmark creation component methods')
once("PARENT = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127')\nPREPARED = PARENT/'prepared3'", "PARENT = Path('/mnt/development/projects/evidence/pinkha-bookmark-creation-contract-20261127')\nPREPARED = PARENT/'prepared1'\nRETAINED_UPLOAD_PREPARED = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127/prepared3')")
once("MANIFEST = CONTROL/'upload-component-inputs.json'", "MANIFEST = CONTROL/'bookmark-component-inputs.json'")
once("MANIFEST_SHA = '74bf4e399ae6988fb9e12cebd544538e76b326636a1c2d8476dd3c556b43614f'", f"MANIFEST_SHA = '{manifest_sha}'")
once("CRYPTO_HELPER = CONTROL/'qualify_upload_crypto_c3.py'", "CRYPTO_HELPER = CONTROL/'qualify_bookmark_crypto_c3.py'")
once("CRYPTO_HELPER_SHA = '1ed69a8431f77c4d5b1b735a6d85efec1fa77b50f0c7185185f712d5bf09abbd'", f"CRYPTO_HELPER_SHA = '{wrapper_sha}'")
source = source.replace('OrdinaryFileUploadTests', 'BookmarkCreationTests').replace('OrdinaryFileUploadProof', 'BookmarkCreationProof')
start = source.index('def fixture_audit(')
end = source.index('\n\ndef main():', start)
audit = (HERE / 'fixture_audit.fragment.py').read_text().rstrip()
source = source[:start] + audit + source[end:]
once("'scope':'35 isolated original-source ordinary upload component methods only'", "'scope':'27 new Bookmark component methods only'")
once("'priorMigrationOrFilesV2MethodsReplayed':0", "'priorMigrationOrFilesV2MethodsReplayed':0, 'priorUpload35MethodsReplayed':0")
once("manifest['scope'] == 'ISOLATED_ORDINARY_UPLOAD_COMPONENT_SOURCE_CLOSURE_ONLY'", "manifest['scope'] == 'ISOLATED_BOOKMARK_CREATION_COMPONENT_SOURCE_CLOSURE_ONLY'")
once("assert manifest['expectedCounts']['methods'] == 35 and len(manifest['preparedSources']) == 10\n        assert manifest['expectedCounts']['compiledTestFiles'] == 4 and manifest['expectedCounts']['excludedNativeMethods'] == 1\n        assert manifest['excludedNativeMethods'] == {'AnyNativeFileUploadNativeRouteTests':['testOriginalNativeAttachResolvesMetadataAndVerifiesInlineAndFullTierBytes']}", "assert manifest['expectedCounts']['methods'] == 27 and len(manifest['preparedSources']) == 8\n        assert manifest['expectedCounts']['compiledTestFiles'] == 2 and manifest['expectedCounts']['excludedNativeMethods'] == 0\n        assert manifest['excludedNativeMethods'] == {}\n        assert manifest['retainedUploadSourceRoot'] == str(RETAINED_UPLOAD_PREPARED)")
once("helper = load_module(CRYPTO_HELPER, 'ordinary_upload_crypto'", "helper = load_module(CRYPTO_HELPER, 'bookmark_creation_crypto'")
once("            source = PREPARED/entry['path']", "            assert entry['sourceBase'] in ('retained-upload-prepared3', 'bookmark-prepared1')\n            source_root = RETAINED_UPLOAD_PREPARED if entry['sourceBase'] == 'retained-upload-prepared3' else PREPARED\n            source = source_root/entry['path']")
once("            elif entry['kind'] in ('test','excluded-native-test'):", "            elif entry['kind'] == 'test':")
once("                assert entry['kind'] == 'fixture' and source.name == 'file_upload_server.py'\n                target = package/'Tests/Fixtures'/source.name", "                raise AssertionError('undeclared new Bookmark source kind')")
once("assert len(list((package/'Sources').rglob('*.swift'))) == 32", "assert len(list((package/'Sources').rglob('*.swift'))) == 33")
once("assert len(list((package/'Tests/BookmarkCreationTests').glob('*.swift'))) == 4", "assert len(list((package/'Tests/BookmarkCreationTests').glob('*.swift'))) == 2")
source = source.replace('PINKHA_FILE_UPLOAD_FIXTURE_ROOT', 'PINKHA_BOOKMARK_FRAME_FIXTURE_ROOT').replace('PINKHA_FILE_UPLOAD_OWNER_RECORD', 'PINKHA_BOOKMARK_FRAME_OWNER_RECORD').replace('PINKHA_FILE_UPLOAD_OWNER_CWD', 'PINKHA_BOOKMARK_FRAME_OWNER_CWD')
once('assert len(expected) == len(starts) == len(passes) == 35', 'assert len(expected) == len(starts) == len(passes) == 27')
once('actual XCTest inventory differs from the frozen 35 methods', 'actual XCTest inventory differs from the frozen 27 new methods')
once("assert re.search(r'Executed 35 tests?, with 0 failures', log)", "assert re.search(r'Executed 27 tests?, with 0 failures', log)")
once("'pure':6, 'http':12, 'host':17, 'total':35", "'exactValue':7, 'frame':20, 'httpBearing':10, 'nonHTTP':17, 'total':27")
once("fixture_audit(output/'http-fixtures', swift_folder/'started.json', swift, base)", "fixture_audit(output/'http-fixtures', swift_folder/'started.json', swift, base, manifest)")
once("len(result['commands']) == 7 and result['actualMethods']['total'] == 35", "len(result['commands']) == 7 and result['actualMethods']['total'] == 27")
once("result['httpFixtureQualification']['instances'] == 26", "result['httpFixtureQualification']['instances'] == 17\n                assert result['httpFixtureQualification']['requestCount'] == 76")
once('def retained_products(build, base):', 'def retained_products(build, base, guard):')
once("    for path in [root]+sorted(root.rglob('*')):\n        before = path.lstat()", "    for path in [root]+sorted(root.rglob('*')):\n        guard()\n        before = path.lstat()")
once("    source_admission_complete = False", "    source_admission_complete = False\n    final_deadline = None")
once("            if time.monotonic()-started_at > TOTAL_SECONDS:\n                return 'bounded component controller deadline'", "            if time.monotonic()-started_at > TOTAL_SECONDS:\n                return 'bounded component controller deadline'\n            if final_deadline is not None and time.monotonic() >= final_deadline:\n                return 'bounded component final verification deadline'")
once("'entireOwnedOutputAllocationCapBytes':OWNED_ALLOCATION_CAP, 'declaredControlledOutputBytesOnRoot':0,", "'entireOwnedOutputAllocationCapBytes':OWNED_ALLOCATION_CAP, 'declaredControlledOutputBytesOnRoot':0,\n                        'finalVerificationSeconds':120, 'unchangedTotalControllerSeconds':TOTAL_SECONDS,")
source = source.replace("retained_products(output/'build', base)", "retained_products(output/'build', base, guard)")
once("        owned.ignore_interrupts()\n        # Cached", "        owned.ignore_interrupts()\n        final_deadline = min(started_at+TOTAL_SECONDS, time.monotonic()+120)\n        # Cached")
once("            for path, expected in immutable.items():\n                assert base.row", "            for path, expected in immutable.items():\n                guard()\n                assert base.row")
once("            for path, expected in copies.items():\n                assert base.row", "            for path, expected in copies.items():\n                guard()\n                assert base.row")
once("            for path, expected in controls.items():\n                base.pinned", "            for path, expected in controls.items():\n                guard()\n                base.pinned")
ast.parse(source)
source = source.replace('27 new Bookmark creation component methods', '31 new Bookmark and recovery component methods')
source = source.replace("'scope':'27 new Bookmark component methods only'", "'scope':'27 new Bookmark plus4 new post-close recovery component methods only'")
source = source.replace("manifest['expectedCounts']['methods'] == 27 and len(manifest['preparedSources']) == 8", "manifest['expectedCounts']['methods'] == 31 and len(manifest['preparedSources']) == 9")
source = source.replace("manifest['expectedCounts']['compiledTestFiles'] == 2", "manifest['expectedCounts']['compiledTestFiles'] == 3")
source = source.replace("len(list((package/'Tests/BookmarkCreationTests').glob('*.swift'))) == 2", "len(list((package/'Tests/BookmarkCreationTests').glob('*.swift'))) == 3")
source = source.replace('len(expected) == len(starts) == len(passes) == 27', 'len(expected) == len(starts) == len(passes) == 31')
source = source.replace('frozen 27 new methods', 'frozen 31 new methods')
source = source.replace('Executed 27 tests?', 'Executed 31 tests?')
source = source.replace("'nonHTTP':17, 'total':27", "'nonHTTP':21, 'postClose':4, 'total':31")
source = source.replace("result['actualMethods']['total'] == 27", "result['actualMethods']['total'] == 31")
ast.parse(source)
save('run_bookmark_components.py', source)
save('bookmark27-qualifier.review.patch', ''.join(difflib.unified_diff(old.splitlines(True), source.splitlines(True), fromfile='actual-uploader35-ee54.py', tofile='new-bookmark27.py')))
print(json.dumps({'status':'SOURCE_ONLY', 'controller':identity(source.encode()), 'manifest':manifest_sha,
    'wrapper':wrapper_sha, 'sourceFiles':33, 'testFiles':3, 'methods':31, 'fixtures':17, 'requests':76}))
