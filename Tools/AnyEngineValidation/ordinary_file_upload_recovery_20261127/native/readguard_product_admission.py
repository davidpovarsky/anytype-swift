"""Exact public native admission from N2bb, without account operations.

The producer block keeps its original predicates. Only its two argument names
and its diagnostic dictionary name are adapted to a reusable function.
Importing the pinned source defines functions; it does not run N's main().
"""
from pathlib import Path, PurePosixPath
import hashlib
import importlib.util
import re
import sys

sys.dont_write_bytecode = True
N_SOURCE_SHA256 = '2bbda0f4d389aef369d1df1459d2e5d03ba9648121211619aa028b99a0990ac5'
SOURCE = Path(__file__).resolve().parent/'source_inputs/verify_current_authority_http.py'
assert SOURCE.resolve()==SOURCE and not SOURCE.is_symlink()
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==N_SOURCE_SHA256
spec = importlib.util.spec_from_file_location('uploader_public_native_admission_source', SOURCE)
native_source = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_source)
require = native_source.require
identity = native_source.identity
json_object = native_source.json_object
public_bytes = native_source.public_bytes
absolute_http_deadline = native_source.absolute_http_deadline
BASE_SOURCE = native_source.BASE_SOURCE
PATCH_SHA = native_source.PATCH_SHA
CANDIDATE_SHA = native_source.CANDIDATE_SHA
BASE_MANIFEST = native_source.BASE_MANIFEST
CANDIDATE = native_source.CANDIDATE
SDK_PREFIX = native_source.SDK_PREFIX
FRESH_FIXTURE = native_source.FRESH_FIXTURE
FRESH_FIXTURE_SHA = native_source.FRESH_FIXTURE_SHA
FRESH_METHODS = native_source.FRESH_METHODS
QUALIFICATION_PARENTS = native_source.QUALIFICATION_PARENTS
MIB = native_source.MIB

