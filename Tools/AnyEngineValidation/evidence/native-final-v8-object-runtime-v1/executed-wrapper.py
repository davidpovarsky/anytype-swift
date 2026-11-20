#!/usr/bin/env python3
"""Run unchanged historical peer16 behavior on exact frozen v8, with owned cleanup."""
from pathlib import Path
from datetime import datetime,timezone
import difflib,hashlib,importlib.util,json,os,re,shutil,subprocess,sys

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
ANY=Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119');SDK=ANY/'.runtime-artifacts/sdk-source'
EVIDENCE=APP/'Tools/AnyEngineValidation/evidence'
ORIGINAL=EVIDENCE/'native-final-v7-object-scripts'
OUT=APP/'build/any-engine-port/native-final-v8-object-runtime-v1'
PRIVATE=ANY/'.runtime-artifacts/native-final-v8-object-runtime-v1-private'
BINARY=ANY/'.runtime-artifacts/any-native-properties-v8.exe'
BINARY_SHA='4856c7214f56dded249095624ea63e3f99b4b340483e8e6f2785163d16a98089'
MANIFEST=EVIDENCE/'native-conditional-properties-v8-source.json'
MANIFEST_SHA='484d377a89b3e53ccab28bbf8defe223441e85db398c40ee5626d71ddc521289'
BASELINE=EVIDENCE/'native-final-v7-object-runtime.json'
BASELINE_SHA='d4dc478a0b273c6e5b44182e5908a6d8ba1ee42d8f56c8429c7a9abddd0c9277'
PINNED_SCRIPTS={'run_native_object_validation.py':'b23086005f33d9911701e6280ba93c8a8a43eb6586f72a853cabc77c4da5d97b','run_native_validation.py':'10e0c4908621efa5033875e5c5eeff6ca6497ca6a3ce6a37c328b95fb9149f76','run_runtime_validation.py':'be81030a5b98ecbb574832429b62e87afcaa498d4d7b10625958a7b97fc32984'}
PROCESS_HELPER=APP/'Tools/AnyEnginePort/run_live_provider_probe.py'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf8')
def need(test,message):
    if not test:raise RuntimeError(message)
def ps(script):
    p=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',"$ErrorActionPreference='Stop'; "+script],capture_output=True,encoding='utf8',errors='replace',timeout=45)
    need(p.returncode==0,'owned_firewall_observation_or_cleanup_failed')
    return json.loads(p.stdout) if p.stdout.strip() else []
def quoted(s):return "'"+str(s).replace("'","''")+"'"
def owned_programs():
    roots=[p for p in PRIVATE.iterdir() if p.is_dir() and p.name.startswith('pinkha-object-validation-')]
    need(len(roots)<=1,'unexpected_owned_peer_root_count')
    paths=[]
    for root in roots:
        for name in ('a','b'):
            p=root/name/'any.exe'
            if p.exists():
                need(p.resolve().is_relative_to(PRIVATE.resolve()) and sha(p)==BINARY_SHA,'owned_peer_executable_identity_changed')
                paths.append(p.resolve())
    return paths

def active_rules(paths):
    if not paths:return []
    programs='@('+','.join(quoted(p) for p in paths)+')'
    value=ps("$programs="+programs+"; $rows=@(Get-NetFirewallRule -PolicyStore ActiveStore -Name 'PinkhaAnyValidation-*' -ErrorAction SilentlyContinue | ForEach-Object { $r=$_; $a=$r | Get-NetFirewallApplicationFilter; if($programs -contains $a.Program){ [pscustomobject]@{name=$r.Name;program=$a.Program;enabled=$r.Enabled.ToString();direction=$r.Direction.ToString();action=$r.Action.ToString()} } }); ConvertTo-Json -InputObject $rows -Compress")
    return value if isinstance(value,list) else [value]

def cleanup_owned():
    paths=owned_programs();before=active_rules(paths);removed=[]
    allowed={str(p).casefold() for p in paths}
    for rule in before:
        need(re.fullmatch(r'PinkhaAnyValidation-[0-9a-fA-F-]{36}',rule['name']) is not None,'unexpected_owned_rule_name')
        need(str(Path(rule['program']).resolve()).casefold() in allowed,'refusing_nonowned_firewall_rule')
        ps('Remove-NetFirewallRule -Name '+quoted(rule['name'])+' -PolicyStore PersistentStore')
        removed.append(rule['name'])
    after=active_rules(paths);need(not after,'owned_firewall_removal_not_verified')
    if paths:
        programs='@('+','.join(quoted(p) for p in paths)+')'
        processes=ps("$programs="+programs+"; $matches=@(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and ($programs -contains $_.ExecutablePath) } | Select-Object ProcessId,ExecutablePath); ConvertTo-Json -InputObject $matches -Compress")
        processes=processes if isinstance(processes,list) else [processes]
        need(not processes,'owned_peer_process_still_running')
    return {'privateExecutableCount':len(paths),'privateExecutableSHA256':BINARY_SHA,'leftoverRulesBeforeFallback':before,'fallbackRemovedRuleNames':removed,'remainingOwnedRules':0,'remainingOwnedProcesses':0,'sharedRulesOrGlobalProfilesModified':False}

