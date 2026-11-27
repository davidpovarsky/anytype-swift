#!/usr/bin/env python3
"""Read-only original 99dc qualification after exact failed-custody recovery.

Run as the original ubuntu/chatgpt-agent user. This imports the exact original
controller and invokes only pinned_inputs, never its main, preparer or Swift.
Ordinary original input reads may advance atime AFTER the immutable completed
custody boundary. No cache-warmness or component execution claim is made.
"""
from pathlib import Path
import datetime
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import time

OUT=Path('/mnt/development/projects/evidence/pinkha-wave2-component-cache-preserved-20261127')
SHARED=Path('/var/lib/pinkha-wave2-native-block-menu-20261127')
PROPERTY=Path('/var/lib/pinkha-wave2-property-lifecycle-20261127')
CLAIM=OUT.parent/'.pinkha-wave2-component-cache-custody-active.json'
RECOVERY=OUT/'recovery1'
CUSTODY_SHA='1204322b44c6f29a9fe08a2009460e5f596349267b8c3ae67ad62725ee59ad51'
FAILED_CUSTODY_SHA='3f34a5660153431980012d1bd6f88c27727eb62e2067ada4e47426ace618210b'
ORIGINAL_CUSTODY_SHA='897cb0a96f82d9fe079059088e847c0fe81ab32fe8ea483f4f9d0aced3acd5b9'
ORIGINAL_CLAIM_SHA='61a99b41950f9975b630cde3c82ebc68399ebff15a295c2e416ad78551accccc'
ORIGINAL_SHA='99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2'
HANDOFF_SHA='493a7d628bdce5642f54b3b3f99deedfe24b28f6d8e68267c18c7629f227367b'
SCOPES=('build','cache','clang-module-cache')
HEADS={'TorahInspectorKit':'9058b489e9acc271b4f8ef69e2ed24648f93b4ed',
       'swift-asn1':'97fd57437fc94cfa6b62f2b8f84c50f433534e17',
       'swift-crypto':'e8d6eba1fef23ae5b359c46b03f7d94be2f41fed'}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pinned(path,want):
    assert path.is_file() and not path.is_symlink()
    raw=path.read_bytes();assert sha(raw)==want,str(path)
    return raw


def aliases(copied):
    result={}
    for name in SCOPES:
        original=SHARED/name;target=OUT/'retained'/name
        assert original.is_symlink() and os.readlink(original)==str(target)
        assert original.resolve(strict=True)==target and target.resolve(strict=True)==target
        actual=target.stat();expected=copied[name]['.']
        assert stat.S_ISDIR(actual.st_mode)
        for key,value in {'device':actual.st_dev,'inode':actual.st_ino,
                          'uid':actual.st_uid,'gid':actual.st_gid,
                          'mode':stat.S_IMODE(actual.st_mode)}.items():assert expected[key]==value,(name,key)
        link=original.lstat()
        result[name]={'original':str(original),'actualPhysicalRoot':str(target),
            'linkDevice':link.st_dev,'linkInode':link.st_ino,'linkMtimeNS':link.st_mtime_ns,
            'device':actual.st_dev,'inode':actual.st_ino,'mode':stat.S_IMODE(actual.st_mode),
            'uid':actual.st_uid,'gid':actual.st_gid}
    return result