def admit(producer_receipt, producer_sha256, pin, source_inventory):
    producer_dir = producer_receipt.parent
    require(producer_dir.parent==native_source.ROOT and re.fullmatch(r'readguard-native[1-9][0-9]{0,2}', producer_dir.name), 'exact qualified native producer location')
    require(producer_receipt.name=='result.json' and re.fullmatch(r'[0-9a-f]{64}', producer_sha256), 'qualified native receipt identity')
    result = {}
    producer = json_object(pin(producer_receipt, producer_sha256))
    require(producer['protocol']=='pinkha-files-readguard-native-qualified-v1', 'future native producer protocol')
    require(producer['status']=='PASS_NATIVE_BUILD_AND_FRESH_FILES_OPEN2', 'full native producer not qualified')
    require(producer['baseSourceManifestSHA256']==BASE_SOURCE and producer['sdkReadguardPatchSHA256']==PATCH_SHA and producer['sdkReadguardCandidateSHA256']==CANDIDATE_SHA, 'exact production overlay composition')
    require(producer['commits']=={'any': '8fbd1e819fb132ac0e0a848d2ddf5c5714189b81', 'sdk': 'c1fd59bd8f0ed62471234ec1a65a402d22eab6a9'}, 'Any/SDK producer versions')
    require(producer['syncModule']=='github.com/anyproto/any-sync@v0.13.8' and producer['productionOverlayApplications']==1, 'single standalone SDK overlay')
    require(producer['allOwnedGroupsPositivelyAbsent'] is True and producer['buildExitCode']==0, 'actual native producer closure')
    require(producer['errors']==[] and producer['completionErrors']==[], 'producer retained errors')
    # Reconstruct the exact complete source union independently of the
    # future producer's manifest. A header naming the correct patch does
    # not admit extra changes or a binary built from a different SDK.
    base_files = json_object(pin(BASE_MANIFEST, BASE_SOURCE))['files']
    require(len(base_files)==1599, 'qualified Any source member count')
    draft = json_object(pin(CANDIDATE/'manifest.json', CANDIDATE_SHA))
    require(draft['baseCurrentSourceManifestSHA256']==BASE_SOURCE and draft['patch']['sha256']==PATCH_SHA, 'source candidate base')
    require(len(draft['paths'])==10 and draft['productionPaths']==7 and draft['testPaths']==3, 'seven production paths and three synthetic test paths')
    pin(CANDIDATE/'sdk-files-readguard.patch', PATCH_SHA)
    union = dict(base_files)
    sdk_base = {name.removeprefix(SDK_PREFIX): value for name, value in base_files.items() if name.startswith(SDK_PREFIX)}
    require(len(sdk_base)==718, 'qualified SDK source member count')
    for name, change in sorted(draft['paths'].items()):
        relative = PurePosixPath(name)
        require(str(relative)==name and not relative.is_absolute() and '..' not in relative.parts and name.startswith('internal/'), 'candidate source path')
        key = SDK_PREFIX+name
        require(union.get(key)==change['before'], 'candidate before-image differs')
        actual = identity(pin(CANDIDATE/name, change['after']['sha256']))
        require(actual==change['after'], 'candidate after-image differs')
        union[key] = actual
    sdk_guard = {name.removeprefix(SDK_PREFIX): value for name, value in union.items() if name.startswith(SDK_PREFIX)}
    require(len(union)==1606 and len(sdk_guard)==725, 'guard source composition')
    fixture = identity(pin(FRESH_FIXTURE, FRESH_FIXTURE_SHA))
    fixture_key = SDK_PREFIX+FRESH_FIXTURE.name
    require(fixture_key not in union and producer['freshFilesFixture']==fixture, 'one fresh synthetic fixture')
    union[fixture_key] = fixture
    sdk_fresh = {name.removeprefix(SDK_PREFIX): value for name, value in union.items() if name.startswith(SDK_PREFIX)}
    require(len(union)==1607 and len(sdk_fresh)==726, 'fresh test composition')
    for name, expected_status in [('synthetic21', 'PASS_SYNTHETIC_SIGNED_ACL_LIFETIME21_ONLY_NOT_NATIVE_ACCEPTANCE'), ('freshFilesOpen2', 'PASS_FRESH_SYNTHETIC_ACTUAL_FILES_OPEN2')]:
        reference = producer['qualifications'][name]
        qpath = Path(reference['path'])
        require(qpath.parent.parent==QUALIFICATION_PARENTS[name] and re.fullmatch(r'attempt[1-9][0-9]{0,2}', qpath.parent.name) and qpath.name=='result.json', 'fixed public qualification receipt location')
        value = json_object(pin(qpath, reference['sha256']))
        require(value['status']==expected_status and value['allOwnedGroupsPositivelyAbsent'], 'actual prerequisite receipt')
        require(value['errors']==[] and value['completionErrors']==[], 'prerequisite retained errors')
        if name=='synthetic21':
            admission = value['sourceAdmission']
            require(admission['baseManifestSHA256']==BASE_SOURCE and admission['candidateManifestSHA256']==CANDIDATE_SHA and admission['candidatePatchSHA256']==PATCH_SHA, 'synthetic qualification source binding')
            require(value['actualMethods']['totalRuns']==35 and value['actualMethods']['totalPasses']==35 and value['actualMethods']['skips']==0, 'all thirty-five signed unit events')
            qualified_manifest = json_object(pin(qpath.parent/'source-before.json', admission['sourceManifest']['sha256']))
            require(qualified_manifest==sdk_guard, 'actual synthetic source must equal this guard union')
        else:
            require(value['fixtureSource']==fixture and value['baseSourceManifestSHA256']==BASE_SOURCE and value['sdkReadguardCandidateSHA256']==CANDIDATE_SHA and value['sdkReadguardPatchSHA256']==PATCH_SHA, 'actual fresh SDK source binding')
            require(value['actualMethods']=={'names': sorted(FRESH_METHODS), 'totalRuns': 2, 'totalPasses': 2, 'skips': 0}, 'both actual Files.Open methods')
            require(value['retainedPrivateInputs']==0 and value['actualOSDenialVerified'] is True, 'fresh-only OS-isolated SDK qualification')
            qualified_manifest = json_object(pin(qpath.parent/'source-before.json', value['sourceManifestSHA256']))
            require(qualified_manifest==sdk_fresh, 'actual fresh SDK source must equal this producer subset')
    source = producer_dir/'source'
    manifest_path = producer_dir/'source-manifest.json'
    expected_source = json_object(pin(manifest_path, producer['sourceManifestSHA256']))['files']
    require(expected_source==union, 'native producer must contain exactly the qualified source union')
    source_inventory(source, expected_source)
    binary = producer_dir/'any'
    binary_identity = identity(pin(binary, producer['binarySHA256'], 128*MIB))
    require(producer['binaryBytes']==binary_identity['bytes'], 'native binary length')
    result['correctedNativeProducer'] = {'receiptSHA256': producer_sha256, 'binary': binary_identity,
        'sourceManifestSHA256': producer['sourceManifestSHA256'], 'sourceFiles': len(expected_source)}
    return {'producer': producer, 'binary': binary, 'source': source, 'expectedSource': expected_source,
            'qualification': result['correctedNativeProducer']}