def prepare():
    need(sha(BINARY)==BINARY_SHA and sha(MANIFEST)==MANIFEST_SHA and sha(BASELINE)==BASELINE_SHA,'pinned_native_input_changed')
    native=json.loads(MANIFEST.read_text(encoding='utf8'))
    build=json.loads((EVIDENCE/'native-conditional-properties-v8-build/result.json').read_text(encoding='utf8'))
    need(build['status']=='PASS' and build['sourceStable'],'native_build_not_verified')
    harness=OUT/'harness';harness.mkdir()
    for name,expected in PINNED_SCRIPTS.items():
        need(sha(ORIGINAL/name)==expected,'prior_executed_script_pin_changed')
        shutil.copy2(ORIGINAL/name,harness/name)
    pins={'nativeManifestSHA256':MANIFEST_SHA,'roots':{str(root.resolve()):{'expected':build['sourceAfter'][label],'testedEffectiveTree':native[label]['testedEffectiveTree']} for label,root in [('any',ANY),('sdk',SDK)]}}
    write(harness/'source-pins.json',pins)
    original=(harness/'run_native_validation.py').read_text(encoding='utf8')
    begin=original.index('\ndef source_manifest(repo):');end=original.index('\nclass NativeRepo:',begin)
    old=original[begin:end]
    new='''
def source_manifest(repo):
    # Frozen v8 deliberately has an existing parent commit plus a tested
    # effective tree. Enforce all exact sealed build input bytes, including
    # new Go files; never mislabel the parent as a clean v8 source commit.
    pins_file=Path(__file__).with_name('source-pins.json')
    require(digest(pins_file)==PINS_DIGEST,'frozen source pin file changed')
    pins=json.loads(pins_file.read_text(encoding='utf8'))
    repo=Path(repo).resolve();entry=pins['roots'].get(str(repo))
    require(entry is not None,'unrecognized frozen native source root')
    def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(repo),*args],encoding='utf8',timeout=30).strip()
    head=git('rev-parse','HEAD')
    paths=sorted({p for p in git('ls-files','--cached','--others','--exclude-standard').splitlines() if p.endswith('.go') or p in ('go.mod','go.sum')})
    files={p:digest(repo/p) for p in paths}
    require(head==entry['expected']['gitHEAD'] and files==entry['expected']['files'],'frozen effective native source differs from exact tested build')
    return {'commit':head,'testedEffectiveTree':entry['testedEffectiveTree'],'workingTreeIncludesExplicitV8Changes':True,'nativeManifestSHA256':pins['nativeManifestSHA256'],'files':files,'manifestSHA256':hashlib.sha256(json.dumps(files,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
'''.replace('PINS_DIGEST',repr(sha(harness/'source-pins.json')))
    changed=original[:begin]+new+original[end:]
    need(changed[:begin]+old+changed[begin+len(new):]==original,'unexpected_business_helper_edit')
    (harness/'run_native_validation.py').write_text(changed,encoding='utf8',newline='\n')
    diff=''.join(difflib.unified_diff(original.splitlines(True),changed.splitlines(True),fromfile='prior/run_native_validation.py',tofile='v8/run_native_validation.py'))
    (OUT/'provenance-only.diff').write_text(diff,encoding='utf8')
    for p in harness.glob('*.py'):compile(p.read_bytes(),str(p),'exec')
    need(sha(harness/'run_native_object_validation.py')==PINNED_SCRIPTS['run_native_object_validation.py'],'main16 assertions changed')
    need(sha(harness/'run_runtime_validation.py')==PINNED_SCRIPTS['run_runtime_validation.py'],'HTTP or firewall helper changed')
    receipt={'main16ByteIdenticalToPrior':True,'httpAndFirewallHelperByteIdenticalToPrior':True,'onlyHelperAdaptation':'source_manifest provenance function','priorScriptsSHA256':PINNED_SCRIPTS,
             'executedScriptsSHA256':{p.name:sha(p) for p in harness.glob('*.py')},'sourcePinsSHA256':sha(harness/'source-pins.json'),'provenanceDiffSHA256':sha(OUT/'provenance-only.diff'),'nativeManifestSHA256':MANIFEST_SHA,'nativeBinarySHA256':BINARY_SHA,'largeSpaceProofEnabled':False}
    write(OUT/'prepared.json',receipt)
    return harness,receipt

