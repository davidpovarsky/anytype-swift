#!/usr/bin/env python3
"""Run only the twelve unqualified HTTP methods against the retained build.

The original attempt2 remains FAIL. Its actual seventeen Host and six pure
passes are reused without another compile or replay. A new, exactly 0700 owned
fixture root corrects inherited setgid setup; neither product nor test changes.
The complete Products census is explicitly a later observation, never a hash
claimed to have been emitted by the original failed producer.
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
    assert output.parent==PARENT and re.fullmatch(r'http12-attempt[1-9][0-9]{0,2}',output.name)
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
        'upload_http12_owned',HELPER_SHA,base)
    owned.install_interrupt_handlers()
    report={'protocol':'pinkha-ordinary-upload-http12-continuation-v1','status':'RUNNING',
        'controllerSHA256':args.controller_sha,'originalComponentControllerSHA256':CONTROLLER_SHA,
        'inputManifestSHA256':MANIFEST_SHA,'originalComponentRoot':str(ORIGINAL),
        'compilerInvocations':0,'priorPassingMethodsReplayed':0,'nativeAccountsOpened':False,
        'nativeStorageQualified':False,'cloudDurabilityQualified':False,'commands':[],
        'errors':[],'completionErrors':[],'sourceUnchanged':False,
        'separateNativeTestStatus':'NOT_RUN','separateNativeTestStarts':[],
        'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'rootAdmissionReserveBytes':32*MIB,
            'developmentFloorBytes':DEV_FLOOR,'developmentAdmissionReserveBytes':OWNED_CAP+16*MIB,
            'ownedOutputCapBytes':OWNED_CAP,'fixtureCapBytes':FIXTURE_CAP,'logCapBytes':LOG_CAP,
            'controllerSeconds':TOTAL_SECONDS,'swiftSkipBuildSeconds':SWIFT_SECONDS,
            'finalizationSeconds':60,'requiredOuterSeconds':420},
        'originalFailureReclassified':False,'productCensusIsLaterObservation':True}
    immutable={}
    copies={}
    products=None
    crypto=None
    crypto_binding=None
    old_fixture=None
    admitted=False
    last_allocation=0.0
    final_deadline=None

    def save():
        report['seconds']=round(time.monotonic()-began,3)
        original_control.save(output/'result.json',report)

    def guard(admission=False,final=False):
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
        for path in output.glob('commands/*/original.log'):
            assert path.stat().st_size<=LOG_CAP,'bounded actual log'
        if time.monotonic()-last_allocation>=1 or final:
            last_allocation=time.monotonic()
            used=original_control.allocation(output)
            assert used<=OWNED_CAP,'bounded new output allocation'
            report['maximumOwnedAllocatedBytes']=max(used,report.get('maximumOwnedAllocatedBytes',0))
            fixtures=output/'http-fixtures'
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
        original_control.save(output/'retained-products-before.json',{
            'phase':'LATER_CENSUS_BEFORE_HTTP12_NOT_ORIGINAL_PRODUCER_OUTPUT',
            'originalReceiptSHA256':ORIGINAL_SHA,'originalCompiledSourceInputsSHA256':SOURCE_SHA,
            'originalBuildLogSHA256':ORIGINAL_LOG_SHA,'products':products})
        report['compiledSourceInputs']=binding
        report['productCensusBefore']={'path':str(output/'retained-products-before.json'),**base.row(output/'retained-products-before.json')}
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
        for name in ('temporary','module-cache','clang-module-cache','swift-cache','swift-config','swift-security','http-fixtures'):
            directory=output/name
            directory.mkdir(mode=0o700)
            os.chmod(directory,0o700)
            assert stat.S_IMODE(directory.lstat().st_mode)==0o700
        env={key:value for key,value in os.environ.items() if not key.startswith(('PINKHA_','SWIFT_','SWIFTPM_','CLANG_','DYLD_','LD_'))}
        env.update(TMPDIR=str(output/'temporary'),SWIFTPM_MODULECACHE_OVERRIDE=str(output/'module-cache'),
            CLANG_MODULE_CACHE_PATH=str(output/'clang-module-cache'),XDG_CACHE_HOME=str(output/'swift-cache'),
            GIT_OPTIONAL_LOCKS='0',SWIFTPM_MAXIMUM_CONCURRENT_OPERATIONS='2',
            PINKHA_FILE_UPLOAD_FIXTURE_ROOT=str(output/'http-fixtures'),
            PINKHA_FILE_UPLOAD_OWNER_RECORD=str(output/'commands/http12/started.json'),
            PINKHA_FILE_UPLOAD_OWNER_CWD=str(ORIGINAL/'package'))
        argv=list(expected_argv)
        argv[argv.index('--filter')+1]='AnyNativeFileUploadHTTPTests'
        for option,name in [('--cache-path','swift-cache'),('--config-path','swift-config'),('--security-path','swift-security')]:
            argv[argv.index(option)+1]=str(output/name)
        argv.append('--skip-build')
        admitted=True
        report['fixtureRootBefore']=fixture_metadata(output/'http-fixtures')
        save()
        path,row=owned.run(output/'commands/http12',argv,ORIGINAL/'package',env,SWIFT_SECONDS,
            observe,original_control.save,base.sha,report['commands'])
        log=base.read(path,maximum=LOG_CAP).decode()
        current_starts=re.findall(r"Test Case '([^']+)' started",log)
        current_passes=re.findall(r"Test Case '([^']+)' passed",log)
        assert Counter(current_starts)==Counter(current_passes)==Counter({name:1 for name in http})
        assert not re.search(r"Test Case '[^']+' (?:failed|skipped)|XCTSkip|Skipping XCTest discovery|Build complete!|Building for|\] Compiling",log)
        assert 'Executed 12 tests, with 0 failures' in log
        report['actualMethods']={'started':current_starts,'passed':current_passes,'http':12,'host':0,'pure':0,'total':12,'skipped':0}
        report['httpFixtureQualification']=original_control.fixture_audit(output/'http-fixtures',output/'commands/http12/started.json',row,base)
        report['qualifiedComponentMethods']={'started':sorted(reused)+current_starts,'passed':sorted(reused)+current_passes,
            'host':17,'pure':6,'http':12,'total':35,'skipped':0,'reusedActualPasses':23,'newActualPasses':12}
        report['status']='PASS_COMPONENT35_WITH_REUSED23_AND_NEW_HTTP12'
    except BaseException as error:
        report['status']='FAIL_HTTP12_CONTINUATION'
        report['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        owned.ignore_interrupts()
        report['allStartedOwnedGroupsPositivelyAbsent']=all(row.get('processGroupAbsent') is True for row in report['commands'])
        final_deadline=time.monotonic()+60
        try:
            verify_rows(immutable,final=True); verify_rows(copies,final=True)
            if products is not None:
                assert product_census(final=True)==products
                report['compiledProductsAndModesUnchanged']=True
            if crypto_binding is not None:
                crypto.validate_after(crypto_binding,lambda:guard(final=True))
            if old_fixture is not None:
                assert fixture_metadata(ORIGINAL/'http-fixtures')==old_fixture
            report['admittedInputsUnchanged']=True
            report['compiledSourceInputsUnchanged']=str(ORIGINAL/'compiled-source-inputs.json') in immutable
            report['sourceUnchanged']=admitted
            assert all(row['exitCode']==0 and row['processGroupAbsent'] and not row['forcedCleanup']
                       and not row['cleanupErrors'] for row in report['commands'])
            if report['status'].startswith('PASS_'):
                assert len(report['commands'])==1 and report['actualMethods']['total']==12
                assert report['qualifiedComponentMethods']['total']==35 and report['httpFixtureQualification']['instances']==26
            guard(final=True)
            assert time.monotonic()<final_deadline,'bounded final verification'
        except BaseException as error:
            report['status']='FAIL_HTTP12_CONTINUATION'
            report['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        save()
    print(json.dumps({'status':report['status'],'path':str(output/'result.json'),'sha256':base.sha(output/'result.json')}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
