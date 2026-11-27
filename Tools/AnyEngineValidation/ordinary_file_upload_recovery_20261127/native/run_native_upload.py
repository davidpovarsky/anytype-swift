#!/usr/bin/env python3
"""Fresh actual native upload proof, pending both independently qualified inputs.

One already-compiled Swift method uploads a zero-byte inline file and a real
PNG through the public Engine adapter. A new OS-offline native process then
reopens only this controller's own new account and verifies both exact files.
No saved account, old fixture, cloud service or second compiler is an input.
"""
import argparse
import ast
from collections import Counter
import hashlib
import http.client
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import signal
import socket
import stat
import struct
import sys
import time
import urllib.parse
import zlib

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PARENT = Path('/mnt/development/projects/evidence/pinkha-ordinary-file-upload-20261127')
SOURCE_MANIFEST = HERE/'native-upload-source-manifest.json'
N_ADMISSION_SHA = '47223411ab35adae53b87fa6fb41d939d6e2645053eeaf62ae3d6339d339ce20'
N_SOURCE_SHA = '2bbda0f4d389aef369d1df1459d2e5d03ba9648121211619aa028b99a0990ac5'
DEADLINE_CONTROL_SOURCE_SHA = '26ed736be9e5ddb8def2af26de6648bba4ab8ad85f55be91bc045dc215de4b84'
DEADLINE_FUNCTION_SHA = 'b92bf5edfce867716532a89c17880cbc6cafe3afe1b97b8e81647c497103be81'
COMPONENT_CONTROLLER_SHA = 'ee54cf07a4f21b53e6a9edec65145e621477c8f51017a54c589a4eccdd116b7e'
COMPONENT_MANIFEST_SHA = '74bf4e399ae6988fb9e12cebd544538e76b326636a1c2d8476dd3c556b43614f'
HTTP_CONTINUATION_SHA = '0f44f90a6a1043ca98eb0d1e010f7ce0660aa007fa1d3c317aa3ea828e0533c3'
HTTP_ROOT = PARENT/'http12-attempt1'
HTTP_RECEIPT_SHA = '0526d95b3e0239387bf0bd94226e797a151d7986c6812ada0768d53dbf5242c3'
HTTP_LOG_SHA = 'f81e79cfe9488d11a066bd402f38db4778c5b0d816cf335fdea07cdd451c19a9'
HTTP_COMPLETION_SHA = 'c6a0b7b10997a7014ddf85ed664d37aa9f5216a11b80019484f4d6e52076150e'
ORIGINAL_COMPONENT_ROOT = PARENT/'components-attempt2'
ORIGINAL_COMPONENT_SHA = '4b24eb81b7e7fa6b108568ea619bf125148e8952b38879a71cc8091b55d101c5'
ORIGINAL_COMPONENT_LOG_SHA = '1d3da611166dbb0194e00a28c0092ca492385336b774f3c80ece0afa4facaa23'
ORIGINAL_COMPILED_SOURCE_SHA = 'de642b7c2cc54367d1b767807443a38e4803bc8cba628beefa3cee819688f9bc'
NATIVE_TEST_SHA = 'b6d071a48fe112fe1bd5ecda788dd1eb1a89f42b89d168dfd5b25e3098b11237'
NATIVE_TEST = 'AnyNativeFileUploadNativeRouteTests.testOriginalNativeAttachResolvesMetadataAndVerifiesInlineAndFullTierBytes'
HELPER_SHA = 'f9de18c0fdc879ff916ba34e9afa0da9d6b91444eebfa1e5a8d6a50d3523ca56'
HELPER_PROOF = Path('/mnt/development/projects/evidence/pinkha-e-engine-retained-root-relocation-20261127/swift-lifecycle-controls1/result.json')
HELPER_PROOF_SHA = '040ffa3fcf93094369e24928732aeba9eb10fdb673db76ab7540a887748aa27d'
OFFLINE = Path('/mnt/development/projects/worktrees/anytype-w1-functional-migration-20261127/Tools/AnyEngineValidation/native_source_preservation/linux_outbound_denial.py')
OFFLINE_SHA = '6eaca8b9602f9c1c7fce4b8a176759ad1a10577c0ee74eddb3264992976e86b1'
OFFLINE_LIBRARY = Path('/usr/lib/aarch64-linux-gnu/libseccomp.so.2.5.5')
OFFLINE_LIBRARY_SHA = '3d128123b494ca9e88f3c237b0912397145af1754e86ea99f460af6857441f19'
OFFLINE_ACTUAL_PROOF = Path('/var/lib/pinkha-c-filesv2-20261126/original-native-authority-reader-continuation1/result.json')
OFFLINE_ACTUAL_SHA = 'ecd4e58378cbb82731926536e82fca655da64ee156057ba411a242c95942c2ab'
DEADLINE_PARENT = Path('/mnt/development/projects/evidence/pinkha-current-authority-http-controls-20261127')
MIB = 1024**2
ROOT_FLOOR = 2*1024**3
DEV_FLOOR = 512*MIB
OUTPUT_CAP = 128*MIB
LOG_CAP = 8*MIB


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def exact_deadline_function(raw):
    nodes=[node for node in ast.parse(raw).body if isinstance(node,ast.FunctionDef) and node.name=='absolute_http_deadline']
    require(len(nodes)==1,'one exact decorated absolute deadline function')
    node=nodes[0]
    first=min([node.lineno]+[decorator.lineno for decorator in node.decorator_list])
    data=b''.join(raw.splitlines(keepends=True)[first-1:node.end_lineno])
    require(len(data)==1745 and hashlib.sha256(data).hexdigest()==DEADLINE_FUNCTION_SHA,
            'byte-exact actually qualified complete HTTP deadline')
    return data


def identity(data):
    return {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def physical(path):
    require(path.is_absolute() and path.resolve()==path and not path.is_symlink(), 'fixed physical path required')


def read_public(path, maximum=8*MIB):
    physical(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=maximum, 'bounded regular public input')
    descriptor = os.open(path, os.O_RDONLY|os.O_NOFOLLOW|os.O_NOATIME)
    with os.fdopen(descriptor, 'rb') as stream:
        require(os.fstat(stream.fileno())==before, 'public input opened with changed identity')
        data = stream.read(maximum+1)
        require(os.fstat(stream.fileno())==before, 'public input changed while reading')
    require(path.lstat()==before and len(data)==before.st_size, 'public input identity changed')
    return data


def json_object(raw):
    def unique(rows):
        result = {}
        for key, value in rows:
            require(key not in result, 'duplicate JSON field')
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(value, dict), 'JSON object required')
    return value


