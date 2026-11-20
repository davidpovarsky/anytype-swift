"""Export complete source-bound v9 overlays without touching any repository index/ref."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json, os, shutil, subprocess

APP=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
ANY=Path(r'C:\Users\DAVID\Code\any-pinkha-runtime-20261119')
SDK=ANY/'.runtime-artifacts/sdk-source'
GO=Path(r'C:\Users\DAVID\go\pkg\mod\golang.org\toolchain@v0.0.1-go1.27.1.windows-amd64\bin\go.exe')
BASE={'any':'88fae2e5ae7d0f46d6707567a3123081faa8de9a','sdk':'854df54cdadd76006ae823cbd1b1d923138356d0'}
PREFIX='native-property-receipts-v9'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(repo,*args,env=None):return subprocess.check_output(['git','--no-optional-locks','-C',str(repo),*args],env=env,timeout=60)
def textgit(repo,*args,env=None):return git(repo,*args,env=env).decode('utf8').strip()
def source(repo):
    paths=textgit(repo,'ls-files','--cached','--others','--exclude-standard').splitlines()
    paths=sorted({p for p in paths if p.endswith('.go') or p in ('go.mod','go.sum')})
    return {'gitHEAD':textgit(repo,'rev-parse','HEAD'),'files':{p:sha(repo/p) for p in paths},'goBinarySHA256':sha(GO)}
def load_test(path):
    x=json.loads(path.read_text(encoding='utf8'))
    assert x['status']=='PASS' and x['sourceStable'] and x.get('dependencySourceStable',True) and x['runnerStable']
    assert x['topLevelTests']>0 and x['passedCases']==x['testCases'] and x['failedEvents']==0 and x['skippedEvents']==0
    return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sdk-result',type=Path,required=True);ap.add_argument('--server-result',type=Path,required=True)
    ap.add_argument('--output-dir',type=Path,required=True);a=ap.parse_args();out=a.output_dir;out.mkdir(parents=True,exist_ok=False)
    sdk=load_test(a.sdk_result);server=load_test(a.server_result)
    before={'sdk':source(SDK),'any':source(ANY)}
    assert json.loads((a.sdk_result.parent/'source-after.json').read_text(encoding='utf8'))==before['sdk']
    assert json.loads((a.server_result.parent/'source-after.json').read_text(encoding='utf8'))==before['any']
    deps=json.loads((a.server_result.parent/'dependency-source-after.json').read_text(encoding='utf8'))
    assert deps[str(SDK.resolve())]==before['sdk']
    old=json.loads((APP/'Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-source.json').read_text(encoding='utf8'))
    old_build=json.loads((APP/'Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-build/result.json').read_text(encoding='utf8'))
    assert before['sdk']==old_build['sourceAfter']['sdk'], 'v9 must not change SDK sources'
    expected_delta={'internal/api/properties.go','internal/server/pinkha_property_condition.go','internal/server/handlers_pinkha_property_cas_test.go','internal/server/handlers_pinkha_property_noop_test.go'}
    assert before['any']['files'].keys()==old_build['sourceAfter']['any']['files'].keys()
    actual_delta={p for p,h in before['any']['files'].items() if h!=old_build['sourceAfter']['any']['files'][p]}
    assert actual_delta==expected_delta
    manifest={'status':'IN_PROGRESS','schemaVersion':1,'createdAt':datetime.now(timezone.utc).isoformat(),
      'scope':'Complete native v9 overlay: dedicated conditional-property responses expose the original accepted SDK applySeq, paired with exact-row version and engine run; zero-history no-op responses omit sequence/version. All v8 native behavior and SDK implementation remain included. Real Host workflow acceptance is recorded separately.',
      'supersedes':'native-conditional-properties-v8-source.json',
      'wireCompatibility':{'contract':'pinkha-torah-native-v1','conditionalPropertiesApplySeq':1,'conditionalPropertiesNoop':1,'dedicatedPropertiesRouteRequiresIfApplySeq':True,'stockPropertiesRouteChanged':False,'dedicatedAcceptedApplySeqResponse':True,'noOpSequenceOmitted':True},
      'sdkTests':{'reusedBecauseExactSDKSourceUnchangedFromV8':True,'resultPath':str(a.sdk_result),'evidenceFile':a.sdk_result.resolve().relative_to(APP/'Tools/AnyEngineValidation/evidence').as_posix(),'sha256':sha(a.sdk_result),'topLevelTests':sdk['topLevelTests'],'cases':sdk['testCases'],'skipped':0},
      'serverTests':{'resultPath':str(a.server_result),'evidenceFile':a.server_result.resolve().relative_to(APP/'Tools/AnyEngineValidation/evidence').as_posix(),'sha256':sha(a.server_result),'topLevelTests':server['topLevelTests'],'cases':server['testCases'],'skipped':0},
      'v8ManifestSHA256':sha(APP/'Tools/AnyEngineValidation/evidence/native-conditional-properties-v8-source.json'),
      'validationNotes':[
       'Both patches are complete diffs against the pinned upstream bases. Apply once to clean checkouts; never stack prior overlays.',
       'testedLocalCommit names the pre-existing isolated branch parent; testedEffectiveTree and exact file blobs bind the tested uncommitted v9 state. No branch ref or real Git index is changed by this exporter.',
       'The complete _ver map alone is insufficient for commutative late collection operations; the independent actual combined witness and prior watchdog failure remain separate immutable evidence.',
       'The empty patch path performs current authority validation without appending a change. It returns no new applySeq or history identity; v9 fixes the previously missing serialized nonempty applySeq field by forwarding the original SDK result without rebasing.',
       'Earlier v7/v8 receipts remain scoped to their exact historical source/binary. Windows intermittent raw URLSession timeout investigation is unresolved; no production transport setting changed.'
      ]}
    real_indices={}
    for label,repo in (('any',ANY),('sdk',SDK)):
        index=Path(textgit(repo,'rev-parse','--path-format=absolute','--git-path','index'));real_indices[label]=(index,sha(index) if index.exists() else None)
        existing={e['path'] for e in old[label]['files']}
        changed=set(textgit(repo,'diff','--name-only','--no-renames',BASE[label]).splitlines())
        new=set(textgit(repo,'ls-files','--others','--exclude-standard').splitlines())
        new={p for p in new if p.endswith('.go') and not p.startswith('.runtime-artifacts/')}
        paths=sorted(changed|new)
        assert paths and all((p in existing or p.endswith('.go') or p in ('go.mod','go.sum')) and '.bak.' not in p and not p.startswith('.runtime-artifacts/') for p in paths)
        env=dict(os.environ,GIT_INDEX_FILE=str((out/(label+'-temporary.index')).resolve()))
        git(repo,'read-tree',BASE[label],env=env)
        entries=[]
        for p in paths:
            f=repo/p
            assert f.is_file(), 'Unexpected removed source path: '+p
            blob=textgit(repo,'hash-object','-w','--path='+p,p)
            mode='100644'
            tree_line=textgit(repo,'ls-tree',BASE[label],'--',p)
            if tree_line:mode=tree_line.split()[0]
            git(repo,'update-index','--add','--cacheinfo',mode,blob,p,env=env)
            entries.append({'path':p,'worktreeSHA256':sha(f),'gitBlob':blob})
        tree=textgit(repo,'write-tree',env=env)
        patch=out/(PREFIX+'-'+label+'.patch');patch.write_bytes(git(repo,'diff','--binary','--no-ext-diff','--no-renames',BASE[label],tree))
        # Independently apply the complete patch to another clean temporary index.
        check_env=dict(os.environ,GIT_INDEX_FILE=str((out/(label+'-apply-check.index')).resolve()))
        git(repo,'read-tree',BASE[label],env=check_env)
        git(repo,'apply','--cached','--check',str(patch),env=check_env)
        git(repo,'apply','--cached',str(patch),env=check_env)
        assert textgit(repo,'write-tree',env=check_env)==tree
        manifest[label]={'upstreamCommit':BASE[label],'testedLocalCommit':before[label]['gitHEAD'],'testedEffectiveTree':tree,'testedWorkingTreeIncludesUncommittedChanges':True,'testedWorkingTreeRevision':'v9',
                         'patch':patch.name,'patchSHA256':sha(patch),'files':entries,'portableCleanIndexApply':'PASS','fullSourceSHA256':before[label]['files']}
        if label=='sdk':
            assert tree==old['sdk']['testedEffectiveTree']
            assert sha(patch)==old['sdk']['patchSHA256']
            manifest[label]['unchangedFromV8']=True
    manifest['sdk'].update(upstreamTag='v0.8.0',upstreamTagObject='b161a0475479bbe7d9d693bc496c6fdd90c3969b')
    helper_path=APP/'Tools/AnyEnginePort/run_live_provider_probe.py'
    spec=importlib.util.spec_from_file_location('process_helper',helper_path);helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    shutil.copy2(__file__,out/'executed-exporter.py');shutil.copy2(helper_path,out/'executed-process-helper.py')
    result={'status':'FAIL','sourceBefore':before,'manifest':manifest,'runnerSHA256':sha(Path(__file__)),'processHelperSHA256':sha(helper_path)}
    binary=ANY/'.runtime-artifacts/any-native-properties-v9.exe';assert not binary.exists()
    build=out/'build';build.mkdir()
    os.environ.update(GOMAXPROCS='2',GOMEMLIMIT='768MiB',GOTOOLCHAIN='go1.27.1',GOCACHE=str(ANY/'.runtime-artifacts/go-build-v8'),GOTMPDIR=str(ANY/'.runtime-artifacts/go-tmp-v8'))
    marker='v9-tree-'+manifest['any']['testedEffectiveTree'][:12]
    flags='-X github.com/anyproto/any/internal/version.Version=v0.5.0-pinkha.1 -X github.com/anyproto/any/internal/version.Commit='+marker+' -X github.com/anyproto/any/internal/version.BuildDate='+datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        command=[str(GO),'build','-p=2','-ldflags',flags,'-o',str(binary),'./cmd/any']
        result['process']=helper.run_process(command,ANY,build,420)
        p=result['process'];assert p.get('exitCode')==0 and not p.get('timedOut') and not p.get('cleanupErrors') and not p.get('runnerErrorType')
        manifest['build']={'status':'PASS','path':str(binary),'sha256':sha(binary),'command':command,'version':'v0.5.0-pinkha.1','embeddedCommitMarker':marker,'goBinarySHA256':sha(GO)}
        manifest['status']='PASS_NATIVE_PROPERTY_RECEIPTS_V9_SOURCE_BUILD'
        result['status']='PASS'
    except Exception as error:result['errorType']=type(error).__name__
    finally:
        after={'sdk':source(SDK),'any':source(ANY)};result['sourceAfter']=after;result['sourceStable']=before==after
        result['actualGitIndicesUnchanged']=all((sha(p) if p.exists() else None)==s for p,s in real_indices.values())
        result['runnerStable']=sha(Path(__file__))==result['runnerSHA256'] and sha(helper_path)==result['processHelperSHA256']
        if not result['sourceStable'] or not result['actualGitIndicesUnchanged'] or not result['runnerStable']:result['status']='FAIL';manifest['status']='FAIL'
        helper.write_json(out/'result.json',result)
    if result['status']=='PASS':
        dest=APP/'Tools/AnyEngineValidation/evidence'
        for label in ('any','sdk'):
            name=manifest[label]['patch'];assert not (dest/name).exists();shutil.copy2(out/name,dest/name)
        name=PREFIX+'-source.json';assert not (dest/name).exists();helper.write_json(dest/name,manifest)
        print(json.dumps({'status':manifest['status'],'manifest':str(dest/name),'manifestSHA256':sha(dest/name),'binary':str(binary),'binarySHA256':sha(binary),'anyFiles':len(manifest['any']['files']),'sdkFiles':len(manifest['sdk']['files'])}))
        return 0
    print(json.dumps({'status':'FAIL','sourceStable':result['sourceStable'],'errorType':result.get('errorType')}));return 1
if __name__=='__main__':raise SystemExit(main())
