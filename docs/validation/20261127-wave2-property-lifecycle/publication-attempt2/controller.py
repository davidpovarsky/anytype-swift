import pathlib,os,pwd,grp,subprocess,json,base64,zlib,hashlib,gzip,datetime,sys,traceback
root=pathlib.Path('/mnt/development/projects/worktrees/anytype-wave2-property-lifecycle-20261127')
private=pathlib.Path('/var/lib/pinkha-wave2-property-lifecycle-20261127')
evidence=private/'source-publication2'
assert not evidence.exists(),'Preserve original publication attempt'
identity=(pwd.getpwnam('ubuntu').pw_uid,grp.getgrnam('chatgpt-agent').gr_gid)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_bytes(raw);os.chown(path,*identity)
def js(path,value):write(path,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
git=['runuser','-u','ubuntu','-g','chatgpt-agent','--','git','-C',str(root)]
def run(args,timeout=15):return subprocess.run(args,cwd=root,check=True,capture_output=True,timeout=timeout)
evidence.mkdir(mode=0o700);os.chown(evidence,*identity)
result={'atUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'FAIL','compilerInvocations':0,'componentTests':'NOT_RUN','nativeCalls':0,'AppleCompilation':'NOT_RUN'}
try:
 assert run(git+['rev-parse','HEAD']).stdout.decode().strip()=='c95395aec96214dfabd73d55755baa95689cc6d3'
 assert run(git+['branch','--show-current']).stdout.decode().strip()=='codex/chatgpt-wave15-wave2-property-lifecycle-20261127'
 assert run(git+['diff','--name-only']).stdout==b'','Unexpected unstaged work'
 raw=zlib.decompress(base64.b64decode(pathlib.Path(sys.argv[1]).read_bytes()));assert sha(raw)==sys.argv[2]
 packet=json.loads(raw)
 tools='Tools/PinkhaDualEngineRuntime/property_lifecycle/'
 docs='docs/validation/20261127-wave2-property-lifecycle/'
 old_runner=root/(tools+'run_component.py')
 assert sha(old_runner.read_bytes())=='4c6bc70fe7bfaa82453dbf4a0cf4d07889decb9be5786b876c9e7f27cf43493a'
 for name,expected in [('Modules/PinkhaAnyUI/Sources/PinkhaAnyUI/AnyNativePropertyPresentation.swift','aa40239c5ba749b20974735337c0af11ba477c9aac870261f4ae5ae76f76c731'),('Modules/PinkhaAnyUI/Tests/PinkhaAnyUITests/AnyNativePropertyPresentationTests.swift','7df1a45aa85cd71bc7ec8353b98150609bc2d2fb07a2aa1ebf08f7fb40fdab61')]:
  assert sha((root/name).read_bytes())==expected,name
 for name,row in packet.items():
  assert name.startswith((tools,docs+'runner-review/')) and '..' not in pathlib.PurePosixPath(name).parts,name
  path=root/name
  assert not path.exists() or name==tools+'run_component.py',name
  data=base64.b64decode(row['base64']);assert len(data)==row['bytes'] and sha(data)==row['sha256'],name
 for name,row in packet.items():write(root/name,base64.b64decode(row['base64']))
 old_private=private/'inputs/run_component.py'
 assert sha(old_private.read_bytes())=='4c6bc70fe7bfaa82453dbf4a0cf4d07889decb9be5786b876c9e7f27cf43493a'
 retained=private/'inputs/run_component.prereview-4c6.py';assert not retained.exists();write(retained,old_private.read_bytes())
 write(old_private,(root/(tools+'run_component.py')).read_bytes())
 qpath=root/(docs+'qualification.json');qraw=qpath.read_bytes()
 assert sha(qraw)=='650bf49df52c52579cb0119694eaf7f8d2d1eb76eced4c01fb23b7868b163757'
 q=json.loads(qraw);q['files']['run_component.py']={k:packet[tools+'run_component.py'][k] for k in ['bytes','sha256']}
 q['runnerReview']={'initialFindings':'runner-review/editor-runner-source-review.json','firstRevisionReview':'runner-review/editor-runner-rereview-5817.json','finalClosure':'runner-review/owned-group-review-closure.json','finalClosureSHA256':'790703dfa506d6e97df1dd4e1c57cdff263e59015745e42bccd62dea1145ae79','allFiveFindingsResolved':True,'baselineFailureRequiresManualIntendedIssueReview':True}
 q['actualOwnedCleanupProbe']={'receipt':'runner-review/owned-cleanup-probe1/receipt.json','sha256':'a9b97a624b8940d8ba609aa5595af9e8ad5a913ce41cfb14563c73b888d68319','elapsedSeconds':0.15096207299939124,'status':'PASS_REAL_OWNED_CLEANUP_AND_ORIGINAL_FAILURE_RETAINED','modelTestsExecuted':0,'terminatingSignal':'SIGTERM','KILLAndPermissionBranches':'SOURCE_REVIEW_ONLY','originalPhaseStatus':'FAIL'}
 js(qpath,q)
 readme=root/(docs+'README.md');assert sha(readme.read_bytes())=='dcff56b0e234f3dbc4a2d59c455c213f278a867f5e7162e3bf08c0e0cbf90b00'
 addition="""
## Runner review before actual model execution

Five concrete controller findings were corrected before any Properties model test started: guaranteed cleanup after post-launch exceptions, exact production Error enum and original dependency closure pins, complete physical dependency input sets, truthful classification of baseline failures pending inspection of their intended expectation issues, and positive process-group absence. The historical Add-block process ID is never probed again; its original pinned owner handoff remains the evidence.

The final runner is 99dcacdacace01b4b7c0646c09dafb45c9b8d167781043542bc6c0ed2a7103e2. The original two runner revisions, both reviews and exact final inverse are retained under runner-review/. A single genuine local Python process probe completed in 0.151 seconds: the leader exited, its child remained, the actual cleanup helper delivered TERM, the child was reaped, and a signal-zero group observation returned ESRCH. Later cached calls issued no further group probe. The deliberately failed original phase stayed FAIL with its exact exception while cleanup was recorded separately as PASS. SIGKILL escalation and permission-error branches were source-reviewed only.

This probe did not run Swift, a Properties model test, Native, an App or UI. The planned two-method original-model and nine-method corrected-model phases remain NOT_RUN pending the same host disk admission; none of their outcomes is inferred from controller or source checks.
"""
 write(readme,readme.read_bytes()+addition.encode())
 run(git+['add','--',tools,docs])
 run(git+['diff','--cached','--check'])
 tree=run(git+['write-tree']).stdout.decode().strip()
 report=evidence/'source-retention.json'
 command=['runuser','-u','ubuntu','-g','chatgpt-agent','--','python3','Tools/AnyEnginePort/verify_source_retention.py','--base','586c98bcc17dee425664224e508fc0e8df277678','--ref',tree,'--output',str(report)]
 actual=subprocess.run(command,cwd=root,capture_output=True,timeout=20)
 write(evidence/'stdout.original.log',actual.stdout);write(evidence/'stderr.original.log',actual.stderr)
 result.update(command=command,tree=tree,exitCode=actual.returncode)
 assert actual.returncode==0,'Source gate failed; original logs retained'
 proof=json.loads(report.read_bytes())
 assert proof['sourceRetentionPassed'] and len(proof['reviewedRefactors'])==129
 assert not proof['unreviewedChangedExistingFiles'] and not proof['inventoryErrors']
 result.update(status='PASS_STAGED_SOURCE_RETENTION_AFTER_RUNNER_REVIEW',retentionSHA256=sha(report.read_bytes()),unchangedMappingCount=129,runnerSHA256=sha(old_private.read_bytes()),stagedFiles=run(git+['diff','--cached','--name-only']).stdout.decode().splitlines())
 js(evidence/'receipt.json',result)
 final=root/(docs+'final-source-gate');assert not final.exists();final.mkdir()
 custody=[]
 for name in ['source-retention.json','receipt.json']:
  data=(evidence/name).read_bytes();write(final/name,data)
 for name in ['stdout.original.log','stderr.original.log']:
  data=(evidence/name).read_bytes();compressed=gzip.compress(data,mtime=0)
  write(final/(name+'.gz'),compressed);custody.append({'path':name+'.gz','rawBytes':len(data),'rawSHA256':sha(data),'gzipSHA256':sha(compressed)})
 js(final/'log-custody.json',custody)
 q=json.loads(qpath.read_bytes());q['priorSourceGate']=q['sourceGate']
 q['sourceGate']={'baselineCommit':'586c98bcc17dee425664224e508fc0e8df277678','receipt':'final-source-gate/source-retention.json','sha256':sha(report.read_bytes()),'status':'PASS_SOURCE_RETENTION_NOT_SEMANTIC_ACCEPTANCE','unchangedMappingCount':129,'verifiedSourceTree':tree}
 js(qpath,q)
 run(git+['add','--',tools,docs]);run(git+['diff','--cached','--check'])
 result['finalStagedCount']=len(run(git+['diff','--cached','--name-only']).stdout.decode().splitlines())
 result['qualificationSHA256']=sha(qpath.read_bytes())
 print(json.dumps({k:result[k] for k in ['status','tree','exitCode','retentionSHA256','runnerSHA256','unchangedMappingCount','finalStagedCount','qualificationSHA256']}))
except BaseException:
 result['failure']=traceback.format_exc();js(evidence/'failure.json',result)
 print(json.dumps(result));raise