def product_inventory(root):
    """Independently retain the entire already-built Products tree and modes."""
    physical(root)
    files, modes, directories, executables = {}, {}, {}, {}
    pending = [root]
    while pending:
        path = pending.pop()
        physical(path)
        before = path.lstat()
        name = str(path); mode = stat.S_IMODE(before.st_mode)
        if stat.S_ISDIR(before.st_mode):
            directories[name] = mode
            descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NOATIME)
            try:
                with os.scandir(descriptor) as entries:pending.extend(path/entry.name for entry in entries)
            finally:os.close(descriptor)
        else:
            require(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'private regular compiled product')
            files[name] = identity(read_public(path,128*MIB))
            modes[name] = mode
            if mode & 0o111:executables[name] = dict(files[name],mode=mode)
        require(path.lstat()==before,'compiled product changed during inventory')
        require(len(files)+len(directories)+len(pending)<=4096,'bounded complete product tree')
    runners = [name for name in files if Path(name).name=='OrdinaryFileUploadTests-test-runner']
    libraries = [name for name in files if Path(name).name=='OrdinaryFileUploadTests.so']
    require(1<=len(files)<=2048 and len(runners)==len(libraries)==1 and runners[0] in executables,
            'one actual executable test runner and shared test library')
    return dict(root=str(root),files=files,modes=modes,directories=directories,
                executables=executables,testRunner=dict(path=runners[0],**executables[runners[0]]))


