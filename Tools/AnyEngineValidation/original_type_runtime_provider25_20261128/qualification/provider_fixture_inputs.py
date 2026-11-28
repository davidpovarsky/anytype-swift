"""Copy exact captured definition bytes into this component owner's fixture root.

This reads the retained source bundle and three immutable mapping documents.
It opens no native account, database, archive, key, session, or network route.
The original bundle-index admission is reused byte-for-byte, without its main.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat

HERE = Path(__file__).absolute().parent
BUNDLE_HELPER = HERE/'bundle_recovery_inputs.py'
BUNDLE_HELPER_SHA = 'f7b8155be19a890cd7e7351c22ca46c4d337ca9b1052bc7b4c80be84abb4c3e4'
C3_RECEIPT = Path('/var/lib/pinkha-w1-functional-migration-20261127/source-facts-components-attempt2/result.json')
C3_SHA = '437fab26265b371180016caae6fc87c72a9b471deecc70d6d99b92309d51959f'
BASELINE = HERE/'compiled-source-313.json'
BASELINE_SHA = 'ca0dd9bb060b738c71bf6d84b992a09b7cb4c5c3182e6a7234cb690e6b9a9eaa'
RETAINED = Path('/var/lib/pinkha-c-native-preservation-20261126/linux-resume-attempt1/private-work')
RETAINED_FILES = {
    'source-preservation-plan.json':'4a61914d5dbd3ccb4874f81444e4d0770c9e7e2dfe4259b8b93f15796accb930',
    'execute-mappings.json':'eabdf2e362189abd5a2e78f7c13f1f1d77d8339c27109d2a6ec19ccdbb2755a3',
    'execute-verification.json':'fee4dc5cb8e689e01bf2d1fbe8bd262c42388fd706da4114be72af3e6cf97350',
}


def source_names(folder):
    assert folder.resolve()==folder and not folder.is_symlink()
    fd = os.open(folder, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME|os.O_CLOEXEC)
    try:
        return set(os.listdir(fd))
    finally:
        os.close(fd)


def qualify(root, base, guard, original_sink, copy_sink):
    immutable, copies, original_modes = {}, {}, {}

    def keep(path, wanted=None):
        guard()
        actual = base.row(path)
        if wanted is not None:
            assert actual['sha256']==wanted, 'exact retained fixture provenance'
        immutable[str(path)] = actual
        original_sink[str(path)] = actual
        original_modes[str(path)] = stat.S_IMODE(path.lstat().st_mode)
        return actual

    keep(BUNDLE_HELPER, BUNDLE_HELPER_SHA)
    raw = base.read(BUNDLE_HELPER, 65536)
    namespace = {'__file__':str(BUNDLE_HELPER), '__name__':'provider_original_bundle_inputs'}
    exec(compile(raw, str(BUNDLE_HELPER), 'exec'), namespace)
    selected = namespace['admitted_members']()
    assert len(selected)==314 and sum(row['bytes'] for row in selected.values())==1526976
    for path, wanted in [(namespace['INDEX'],namespace['INDEX_SHA']),
                         (namespace['AUDIT'],namespace['AUDIT_SHA']),
                         (namespace['READBACK'],namespace['READBACK_SHA'])]:
        keep(path, wanted)
    keep(C3_RECEIPT, C3_SHA)
    c3 = json.loads(base.read(C3_RECEIPT, 65536))
    assert c3['status']=='PASS' and c3['exitCode']==0 and c3['ownedGroupAbsent'] and not c3['errors']
    assert c3['sourceBeforeSHA256']==c3['sourceAfterSHA256']==c3['preparedSwiftSourceClosureSHA256']==BASELINE_SHA
    assert c3['sourceUnchanged'] and not c3['cleanupRequired'] and not c3['cleanupForcedKill']
    keep(BASELINE, BASELINE_SHA)
    baseline = json.loads(base.read(BASELINE, 131072))
    assert len(baseline)==313 and all(len(value)==64 for value in baseline.values())
    source_bundle = namespace['DESTINATION']
    assert source_names(source_bundle)==set(selected), 'complete original bundle membership'
    root.mkdir(mode=0o700)
    os.chmod(root,0o700)
    retained = root/'retained'
    original = root/'original156'
    for directory in (retained, original, original/'bundle'):
        directory.mkdir(mode=0o700)
        os.chmod(directory,0o700)
    for name, wanted in sorted(RETAINED_FILES.items()):
        source = RETAINED/name
        expected = keep(source,wanted)
        assert c3['sourceDefinitionsBefore'][name]==c3['sourceDefinitionsAfter'][name]==wanted
        target = retained/name
        copy_sink[str(target)] = expected
        base.copy_exact(source,target,expected)
        copies[str(target)] = expected
    for name, expected in sorted(selected.items()):
        source = source_bundle/name
        assert keep(source)==expected, 'original source byte identity'
        target = original/'bundle'/name
        copy_sink[str(target)] = expected
        base.copy_exact(source,target,expected)
        copies[str(target)] = expected
    assert source_names(original/'bundle')==set(selected)
    assert len(copies)==317
    receipt = {'status':'EXACT_ORIGINAL_FIXTURE_BYTES_COPIED_ONLY',
        'originalBundleMembers':314, 'retainedMappingDocuments':3,
        'originalSourceOrAccountWrites':0, 'nativeAccountsOpened':0,
        'originalHistoryDecrypted':False, 'original182OperationsReplayed':0,
        'immutableInputs':immutable, 'originalModes':original_modes, 'isolatedCopies':copies}
    base.save(root/'custody.json', receipt)
    copies[str(root/'custody.json')] = base.row(root/'custody.json')
    copy_sink[str(root/'custody.json')] = copies[str(root/'custody.json')]
    return {'receipt':dict(path=str(root/'custody.json'),**copies[str(root/'custody.json')]),
            'immutableInputs':immutable,'copiedInputs':copies,'originalModes':original_modes,
            'bundleSource':str(source_bundle),'bundleNames':sorted(selected),
            'retainedDirectory':str(retained),'originalDirectory':str(original)}


def validate_after(admission, base, guard):
    assert source_names(Path(admission['bundleSource']))==set(admission['bundleNames'])
    for path, expected in admission['immutableInputs'].items():
        guard()
        assert base.row(Path(path))==expected
        assert stat.S_IMODE(Path(path).lstat().st_mode)==admission['originalModes'][path]
    for path, expected in admission['copiedInputs'].items():
        guard()
        assert base.row(Path(path))==expected
