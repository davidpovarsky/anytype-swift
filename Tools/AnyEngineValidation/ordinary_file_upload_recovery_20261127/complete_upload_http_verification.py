#!/usr/bin/env python3
"""Complete the unchanged source audit of twelve actual passing HTTP methods.

The original component4b24 and HTTP0526 runs both remain FAIL at their exact
scopes. No compiler, XCTest, native process or fixture is started. This new
receipt reuses the actual23 plus actual12 and proves the remaining unchanged
source/Products/Crypto closure, with the original sixty-second final deadline.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time

PARENT = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127')
ORIGINAL = PARENT/'components-attempt2'
CONTROL = PARENT/'prepared3/Tools/AnyEngineValidation/ordinary_file_upload'
CONTROLLER = CONTROL/'run_upload_components.py'
CONTROLLER_SHA = 'ee54cf07a4f21b53e6a9edec65145e621477c8f51017a54c589a4eccdd116b7e'
ORIGINAL_SHA = '4b24eb81b7e7fa6b108568ea619bf125148e8952b38879a71cc8091b55d101c5'
ORIGINAL_LOG_SHA = '1d3da611166dbb0194e00a28c0092ca492385336b774f3c80ece0afa4facaa23'
SOURCE_SHA = 'de642b7c2cc54367d1b767807443a38e4803bc8cba628beefa3cee819688f9bc'
MANIFEST_SHA = '74bf4e399ae6988fb9e12cebd544538e76b326636a1c2d8476dd3c556b43614f'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
CRYPTO_SHA = '1ed69a8431f77c4d5b1b735a6d85efec1fa77b50f0c7185185f712d5bf09abbd'
LIFECYCLE_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
HTTP_RUN = PARENT/'http12-attempt1'
HTTP_RUN_SHA = '0526d95b3e0239387bf0bd94226e797a151d7986c6812ada0768d53dbf5242c3'
HTTP_LOG_SHA = 'f81e79cfe9488d11a066bd402f38db4778c5b0d816cf335fdea07cdd451c19a9'
HTTP_CONTROL = PARENT/'prepared-native1/run_upload_http_continuation.py'
HTTP_CONTROL_SHA = '0f44f90a6a1043ca98eb0d1e010f7ce0660aa007fa1d3c317aa3ea828e0533c3'
MIB = 1024**2
ROOT_FLOOR, DEV_FLOOR = 2*1024**3, 512*MIB
OWNED_CAP, LOG_CAP, FIXTURE_CAP = 64*MIB, 8*MIB, 16*MIB
TOTAL_SECONDS, SWIFT_SECONDS = 300, 120


def load_exact(path, name, wanted):
    assert path.resolve()==path and not path.is_symlink()
    data=path.read_bytes()
    assert len(data)<=65536 and hashlib.sha256(data).hexdigest()==wanted
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==wanted
    return module


def main():
    if sys.flags.optimize:
        raise RuntimeError('assertions must remain enabled')
    sys.dont_write_bytecode=True
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--controller-sha',required=True)
    args=parser.parse_args()
    assert os.geteuid()==0 and os.uname().nodename=='torah-social'
    assert re.fullmatch(r'[0-9a-f]{64}',args.controller_sha)
    output=args.output
    assert output.parent==PARENT and re.fullmatch(r'http12-completion[1-9][0-9]{0,2}',output.name)
    assert PARENT.resolve()==PARENT and output.resolve()==output
    os.umask(0o077)
    # Exclusive creation precedes every child. Remove inherited setgid only on
    # this new synthetic output; the failed original fixture root is untouched.
    output.mkdir(mode=0o700,exist_ok=False)
    os.chmod(output,0o700)
    assert stat.S_IMODE(output.lstat().st_mode)==0o700
    began=time.monotonic()
    original_control=load_exact(CONTROLLER,'upload35_original_control',CONTROLLER_SHA)
    base=original_control.Inputs()
    own=Path(__file__).absolute()
    base.pinned(own,args.controller_sha)
    owned=original_control.load_module(CONTROL/'owned_swift_commands.py',
        'upload_http12_completion_owned',HELPER_SHA,base)
    owned.install_interrupt_handlers()
    report={'protocol':'pinkha-ordinary-upload-http12-completion-v1','status':'RUNNING_COMPLETION_ONLY',
        'controllerSHA256':args.controller_sha,'originalComponentControllerSHA256':CONTROLLER_SHA,
        'inputManifestSHA256':MANIFEST_SHA,'originalComponentRoot':str(ORIGINAL),
        'compilerInvocations':0,'priorPassingMethodsReplayed':0,'nativeAccountsOpened':False,
        'nativeStorageQualified':False,'cloudDurabilityQualified':False,'commands':[],
        'errors':[],'completionErrors':[],'sourceUnchanged':False,
        'separateNativeTestStatus':'NOT_RUN','separateNativeTestStarts':[],
        'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'rootAdmissionReserveBytes':32*MIB,
            'developmentFloorBytes':DEV_FLOOR,'developmentAdmissionReserveBytes':OWNED_CAP+16*MIB,
            'ownedOutputCapBytes':OWNED_CAP,'fixtureCapBytes':FIXTURE_CAP,'logCapBytes':LOG_CAP,
            'controllerSeconds':TOTAL_SECONDS,'originalHTTPCommandSeconds':SWIFT_SECONDS,
            'finalizationSeconds':60,'requiredOuterSeconds':420},
        'originalFailureReclassified':False,'httpFailureReclassified':False,'productCensusIsLaterObservation':True,
        'newTestMethods':0,'newFixtureProcesses':0,'newChildCommands':0,
        'originalHTTPReceipt':{'path':str(HTTP_RUN/'result.json'),'sha256':HTTP_RUN_SHA,'status':'FAIL_HTTP12_CONTINUATION'},
        'originalHTTPLog':{'path':str(HTTP_RUN/'commands/http12/original.log'),'sha256':HTTP_LOG_SHA},
        'completionSourceAuditOnly':True}
    immutable={}
    copies={}
    products=None
    crypto=None
    crypto_binding=None
    old_fixture=None
    current_fixture=None
    admitted=False
    last_allocation=0.0
    final_deadline=None

    def save():
        report['seconds']=round(time.monotonic()-began,3)
        original_control.save(output/'result.json',report)

    def guard(admission=False,final=False,force_allocation=False):
        nonlocal last_allocation
        assert final or time.monotonic()-began<TOTAL_SECONDS,'bounded HTTP continuation deadline'
        if final:
            assert final_deadline is not None and time.monotonic()<final_deadline,'bounded final verification'
        assert not (output/'abort').exists(),'owned continuation abort'
        free={'root':shutil.disk_usage('/').free,'development':shutil.disk_usage(PARENT).free}
        assert free['root']>=ROOT_FLOOR+(32*MIB if admission else 0),'original root floor/reserve'
        assert free['development']>=DEV_FLOOR+(OWNED_CAP+16*MIB if admission else 0),'development floor/reserve'
        for name,value in free.items():
            report.setdefault('minimumFreeBytes',{})[name]=min(value,report.get('minimumFreeBytes',{}).get(name,value))
        for path in HTTP_RUN.glob('commands/*/original.log'):
            assert path.stat().st_size<=LOG_CAP,'bounded actual log'
        # Every input still checks time/floors; the unchanged output cap is
        # scanned at most once per second plus explicit begin/end fences.
        # The original force-per-input scan made the audit quadratic.
        if time.monotonic()-last_allocation>=1 or force_allocation:
            last_allocation=time.monotonic()
            used=original_control.allocation(output)
            assert used<=OWNED_CAP,'bounded new output allocation'
            report['maximumOwnedAllocatedBytes']=max(used,report.get('maximumOwnedAllocatedBytes',0))
            fixtures=HTTP_RUN/'http-fixtures'
            if fixtures.exists():
                assert original_control.allocation(fixtures)<=FIXTURE_CAP,'bounded loopback fixture allocation'

    def observe():
        try: guard(); return None
        except BaseException as error: return type(error).__name__+': '+str(error)

    def pin(path,wanted):
        base.pinned(path,wanted)
        immutable[str(path)]=base.row(path)
        return base.read(path,maximum=8*MIB)

    def verify_rows(rows,final=False):
        for name,wanted in rows.items():
            guard(final=final)
            assert base.row(Path(name))==wanted,'bound original input or copy changed: '+name

    def fixture_metadata(path):
        info=path.lstat()
        assert stat.S_ISDIR(info.st_mode) and path.resolve()==path and not path.is_symlink()
        return {'path':str(path),'mode':stat.S_IMODE(info.st_mode),'uid':info.st_uid,
            'gid':info.st_gid,'device':info.st_dev,'inode':info.st_ino,
            'entries':sorted(entry.name for entry in path.iterdir())}

    def product_census(final=False):
        class BoundedProductInputs:
            def row(self,path):
                guard(final=final)
                return base.row(path)
        guard(final=final)
        value=original_control.retained_products(ORIGINAL/'build',BoundedProductInputs())
        guard(final=final)
        return value

    try:
        guard(admission=True)
        lifecycle=json.loads(pin(original_control.LIFECYCLE_RECEIPT,LIFECYCLE_SHA))
        assert lifecycle['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS'
        assert lifecycle['helperSHA256']==HELPER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent']
        assert len(lifecycle['methods'])==5 and all(row['status']=='PASS' for row in lifecycle['methods'])
        pin(CONTROLLER,CONTROLLER_SHA); pin(own,args.controller_sha)
        pin(CONTROL/'owned_swift_commands.py',HELPER_SHA)
        pin(HTTP_CONTROL,HTTP_CONTROL_SHA)
        partial=json.loads(pin(HTTP_RUN/'result.json',HTTP_RUN_SHA))
        assert partial['protocol']=='pinkha-ordinary-upload-http12-continuation-v1'
        assert partial['status']=='FAIL_HTTP12_CONTINUATION' and partial['errors']==[]
        assert partial['completionErrors']==[{'message':'bounded final verification','type':'AssertionError'}]
        assert partial['controllerSHA256']==HTTP_CONTROL_SHA and partial['originalComponentControllerSHA256']==CONTROLLER_SHA
        assert partial['inputManifestSHA256']==MANIFEST_SHA and partial['originalComponentRoot']==str(ORIGINAL)
        assert partial['compilerInvocations']==partial['priorPassingMethodsReplayed']==0
        assert partial['nativeAccountsOpened'] is False and partial['originalFailureReclassified'] is False
        assert partial['sourceUnchanged'] is False and partial['compiledProductsAndModesUnchanged'] is True
        assert partial['allStartedOwnedGroupsPositivelyAbsent'] is True and len(partial['commands'])==1
        assert partial['productCensusIsLaterObservation'] is True
        assert partial['separateNativeTestStatus']=='NOT_RUN' and partial['separateNativeTestStarts']==[]
        assert partial['resourcePolicy']['finalizationSeconds']==60
        http_command=partial['commands'][0]
        assert http_command['exitCode']==0 and http_command['processGroupAbsent'] is True
        assert not http_command['forcedCleanup'] and http_command['cleanupErrors']==[] and http_command['signals']==[]
        assert http_command['logSHA256']==HTTP_LOG_SHA
        http_log=pin(HTTP_RUN/'commands/http12/original.log',HTTP_LOG_SHA).decode()
        manifest=json.loads(pin(CONTROL/'upload-component-inputs.json',MANIFEST_SHA))
        original=json.loads(pin(ORIGINAL/'result.json',ORIGINAL_SHA))
        assert original['status']=='FAIL' and original['controllerSHA256']==CONTROLLER_SHA
        assert original['inputManifestSHA256']==MANIFEST_SHA
        assert original['sourceUnchanged'] and original['admittedInputsUnchanged'] and original['compiledSourceInputsUnchanged']
        assert original['allStartedOwnedGroupsPositivelyAbsent'] and len(original['commands'])==4
        assert [row['exitCode'] for row in original['commands']]==[0,0,0,1]
        assert all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors']
                   and not row['signals'] for row in original['commands'])
        assert original['errors']==[
            {'message':'owned command did not finish normally: swift-components','type':'RuntimeError'},
            {'message':'','phase':'final-lifecycle-and-budget','type':'AssertionError'}]
        assert original['separateNativeTestStarts']==[] and original['separateNativeTestStatus']=='NOT_RUN'
        assert original['nativeAccountsOpened'] is False and 'compiledProducts' not in original
        raw=pin(ORIGINAL/'commands/swift-components/original.log',ORIGINAL_LOG_SHA)
        log=raw.decode()
        starts=re.findall(r"Test Case '([^']+)' started",log)
        passes=re.findall(r"Test Case '([^']+)' passed",log)
        failures=re.findall(r"Test Case '([^']+)' failed",log)
        http={"AnyNativeFileUploadHTTPTests."+method for method in manifest['methods']['AnyNativeFileUploadHTTPTests']}
        expected={name+'.'+method for name,methods in manifest['methods'].items() for method in methods}
        reused=expected-http
        assert len(http)==12 and len(reused)==23 and len(expected)==35
        assert Counter(starts)==Counter({name:1 for name in expected})
        assert Counter(passes)==Counter({name:1 for name in reused})
        assert Counter(failures)==Counter({name:1 for name in http})
        assert len(re.findall(r'threw error "fixtureFailed"',log))==12
        assert 'Build complete! (50.92 secs)' in log and 'Executed 35 tests, with 12 failures (12 unexpected)' in log
        assert not re.search(r"Test Case '[^']+' skipped|XCTSkip|Skipping XCTest discovery",log)
        old_fixture=fixture_metadata(ORIGINAL/'http-fixtures')
        assert old_fixture['mode']==0o2700 and old_fixture['uid']==os.geteuid() and old_fixture['entries']==[]
        report['originalFixtureSetupFailure']={'observed':old_fixture,'requiredMode':0o700,
            'productAndTestsUnchanged':True,'originalDirectoryModified':False}
        report['reusedMethods']={'host':17,'pure':6,'total':23,'started':sorted(reused),'passed':sorted(reused),
            'originalReceipt':{'path':str(ORIGINAL/'result.json'),'sha256':ORIGINAL_SHA,'status':'FAIL'},
            'originalLog':{'path':str(ORIGINAL/'commands/swift-components/original.log'),'sha256':ORIGINAL_LOG_SHA},
            'newExecutions':0}
        binding=original['compiledSourceInputs']
        assert binding=={'path':str(ORIGINAL/'compiled-source-inputs.json'),'bytes':526113,'sha256':SOURCE_SHA}
        source=json.loads(pin(Path(binding['path']),SOURCE_SHA))
        assert source['counts']==manifest['expectedCounts']
        base.admit_retained_crypto_alias(original_control.CACHE,original_control.PHYSICAL_CACHE,
            'a049e79aa6e185cd2721cf1b18a61a268474275a3b2d00cb187fe41ef8f8d8e8')
        immutable.update(source['originalInputs'])
        copies=source['isolatedCopies']
        expected_copies={}
        for row in manifest['originalProjectFiles']:
            if row['compile']:
                expected_copies[str(ORIGINAL/'package/Sources'/row['target']/Path(row['path']).name)]={key:row[key] for key in ('bytes','sha256')}
        for row in manifest['originalCoreFiles']:
            expected_copies[str(ORIGINAL/'package/Sources/TorahInspectorCore'/Path(row['path']).name)]={key:row[key] for key in ('bytes','sha256')}
        for row in manifest['preparedSources']:
            if row['kind']=='production': target=ORIGINAL/'package/Sources'/row['target']/Path(row['path']).name
            elif row['kind'] in ('test','excluded-native-test'): target=ORIGINAL/'package/Tests/OrdinaryFileUploadTests'/Path(row['path']).name
            else:
                assert row['kind']=='fixture'
                target=ORIGINAL/'package/Tests/Fixtures'/Path(row['path']).name
            expected_copies[str(target)]={key:row[key] for key in ('bytes','sha256')}
        assert len(expected_copies)==37 and source['counts']['productionCompiledFiles']==32
        assert source['counts']['compiledTestFiles']==4
        assert {str(path) for prefix in ('Sources','Tests') for path in (ORIGINAL/'package'/prefix).rglob('*') if path.is_file()}==set(expected_copies)
        assert all(copies.get(name)==wanted for name,wanted in expected_copies.items())
        assert all(Path(name).is_relative_to(ORIGINAL) for name in copies)
        verify_rows(immutable); verify_rows(copies)
        crypto=original_control.load_module(CONTROL/'qualify_upload_crypto_c3.py','http12_crypto',CRYPTO_SHA,base)
        crypto_receipt=ORIGINAL/'retained-dependency-products.json'
        assert str(crypto_receipt) in copies
        crypto_data=json.loads(base.read(crypto_receipt,maximum=4*MIB))
        assert crypto_data['status']=='CURRENT_C3_CRYPTO_PRODUCTS_QUALIFIED_FOR_ORDINARY_UPLOAD_COMPONENTS_ONLY'
        crypto_binding={'sharedAdmission':crypto_data['sharedProducerAdmission'],'inputModes':crypto_data['modes']}
        crypto.validate_after(crypto_binding,guard)
        products=product_census()
        census=partial['productCensusBefore']
        assert census['path']==str(HTTP_RUN/'retained-products-before.json')
        census_raw=pin(Path(census['path']),census['sha256'])
        assert {'bytes':len(census_raw),'sha256':hashlib.sha256(census_raw).hexdigest()}=={key:census[key] for key in ('bytes','sha256')}
        census_body=json.loads(census_raw)
        assert census_body=={'phase':'LATER_CENSUS_BEFORE_HTTP12_NOT_ORIGINAL_PRODUCER_OUTPUT',
            'originalReceiptSHA256':ORIGINAL_SHA,'originalCompiledSourceInputsSHA256':SOURCE_SHA,
            'originalBuildLogSHA256':ORIGINAL_LOG_SHA,'products':products}
        report['compiledSourceInputs']=binding
        report['productCensusBefore']=census
        report['retainedDependencyProducts']={'path':str(crypto_receipt),**base.row(crypto_receipt)}
        for key,name in [('root','compiledProductsRoot'),('files','compiledProducts'),('modes','compiledProductModes'),
                         ('directories','compiledProductDirectories'),('executables','compiledExecutables'),('testRunner','compiledTestRunner')]:
            report[name]=products[key]
        original_swift=original['commands'][3]
        expected_argv=[str(original_control.TOOLCHAIN/'swift'),'test','--package-path',str(ORIGINAL/'package'),
            '--scratch-path',str(ORIGINAL/'build'),'--cache-path',str(ORIGINAL/'swift-cache'),
            '--config-path',str(ORIGINAL/'swift-config'),'--security-path',str(ORIGINAL/'swift-security'),
            '--disable-automatic-resolution','--jobs','2','--filter','|'.join(manifest['methods'])]
        assert original_swift['argv']==expected_argv and original_swift['cwd']==str(ORIGINAL/'package')
        assert original_swift['logSHA256']==ORIGINAL_LOG_SHA
        report['originalCompilerCommand']=original_swift
        argv=list(expected_argv)
        argv[argv.index('--filter')+1]='AnyNativeFileUploadHTTPTests'
        for option,name in [('--cache-path','swift-cache'),('--config-path','swift-config'),('--security-path','swift-security')]:
            argv[argv.index(option)+1]=str(HTTP_RUN/name)
        argv.append('--skip-build')
        assert http_command['argv']==argv and http_command['cwd']==str(ORIGINAL/'package')
        current_starts=re.findall(r"Test Case '([^']+)' started",http_log)
        current_passes=re.findall(r"Test Case '([^']+)' passed",http_log)
        assert Counter(current_starts)==Counter(current_passes)==Counter({name:1 for name in http})
        assert not re.search(r"Test Case '[^']+' (?:failed|skipped)|XCTSkip|Skipping XCTest discovery|Build complete!|Building for|\] Compiling",http_log)
        assert 'Executed 12 tests, with 0 failures' in http_log
        actual={'started':current_starts,'passed':current_passes,'http':12,'host':0,'pure':0,'total':12,'skipped':0}
        assert partial['actualMethods']==actual
        qualification=original_control.fixture_audit(HTTP_RUN/'http-fixtures',HTTP_RUN/'commands/http12/started.json',http_command,base)
        assert qualification==partial['httpFixtureQualification'] and qualification['instances']==26
        # Preserve the original fixture journals as inputs; never query or signal
        # their historical PIDs, and never start a new fixture/Swift process.
        pin(HTTP_RUN/'commands/http12/started.json',base.sha(HTTP_RUN/'commands/http12/started.json'))
        for fixture in qualification['fixtureRows']:
            for name,wanted in fixture['artifacts'].items():
                path=Path(fixture['directory'])/name
                assert {'bytes':len(pin(path,wanted['sha256'])),'sha256':wanted['sha256']}==wanted
        assert partial['reusedMethods']==report['reusedMethods']
        aggregate={'started':sorted(reused)+current_starts,'passed':sorted(reused)+current_passes,
            'host':17,'pure':6,'http':12,'total':35,'skipped':0,'reusedActualPasses':23,'newActualPasses':12}
        assert partial['qualifiedComponentMethods']==aggregate
        report['reusedHTTPMethods']=actual
        report['reusedHTTPCommand']=http_command
        report['httpFixtureQualification']=qualification
        report['qualifiedComponentMethods']={'host':17,'pure':6,'http':12,'total':35,'skipped':0,
            'started':aggregate['started'],'passed':aggregate['passed'],
            'originalComponentActualPasses':23,'originalHTTPActualPasses':12,'newExecutions':0}
        for key,name in [('root','compiledProductsRoot'),('files','compiledProducts'),('modes','compiledProductModes'),
                         ('directories','compiledProductDirectories'),('executables','compiledExecutables'),('testRunner','compiledTestRunner')]:
            assert partial[name]==products[key]
        assert partial['compiledSourceInputs']==binding and partial['retainedDependencyProducts']==report['retainedDependencyProducts']
        assert partial['originalCompilerCommand']==original_swift
        assert partial['fixtureRootBefore']['mode']==0o700
        current_fixture=fixture_metadata(HTTP_RUN/'http-fixtures')
        assert {k:v for k,v in current_fixture.items() if k!='entries'}=={k:v for k,v in partial['fixtureRootBefore'].items() if k!='entries'}
        report['originalHTTPFixtureRootUnchanged']=current_fixture
        admitted=True
        report['status']='PASS_COMPONENT35_WITH_REUSED23_REUSED_HTTP12_AND_COMPLETED_SOURCE_AUDIT'
    except BaseException as error:
        report['status']='FAIL_HTTP12_COMPLETION'
        report['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        owned.ignore_interrupts()
        report['allStartedOwnedGroupsPositivelyAbsent']=all(row.get('processGroupAbsent') is True for row in report['commands'])
        final_deadline=time.monotonic()+60
        try:
            guard(final=True,force_allocation=True)
            verify_rows(immutable,final=True); verify_rows(copies,final=True)
            if products is not None:
                assert product_census(final=True)==products
                report['compiledProductsAndModesUnchanged']=True
            if crypto_binding is not None:
                crypto.validate_after(crypto_binding,lambda:guard(final=True))
            if old_fixture is not None:
                assert fixture_metadata(ORIGINAL/'http-fixtures')==old_fixture
            if current_fixture is not None:
                assert fixture_metadata(HTTP_RUN/'http-fixtures')==current_fixture
                report['originalHTTPFixtureRootUnchangedAtCompletion']=True
            report['admittedInputsUnchanged']=True
            report['compiledSourceInputsUnchanged']=str(ORIGINAL/'compiled-source-inputs.json') in immutable
            report['sourceUnchanged']=admitted
            assert report['commands']==[] and report['newChildCommands']==0
            if report['status'].startswith('PASS_'):
                assert report['reusedHTTPMethods']['total']==12 and report['newTestMethods']==0
                assert report['qualifiedComponentMethods']['total']==35 and report['httpFixtureQualification']['instances']==26
            guard(final=True,force_allocation=True)
            assert time.monotonic()<final_deadline,'bounded final verification'
        except BaseException as error:
            report['status']='FAIL_HTTP12_COMPLETION'
            report['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        save()
    print(json.dumps({'status':report['status'],'path':str(output/'result.json'),'sha256':base.sha(output/'result.json')}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