def png_bytes():
    # Exact reproducible RGB bytes, independent of any user image or encoder.
    width = height = 64
    pixels = bytes((index*73 + (index//17)*29) % 256 for index in range(width*height*3))
    rows = b''.join(b'\0'+pixels[y*width*3:(y+1)*width*3] for y in range(height))
    def chunk(kind, body):
        return struct.pack('>I', len(body))+kind+body+struct.pack('>I', zlib.crc32(kind+body)&0xffffffff)
    data = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('>IIBBBBB',width,height,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows,0))+chunk(b'IEND',b'')
    require(4096<=len(data)<=MIB, 'PNG must exercise full file tier')
    return data


def main():
    require(not sys.flags.optimize, 'assertions must remain enabled')
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output','native-receipt','component-receipt','deadline-receipt'):
        parser.add_argument('--'+name, type=Path, required=True)
    for name in ('native-sha256','component-sha256','deadline-sha256','source-manifest-sha256'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    require(os.geteuid()==0 and os.uname().nodename=='torah-social', 'fixed authorized Oracle host')
    for value in (args.native_sha256,args.component_sha256,args.deadline_sha256,args.source_manifest_sha256):
        require(re.fullmatch(r'[0-9a-f]{64}',value), 'exact input receipt hash required')
    output = args.output
    require(output.parent==PARENT and re.fullmatch(r'native-attempt[1-9][0-9]{0,2}',output.name), 'new owned native proof scope')
    require(args.component_receipt.parent.parent==PARENT and re.fullmatch(r'http12-completion[1-9][0-9]{0,2}',args.component_receipt.parent.name) and args.component_receipt.name=='result.json', 'exact separate HTTP12 source-audit completion output')
    require(args.deadline_receipt.parent.parent==DEADLINE_PARENT and re.fullmatch(r'attempt[1-9][0-9]{0,2}',args.deadline_receipt.parent.name) and args.deadline_receipt.name=='result.json', 'exact prior HTTP deadline output')
    physical(PARENT); physical(HERE); physical(output)
    os.umask(0o077)
    output.mkdir(mode=0o700,exist_ok=False)
    began = time.monotonic()
    serial = 0
    public_inputs = {}
    native = None
    native_sources = None
    component_copies = {}
    compiled_products = {}
    compiled_product_closure = None
    retained_setup_files = {}
    report = {'protocol':'pinkha-fresh-ordinary-upload-native-v1','status':'RUNNING',
              'declaredNewSwiftMethods':1,'executedSwiftMethods':0,'replayedComponentMethods':0,
              'compilerInvocations':0,'retainedPrivateAccountInputs':0,'accountInitializations':0,
              'productionJournalQualified':False,'cloudCustodyQualified':False,'appleQualified':False,
              'nativeProcessesOSDenialRequired':True,'nativeProcessesOSDenialVerified':False,
              'swiftProcessUsesOSDenialWrapper':False,'swiftEndpointLoopback':True,
              'uploadHTTPAttemptsDirectlyInstrumented':False,'requests':[],'commands':[],
              'phases':[],'errors':[],'completionErrors':[],
              'resourcePolicy':{'rootFloorBytes':ROOT_FLOOR,'developmentFloorBytes':DEV_FLOOR,
                 'rootAdmissionReserveBytes':32*MIB,'developmentAdmissionReserveBytes':OUTPUT_CAP+16*MIB,
                 'ownedOutputCapBytes':OUTPUT_CAP,'controllerSeconds':360,'finalVerificationSeconds':60,
                 'nativeServiceSeconds':240,'swiftSkipBuildSeconds':90,'requiredOuterSeconds':480}}

    def save(path,value):
        nonlocal serial
        require(path.is_relative_to(output), 'owned evidence destination')
        serial += 1
        data = (json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
        require(len(data)<=4*MIB, 'bounded receipt')
        temporary = path.with_name(path.name+'.next-'+str(serial))
        with temporary.open('xb') as stream:
            stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        descriptor = os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)

    def save_report():
        report['seconds'] = time.monotonic()-began
        save(output/'result.json',report)

    def guard(admit=False,final=False):
        require(final or time.monotonic()-began<360,'native proof controller deadline')
        require(not (output/'abort').exists(),'owned native proof abort')
        free = {'root':shutil.disk_usage('/').free,'development':shutil.disk_usage('/mnt/development').free}
        require(free['root']>=ROOT_FLOOR+(32*MIB if admit else 0),'root original disk floor')
        require(free['development']>=DEV_FLOOR+(OUTPUT_CAP+16*MIB if admit else 0),'development original disk floor')
        report['minimumFreeBytes']={key:min(value,report.get('minimumFreeBytes',{}).get(key,value)) for key,value in free.items()}
        used = 0;count = 0;seen=set();census_started=time.monotonic()
        for folder,dirs,files in os.walk(output,followlinks=False):
            for name in [None]+dirs+files:
                path=Path(folder) if name is None else Path(folder)/name
                try:info=path.lstat()
                except FileNotFoundError:continue
                require(not stat.S_ISLNK(info.st_mode),'owned output alias')
                require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode),'owned output special file')
                key=(info.st_dev,info.st_ino)
                if key not in seen:used+=info.st_blocks*512;seen.add(key)
                count+=1
                require(count<=200000 and time.monotonic()-census_started<5,'bounded owned allocation census')
                if name=='original.log':require(info.st_size<=LOG_CAP,'bounded original command log')
        require(used<=OUTPUT_CAP,'bounded complete fresh native output')
        report['peakOwnedAllocatedBytes']=max(used,report.get('peakOwnedAllocatedBytes',0))
        return free

    def observe():
        try:guard();return None
        except BaseException as error:return type(error).__name__+': '+str(error)

    def pin(path,wanted,maximum=8*MIB):
        raw=read_public(path,maximum)
        require(identity(raw)['sha256']==wanted,'public input hash changed: '+str(path))
        public_inputs[str(path)]={'identity':identity(raw),'maximum':maximum}
        return raw

    def source_inventory(root,expected):
        physical(root);names=set()
        for folder,dirs,files in os.walk(root,followlinks=False):
            for name in dirs:physical(Path(folder)/name)
            for name in files:names.add((Path(folder)/name).relative_to(root).as_posix())
        require(names==set(expected),'complete native source member set')
        for name,wanted in expected.items():
            relative=PurePosixPath(name)
            require(not relative.is_absolute() and '..' not in relative.parts and str(relative)==name,'safe source manifest path')
            require(identity(read_public(root/name,256*MIB))==wanted,'exact native source member')

    def load(path,name,wanted):
        pin(path,wanted)
        spec=importlib.util.spec_from_file_location(name,path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        pin(path,wanted);return module

    def command(label,argv,cwd,env,timeout,observer=observe,private=False):
        folder=output/('private' if private else 'commands')/label
        log,row=owned.run(folder,argv,cwd,env,timeout,observer,save,
                         lambda path:identity(read_public(path,LOG_CAP))['sha256'],report['commands'])
        # The native init log may contain only this new fixture's mnemonic.
        # It remains private; neither raw bytes nor decoded content are emitted.
        save_report();return log,row

    try:
        report['initialFreeBytes']=guard(True)
        require(int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024>=2*1024**3,'native memory admission')
        source_manifest=json_object(pin(SOURCE_MANIFEST,args.source_manifest_sha256))
        require(source_manifest['status']=='SOURCE_ONLY_PENDING_NATIVE_METHOD_WITH_COMPONENT35_COMPLETE','source admission status')
        require(source_manifest['nativeTestSHA256']==NATIVE_TEST_SHA,'exact separate native test')
        for name,wanted in source_manifest['files'].items():
            relative=PurePosixPath(name)
            require(not relative.is_absolute() and '..' not in relative.parts,'control source member path')
            require(identity(pin(HERE/name,wanted['sha256']))==wanted,'exact native-control source')
        pin(Path(__file__).resolve(),source_manifest['files']['run_native_upload.py']['sha256'])
        pin(HERE/'source_inputs/verify_current_authority_http.py',N_SOURCE_SHA)
        admission=load(HERE/'readguard_product_admission.py','ordinary_upload_native_admission',N_ADMISSION_SHA)
        owned=load(HERE/'owned_swift_commands.py','ordinary_upload_native_owned',HELPER_SHA)
        owned.install_interrupt_handlers()
        lifecycle=json_object(pin(HELPER_PROOF,HELPER_PROOF_SHA))
        require(lifecycle['status']=='PASS_FIVE_ACTUAL_OWNED_PROCESS_LIFECYCLE_CONTROLS' and lifecycle['helperSHA256']==HELPER_SHA and lifecycle['allOwnedGroupsPositivelyAbsent'],'actual reused lifecycle controls')
        require(len(lifecycle['methods'])==5 and all(row['status']=='PASS' for row in lifecycle['methods']),'five original lifecycle outcomes')
        deadline=json_object(pin(args.deadline_receipt,args.deadline_sha256))
        require(deadline['status']=='PASS_TWO_ACTUAL_HTTP_DEADLINES_AND_OWNED_CLOSURE' and deadline['allOwnedGroupsPositivelyAbsent'] and deadline['errors']==[] and deadline['completionErrors']==[],'actual absolute HTTP deadline controls')
        require(deadline['actualControls']['controllerSHA256']==DEADLINE_CONTROL_SOURCE_SHA and deadline['actualControls']['actualMethods']=={'runs':2,'failures':0,'errors':0,'skips':0},'exact two original deadline controls')
        original_deadline=pin(HERE/'source_inputs/original_deadline_controller.py',DEADLINE_CONTROL_SOURCE_SHA)
        current_deadline=pin(HERE/'source_inputs/verify_current_authority_http.py',N_SOURCE_SHA)
        require(exact_deadline_function(original_deadline)==exact_deadline_function(current_deadline),
                'current source uses the unchanged actually qualified deadline')
        report['reusedDeadlineControls']={'originalControllerSHA256':DEADLINE_CONTROL_SOURCE_SHA,
            'currentControllerSHA256':N_SOURCE_SHA,'decoratedFunctionSHA256':DEADLINE_FUNCTION_SHA,
            'actualReceiptSHA256':args.deadline_sha256,'newControlExecutions':0}
        native=admission.admit(args.native_receipt,args.native_sha256,pin,source_inventory)
        native_sources=native['expectedSource']
        report['nativeProducer']=native['qualification']
        # Actual HTTP method credit belongs to the immutable failed0526 run.
        # The later completion receipt supplies only its missing source audit.
        # Never rewrite either failure or manufacture a new command/test run.
        pin(HERE/'source_inputs/complete_upload_http_verification.py',HTTP_COMPLETION_SHA)
        completion=json_object(pin(args.component_receipt,args.component_sha256))
        require(source_manifest['componentCompletionReceipt']=={
                'path':str(args.component_receipt),'sha256':args.component_sha256,
                'controllerSHA256':HTTP_COMPLETION_SHA,
                'status':'PASS_COMPONENT35_WITH_REUSED23_REUSED_HTTP12_AND_COMPLETED_SOURCE_AUDIT'},
                'exact actual completion receipt declared by the frozen source manifest')
        require(completion['protocol']=='pinkha-ordinary-upload-http12-completion-v1' and
                completion['status']=='PASS_COMPONENT35_WITH_REUSED23_REUSED_HTTP12_AND_COMPLETED_SOURCE_AUDIT' and
                completion['controllerSHA256']==HTTP_COMPLETION_SHA and
                completion['originalComponentControllerSHA256']==COMPONENT_CONTROLLER_SHA and
                completion['inputManifestSHA256']==COMPONENT_MANIFEST_SHA,'exact reviewed completion-only qualification')
        require(completion['errors']==completion['completionErrors']==[] and
                completion['sourceUnchanged'] is True and completion['admittedInputsUnchanged'] is True and
                completion['compiledSourceInputsUnchanged'] is True and completion['compiledProductsAndModesUnchanged'] is True and
                completion['originalHTTPFixtureRootUnchangedAtCompletion'] is True,
                'completed exact source/Crypto/Products and original HTTP fixture audit')
        require(completion['commands']==[] and completion['newChildCommands']==completion['newTestMethods']==
                completion['newFixtureProcesses']==completion['compilerInvocations']==completion['priorPassingMethodsReplayed']==0 and
                completion['allStartedOwnedGroupsPositivelyAbsent'] is True and completion['completionSourceAuditOnly'] is True,
                'completion is source audit only with zero child or method credit')
        require(completion['nativeAccountsOpened'] is False and completion['originalFailureReclassified'] is False and
                completion['httpFailureReclassified'] is False and completion['productCensusIsLaterObservation'] is True and
                completion['separateNativeTestStatus']=='NOT_RUN' and completion['separateNativeTestStarts']==[],
                'completion preserves both original failures and excluded native method')
        require(completion['resourcePolicy']['finalizationSeconds']==60,'unchanged bounded completion verification')
        require(completion['originalHTTPReceipt']=={'path':str(HTTP_ROOT/'result.json'),
                'sha256':HTTP_RECEIPT_SHA,'status':'FAIL_HTTP12_CONTINUATION'} and
                completion['originalHTTPLog']=={'path':str(HTTP_ROOT/'commands/http12/original.log'),'sha256':HTTP_LOG_SHA},
                'completion linked to exact actual HTTP receipt and log')
        component=json_object(pin(HTTP_ROOT/'result.json',HTTP_RECEIPT_SHA))
        require(component['protocol']=='pinkha-ordinary-upload-http12-continuation-v1' and
                component['status']=='FAIL_HTTP12_CONTINUATION' and
                component['controllerSHA256']==HTTP_CONTINUATION_SHA and
                component['originalComponentControllerSHA256']==COMPONENT_CONTROLLER_SHA and
                component['inputManifestSHA256']==COMPONENT_MANIFEST_SHA,'immutable actual HTTP12 failure identity')
        require(component['errors']==[] and component['completionErrors']==[
                {'message':'bounded final verification','type':'AssertionError'}] and
                component['sourceUnchanged'] is False and component['compiledProductsAndModesUnchanged'] is True and
                component['allStartedOwnedGroupsPositivelyAbsent'] is True,
                'actual twelve passes retain only the observed final-audit timeout')
        require(component['compilerInvocations']==component['priorPassingMethodsReplayed']==0 and
                component['nativeAccountsOpened'] is False and component['originalFailureReclassified'] is False and
                component['productCensusIsLaterObservation'] is True,'no original-failure rewrite or invented producer census')
        require(len(component['commands'])==1 and all(row['exitCode']==0 and row['processGroupAbsent'] and
                not row['forcedCleanup'] and not row['cleanupErrors'] for row in component['commands']),
                'one clean HTTP-only skip-build command')
        require(component['actualMethods']['total']==component['actualMethods']['http']==12 and
                component['actualMethods']['host']==component['actualMethods']['pure']==component['actualMethods']['skipped']==0 and
                component['httpFixtureQualification']['instances']==26,'twelve new actual HTTP methods and26 owned fixtures')
        require(component['separateNativeTestStatus']=='NOT_RUN' and component['separateNativeTestStarts']==[],'new native method must not have run before')
        component_root=ORIGINAL_COMPONENT_ROOT
        require(component['originalComponentRoot']==completion['originalComponentRoot']==str(component_root),'fixed original retained package and build')
        component_manifest=json_object(pin(HERE/'source_inputs/upload-component-inputs.json',COMPONENT_MANIFEST_SHA))
        expected_methods={name+'.'+method for name,methods in component_manifest['methods'].items() for method in methods}
        http_methods={'AnyNativeFileUploadHTTPTests.'+method for method in component_manifest['methods']['AnyNativeFileUploadHTTPTests']}
        reused_methods=expected_methods-http_methods
        require(len(expected_methods)==35 and len(http_methods)==12 and len(reused_methods)==23,'finite component inventories')
        for action in ('started','passed'):
            require(Counter(component['actualMethods'][action])==Counter({name:1 for name in http_methods}),
                    'exact new HTTP method identities')
            require(Counter(component['qualifiedComponentMethods'][action])==Counter({name:1 for name in expected_methods}),
                    'exact aggregate of original23 and new12 passes')
            require(Counter(component['reusedMethods'][action])==Counter({name:1 for name in reused_methods}),
                    'exact unchanged actual23 reused methods')
        require(component['qualifiedComponentMethods']['total']==35 and
                component['qualifiedComponentMethods']['reusedActualPasses']==23 and
                component['qualifiedComponentMethods']['newActualPasses']==12 and
                component['qualifiedComponentMethods']['skipped']==0 and component['reusedMethods']['newExecutions']==0,
                'aggregate is explicitly23reused plus12new')
        require(completion['reusedMethods']==component['reusedMethods'] and
                completion['reusedHTTPMethods']==component['actualMethods'] and
                completion['reusedHTTPCommand']==component['commands'][0] and
                completion['httpFixtureQualification']==component['httpFixtureQualification'],
                'completion reuses the exact actual23 and HTTP12/26/one-group records')
        require(completion['qualifiedComponentMethods']=={
                'started':component['qualifiedComponentMethods']['started'],
                'passed':component['qualifiedComponentMethods']['passed'],
                'host':17,'pure':6,'http':12,'total':35,'skipped':0,
                'originalComponentActualPasses':23,'originalHTTPActualPasses':12,'newExecutions':0},
                'completion has no new method credit in the exact35-event aggregate')
        for name in ('compiledSourceInputs','productCensusBefore','retainedDependencyProducts','originalCompilerCommand',
                     'compiledProductsRoot','compiledProducts','compiledProductModes','compiledProductDirectories',
                     'compiledExecutables','compiledTestRunner'):
            require(completion[name]==component[name],'completion preserves the exact actual HTTP input/product binding: '+name)
        require(component['reusedMethods']['originalReceipt']=={
                'path':str(component_root/'result.json'),'sha256':ORIGINAL_COMPONENT_SHA,'status':'FAIL'},
                'original overall FAIL remains a distinct immutable receipt')
        original_component=json_object(pin(component_root/'result.json',ORIGINAL_COMPONENT_SHA))
        require(original_component['status']=='FAIL' and original_component['controllerSHA256']==COMPONENT_CONTROLLER_SHA and
                original_component['inputManifestSHA256']==COMPONENT_MANIFEST_SHA and original_component['sourceUnchanged'] and
                original_component['admittedInputsUnchanged'] and original_component['compiledSourceInputsUnchanged'] and
                original_component['allStartedOwnedGroupsPositivelyAbsent'],'exact original failed run with unchanged sources')
        require(len(original_component['commands'])==4 and [row['exitCode'] for row in original_component['commands']]==[0,0,0,1] and
                all(row['processGroupAbsent'] and not row['forcedCleanup'] and not row['cleanupErrors'] and not row['signals']
                    for row in original_component['commands']),'original four closed groups retain Swift exit1')
        require(original_component['separateNativeTestStatus']=='NOT_RUN' and original_component['separateNativeTestStarts']==[] and
                original_component['nativeAccountsOpened'] is False and 'compiledProducts' not in original_component,
                'original producer did not claim a later product census or native method')
        original_log=pin(component_root/'commands/swift-components/original.log',ORIGINAL_COMPONENT_LOG_SHA).decode()
        for action,wanted in [('started',expected_methods),('passed',reused_methods),('failed',http_methods)]:
            require(Counter(re.findall(r"Test Case '([^']+)' "+action,original_log))==Counter({name:1 for name in wanted}),
                    'original actual35/23/12 log events')
        require(len(re.findall(r'threw error "fixtureFailed"',original_log))==12 and
                'Build complete! (50.92 secs)' in original_log and
                not re.search(r"Test Case '[^']+' skipped|XCTSkip|Skipping XCTest discovery",original_log),
                'actual original compiler completion and fixture setup failures')
        http_command=component['commands'][0]
        require(http_command['logSHA256']==HTTP_LOG_SHA and http_command['signals']==[],'exact actual HTTP log and normal closure')
        http_log=pin(HTTP_ROOT/'commands/http12/original.log',HTTP_LOG_SHA).decode()
        for action in ('started','passed'):
            require(Counter(re.findall(r"Test Case '([^']+)' "+action,http_log))==Counter({name:1 for name in http_methods}),
                    'actual new HTTP-only log events')
        require('--skip-build' in http_command['argv'] and
                http_command['argv'][http_command['argv'].index('--filter')+1]=='AnyNativeFileUploadHTTPTests' and
                not re.search(r"Test Case '[^']+' (?:failed|skipped)|XCTSkip|Build complete!|Building for|\] Compiling",http_log),
                'continuation did not compile or replay an already passed method')
        report['componentQualification']={
            'protocol':'pinkha-ordinary-upload-component35-three-stage-chain-v1',
            'originalComponent':{'receiptSHA256':ORIGINAL_COMPONENT_SHA,'status':'FAIL',
                'actualPassesReused':23,'logSHA256':ORIGINAL_COMPONENT_LOG_SHA,'closedCommandCount':4},
            'actualHTTP':{'receiptSHA256':HTTP_RECEIPT_SHA,'status':'FAIL_HTTP12_CONTINUATION',
                'actualPassesReused':12,'fixtureCount':26,'logSHA256':HTTP_LOG_SHA,'closedCommandCount':1,
                'remainingFailure':'bounded final verification'},
            'sourceCompletion':{'receiptPath':str(args.component_receipt),'receiptSHA256':args.component_sha256,
                'controllerSHA256':HTTP_COMPLETION_SHA,'status':completion['status'],
                'newTestMethods':0,'newChildCommands':0,'commands':[],
                'completeSourceCryptoProductsVerified':True},
            'qualifiedMethods':35,'componentMethodReplays':0,'originalFailureReclassified':False,
            'httpFailureReclassified':False,'productCensusIsLaterObservation':True}
        require(completion['compiledSourceInputsUnchanged'] and completion['compiledProductsAndModesUnchanged'],
                'separate completion bound exact original source admission and complete Products closure')
        compiled_source_path=component_root/'compiled-source-inputs.json'
        compiled_source_binding=component['compiledSourceInputs']
        require(compiled_source_binding['path']==str(compiled_source_path),'original bound compiled-source admission path')
        require(compiled_source_binding==original_component['compiledSourceInputs'] and
                compiled_source_binding['sha256']==ORIGINAL_COMPILED_SOURCE_SHA and compiled_source_binding['bytes']==526113,
                'same original compiled-input binding, never a replacement manifest')
        compiled_source_raw=pin(compiled_source_path,compiled_source_binding['sha256'])
        require(identity(compiled_source_raw)=={key:compiled_source_binding[key] for key in ('bytes','sha256')},
                'compiled-source admission exact original producer bytes')
        component_source=json_object(compiled_source_raw)
        component_copies=component_source['isolatedCopies']
        require(component_source['counts']['productionCompiledFiles']==32 and component_source['counts']['compiledTestFiles']==4,'full32 production and4 test source closure')
        expected_copies={}
        for row in component_manifest['originalProjectFiles']:
            if row['compile']:expected_copies[str(component_root/'package/Sources'/row['target']/Path(row['path']).name)]={'bytes':row['bytes'],'sha256':row['sha256']}
        for row in component_manifest['originalCoreFiles']:
            expected_copies[str(component_root/'package/Sources/TorahInspectorCore'/Path(row['path']).name)]={'bytes':row['bytes'],'sha256':row['sha256']}
        for row in component_manifest['preparedSources']:
            if row['kind']=='production':target=component_root/'package/Sources'/row['target']/Path(row['path']).name
            elif row['kind'] in ('test','excluded-native-test'):target=component_root/'package/Tests/OrdinaryFileUploadTests'/Path(row['path']).name
            else:
                require(row['kind']=='fixture','finite original fixture kind')
                target=component_root/'package/Tests/Fixtures'/Path(row['path']).name
            expected_copies[str(target)]={'bytes':row['bytes'],'sha256':row['sha256']}
        require(len(expected_copies)==37,'32 production files,4 compiled tests and1 fixture')
        for name,wanted in expected_copies.items():require(component_copies.get(name)==wanted,'compiled source independently matches frozen manifest')
        package_source_members={str(path) for prefix in ('Sources','Tests') for path in (component_root/'package'/prefix).rglob('*') if path.is_file()}
        require(package_source_members==set(expected_copies),'complete compiled source set has no extra files')
        for name,wanted in component_copies.items():
            require(Path(name).is_relative_to(component_root),'owned component source/product copy')
            require(identity(pin(Path(name),wanted['sha256'],128*MIB))==wanted,'original compiled source copy')
        test_path=component_root/'package/Tests/OrdinaryFileUploadTests/AnyNativeFileUploadNativeRouteTests.swift'
        pin(test_path,NATIVE_TEST_SHA)
        compiled_products=component['compiledProducts']
        require(1<=len(compiled_products)<=2048,'bounded complete compiled product closure')
        products_root=component_root/'build/out/Products'
        require(component['compiledProductsRoot']==str(products_root),'original physical Products root')
        compiled_product_closure=product_inventory(products_root)
        census=component['productCensusBefore']
        require(census['path']==str(HTTP_ROOT/'retained-products-before.json'),
                'later product census has its own continuation evidence path')
        census_raw=pin(Path(census['path']),census['sha256'])
        require(identity(census_raw)=={key:census[key] for key in ('bytes','sha256')},'exact later census bytes')
        census_body=json_object(census_raw)
        require(census_body['phase']=='LATER_CENSUS_BEFORE_HTTP12_NOT_ORIGINAL_PRODUCER_OUTPUT' and
                census_body['originalReceiptSHA256']==ORIGINAL_COMPONENT_SHA and
                census_body['originalCompiledSourceInputsSHA256']==ORIGINAL_COMPILED_SOURCE_SHA and
                census_body['originalBuildLogSHA256']==ORIGINAL_COMPONENT_LOG_SHA and
                census_body['products']==compiled_product_closure,'explicit later full-product observation')
        for key,receipt_key in [('root','compiledProductsRoot'),('files','compiledProducts'),
                ('modes','compiledProductModes'),('directories','compiledProductDirectories'),
                ('executables','compiledExecutables'),('testRunner','compiledTestRunner')]:
            require(compiled_product_closure[key]==component[receipt_key],'exact producer Products '+key)
        for name,wanted in compiled_products.items():
            require(Path(name).is_relative_to(component_root/'build'),'original component compiled product path')
            require(identity(pin(Path(name),wanted['sha256'],128*MIB))==wanted,'original compiled product identity')
        swift_rows=[row for row in original_component['commands'] if row['argv'][1:2]==['test']]
        require(len(swift_rows)==1,'one original Swift component invocation')
        require(component['originalCompilerCommand']==swift_rows[0],'unchanged original compile command receipt')
        original_argv=swift_rows[0]['argv']
        require(original_argv.count('--filter')==1 and '--skip-build' not in original_argv,'original component selection')
        expected_driver=Path('/mnt/development/tooling/swiftly/toolchains/6.4.3/usr/bin/swift')
        physical_driver=expected_driver.with_name('swift-driver')
        require(expected_driver.is_symlink() and os.readlink(expected_driver)=='swift-driver' and expected_driver.resolve()==physical_driver,'one exact original Swift driver alias')
        expected_argv=[str(expected_driver),'test','--package-path',str(component_root/'package'),'--scratch-path',str(component_root/'build'),
            '--cache-path',str(component_root/'swift-cache'),'--config-path',str(component_root/'swift-config'),
            '--security-path',str(component_root/'swift-security'),'--disable-automatic-resolution','--jobs','2',
            '--filter','|'.join(component_manifest['methods'])]
        require(original_argv==expected_argv and swift_rows[0]['cwd']==str(component_root/'package'),'exact original compiler invocation and owned package')
        argv=list(original_argv)
        index=argv.index('--filter');argv[index+1]='AnyNativeFileUploadNativeRouteTests'
        argv.append('--skip-build')
        require(str(physical_driver) in component_source['originalInputs'],'original physical compiler input is present')
        driver_identity=component_source['originalInputs'][str(physical_driver)]
        require(driver_identity['sha256']=='39d41b0dc9eba623b0e37cea42c3145720168214ba4349d6fa3bd9db9b1e651a','original compiler fixed identity')
        require(identity(pin(physical_driver,driver_identity['sha256'],128*MIB))==driver_identity,'exact original Swift driver bytes')
        report['originalSwiftDriverAlias']={'path':str(expected_driver),'target':str(physical_driver)}
        pin(OFFLINE,OFFLINE_SHA);pin(OFFLINE_LIBRARY,OFFLINE_LIBRARY_SHA,4*MIB)
        policy=json_object(pin(OFFLINE_ACTUAL_PROOF,OFFLINE_ACTUAL_SHA))
        require(policy['offlinePolicy']['helperSHA256']==OFFLINE_SHA and policy['offlinePolicy']['actual']['librarySHA256']==OFFLINE_LIBRARY_SHA,'reuse exact previously observed OS policy only')
        report['offlinePolicy']={'helperSHA256':OFFLINE_SHA,'librarySHA256':OFFLINE_LIBRARY_SHA,'priorActualProofSHA256':OFFLINE_ACTUAL_SHA,'oldPermissionFailureRetained':True,'replayedProbe':False}
        local_nodeconf=native['source']/'internal/pinkha/migrationnative/testdata/local.yml'
        require('internal/pinkha/migrationnative/testdata/local.yml' in native_sources,'original local-only native fixture configuration')
        pin(local_nodeconf,native_sources['internal/pinkha/migrationnative/testdata/local.yml']['sha256'],65536)
        for name in ('private','commands','temporary'):(output/name).mkdir(mode=0o700)
        config=output/'native.yml'
        config.write_text('network:\n  nodeconfPath: '+str(local_nodeconf)+'\nindex:\n  embedder: none\np2p:\n  enabled: false\n  localDiscovery: false\n  global:\n    enabled: false\n')
        os.chmod(config,0o600)
        public_inputs[str(config)]={'identity':identity(config.read_bytes()),'maximum':65536}
        account_dir=output/'private/fresh-account'
        require(not account_dir.exists() and not account_dir.is_symlink(),'fresh account directory is exclusive and absent')
        environment={key:value for key,value in os.environ.items() if not key.startswith(('ANY_','PINKHA_','SWIFT_','SWIFTPM_','CLANG_','DYLD_','LD_'))}
        environment.update(ANY_DATA_DIR=str(account_dir),GOMAXPROCS='2',GOMEMLIMIT='512MiB',TMPDIR=str(output/'temporary'),GIT_OPTIONAL_LOCKS='0')
        python=str(Path(sys.executable).resolve())
        public_inputs[python]={'identity':identity(read_public(Path(python),32*MIB)),'maximum':32*MIB}
        report['accountInitializationIntent']={'directory':str(account_dir),'exclusiveNewDirectory':True,'priorAccountCopies':0}
        save_report()
        command('native-init',[python,'-B',str(OFFLINE),'--exec',str(native['binary']),'init','--config',str(config),'--data-dir',str(account_dir)],output,environment,30,private=True)
        report['accountInitializations']=1
        require(account_dir.is_dir() and account_dir.resolve()==account_dir,'new native account directory')
        payloads={'empty-inline':b'','sniffed-png-full':png_bytes()}
        sources=[]
        for label,filename,name,mime,inline in [('empty-inline','empty.bin','empty','',True),('sniffed-png-full','generated.png','ordinary-upload-proof','image/png',False)]:
            data=payloads[label];path=output/filename
            with path.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
            os.chmod(path,0o600)
            sources.append({'label':label,'relativePath':filename,'byteCount':len(data),'sha256':hashlib.sha256(data).hexdigest(),'nameHint':name,'mimeHint':'application/octet-stream','expectedName':name+('.png' if not inline else ''),'expectedMIME':mime,'inline':inline})
            public_inputs[str(path)]={'identity':identity(data),'maximum':MIB}
        scope={};acknowledgements={}

        def segment(value):
            require(isinstance(value,str) and 1<=len(value.encode())<=512 and not any(ord(c)<32 for c in value),'bounded exact native identity')
            return urllib.parse.quote(value,safe='')

        def run_phase(label,cold):
            phase={'name':label,'coldReopen':cold,'steps':[],'gracefulStopRequested':False}
            report['phases'].append(phase)
            with socket.socket() as reservation:reservation.bind(('127.0.0.1',0));port=reservation.getsockname()[1]
            base_url='http://127.0.0.1:'+str(port)
            process_index=len(report['commands']);phase_started=time.monotonic();done=False

            def request(method,path,body=None,expected=200,health=False,content=False):
                require(method in ('GET','POST'),'fixed method vocabulary')
                require(not cold or method=='GET','cold reopening must be read-only')
                if method=='POST':
                    require(path=='/v1/spaces' or path=='/v1/spaces/'+segment(scope['spaceID'])+'/objects','only original fresh setup mutation')
                    require(not any(r['method']=='POST' and r['path']==path for r in report['requests']),'setup mutation must not repeat')
                row={'phase':label,'method':method,'path':path,'stage':'dispatching','responseBodyReads':0}
                report['requests'].append(row);save_report();guard()
                response=None;connection=None
                try:
                    with admission.absolute_http_deadline(2 if health else 5):
                        original_error=None
                        try:
                            connection=http.client.HTTPConnection('127.0.0.1',port,timeout=2 if health else 5)
                            headers={'Connection':'close'}
                            raw_body=None if body is None else json.dumps(body,separators=(',',':')).encode()
                            if raw_body is not None:headers['Content-Type']='application/json'
                            connection.request(method,path,body=raw_body,headers=headers)
                            response=connection.getresponse();row['status']=response.status
                            if method!='POST':require(response.status==expected,'exact native HTTP status')
                            if health:raw=b''
                            else:
                                maximum=MIB if content else 65536
                                row['responseBodyReads']+=1;raw=response.read(maximum+1)
                                if method=='POST':
                                    # Retain the original bounded setup ACK before
                                    # status/JSON/ID checks or fallible transport close.
                                    ack_path=output/'private'/('setup-ack-'+str(len(report['requests']))+'.body')
                                    descriptor=os.open(ack_path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
                                    with os.fdopen(descriptor,'wb') as stream:
                                        stream.write(raw);stream.flush();os.fsync(stream.fileno())
                                    descriptor=os.open(ack_path.parent,os.O_RDONLY|os.O_DIRECTORY)
                                    try:os.fsync(descriptor)
                                    finally:os.close(descriptor)
                                    retained_setup_files[str(ack_path)]={'identity':identity(raw),'maximum':65537}
                                    row['unvalidatedSetupAcknowledgement']={'path':str(ack_path),'status':response.status,'completeBody':len(raw)<=maximum,
                                        'boundedPrefixOnly':len(raw)>maximum,**identity(raw)}
                                    save_report()
                                require(len(raw)<=maximum,'bounded native response')
                            require(response.status==expected,'exact native HTTP status')
                        except BaseException as error:
                            original_error=error
                            raise
                        finally:
                            close_errors=[]
                            for handle in (response,connection):
                                if handle is not None:
                                    try:handle.close()
                                    except BaseException as error:close_errors.append(error)
                            if close_errors:
                                row['closeErrors']=[type(error).__name__ for error in close_errors]
                                if original_error is None:raise close_errors[0]
                    row['response']=identity(raw);row['stage']='received';save_report()
                    decoded=raw if content else ({} if health else json_object(raw))
                    if method=='POST':
                        decoded_path=ack_path.with_suffix('.decoded.json')
                        # This is still unvalidated setup data: the caller has
                        # not selected or accepted its Space/object identity yet.
                        save(decoded_path,{'status':row['status'],'decodedUnvalidated':decoded})
                        retained_setup_files[str(decoded_path)]={'identity':identity(read_public(decoded_path,4*MIB)),'maximum':4*MIB}
                        row['unvalidatedDecodedSetupAcknowledgement']={'path':str(decoded_path),**retained_setup_files[str(decoded_path)]['identity']}
                        save_report()
                    return decoded
                except BaseException as error:
                    row['stage']='failed';row['failureType']=type(error).__name__;save_report();raise

            def require_owner():
                observed=request('GET','/v1/spaces/'+segment(scope['spaceID'])+'/members/me')
                require({key:observed.get(key) for key in ('identity','status','permission')}=={'identity':scope['accountID'],'status':'active','permission':'owner'},'exact current new-fixture owner')

            def native_steps():
                account=request('GET','/v1/account')
                account_id=account.get('id');segment(account_id)
                if cold:require(account_id==scope['accountID'],'same fresh account on new OS-offline process')
                else:
                    require(account_id not in (admission.native_source.OWNER,admission.native_source.MEMBER),'new fixture identity must differ from public retained baseline')
                    scope['accountID']=account_id
                    space=request('POST','/v1/spaces',{'name':'Ordinary upload fresh native proof'},201)
                    scope['spaceID']=space.get('id');segment(scope['spaceID'])
                    obj=request('POST','/v1/spaces/'+segment(scope['spaceID'])+'/objects',{'type':'page'},201)
                    scope['objectID']=obj.get('objectId');segment(scope['objectID'])
                require_owner()
                list_path='/v1/spaces/'+segment(scope['spaceID'])+'/files?'+urllib.parse.urlencode({'objectId':scope['objectID']})
                before=request('GET',list_path)
                require(set(before)=={'files'} and isinstance(before['files'],list),'exact native file-list envelope')
                if not cold:
                    require(before['files']==[],'new fixture object starts without files')
                    input_path=output/'native-upload-input.json'
                    save(input_path,dict(schema=1,baseURL=base_url,controlToken=None,**scope,files=sources))
                    require(input_path.stat().st_mode&0o777==0o600,'private bounded Swift fixture input')
                    swift_env=dict(environment,PINKHA_ORDINARY_NATIVE_UPLOAD_INPUT=str(input_path))
                    log,_=command('swift-native-only',argv,component_root/'package',swift_env,90)
                    text=read_public(log,LOG_CAP).decode()
                    starts=re.findall(r"Test Case '([^']+)' started",text)
                    passes=re.findall(r"Test Case '([^']+)' passed",text)
                    require(starts==passes==[NATIVE_TEST],'one and only one actual new native Swift method')
                    require(not re.search(r"Test Case '[^']+' (?:failed|skipped)|XCTSkip|Skipping XCTest discovery",text),'no skipped or failed native method')
                    require(re.search(r'Executed 1 tests?, with 0 failures',text),'actual native XCTest summary')
                    report['executedSwiftMethods']=1
                    observations=json_object(read_public(output/'swift-native-observations.json',16384))
                    require(observations['status']=='NATIVE_ROUTE_OBSERVED_REQUIRES_XCTEST_AND_CONTROLLER_QUALIFICATION' and observations['productionJournalQualified'] is False and observations['cloudQualified'] is False,'exact native test observation status')
                    rows=observations['rows'];require(len(rows)==4,'two original native acknowledgements and two verified reads')
                    for index,source in enumerate(sources):
                        ack=rows[index*2];verified=rows[index*2+1]
                        require(ack['stage']=='acknowledged' and verified['stage']=='verified' and ack['label']==verified['label']==source['label'],'native receipt and digest order')
                        require(ack['fileID']==verified['fileID'] and ack['byteCount']==verified['byteCount']==source['byteCount'] and verified['contentSHA256']==source['sha256'],'original receipt identity and exact payload')
                        require(ack['name']==source['expectedName'] and ack['mime']==source['expectedMIME'] and ack['inline'] is source['inline'] and ack['cached'] is True and ack['durable'] is source['inline'],'resolved metadata and local custody')
                        segment(ack['fileID']);acknowledgements[source['label']]=ack
                    require(len({row['fileID'] for row in acknowledgements.values()})==2,'distinct native file identities')
                    report['nativeObservations']=observations
                after=request('GET',list_path)
                require(set(after)=={'files'} and len(after['files'])==2,'exactly two committed file rows')
                by_id={value['fileId']:value for value in after['files']}
                require(set(by_id)=={ack['fileID'] for ack in acknowledgements.values()},'native original file IDs stable across reopen')
                for source in sources:
                    ack=acknowledgements[source['label']];metadata=by_id[ack['fileID']]
                    wanted={'objectId':scope['objectID'],'size':source['byteCount'],'name':source['expectedName'],'mime':source['expectedMIME'],'inline':source['inline'],'rootCid':ack['rootCID']}
                    def equal_metadata(value):
                        for key,wanted_value in wanted.items():
                            require(value.get(key,'' if key in ('name','mime') else None)==wanted_value,'immutable native attachment metadata')
                        require(value['cached'] is True and value['durable'] is source['inline'],'exact local-only file custody')
                    equal_metadata(metadata)
                    if cold:
                        route='/v1/spaces/'+segment(scope['spaceID'])+'/files/'+segment(ack['fileID'])
                        equal_metadata(request('GET',route))
                        raw=request('GET',route+'/content',content=True)
                        require(identity(raw)=={'bytes':source['byteCount'],'sha256':source['sha256']},'cold OS-offline original exact plaintext bytes')
                        equal_metadata(request('GET',route))
                require_owner()
                sync=request('GET','/v1/spaces/'+segment(scope['spaceID'])+'/sync-status')
                require(all(sync.get(key)==0 for key in ('networkPeers','localPeers','globalPeers')),'fresh native OS-offline process has no peers')
                phase['steps']=['same-new-account','current-owner','exact-two-files','content-and-metadata-verified','current-owner-final','zero-peers']
                phase['status']='PASS_PHASE';report['scope']=dict(scope);save_report()

            def service_observer():
                nonlocal done
                try:
                    guard()
                    if len(report['commands'])<=process_index:return None
                    row=report['commands'][process_index]
                    if row.get('exitCode') is not None or row.get('processGroupAbsent'):return None
                    if 'pid' not in row or phase['gracefulStopRequested']:return None
                    pid=row['pid']
                    require(os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None,'owned native service exited before its stop')
                    require(os.getpgid(pid)==pid and os.getsid(pid)==pid,'live original native process ownership')
                    if not done:
                        try:request('GET','/v1/health',health=True)
                        except (OSError,http.client.HTTPException):
                            require(time.monotonic()-phase_started<60,'bounded fresh native startup');return None
                        status=dict(line.split(':',1) for line in Path('/proc/'+str(pid)+'/status').read_text().splitlines() if ':' in line)
                        require(status['NoNewPrivs'].strip()=='1' and status['Seccomp'].strip()=='2' and Path('/proc/'+str(pid)+'/exe').resolve()==native['binary'],'actual OS denial inherited before native startup')
                        phase['osDenial']={'noNewPrivileges':True,'seccompFilterMode':2,'nativeExecutable':str(native['binary'])}
                        native_steps();done=True
                        # The nested Swift command has fully closed before
                        # returning here. Recheck this still-unreaped service.
                        require(os.waitid(os.P_PID,pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is None,'native service must still own its lifetime')
                    phase['gracefulStopIntent']={'signal':int(signal.SIGTERM),'leaderUnreaped':True}
                    save_report();os.killpg(pid,signal.SIGTERM)
                    phase['gracefulStopRequested']=True;row['expectedServiceShutdown']=True
                    save_report();return None
                except BaseException as error:
                    phase.setdefault('error',{'type':type(error).__name__,'message':str(error)})
                    return type(error).__name__+': '+str(error)

            service_argv=[python,'-B',str(OFFLINE),'--exec',str(native['binary']),'run','--config',str(config),'--data-dir',str(account_dir),'--addr','127.0.0.1:'+str(port)]
            _,row=command(label,service_argv,output,environment,240,service_observer)
            require(done and phase['status']=='PASS_PHASE' and phase['gracefulStopRequested'],'complete fresh native phase')
            require(row['exitCode']==0 and row['processGroupAbsent'] and not row['forcedCleanup'] and row['cleanupErrors']==[],'normal fresh native service closure')

        run_phase('native-warm',False)
        run_phase('native-cold-offline',True)
        require(len(report['commands'])==4,'one fresh init, two original native services and one Swift skip-build command')
        require(report['executedSwiftMethods']==1 and report['accountInitializations']==1,'exact actual proof scope')
        require(len([row for row in report['requests'] if row['method']=='POST'])==2,'one Space and one object setup mutation')
        report.update(status='PASS_FRESH_NATIVE_UPLOAD2_AND_OS_OFFLINE_REOPEN_ONLY',actualAttachments=2,
                      coldOfflineReads=2,normalNativeReopens=1,setupMutations=2,controllerRetryRequests=0,
                      actualAdapterDispatchApprovals=2,nativeProcessesOSDenialVerified=True)
    except BaseException as error:
        report['status']='FAIL_FRESH_NATIVE_UPLOAD_PRESERVED'
        report['errors'].append({'type':type(error).__name__,'message':str(error)})
    finally:
        for number in (signal.SIGTERM,signal.SIGINT):signal.signal(number,signal.SIG_IGN)
        report['allOwnedGroupsPositivelyAbsent']=bool(report['commands']) and all(row.get('processGroupAbsent') for row in report['commands'])
        final_started=time.monotonic()
        try:
            for name,wanted in public_inputs.items():
                require(time.monotonic()-final_started<60,'bounded final public source/product verification')
                require(identity(read_public(Path(name),wanted['maximum']))==wanted['identity'],'original public input changed at completion')
            if native is not None and native_sources is not None:source_inventory(native['source'],native_sources)
            if compiled_product_closure is not None:
                require(product_inventory(Path(compiled_product_closure['root']))==compiled_product_closure,
                        'complete original Products bytes, modes, runner and membership unchanged')
            for name,wanted in retained_setup_files.items():
                require(identity(read_public(Path(name),wanted['maximum']))==wanted['identity'],
                        'original privately retained setup acknowledgement changed')
            report['retainedSetupAcknowledgementFilesUnchanged']=True
            if 'originalSwiftDriverAlias' in report:
                alias=Path(report['originalSwiftDriverAlias']['path']);target=Path(report['originalSwiftDriverAlias']['target'])
                require(alias.is_symlink() and os.readlink(alias)=='swift-driver' and alias.resolve()==target,'original compiler alias unchanged')
            require(time.monotonic()-final_started<60,'bounded final source verification')
            report['publicInputsAndCompiledProductsUnchanged']=True
            if report['status'].startswith('PASS_'):
                require(report['allOwnedGroupsPositivelyAbsent'] and len(report['commands'])==4,'all actual owned groups closed')
                require(all(row['exitCode']==0 and not row['forcedCleanup'] and not row['cleanupErrors'] for row in report['commands']),'all owned commands completed normally')
            report['finalFreeBytes']=guard(final=True)
        except BaseException as error:
            report['status']='FAIL_FRESH_NATIVE_UPLOAD_PRESERVED'
            report['completionErrors'].append({'type':type(error).__name__,'message':str(error)})
        save_report()
    print(json.dumps({'status':report['status'],'receipt':str(output/'result.json'),
                      'sha256':identity(read_public(output/'result.json',4*MIB))['sha256'],
                      'executedSwiftMethods':report['executedSwiftMethods'],
                      'allOwnedGroupsPositivelyAbsent':report['allOwnedGroupsPositivelyAbsent'],
                      'errors':report['errors'],'completionErrors':report['completionErrors']}))
    return 0 if report['status'].startswith('PASS_') else 1


if __name__=='__main__':
    raise SystemExit(main())
