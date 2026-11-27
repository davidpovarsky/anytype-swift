"""Current compiled products and retained T5 fixture are separate authorities."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import stat

FIXTURE_SOURCE = '379ca3568f247d2fc218ed63df24796d461713c0'
NATIVE_MANIFEST = '8ac407e75a4bfb42c359a2f72b3822c44990caedf2351d00d78315de5c96a04b'
NATIVE_BINARY = 'f94079de9eeb9e2e869f02bd1dda93fcd272e3191b2417ca4b4657cae5dc6763'
UI_SOURCE_PATH = 'PinkhaStage1Acceptance/Tests/PinkhaT5NativeAcceptanceUITests.swift'
UI_SOURCE_SHA256 = '698f4ed7f1f81fe567b94b531f43e14259d08e6acbf79d72e132a5b9b6b941a7'
ADMISSION_MODULE_SHA256 = 'e56571d5f367f207d5ca586dfaa0cb35028abe1a29d67e8680c79c33eb3d1c49'
ACTUAL_PREVIOUS = Path('/Users/m1/development/anytype-root-active-20261125/app15-t5-retained-core-r08-fa4b3ff-20261127-02')
PREVIOUS_EXECUTION_SHA256 = '2062159a6a9b2d9c6646bfa68cefc36b1fb44167001e32ebf91dab7f11e748ad'
PREVIOUS_RESULT_SHA256 = 'f3f9922fad3f593c950582d3d3c57653dfe051fb5e98dbafc3b00f932eb74f93'
PREVIOUS_SUMMARY_SHA256 = '5001562de3c2c1d2cc803a84e2e5afbdac05efc73ae7103ca7074cdcef4ef13b'
PREPARATION_SOURCE = Path('/Users/m1/development/anytype-d-active-20261125/main16-wave2-20261127/retained-App15/source')

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def json_pin(path, expected):
    path = Path(path)
    require(path.is_absolute() and path.resolve(strict=True) == path and path.is_file()
            and path.stat().st_size < 64 * 1024**2 and digest(path) == expected,
            'Original pinned JSON changed: ' + str(path))
    return json.loads(path.read_bytes())

def admit_original_failure(identity, udid):
    """Preserve the sole actual old-product failure, distinct from old preflight."""
    execution = json_pin(ACTUAL_PREVIOUS / 'evidence/execution.json', PREVIOUS_EXECUTION_SHA256)
    stage = ACTUAL_PREVIOUS / 'evidence/lanes/t5-native-ui-continuation/core-ui'
    failure = json_pin(stage / 'result.json', PREVIOUS_RESULT_SHA256)
    json_pin(stage / 'summary.json', PREVIOUS_SUMMARY_SHA256)
    require(execution['status'] == failure['status'] == 'FAIL' and failure['testInvoked'] is True
            and execution['sourceCommit'] == FIXTURE_SOURCE and execution['simulatorUDID'] == udid,
            'Expected original App15 actual core2 failure is absent')
    require(execution.get('fixtureIdentityBefore') == execution.get('fixtureIdentityAfter') == identity
            and 'originalCoreReceipts' not in execution and 'r08' not in execution,
            'Original failed run must not contain a successful Note witness or R08 invocation')
    require(execution['ownedSimulator'] == {'udid': udid, 'deleted': False,
            'status': 'SHUTDOWN_ACCOUNT_RETAINED'}, 'Original failed account was not retained')
    return {'root': str(ACTUAL_PREVIOUS), 'executionSHA256': PREVIOUS_EXECUTION_SHA256,
            'coreResultSHA256': PREVIOUS_RESULT_SHA256, 'summarySHA256': PREVIOUS_SUMMARY_SHA256,
            'actualCoreMethods': 2, 'passed': 0, 'failed': 2, 'r08': 'NOT_RUN',
            'sourceCommit': FIXTURE_SOURCE, 'originalsUnmodified': True}

def compiled_origin(contract, proof):
    commit = contract['source']['commit']
    receipt = contract['build']['receipt']['sha256']
    inputs = proof['inputs']
    require(re.fullmatch(r'[a-f0-9]{40}', commit) is not None and commit != FIXTURE_SOURCE
            and re.fullmatch(r'[a-f0-9]{64}', receipt) is not None,
            'A distinct exact new compiled App/UI source and build receipt are required')
    require(inputs['nativeSourceManifestSHA256'] == NATIVE_MANIFEST
            and inputs['nativeSHA256'] == NATIVE_BINARY,
            'The retained account requires its unchanged original native source and binary')
    return {'compiledAppAndUISourceSHA': commit, 'buildReceiptSHA256': receipt,
            'nativeSourceManifestSHA256': NATIVE_MANIFEST,
            'fixturePreparationAppSourceSHA': FIXTURE_SOURCE,
            'acceptanceScope': 'current-product-with-retained-fixture-preparation'}

def verify_ui_origin(receipts, origin, fixture):
    require(isinstance(receipts, list) and receipts, 'Actual selected UI receipts required')
    for receipt in receipts:
        require(receipt.get('currentCompiledBuild') == origin,
                'Actual UI receipt omitted or changed its current compiled origin')
        require(all(receipt.get(key) == fixture[key] for key in ('token', 'appSourceSHA', 'runID', 'spaceID'))
                and receipt['appSourceSHA'] == FIXTURE_SOURCE,
                'Current UI receipt rewrote the original preparation fixture binding')
    return {'status': 'PASS_BOTH_CURRENT_COMPILED_AND_ORIGINAL_PREPARATION_ORIGINS',
            'receiptCount': len(receipts), 'currentCompiledBuild': origin}

def admit_build(path, expected_sha256):
    contract = json_pin(path, expected_sha256)
    root = Path(contract['controls']['root'])
    module_path = root / 'Tools/MiniApps/receipt_admission.py'
    require(root.is_absolute() and root.resolve(strict=True) == root
            and module_path.resolve(strict=True) == module_path
            and digest(module_path) == ADMISSION_MODULE_SHA256,
            'The exact independently reviewed e2e7 build admission module is required')
    spec = importlib.util.spec_from_file_location('pinkha_current_t5_product_admission', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    contract, proof, products = module.admit(path, expected_sha256)
    require(proof['status'] == 'ADMITTED_ORIGINAL_BUILD_NOT_APPLICATION_ACCEPTANCE'
            and proof['testMethodsExecuted'] == 0, 'Product admission cannot grant test acceptance')
    ui_source = Path(contract['source']['root']) / UI_SOURCE_PATH
    require(digest(ui_source) == UI_SOURCE_SHA256,
            'The compiled T5 source must contain the reviewed warning and dual-origin receipt')
    origin = compiled_origin(contract, proof)
    # The original module lists prospective MiniApps methods. Preserve its proof
    # verbatim; those methods are neither T5 selections nor executed test credit.
    return contract, proof, products, origin

def product_selection(descriptor, kind):
    value = plistlib.loads(Path(descriptor).read_bytes())
    if kind == 'app':
        require(value.get('__xctestrun_metadata__', {}).get('FormatVersion') == 2,
                'Native test descriptor format changed')
        configs = value.get('TestConfigurations')
        require(isinstance(configs, list) and len(configs) == 1, 'One original native configuration required')
        matches = [row for row in configs[0]['TestTargets'] if row.get('BlueprintName') == 'AnytypeTests']
        require(len(matches) == 1, 'One original AnytypeTests blueprint required')
        target = matches[0]
    else:
        require(kind == 'ui' and set(value) == {'__xctestrun_metadata__', 'PinkhaStage1AcceptanceUITests'},
                'One original complete UI blueprint required')
        target = value['PinkhaStage1AcceptanceUITests']
    selection = target.get('OnlyTestIdentifiers', [])
    require(isinstance(selection, list) and all(isinstance(item, str) and item for item in selection)
            and len(selection) == len(set(selection)), 'Original selector inventory is invalid')
    return selection

def clone_products(contract, products, root, evidence, commands, shared):
    require(root.resolve() == root and stat.S_IMODE(root.lstat().st_mode) == 0o700,
            'Private owned product clone root required')
    built = {}
    for kind in ('app', 'ui'):
        producer = products[kind + '-derived']
        original = Path(producer['base'])
        before = shared.inventory(original)
        files = {name: {k: v for k, v in row.items() if k != 'mode'}
                 for name, row in before.items() if row['kind'] != 'directory'}
        expected = {row['path']: {k: v for k, v in row.items() if k != 'path'}
                    for row in producer['entries']}
        require(files == expected, 'Current original complete product inventory changed')
        destination = root / (kind + '-products')
        mask = os.umask(0)
        try:
            commands.run(['cp', '-cR', str(original), str(destination)], 'clone-current-' + kind + '-products', 180)
        finally:
            os.umask(mask)
        require(shared.inventory(destination) == before and shared.inventory(original) == before,
                'APFS product clone or original bytes/modes/links changed')
        relative = contract['descriptors'][kind]['path']
        descriptor = destination / relative
        require(descriptor.parent == destination and descriptor.suffix == '.xctestrun'
                and before[relative]['kind'] == 'file' and digest(descriptor) == before[relative]['sha256'],
                'Exact original descriptor must remain at the product root')
        built[kind] = {'products': destination, 'inventory': before, 'copies': {},
                       'descriptor': descriptor, 'originalSelection': product_selection(descriptor, kind)}
        shared.write(evidence / (kind + '-current-original-products.json'), before)
    app = built['app']['products'] / 'Debug-Anytype-iphonesimulator/Anytype.app'
    require(plistlib.loads((app / 'Info.plist').read_bytes())['CFBundleIdentifier'] == shared.BUNDLE,
            'Current App bundle differs from the retained account app')
    return built, app
