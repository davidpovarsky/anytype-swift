from pathlib import Path
import subprocess,json,hashlib,datetime
repo=Path(r'C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122')
proof='docs/pinkha/torah-integration/original-space-edit-composition-integration-20261122'
p=repo/proof
sha=lambda b:hashlib.sha256(b).hexdigest()
def g(*a,check=True):
 r=subprocess.run(['git','-c','core.autocrlf=false',*a],cwd=repo,capture_output=True,timeout=60)
 if check:assert r.returncode==0,(a,r.returncode,r.stdout.decode(errors='replace')[:2000],r.stderr.decode(errors='replace')[:1000])
 return r
assert g('rev-parse','HEAD').stdout.decode().strip()=='d84a52e65df162771d320d4e744821b2eae01e71'
assert g('show','-s','--format=%P','HEAD').stdout.decode().split()==['403725a24422103b3562228a64061d24d639eabf','31d3f65c0132ec17e76b11c39d3a5e3314a7aa23']
review=json.loads((p/'ROOT_REVIEW.json').read_bytes())
assert sha((p/'ROOT_REVIEW.json').read_bytes())=='086acb1707fad951fe4bd2a9028f76f13212e613e72e9b6f43d5a0e8bec77e5c'
original_script=(p/'EXECUTED_ROOT_SCRIPT.py').read_bytes()
assert sha(original_script)==review['executed_script_sha256']=='6cff26ec4fa37e270af814fd355229591346dc3ce706f27556b6be703ca52e62'
assert original_script.count(b'\r\n')==148 and b'\r' not in original_script.replace(b'\r\n',b'\n')
before=json.loads((p/'FILE_INDEX.json').read_bytes())
for item in before['files']:
 b=(p/item['path']).read_bytes();assert len(b)==item['bytes'] and sha(b)==item['sha256']
lint=g('diff','--cached','--check',check=False);assert lint.returncode==2
diagnostics=[l for l in lint.stdout.decode().splitlines() if l.endswith('trailing whitespace.')]
assert len(diagnostics)==148 and all(l.startswith(proof+'/EXECUTED_ROOT_SCRIPT.py:') for l in diagnostics)
(p/'ORIGINAL_PACKAGING_LINT.txt').write_bytes(lint.stdout)
(p/'ORIGINAL_TOOL_JOB.json').write_bytes("{\n  \"id\": \"job_bc3db4a8fc60\",\n  \"type\": \"job_result\",\n  \"source\": \"script_run@host_7ec8382e82747448\",\n  \"severity\": \"warning\",\n  \"tool\": \"script_run\",\n  \"host\": \"host_7ec8382e82747448\",\n  \"status\": \"failed\",\n  \"exit_code\": 1,\n  \"created_at\": 1795336210.5398397,\n  \"started_at\": \"2026-11-22T08:30:10.625069+00:00\",\n  \"finished_at\": \"2026-11-22T08:30:34.670604+00:00\",\n  \"duration_s\": 24.05,\n  \"error\": null,\n  \"output_truncated\": false,\n  \"timeout_s\": 300,\n  \"read\": false,\n  \"notified\": {\n    \"telegram\": null,\n    \"resend\": null\n  },\n  \"notify_spec\": {},\n  \"output\": \"Traceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_046d030257324a3ab13d8f0786553911\\\\integrate_original_space_edit_composition.py\\\", line 144, in <module>\\r\\n    git('add','--',proof);git('diff','--cached','--check')\\r\\n                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_046d030257324a3ab13d8f0786553911\\\\integrate_original_space_edit_composition.py\\\", line 15, in git\\r\\n    if p.returncode: raise RuntimeError('git failure '+str(args)+' '+p.stderr.decode(errors='replace')[:2000])\\r\\n                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\\r\\nRuntimeError: git failure ('diff', '--cached', '--check')\"\n}\n".encode('utf8'))
(p/'.gitattributes').write_bytes(b'*.py -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\nORIGINAL_PACKAGING_LINT.txt -text whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol\n')
(p/'EXECUTED_CONTINUATION.py').write_bytes(Path(__file__).read_bytes())
erratum={'schema':1,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'original_job':'job_bc3db4a8fc60','actual_merge':'d84a52e65df162771d320d4e744821b2eae01e71','original_job_exit':1,'failed_step':'Post-merge evidence git diff --cached --check','cause':'Exact executed Sentinel Python script retains 148 CRLF line endings. Git lint treated CR as trailing whitespace before explicit per-evidence-path policy. All evidence verification and true merge had already succeeded.','correction':'Preserve exact executed bytes. Add scoped attributes allowing CR-at-EOL only for raw script and diagnostic evidence; retain all ordinary whitespace checks. Complete documentation commit from observed existing merge, without repeating source verification, tests or merge.','original_script_sha256':sha(original_script),'root_review_sha256':sha((p/'ROOT_REVIEW.json').read_bytes()),'merge_repeated':False,'tests_reexecuted':0,'candidate_changed':False}
(p/'PACKAGING_ERRATUM.json').write_bytes((json.dumps(erratum,indent=2)+'\n').encode())
with (p/'README.md').open('ab') as f:f.write(b'\n## Exact executed-script preservation\n\nThe first root tool completed all independent evidence admission and the true merge, then stopped at Git whitespace lint for the transported CRLF script. The exact executed bytes, original tool failure and raw lint output remain retained. A scoped CR-at-EOL attribute permits those raw evidence line endings while retaining the other whitespace checks. This continuation only completes the evidence commit; it does not repeat the merge or any test.\n')
files=[{'path':x.name,'bytes':x.stat().st_size,'sha256':sha(x.read_bytes())} for x in sorted(p.iterdir()) if x.is_file() and x.name!='FILE_INDEX.json']
(p/'FILE_INDEX.json').write_bytes((json.dumps({'schema':1,'count':len(files),'files':files},indent=2)+'\n').encode())
g('add','--',proof);g('diff','--cached','--check')
g('commit','-m','Record verified original Space edit composition and exact evidence provenance')
assert g('status','--porcelain').stdout==b''
head=g('rev-parse','HEAD').stdout.decode().strip()
for item in files:assert sha(g('show',head+':'+proof+'/'+item['path']).stdout)==item['sha256']
print(json.dumps({'status':'PASS','final_commit':head,'merge':erratum['actual_merge'],'proof_payloads':len(files),'proof_index_sha256':sha((p/'FILE_INDEX.json').read_bytes()),'root_review_sha256':erratum['root_review_sha256'],'original_payloads_verified':review['payload_count'],'original_payload_bytes':review['payload_bytes'],'new_tests_executed':0,'remote':g('remote','get-url','origin').stdout.decode().strip()}))
