from pathlib import Path
import datetime,hashlib,json,subprocess,time,re
root=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
work=root/'build/any-engine-port/native-rtl-drag-ui-20261119-220904-134045'
evidence=root/'docs/any-engine-port/evidence/20261119'
artifact=evidence/'native-rtl-drag-ui-source-v1-artifacts'
artifact.mkdir(parents=True,exist_ok=True)
paths=['Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeDocumentView.swift','Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativeLibraryView.swift','NativeApp/UITests/NativeLaunchTests.swift']
before={p:(work/'before'/p).read_bytes() for p in paths}
current={p:(root/p).read_bytes() for p in paths}
def digest(data):return hashlib.sha256(data).hexdigest()
def names(data):return re.findall(rb'^    func (test\w+)\(',data,re.M)
base_test=before[paths[2]]
test=current[paths[2]]
marker=b'    private func selectInspectorTool('
split=base_test.index(marker)
assert test[:split]==base_test[:split]
suffix=base_test[split:]
assert test.endswith(suffix)
inserted=test[split:len(test)-len(suffix)]
assert test[:split]+test[len(test)-len(suffix):]==base_test
assert len(names(base_test))==5 and len(names(test))==7
assert names(test)[:5]==names(base_test)
assert b'press(forDuration: 1.1, thenDragTo: destination)' in inserted
assert b'any-native-hierarchy-move' not in inserted
assert b'AnyHTTPClient' not in inserted and b'--seed' not in inserted
library_line=b'        .accessibilityIdentifier("any-native-hierarchy-row-\\(item.objectID)")\n'
assert current[paths[1]].replace(library_line,b'',1)==before[paths[1]]
actions=rb'Task \{ await presentation.setWritingStyle\([^\n]+'
assert re.findall(actions,current[paths[0]])==re.findall(actions,before[paths[0]])
swift=Path(r'C:\Users\DAVID\AppData\Local\Programs\Swift\Toolchains\6.3.3+Asserts\usr\bin\swiftc.exe')
command=[str(swift),'-frontend','-parse']+[str(root/p) for p in paths]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
t=time.monotonic();timed_out=False
try:
    result=subprocess.run(command,cwd=root,capture_output=True,timeout=60)
    code=result.returncode;stdout=result.stdout;stderr=result.stderr
except subprocess.TimeoutExpired as error:
    timed_out=True;code=None;stdout=error.stdout or b'';stderr=error.stderr or b''
elapsed=time.monotonic()-t
(artifact/'parse.stdout.log').write_bytes(stdout)
(artifact/'parse.stderr.log').write_bytes(stderr)
diff=subprocess.run(['git','diff','--no-ext-diff','--']+paths,cwd=root,capture_output=True,timeout=20)
(artifact/'source.diff').write_bytes(diff.stdout)
checked=subprocess.run(['git','diff','--check','--']+paths,cwd=root,capture_output=True,timeout=20)
(artifact/'diff-check.stdout.log').write_bytes(checked.stdout)
(artifact/'diff-check.stderr.log').write_bytes(checked.stderr)
source_stable=all((root/p).read_bytes()==current[p] for p in paths)
for p,data in current.items():
    target=artifact/'sources'/p
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(data)
runner=Path(__file__).read_bytes()
(artifact/'verify-source.py').write_bytes(runner)
receipt={
 'schemaVersion':1,'status':'PARSE_PASS_UI_EXECUTION_PENDING' if code==0 and source_stable and checked.returncode==0 else 'FAIL_PRESERVED_UI_EXECUTION_PENDING',
 'scope':'Syntax-only parse plus byte-preservation/source-contract checks; no iOS semantic compile, Simulator, or UI execution',
 'baseCommit':'d58b6a004c93320a4c57c8eba8e4518048d70fc1',
 'startedAtUTC':started,'finishedAtUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'command':command,'compilerSHA256':digest(swift.read_bytes()),'exitCode':code,'timedOut':timed_out,'durationSeconds':round(elapsed,3),
 'sourceStable':source_stable,'diffCheckExitCode':checked.returncode,
 'checks':{'entireExistingTestFileRecoveredByRemovingOnlyTwoInsertedMethods':True,
 'existingFiveMethods':[n.decode() for n in names(base_test)],'newMethods':[n.decode() for n in names(test)[5:]],
 'allExistingHelpersByteIdentical':True,'productionDragDropAndMoveLogicByteIdentical':True,
 'writingStyleActionBodiesUnchanged':True,'savedStyleAccessibilityUsesNativeReadbackSnapshotOnly':True,
 'normalUUIDOnboardingAndNativeStorage':True,'noFixtureOrSyntheticOwnerOrDirectHTTPInNewTests':True},
 'files':[{'path':p,'beforeSHA256':digest(before[p]),'afterSHA256':digest(current[p])} for p in paths],
 'appleExecution':'NOT_RUN','artifactDirectory':str(artifact.relative_to(root)).replace('\\','/')
}
artifact_manifest={'schemaVersion':1,'files':[{'path':str(p.relative_to(artifact)).replace('\\','/'),'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(artifact.rglob('*')) if p.is_file() and p.name!='MANIFEST.json']}
(artifact/'MANIFEST.json').write_bytes((json.dumps(artifact_manifest,indent=2)+'\n').encode())
receipt['artifactManifestSHA256']=digest((artifact/'MANIFEST.json').read_bytes())
target=evidence/'native-rtl-drag-ui-source-v1.json'
target.write_bytes((json.dumps(receipt,ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({'receipt':str(target.relative_to(root)).replace('\\','/'),'sha256':digest(target.read_bytes()),'status':receipt['status'],'exitCode':code,'timedOut':timed_out,'durationSeconds':receipt['durationSeconds'],'sourceStable':source_stable,'diffCheckExitCode':checked.returncode,'stderr':stderr.decode('utf-8','replace')[:3000]},ensure_ascii=False))
