from pathlib import Path
import base64,hashlib,json,os,stat,sys
out=Path('/mnt/development/projects/diagnostics/sdk-ui-page-publication-originals-20261123')
request=json.load(sys.stdin)
assert request['protocol']=='three-route-completed-originals-transfer-v1'
assert 1<=len(request['files'])<=100
assert len({x['relative'] for x in request['files']})==len(request['files'])
total=sum(x['bytes'] for x in request['files']);assert total<4*1024**2
s=os.statvfs(out);assert s.f_bavail*s.f_frsize>=2_500_000_000+total+16*1024**2
rows=[]
for row in request['files']:
 rel=Path(row['relative'])
 assert not rel.is_absolute() and len(rel.parts)==2 and rel.parts[0] in {'dispatch','identity'} and rel.name not in {'.','..'} and '\\' not in row['relative']
 raw=base64.b64decode(row['base64'],validate=True);assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
 dest=out/rel;dest.parent.mkdir(mode=0o700,exist_ok=True)
 with dest.open('xb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
 dest.chmod(0o400)
 rows.append({k:v for k,v in row.items() if k!='base64'})
receipt={'status':'PASS_BYTE_EXACT_COMPLETED_WINDOWS_ORIGINALS_RETAINED','files':rows,'count':len(rows),'bytes':total,'sourceProgramsOrGitMoved':False,'extraAPIQueries':0,'artifactsDownloaded':0}
p=out/'transfer-receipt.json'
with p.open('x') as f:json.dump(receipt,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps({'status':receipt['status'],'count':len(rows),'bytes':total,'receiptSHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'directory':str(out)}))
