#!/usr/bin/env python3
"""Archive completed Apple57 patched-job evidence without rerunning any CI work."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import argparse,hashlib,json,subprocess,zipfile,shutil
REPO='davidpovarsky/anytype-swift'
RUN=44673740725
JOB=136080515969
HEAD='57c116e02ee6dbce21f3bbffcc297841d2bd1235'
NAME='any-engine-port-ios-patched-runtime-'+HEAD
GH=Path(r'C:\Program Files\GitHub CLI\gh.exe')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def api(endpoint,path,timeout=120):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('wb') as output:
  proc=subprocess.run([str(GH),'api',endpoint],stdout=output,stderr=subprocess.PIPE,timeout=timeout)
 if proc.returncode:
  raise RuntimeError('github_api_failed:'+endpoint+':exit'+str(proc.returncode))
 return path
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,sort_keys=True,ensure_ascii=True)+'\n',encoding='utf-8')
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--repo-root',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
 a=parser.parse_args();root=a.repo_root.resolve();out=a.output_dir.resolve()
 out.mkdir(parents=True,exist_ok=False)
 shutil.copyfile(__file__,out/'executed-collector.py')
 result={'status':'FAIL','scope':'completed_apple57_patched_runtime_artifact_read_only','runID':RUN,'jobID':JOB,'expectedHeadSHA':HEAD,
  'startedAt':datetime.now(timezone.utc).isoformat(),'newCIExecution':False}
 try:
  job=json.loads(api(f'repos/{REPO}/actions/jobs/{JOB}',out/'job.json').read_text(encoding='utf-8'))
  run=json.loads(api(f'repos/{REPO}/actions/runs/{RUN}',out/'run.json').read_text(encoding='utf-8'))
  if job['run_id']!=RUN or run['head_sha']!=HEAD:raise RuntimeError('job_source_identity_mismatch')
  if job['status']!='completed':raise RuntimeError('job_not_completed_no_log_request')
  result['jobConclusion']=job['conclusion']
  result['steps']=[{k:s.get(k) for k in ['name','number','status','conclusion','started_at','completed_at']} for s in job['steps']]
  api(f'repos/{REPO}/actions/jobs/{JOB}/logs',out/'workflow-job.log')
  artifacts=json.loads(api(f'repos/{REPO}/actions/runs/{RUN}/artifacts?per_page=100',out/'artifacts.json').read_text(encoding='utf-8'))
  matches=[x for x in artifacts['artifacts'] if x['name']==NAME]
  if len(matches)!=1:raise RuntimeError('exact_patched_evidence_artifact_missing')
  artifact=matches[0]
  if artifact.get('expired') or artifact['workflow_run']['head_sha']!=HEAD or artifact['workflow_run']['id']!=RUN:raise RuntimeError('artifact_source_identity_mismatch')
  archive=api(f'repos/{REPO}/actions/artifacts/{artifact["id"]}/zip',out/'artifact.zip',540)
  if archive.stat().st_size!=artifact['size_in_bytes']:raise RuntimeError('artifact_size_mismatch')
  if artifact.get('digest')!='sha256:'+sha(archive):raise RuntimeError('artifact_digest_mismatch')
  write(out/'selected-artifact.json',artifact)
  contents=[]
  with zipfile.ZipFile(archive) as z:
   seen=set()
   for info in z.infolist():
    name=info.filename;p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or name in seen:raise RuntimeError('unsafe_or_duplicate_zip_member')
    seen.add(name)
    if info.is_dir():continue
    data=z.read(info)
    entry={'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    if not any(part.endswith('.xcresult') for part in p.parts) and p.suffix in ['.json','.txt','.log','.xml','.md','.yml','.yaml']:
     target=out/'extracted'/Path(*p.parts);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data);entry['extracted']=True
    else:entry['extracted']=False
    contents.append(entry)
  write(out/'artifact-contents.json',contents)
  source_roots=['Modules/PinkhaAnyRuntime','Modules/PinkhaAnyNative/Tests','Modules/PinkhaAnyUI/Tests','Modules/PinkhaAnyHanlin/Tests']
  tracked=subprocess.run(['git','ls-tree','-r','--name-only',HEAD,'--']+source_roots,cwd=root,capture_output=True,check=True).stdout.decode('utf-8').splitlines()
  pins=['.github/workflows/pinkha-any-engine-port.yml','Tools/AnyEnginePort/verify_native_test_execution.py','Tools/AnyEnginePort/verify_native_app_bundle.py','Tools/AnyEnginePort/install_native_any.py']
  tracked=sorted(set(tracked+pins))
  source=[]
  for path in tracked:
   proc=subprocess.run(['git','show',HEAD+':'+path],cwd=root,capture_output=True)
   if proc.returncode:
    source.append({'path':path,'status':'not_in_commit'});continue
   b=proc.stdout;dest=out/'pinned-source'/Path(path)
   dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
   source.append({'path':path,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'headSHA':HEAD})
  write(out/'pinned-source.json',source)
  result.update(status='ARCHIVED_COMPLETED_JOB',artifactID=artifact['id'],artifactSHA256=sha(archive),artifactBytes=archive.stat().st_size,
   artifactMemberCount=len(contents),artifactExtractionCount=sum(x['extracted'] for x in contents),
   jobLogSHA256=sha(out/'workflow-job.log'),sourcePinsSHA256=sha(out/'pinned-source.json'))
 except Exception as error:
  result['errorType']=type(error).__name__;result['errorCode']=str(error)
 finally:
  result['finishedAt']=datetime.now(timezone.utc).isoformat();write(out/'collection-result.json',result)
 print(json.dumps({k:result.get(k) for k in ['status','jobConclusion','artifactID','artifactBytes','artifactSHA256','errorCode']},ensure_ascii=True))
 return 0 if result['status']=='ARCHIVED_COMPLETED_JOB' else 1
if __name__=='__main__':raise SystemExit(main())
