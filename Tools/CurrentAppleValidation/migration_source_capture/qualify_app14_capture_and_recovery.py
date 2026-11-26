"""Publish bounded source-capture and historical registry-recovery receipts.

Reads already completed, SHA-pinned originals only. It never runs an engine,
boots a device, restores an account, or changes any original acceptance result.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import tarfile

REPO = Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
PRIVATE = Path('/mnt/development/projects/evidence/migration-final-20261125/source-capture-app14/postboot-pass-originals')
RECOVERY = Path('/mnt/development/projects/evidence/c-source-asset-recovery-20261126/original-seven-descriptors-attempt1')
CAPTURE_STATUS = 'PASS_FRESH_ACTUAL_SOURCE_UI_TWO_CAPTURES_CLOSE_AND_NATIVE_BUNDLES'
PINS = {
    'evidence/execution.json': 'd2a636a7beee13fd119858c798f901be8f02e223895a48597bbe0571a934fb6b',
    'evidence/final-outcome.json': '357d6ecfd55b5d45fd88e93054b974d230678e0094de092b5a066514d4cddc91',
    'evidence/source-review/result.json': 'b3d4c2c0362adb8463f3984ba50dd0a98859b76a706ee1889a5ddb45276a36f9',
    'private/owned-account-originals/retention.json': 'ad5abe740d647ba0d00524f1b6658eeb41921d675c5300dbfffe92d4d9e896bc',
    'private/actual-ui-observation.json': '977a7eade8a57e9c25e8e1f1b6075632e8db482acf7a72357671b5e3ff3e4502',
    'evidence/source-review/private-attachments/C1040B49-19DF-4E64-A6B3-BF88E034E834.json': '9a5f36c16666350923c1dd9552366b80cb2b3a3f622c60f9f2ce301880b943d5',
}
def sha(data):
    return hashlib.sha256(data).hexdigest()
def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()
def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(data)
    return sha(data)
def main():
    archive = PRIVATE / 'app14-source-capture-originals.private.tar'
    assert file_sha(archive) == '46c2bbffa0dd9b1c74604b57056e5ae358d006c96cab32d926672e693f271d07'
    receiver = json.loads((PRIVATE / 'receipt.json').read_bytes())
    assert receiver['status'] == 'PASS_PRIVATE_ORIGINALS_VERIFIED'
    assert receiver['allKindsModesOwnersAndBytesMatch'] is True and receiver['entries'] == 1787
    assert receiver['originalExecutionSHA256'] == PINS['evidence/execution.json']
    assert file_sha(PRIVATE / 'source-index.json') == receiver['sourceIndexSHA256']
    with tarfile.open(archive, 'r:') as tar:
        names = tar.getnames()
        assert len(names) == len(set(names)) == 1787
        def raw(path, expected=None):
            member = tar.getmember(path)
            assert member.isfile() and not member.issym() and not member.islnk()
            value = tar.extractfile(member).read()
            if expected is not None:
                assert sha(value) == expected, path
            return value
        originals = {path: raw(path, expected) for path, expected in PINS.items()}
        execution = json.loads(originals['evidence/execution.json'])
        final = json.loads(originals['evidence/final-outcome.json'])
        ui = json.loads(originals['private/actual-ui-observation.json'])
        assert ui == json.loads(originals['evidence/source-review/private-attachments/C1040B49-19DF-4E64-A6B3-BF88E034E834.json'])
        retention = json.loads(originals['private/owned-account-originals/retention.json'])
        assert execution['status'] == final['status'] == CAPTURE_STATUS
        assert final['executionSHA256'] == PINS['evidence/execution.json']
        assert execution['coreSHA256'] == '59a9d5627bf0f2144d1d4f73d044c8e2b0b5156cd2c2f2e580be5667f62605de'
        assert execution['admissionSHA256'] == 'e3871c16ccaa3147d90c1c3061690cca2551a54ff8b3c81583196720abaace9e'
        assert execution['sourceCommit'] == execution['uiSourceCommit'] == '76f59f1e838991d1bbc7a07ecd08c6a2f15915c7'
        assert execution['originalCUIFileSHA256'] == 'd8296d08ce03c4756c43e821116f244d4b26c26988134c8457f8dc4c55f6f03d'
        assert execution['controllerSHA256'] == 'a062d5311be3c7348bbcb518e935ef20c79a886d7cd8679cfb8202d275904c91'
        assert execution['sameSourceAppAndUI'] is True
        assert execution['distinctCaptureRequests'] == execution['closedReviews'] == 2
        assert execution['factoryMethodsExecuted'] == 1 and execution['originalMethodsReplayed'] == 0
        assert execution['fullEAcceptance'] is False and execution['wholeSpaceMigration'] is False
        assert execution['cleanup']['status'] == 'PASS' and not execution['cleanup']['errors']
        assert len(execution['cleanup']['groups']) == 29
        assert all(g['absentAtOriginalExit'] is True and g['historicalGroupReprobed'] is False
                   for g in execution['cleanup']['groups'])
        assert execution['cleanup']['ownedSimulatorDeleted'] is False
        assert execution['originalAppInstallation']['installsExecuted'] == 0
        assert execution['priorFixtureDeadlineExtended'] is False
        assert ui['protocol'] == 'pinkha-heart-source-capture-ui-v1' and ui['status'] == 'UI_PASS'
        assert ui['closeCompletions'] == 2 and len(ui['captures']) == 2
        assert ui['fixtureSHA256'] == execution['fixtureSHA256']
        assert ui['deadlineEpoch'] == execution['originalFixtureDeadlineEpoch']
        assert ui['freshStartupNavigationRequested'] is True and ui['freshStartupNavigationCompleted'] is True
        assert len({c['captureID'] for c in ui['captures']}) == 2
        bundles = execution['nativeBundles']
        assert len(bundles) == 2 and len({b['manifestSHA256'] for b in bundles}) == 2
        assert len({b['sourceWitnessSHA256'] for b in bundles}) == 1
        by_manifest = {b['manifestSHA256']: b for b in bundles}
        for capture in ui['captures']:
            native = by_manifest[capture['manifestSHA256']]
            assert sha(capture['accountID'].encode()) == native['accountSHA256']
            assert sha(capture['spaceID'].encode()) == native['spaceSHA256']
            assert all(capture['counts'][key] == value for key, value in native['counts'].items())
            assert native['destinationAdmission'] is False
            assert native['verifiedMembers'] == 335 and native['verifiedBytes'] == 1364413
        assert bundles[0]['counts'] == bundles[1]['counts'] == {
            'blocks':625,'files':0,'nativeHeads':161,'objects':158,
            'options':0,'properties':125,'trees':159,'types':24}
        stage_rows = []
        for name, stage in execution['stages'].items():
            assert name in ('preparation','source-review')
            assert stage['status'] == 'PASS' and stage['testInvoked'] is True and not stage['errors']
            assert stage['actual']['counts'] == {
                'failedTests':0,'passedTests':1,'skippedTests':0,'totalTestCount':1}
            assert stage['actual']['rawNamedLogVerified'] is True
            assert stage['actual']['selector'] == stage['selector']
            assert stage['command']['exitCode'] == 0 and stage['command']['ownedGroupPresentAfterExit'] is False
            log_path = 'commands/' + name + '-test/original.log'
            log = raw(log_path, stage['command']['logSHA256']).decode('utf-8')
            method = stage['selector'].split('/')[-1]
            passed_lines = [line.strip() for line in log.splitlines()
                            if method in line and 'passed (' in line]
            assert len(passed_lines) == 1, (name, passed_lines)
            assert re.search(r'Executed 1 test, with 0 failures', log)
            enabled = stage['enumeration']['enabledTests']
            assert enabled == [stage['selector']+'()']
            stage_rows.append({
                'stage':name,'selector':stage['selector'],
                'status':'PASS','counts':stage['actual']['counts'],
                'originalCommandExitCode':0,'ownedGroupPresentAfterExit':False,
                'originalLogSHA256':stage['command']['logSHA256'],
                'originalLogBytes':stage['command']['logBytes'],
                'originalPassedLine':passed_lines[0],
                'originalCommandResultSHA256':sha(raw('commands/'+name+'-test/result.json')),
                'originalStageResultSHA256':sha(raw('evidence/'+name+'/result.json')),
            })
        assert {s['stage'] for s in stage_rows} == {'preparation','source-review'}
        output = REPO / 'docs/validation/20261126-app14-fresh-source-capture/native-acceptance'
        output.mkdir(parents=True, exist_ok=False)
        qualification = {
            'protocol':'pinkha-app14-source-capture-public-qualification-v1',
            'status':CAPTURE_STATUS,
            'originalPins':PINS,
            'controllerSHA256':execution['controllerSHA256'],
            'captureHelperSHA256':execution['captureHelperSHA256'],
            'commonAdmissionSHA256':execution['coreSHA256'],
            'app14AdmissionSHA256':execution['admissionSHA256'],
            'sourceCommit':execution['sourceCommit'],
            'originalCUIFileSHA256':execution['originalCUIFileSHA256'],
            'sourceAdmission':execution['sourceAdmission'],
            'sameSourceAppAndUI':True,'stages':stage_rows,
            'distinctNativeCaptures':2,'closedReviews':2,
            'nativeBundles':bundles,
            'uiNativeIdentityAndCountComparison':True,
            'originalFixtureSHA256':execution['fixtureSHA256'],
            'originalFixtureDeadlineEpoch':execution['originalFixtureDeadlineEpoch'],
            'fixtureDeadlineExtended':False,
            'uiReportedSemanticBlockers':{
                key:ui['captures'][0]['counts'][key]
                for key in ('definition-issues','page-plans','unmapped')},
            'ownedSimulator':execution['ownedSimulator'],
            'ownedSimulatorState':'Shutdown',
            'ownedSimulatorDeleted':False,
            'ownedCommandGroupsAbsent':29,
            'historicalAbsentGroupsReprobed':False,
            'fourScopeRetentionSHA256':PINS['private/owned-account-originals/retention.json'],
            'fourScopeRetentionStatus':retention['status'],
            'offhostOriginals':receiver,
            'nativeBuilds':0,'appBuilds':0,'uiBuilds':0,'installsInThisContinuation':0,
            'fullEAcceptance':False,'destinationAdmission':False,
            'filePayloadAcceptance':False,'wholeSpaceMigration':False,
            'historical156Replaced':False,
            'priorFailuresRetained':[
                {'executionSHA256':'955d9fd4fb398a2d09649bc8db28affc095ace4ff3c30a0cb096c6be0f6501c6',
                 'actualMethods':0,'status':'FAIL','cause':'Original enumeration timeout and EPERM'},
                {'executionSHA256':'4e9b7a5db210f04c015d111b6793cd44136c1e076e1887ffec4bf91c6890a3d2',
                 'actualMethods':0,'status':'FAIL','cause':'App container lookup while owned simulator was Shutdown'},
            ],
            'collectorNativeCalls':0,
        }
        result_sha = write(output/'qualification.json',qualification)
        write(output/'offhost-retention.json',receiver)
        (output/'README.md').write_text(
            '# Actual App14 source capture\n\n'
            'The original preparation method and the original C source-review method each passed once '
            'on the same owned iOS 27 simulator. The C method completed two distinct native captures '
            'and two closes. Its UI identities, fingerprints and counts matched two independently '
            'verified native bundles. The original C assertions were unchanged.\n\n'
            'Each fresh bundle contains 158 objects, 159 trees, 161 native heads, 625 blocks, '
            '125 properties and 24 types. Both contain zero files. The review still displays '
            'semantic blockers; destination writes and whole-space migration remain unqualified. '
            'The historical 156-object capture remains the separate original migration obligation.\n\n'
            'The two earlier zero-method infrastructure failures remain failed. The successful '
            'continuation reused the exact retained simulator and installed App, performed no '
            'install/build/restore, and kept the newly created fixture\'s original two-hour deadline. '
            'All 29 owned command groups were absent and the device was shut down.\n\n'
            'Complete original command logs, xcresults, UI attachments, native bundles and the '
            'four-scope account backup are retained privately in the independently verified '
            '1,787-entry offhost archive. This public receipt contains hashes and bounded projections; '
            'it does not publish source content, account recovery material or raw identifiers.\n')
    assert file_sha(RECOVERY/'receipt.json') == 'b4561fa708141c463fce941ba4e266e42d12760d81cc63524d1cb96766ad7eb6'
    recovery = json.loads((RECOVERY/'receipt.json').read_bytes())
    assert recovery['status'] == 'PASS_RECOVERED_ORIGINAL_SEVEN_DESCRIPTORS_NOT_CAPTURED_MEMBERS'
    assert recovery['original59826SourceFilesUnchanged'] is True
    assert recovery['originalCompiledWireAndFullDecodedModelEqual'] is True
    assert recovery['compiledInputFiles'] == 1982 and recovery['accountOrSpaceCalls'] == 0
    assert recovery['destinationWrites'] is False and recovery['originalCapturedMembersReplaced'] is False
    export_raw = (RECOVERY/'descriptors/export.json').read_bytes()
    assert sha(export_raw) == recovery['exportManifestSHA256'] == '50458de19c0c9c8ae0bfc1b9cca1b6c5e29fbcf53d63bf32c5caabd0a3358ebb'
    export = json.loads(export_raw)
    assert len(export['Descriptors']) == 7 and export['OriginalCapturedMember'] is False
    recovered = REPO/'docs/validation/20261126-original-source-compiled-definitions/actual-original-go-export'
    recovered.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(RECOVERY/'receipt.json',recovered/'receipt.json')
    shutil.copyfile(RECOVERY/'compiled-inputs.json',recovered/'compiled-inputs.json')
    assert file_sha(recovered/'compiled-inputs.json') == recovery['compiledInputsSHA256']
    (recovered/'descriptors').mkdir()
    (recovered/'descriptors/export.json').write_bytes(export_raw)
    descriptor_summary=[]
    for row in export['Descriptors']:
        for kind in ('Protobuf','JSONView'):
            member=row[kind]; path=member['Path']
            assert re.fullmatch('[0-9a-f]{64}\\.(pb|json)',path)
            data=(RECOVERY/'descriptors'/path).read_bytes()
            assert len(data)==member['Bytes'] and sha(data)==member['SHA256']
            (recovered/'descriptors'/path).write_bytes(data)
        view=json.loads((RECOVERY/'descriptors'/row['JSONView']['Path']).read_bytes())
        descriptor_summary.append({'id':row['Kind']+':'+row['Key'],'definition':view['Definition'],
                                   'protobufSHA256':row['Protobuf']['SHA256'],
                                   'jsonViewSHA256':row['JSONView']['SHA256']})
    write(recovered/'definition-summary.json',descriptor_summary)
    for label in ('original-go-version','actual-dependencies','build-registry-exporter','export-seven'):
        shutil.copyfile(RECOVERY/(label+'-result.json'),recovered/(label+'-result.json'))
    (recovered/'README.md').write_text(
        '# Original compiled-definition recovery\n\n'
        'The exact original source archive and all 59,826 manifest members were recovered. '
        'A pure registry/codecs exporter compiled with the recovered original Go 1.26.5 toolchain '
        'and 1,982 original-manifest-bound inputs. It called the actual original bundle.GetRelation '
        'for the seven declared missing keys and preserved the first ordinary gogo protobuf wire '
        'bytes. Wire decoding and JSON decoding both equaled the complete original registry models; '
        'all original source bytes remained unchanged.\n\n'
        'These are separately recovered compiled descriptors. They were not members of the '
        'historical capture, and the original capture has not been rewritten. The original '
        'producer\'s broader failed status is preserved. No account, space or native engine '
        'was opened and no destination write occurred. Explicit recovered-source admission '
        'and full historical migration still require separate qualification.\n')
    print(json.dumps({'captureQualificationSHA256':result_sha,
                      'capture':str(output),'recoveredDefinitions':str(recovered),
                      'recoveryReceiptSHA256':file_sha(recovered/'receipt.json')},sort_keys=True))
if __name__=='__main__':
    main()