def main():
    assert not sys.flags.optimize and os.uname().nodename=='torah-social'
    assert os.geteuid()==1001 and os.getegid()==1002,'original compiler identity required'
    assert len(sys.argv)==2 and re.fullmatch('[0-9a-f]{64}',sys.argv[1]),'exact actual custody receipt SHA required'
    assert SHARED.resolve()==SHARED and (SHARED/'component').resolve()==SHARED/'component'
    assert (SHARED/'attempt1').resolve()==SHARED/'attempt1'
    assert not os.path.lexists(CLAIM) and not os.path.lexists(RECOVERY/'active-recovery.json'),'unresolved preservation/recovery claim'
    evidence=RECOVERY/'source-qualification1';assert evidence.resolve()==evidence and not evidence.is_symlink()
    receipt_path=evidence/'receipt.json'
    fd=os.open(receipt_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    began=time.monotonic()
    receipt={'schema':'pinkha-component-cache-source-location-qualification-v1','status':'FAIL',
        'startedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'controllerSHA256':sha(Path(__file__).read_bytes()),'errors':[],
        'compilerInvocations':0,'nativeInvocations':0,'testInvocations':0,
        'preparationInvocations':0,'historicalProcessGroupReprobed':False,
        'compilerWarmness':'UNPROVEN','compilerAdmission':'NOT_PERFORMED',
        'ordinaryReadAtimePhase':'AFTER_COMPLETED_IMMUTABLE_CUSTODY'}
    try:
        raw=pinned(RECOVERY/'result.json',sys.argv[1]);custody=json.loads(raw)
        assert custody['protocol']=='pinkha-exact-failed-component-cache-custody-continuation-v1'
        assert custody['status']=='PASS_EXACT_THREE_CACHE_CUSTODY_RECOVERED_ORIGINAL_FAILURE_RETAINED_NO_COMPILER_ACCEPTANCE'
        assert custody['controllerSHA256']==CUSTODY_SHA and custody['phase']=='completed'
        assert custody['originalControllerSHA256']==ORIGINAL_CUSTODY_SHA
        assert custody['originalFailedReceiptSHA256']==FAILED_CUSTODY_SHA
        assert custody['originalClaimSHA256']==ORIGINAL_CLAIM_SHA
        assert custody['originalFailureRetained'] is True and custody['originalFailureOverwritten'] is False
        assert custody['protectedOriginalInputsUnchanged'] is True and custody['originalSourceMetadataRepaired'] is False
        assert custody['observedExternalAtimeCounts']=={'build':1012,'cache':33,'clang-module-cache':3}
        assert custody['copiedBytes']==0 and custody['recoveredRootAllocatedBytes']==401940480
        assert custody['token']=='42c71f7f1a754e0da0ac5033fce320bf'
        assert {r['name'] for r in custody['retiredDuplicates']}==set(SCOPES) and len(custody['retiredDuplicates'])==3
        assert custody['originalInputPins']=={
            'result.json':FAILED_CUSTODY_SHA,
            'restoration-map.json':'95d9488413158c0da62338e277eeca0a0333f740ea8e3375219a214b8fa0c880',
            'protected-files-before.json':'0fff4d81264fbd2d7c9f566dd57fd750f4ea97cec70340b7df19071565bb4180',
            'private-protected-trees-before.json':'ca219c922e1aec624df2a4c17185f8f9f74530d585bbf91b119e7d808c773c49',
            'private-source-manifests.json':'f0a895e98d7693a264486867f613447fb7fae5c5b2183b58eb1090912fff9a98',
            'private-copied-manifests.json':'437ec66425f021dedf51eb4d52ede0a098fd96ba6aea27006af19ab944910c0b'}
        claim=json.loads(pinned(RECOVERY/'original-active-claim.json',ORIGINAL_CLAIM_SHA))
        assert claim['controllerSHA256']==ORIGINAL_CUSTODY_SHA and claim['token']==custody['token']
        copied=json.loads(pinned(RECOVERY/'private-final-manifests.json',custody['finalManifestsSHA256']))
        assert set(copied)==set(SCOPES) and sum(len(rows) for rows in copied.values())==6315
        before=aliases(copied)
        handoff_raw=pinned(SHARED/'attempt1/cache-handoff.json',HANDOFF_SHA)
        handoff=json.loads(handoff_raw)
        assert handoff['compilerUser']=='ubuntu' and handoff['compilerGroup']=='chatgpt-agent'
        assert handoff['nextOwner']=='wave2-root-properties' and handoff['noOwnedProcessGroupRemains'] is True
        runner=PROPERTY/'inputs/run_component.py';pinned(runner,ORIGINAL_SHA)
        sys.dont_write_bytecode=True
        spec=importlib.util.spec_from_file_location('unchanged_property_component_99dc',runner)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        assert module.HANDOFF_SHA==HANDOFF_SHA and module.SHARED==SHARED
        proof=module.pinned_inputs(handoff)
        assert proof['dependencySourceFiles']==370 and proof['exactDependencyPhysicalSetsVerified']
        checkout_rows=proof['checkoutClosures']
        assert len(checkout_rows)==3 and sorted(row['files'] for row in checkout_rows)==[135,211,919]
        assert {Path(row['path']).name for row in checkout_rows}==set(HEADS)
        for row in checkout_rows:
            name=Path(row['path']).name
            assert row['path']==str(SHARED/'build/checkouts'/name) and row['head']==HEADS[name]
        after=aliases(copied);assert before==after,'stable alias or physical root changed during original qualification'
        pinned(runner,ORIGINAL_SHA);pinned(SHARED/'attempt1/cache-handoff.json',HANDOFF_SHA)
        pinned(RECOVERY/'result.json',sys.argv[1]);assert not os.path.lexists(CLAIM) and not os.path.lexists(RECOVERY/'active-recovery.json')
        assert receipt['controllerSHA256']==sha(Path(__file__).read_bytes())
        receipt.update(status='PASS_ORIGINAL_99DC_SOURCE_INPUTS_AT_EXACT_RELOCATED_PATHS_NO_COMPILER_ADMISSION',
            custodyRecoveryReceiptSHA256=sys.argv[1],originalFailedCustodyReceiptSHA256=FAILED_CUSTODY_SHA,
            unchanged99dcSHA256=ORIGINAL_SHA,
            originalHandoffSHA256=HANDOFF_SHA,sourceInputs=proof,
            aliasesBefore=before,aliasesAfter=after,
            rootCompilerResourcePath=str(SHARED),rootCompilerFloorUnchangedBytes=2*1024**3,
            componentBudgetUnchangedBytes=256*1024**2,deadlineUnchangedSeconds=300,
            contentModeOwnerAndPhysicalSourceSetsQualified=True,
            originalCustodyMetadataAfterOrdinaryReadsReasserted=False)
    except BaseException as error:
        receipt['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        receipt['seconds']=round(time.monotonic()-began,3)
        raw=(json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode()
        try:
            with os.fdopen(fd,'wb',closefd=False) as stream:stream.write(raw);stream.flush();os.fsync(fd)
        finally:os.close(fd)
        directory=os.open(evidence,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(directory)
        finally:os.close(directory)
        print(json.dumps({'status':receipt['status'],'receipt':str(receipt_path),'sha256':sha(raw),'errors':receipt['errors']}))
    return 0 if receipt['status'].startswith('PASS') else 1

if __name__=='__main__':raise SystemExit(main())