def main():
    OUT.mkdir(parents=True,exist_ok=False);PRIVATE.mkdir(parents=True,exist_ok=False)
    result={'status':'FAIL','scope':'Exact prior16 native two-peer partition/rejoin/object-history/watch assertions on frozenv8; no10001 scale repeat, no production account/fixture use.','startedAtUTC':datetime.now(timezone.utc).isoformat(),'nativeManifestSHA256':MANIFEST_SHA,'nativeBinarySHA256':BINARY_SHA}
    prepared=None
    try:
        harness,prepared=prepare();result['provenance']=prepared
        shutil.copyfile(__file__,OUT/'executed-wrapper.py');shutil.copyfile(PROCESS_HELPER,OUT/'executed-process-helper.py')
        result['wrapperSHA256']=sha(Path(__file__));result['processHelperSHA256']=sha(PROCESS_HELPER)
        spec=importlib.util.spec_from_file_location('bounded',PROCESS_HELPER);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
        # Only this child's process environment selects its wholly new private
        # temp parent. Existing account directories and app fixtures are absent.
        os.environ['TEMP']=str(PRIVATE);os.environ['TMP']=str(PRIVATE)
        stage=OUT/'run';stage.mkdir()
        command=[sys.executable,str(harness/'run_native_object_validation.py'),'--binary',str(BINARY),'--expected-binary-sha256',BINARY_SHA,'--runtime-source',str(ANY),'--sdk-source',str(SDK),'--result',str(OUT/'native-runtime-result.json')]
        result['process']=helper.run_process(command,harness,stage,1000);write(OUT/'process.json',result['process'])
        raw=json.loads((OUT/'native-runtime-result.json').read_text(encoding='utf8'))
        baseline=json.loads(BASELINE.read_text(encoding='utf8'))
        expected=[c['name'] for c in baseline['checks']]
        need(len(expected)==16 and [c['name'] for c in raw['checks']]==expected,'original16 selection changed or did not finish')
        need(raw['status']=='PASS_NATIVE_OBJECT_SCOPE_END_TO_END' and all(c['status']=='PASS' for c in raw['checks']),'native_peer_workflow_failed')
        need('unrelatedSignedClaims' not in raw,'unrequested_scale_phase_executed')
        need(len(raw.get('firewallRules',[]))==2 and all(r.get('activeVerified') and r.get('removalVerified') and not r.get('existingRulesModified') and not r.get('globalProfileChanges') and r['privateExecutableSHA256']==BINARY_SHA for r in raw['firewallRules']),'native_firewall_cleanup_proof_incomplete')
        p=result['process'];need(p.get('exitCode')==0 and not p.get('timedOut') and not p.get('cleanupErrors') and not p.get('runnerErrorType'),'bounded_native_process_failed')
        result.update(status='PASS_FINAL_NATIVE_V8_PEER16',checks=16,rawResultSHA256=sha(OUT/'native-runtime-result.json'),sourceStable=True,baselineReceiptSHA256=BASELINE_SHA)
    except Exception as error:
        result['errorType']=type(error).__name__
        if type(error) is RuntimeError:result['errorCode']=str(error)
    finally:
        try:result['independentOwnedCleanup']=cleanup_owned()
        except Exception as error:result['status']='FAIL';result['cleanupFailureType']=type(error).__name__;result['cleanupFailureCode']=str(error)[:180]
        result['binaryStable']=sha(BINARY)==BINARY_SHA;result['manifestStable']=sha(MANIFEST)==MANIFEST_SHA
        if prepared:
            result['harnessStable']=all(sha(OUT/'harness'/name)==expected for name,expected in prepared['executedScriptsSHA256'].items()) and sha(OUT/'harness/source-pins.json')==prepared['sourcePinsSHA256']
        else:result['harnessStable']=False
        result['wrapperStable']=sha(Path(__file__))==result.get('wrapperSHA256')
        result['processHelperStable']=sha(PROCESS_HELPER)==result.get('processHelperSHA256')
        if not result['binaryStable'] or not result['manifestStable'] or not result['harnessStable'] or not result['wrapperStable'] or not result['processHelperStable']:result['status']='FAIL'
        result['finishedAtUTC']=datetime.now(timezone.utc).isoformat();write(OUT/'result.json',result)
    print(json.dumps({k:result.get(k) for k in ('status','checks','errorType','errorCode','cleanupFailureCode','sourceStable','binaryStable','manifestStable','harnessStable','wrapperStable','processHelperStable','independentOwnedCleanup')}),flush=True)
    return 0 if result['status']=='PASS_FINAL_NATIVE_V8_PEER16' else 1
if __name__=='__main__':raise SystemExit(main())
