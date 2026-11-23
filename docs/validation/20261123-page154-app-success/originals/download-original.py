from pathlib import Path
import hashlib,json,subprocess,shutil,time
from datetime import datetime,timezone
root=Path('/mnt/development/projects/diagnostics/semantic-page-pinned-consumer-20261123/terminal-audit')
meta=json.loads((root/'original-artifacts-api.json').read_bytes())
assert meta['total_count']==1
a=meta['artifacts'][0]
expected_size=703289417
expected_sha='082d7cf6c589c6770186390091d997de29d7148fe917ea2f0785450688cada46'
assert a['id']==14794983588 and a['size_in_bytes']==expected_size and a['digest']=='sha256:'+expected_sha
assert a['workflow_run']['id']==45116855451 and a['workflow_run']['head_sha']=='68148339c275268795360d71d519a5baf003adf8'
final=root/'artifact-14794983588.zip';partial=root/'artifact-14794983588.zip.partial'
assert not final.exists() and not partial.exists() and not (root/'download-result.json').exists()
free=shutil.disk_usage('/mnt/development').free
assert free-expected_size>=2500000000, ('Reserve insufficient',free)
argv=['gh','api','repos/davidpovarsky/anytype-swift/actions/artifacts/14794983588/zip']
record={'artifact_id':14794983588,'run_id':45116855451,'run_attempt':1,'source_sha':a['workflow_run']['head_sha'],'declared_bytes':expected_size,'api_sha256':expected_sha,'argv':argv,'started_at':datetime.now(timezone.utc).isoformat(),'development_free_before':free,'reserve_bytes':2500000000}
(root/'download-request.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
try:
 with partial.open('xb') as out,(root/'download.stderr').open('xb') as err:
  p=subprocess.run(argv,stdout=out,stderr=err,timeout=600)
 record['return_code']=p.returncode
 assert p.returncode==0, 'gh artifact download failed'
 record['actual_bytes']=partial.stat().st_size
 assert record['actual_bytes']==expected_size, 'Downloaded byte count differs'
 h=hashlib.sha256()
 with partial.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 record['actual_sha256']=h.hexdigest()
 assert record['actual_sha256']==expected_sha, 'Downloaded API digest differs'
 partial.rename(final);record.update(status='VERIFIED_ORIGINAL_ZIP',path=str(final))
except BaseException as e:
 record.update(status='FAIL',error_type=type(e).__name__,error=str(e))
finally:
 record['finished_at']=datetime.now(timezone.utc).isoformat()
 record['development_free_after']=shutil.disk_usage('/mnt/development').free
 (root/'download-result.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,sort_keys=True))
raise SystemExit(0 if record['status']=='VERIFIED_ORIGINAL_ZIP' else 1)
