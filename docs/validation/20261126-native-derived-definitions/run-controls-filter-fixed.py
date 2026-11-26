from pathlib import Path
import hashlib, json, os, re, signal, subprocess, time, shutil

ROOT = Path('/mnt/development/projects/worktrees/anytype-migration-final-20261125')
CACHE = Path('/tmp/pinkha-c-swift-cache-20261125')
OUTPUT = Path('/mnt/development/projects/evidence/migration-final-20261125/native-derived-definitions/controls-attempt2')
TESTS = [
    'testNativeDerivedDefinitionsBindActualNativeFieldsWithoutMutableShadows',
    'testNativeDerivedSourceClocksAndParticipantsRemainHistoricalFacts',
    'testChangedDerivedDefinitionAndParticipantTypeCannotAcquireCanonicalCoverage',
    'testCanonicalSystemIdentityDefinitionsUseOriginalNativeAddressesAndTargetEvidence',
    'testCanonicalSystemIdentityConsumesOnlyMatchingContextWithoutPropertyWrites',
    'testCanonicalSystemIdentityOverridesAndForeignCapturedTargetTypeRefuse',
    'testCanonicalDescriptionSharesNativeNamespaceWithoutChangingTitleIdentity',
    'testCanonicalDescriptionRefusesOverridesAndRequiresExactLiveDescriptor',
    'testCanonicalNameHasOneNativeAddressAndMixedOwnerValuesPreserveAbsence',
    'testCanonicalNameOverridesShadowingAndChangedNativeContractsRefuse',
    'testOriginalCustomCaptureMapsCurrentChoicesAndValuesWithoutPromotingSourceAcceptance',
]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, value): p.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')
def sources():
    roots = ['Modules/PinkhaAnyHost', 'Modules/PinkhaAnyEngine', 'Modules/PinkhaAnyIntegration', 'Modules/PinkhaKit']
    raw = subprocess.check_output(['git', '-c', 'safe.directory='+str(ROOT), '-C', str(ROOT), 'ls-files', '-z', '--'] + roots)
    paths = sorted(p.decode() for p in raw.split(b'\0') if p and (p.endswith(b'.swift') or p.endswith(b'/Package.resolved')))
    return {p: digest(ROOT/p) for p in paths}

os.umask(0o077)
OUTPUT.mkdir(mode=0o700, parents=True, exist_ok=False)
start = time.monotonic(); child = None; group_absent = False
result = {'protocol': 'pinkha-native-derived-definitions-component-v1', 'status': 'RUNNING',
          'scope': 'four native derived definitions, unchanged prior canonical controls and exact original156 projection',
          'nativeCalls': 0, 'wholeSpaceMigration': False, 'sourceAdmission': False,
          'expectedMethods': TESTS, 'errors': []}
def persist():
    result['elapsedSeconds'] = round(time.monotonic()-start, 3); save(OUTPUT/'result.json', result)
def absent():
    global group_absent
    if group_absent: return True
    try: os.killpg(child.pid, 0)
    except ProcessLookupError: group_absent = True
    return group_absent
def interrupted(signum, frame): raise RuntimeError('owned component controller interrupted')
signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
try:
    before = sources(); save(OUTPUT/'source-before.json', before)
    deps = json.loads((CACHE/'workspace-state.json').read_bytes())['object']['dependencies']
    save(OUTPUT/'dependencies-before.json', deps)
    result['sourceCommit'] = subprocess.check_output(['git','-c','safe.directory='+str(ROOT),'-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
    result['freeBytesBefore'] = shutil.disk_usage(CACHE).free
    result['resourceRationale'] = 'One warmed Swift component compiler/test, two package workers; no native or Apple compilation. Changed three Swift sources. Estimated extra compiler/log footprint512MiB, emergency floor256MiB on this Oracle scratch filesystem.'
    assert result['freeBytesBefore'] >= 768*1024*1024
    command = ['/usr/local/bin/swift','test','--skip-build','--package-path',str(ROOT/'Modules/PinkhaAnyHost'),
        '--scratch-path',str(CACHE),'--jobs','2','--filter',
        'NativeDefinitionPlanTests[/.]('+'|'.join(TESTS)+')$']
    save(OUTPUT/'command.json', command)
    env=os.environ.copy();env['PINKHA_NATIVE_CUSTOM_CAPTURE_FIXTURE']='/mnt/development/projects/evidence/migration-final-20261125/native-head-census/original-source-recovery/original156'
    with (OUTPUT/'original.log').open('wb') as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
        result['pid']=child.pid;persist()
        deadline=time.monotonic()+900
        while child.poll() is None:
            assert time.monotonic()<deadline,'component deadline'
            assert shutil.disk_usage(CACHE).free>=256*1024*1024,'component emergency floor'
            time.sleep(.5)
        result['exitCode']=child.wait();result['ownedGroupAbsent']=absent();persist()
    after=sources();save(OUTPUT/'source-after.json',after)
    dep_after=json.loads((CACHE/'workspace-state.json').read_bytes())['object']['dependencies']
    save(OUTPUT/'dependencies-after.json',dep_after)
    result['sourceUnchanged']=before==after;result['dependenciesUnchanged']=deps==dep_after
    original=(OUTPUT/'original.log').read_text(errors='replace')
    passed=re.findall(r"Test Case 'NativeDefinitionPlanTests\.([^']+)' passed",original)
    result['passedMethods']=passed;result['logSHA256']=digest(OUTPUT/'original.log')
    assert result['exitCode']==0 and result['ownedGroupAbsent']
    assert result['sourceUnchanged'] and result['dependenciesUnchanged']
    assert len(passed)==len(TESTS) and set(passed)==set(TESTS)
    assert 'Executed 11 tests, with 0 failures' in original and 'skipped' not in original.lower()
    result['status']='PASS_COMPONENT_ONLY'
except BaseException as error:
    result['status']='FAIL';result['errors'].append({'type':type(error).__name__,'error':str(error)})
finally:
    if child is not None:
        try:
            if child.poll() is None and not absent():
                os.killpg(child.pid,signal.SIGTERM)
                child.wait(timeout=30)
            if not absent(): raise RuntimeError('owned group unresolved after exit; no historical group signal')
            result['ownedGroupAbsent']=True
        except BaseException as error:
            result['status']='FAIL';result['errors'].append({'cleanup':type(error).__name__,'error':str(error)})
    persist()
print(json.dumps({'status':result['status'],'path':str(OUTPUT),'sha256':digest(OUTPUT/'result.json'),'passed':len(result.get('passedMethods',[]))}))
raise SystemExit(0 if result['status']=='PASS_COMPONENT_ONLY' else 1)
