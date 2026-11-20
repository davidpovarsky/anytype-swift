from pathlib import Path
import hashlib,json,re,subprocess
root=Path(r'C:\Users\DAVID\Code\anytype-swift-any-engine-20261119')
base=Path(__file__).parent
out=base/'sealed-safe-review'
out.mkdir(exist_ok=False)
h=lambda b:hashlib.sha256(b).hexdigest()
old='57c116e02ee6dbce21f3bbffcc297841d2bd1235'
current='3d9932b1b68fada61a3d1ef54694f75c9ef2398d'
path='Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinCreatePageRunner.swift'
def show(ref,name):
    result=subprocess.run(['git','show',ref+':'+name],cwd=root,capture_output=True,timeout=15)
    assert result.returncode==0
    return result.stdout
before=show(old,path)
now=show(current,path)
assert before==now
assert b'import HanlinPlatformContracts' not in before
assert b'HanlinToolInvocationID' in before.splitlines()[44] and b'HanlinToolInvocationID' in before.splitlines()[45]
(out/'57-PinkhaHanlinCreatePageRunner.swift').write_bytes(before)
(out/'3d-PinkhaHanlinCreatePageRunner.swift').write_bytes(now)
working=(root/path).read_bytes()
normalized=working.replace(b'\r\n',b'\n')
expected=now.replace(b'import HanlinHostContracts\n',b'import HanlinHostContracts\nimport HanlinPlatformContracts\n',1)
owner_fix_present=normalized==expected
declaration_path='Dependencies/Hanlin/Packages/HanlinPlatform/Sources/HanlinPlatformContracts/HanlinIdentifiers.swift'
declaration=(root/declaration_path).read_bytes()
decl_lines=declaration.decode('utf-8').splitlines()
assert 'public struct HanlinToolInvocationID: HanlinStringIdentifier' in decl_lines[336]
excerpt='\n'.join(str(i+1)+': '+decl_lines[i] for i in range(330,345))+'\n'
(out/'HanlinToolInvocationID-declaration.txt').write_text(excerpt,encoding='utf-8',newline='\n')
context_path='Anytype/Sources/Pinkha/AI/Write/PinkhaHanlinCreatePageContext.swift'
context_before=show(old,context_path)
assert b'import HanlinPlatformContracts' in context_before
raw=(base/'private-job.log').read_bytes()
assert h(raw)=='fc5f212d8ba8570595a610ae46a5ee78bd791b9889491b980cc14557cde9c027'
lines=raw.decode('utf-8-sig').splitlines()
diagnostic_lines=[{'line':i+1,'message':line} for i,line in enumerate(lines)
 if "error: cannot find type 'HanlinToolInvocationID' in scope" in line]
assert len(diagnostic_lines)==4
exit_lines=[{'line':i+1,'message':line} for i,line in enumerate(lines)
 if 'Process completed with exit code 1.' in line]
assert len(exit_lines)==1
safe='\n'.join(str(x['line'])+': '+x['message'] for x in diagnostic_lines+exit_lines)+'\n'
(out/'retained-compile-error.sanitized.log').write_text(safe,encoding='utf-8',newline='\n')
build_failure=[line for line in lines if '"error": "Command' in line and "'xcodebuild', 'build-for-testing'" in line]
assert len(build_failure)==1
exit_match=re.search(r'returned non-zero exit status (\d+)',build_failure[0])
native_build_exit=int(exit_match.group(1)) if exit_match else None
assert native_build_exit==65
starts=[line for line in lines if re.search(r"Test Case '.*' started",line)]
outcomes=[line for line in lines if re.search(r"Test Case '.*' (?:passed|failed|skipped)",line)]
report={'schemaVersion':1,'status':'ACTUAL_RETAINED_CONSUMER_BUILD_FAILURE',
 'runId':44673740725,'jobId':136094169244,'sourceCommit':old,
 'comparisonCommit':current,'sourcePath':path,'sourceLines':[45,46],
 'diagnostic':"cannot find type 'HanlinToolInvocationID' in scope",
 'definingModule':'HanlinPlatformContracts','declarationPath':declaration_path,'declarationLine':337,
 'oldAndCurrentCommittedFileIdentical':True,'oldAndCurrentGitBlob':'804904d619a630d2a7610f1a55698fecc60a9125',
 'oldAndCurrentGitBytesSHA256':h(before),
 'existingSameTargetImportAt57':{'path':context_path,'gitBytesSHA256':h(context_before)},
 'materializedDeclarationFileSHA256':h(declaration),
 'workingTreeAtSealSHA256':h(working),'workingTreeAtSealContainsOwnerImportOnlyCorrection':owner_fix_present,
 'phase':'xcodebuild build-for-testing Debug-Anytype','xcodebuildExitCode':native_build_exit,'wrapperExitCode':1,
 'observedTestCaseStarts':len(starts),'observedTestCaseOutcomes':len(outcomes),
 'retainedProfileRuntimeNotReached':True,
 'plannedSuites':['HanlinHostAdapterTests','HanlinHostWriteTests','HanlinHostReadWriteTests','HanlinSDKConsumerTests','PinkhaBootstrapStateManagerTests'],
 'intentionalSelfTestErrorExcluded':'Earlier actual exit seven is an expected harness self-test, not the failing retained build.',
 'correctionOwner':'capability_inventory','minimalCorrection':'Explicit import HanlinPlatformContracts only.',
 'refactorMapUpdateOwner':'root','noSourceEditsByReviewer':True,'noRuntimeRerun':True,
 'rawJobLogSHA256':h(raw),'rawJobLogBytes':len(raw),'rawJobLogIncluded':False,
 'currentCommittedSourceNotTestedByThisOld57Job':True,'correctionNotYetProvenByRetainedAppleGate':True}
(out/'failure-review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
for name in ['job-metadata.json','download-receipt.json']:
    (out/name).write_bytes((base/name).read_bytes())
(out/'seal_safe_failure.py').write_bytes(Path(__file__).read_bytes())
files={p.name:{'sha256':h(p.read_bytes()),'bytes':p.stat().st_size} for p in sorted(out.iterdir()) if p.is_file()}
manifest={'schemaVersion':1,'status':'SEALED_SAFE_RETAINED57_COMPILER_FAILURE','sourceCommit':old,'comparisonCommit':current,
 'runId':44673740725,'jobId':136094169244,'files':files,'rawLogIncluded':False,'retainedRuntimeTestsExecuted':False,
 'noSourceEditsByReviewer':True}
data=(json.dumps(manifest,indent=2)+'\n').encode()
(out/'MANIFEST.json').write_bytes(data)
print(json.dumps({'directory':str(out),'manifestSHA256':h(data),'files':len(files),
 'oldAndCurrentSourceIdentical':True,'oldAndCurrentGitBytesSHA256':h(before),
 'workingTreeContainsOwnerImportOnlyCorrection':owner_fix_present,
 'declarationFileSHA256':h(declaration),'safeExcerptSHA256':files['retained-compile-error.sanitized.log']['sha256'],
 'observedTestCaseStarts':len(starts),'observedTestCaseOutcomes':len(outcomes),'xcodebuildExitCode':native_build_exit}))
