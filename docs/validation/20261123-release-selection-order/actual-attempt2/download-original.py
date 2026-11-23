#!/usr/bin/env python3
import base64,hashlib,json,os,pathlib,shutil,stat,sys,time,urllib.error,urllib.parse,urllib.request
D=pathlib.Path("/mnt/development/projects/diagnostics/coherent-original-products-451635-attempt2-original-result-20261123")
EXPECTED_SIZE=2223532
EXPECTED_SHA="8fc2cac021e7c9a8a14cbcefc718a1f5eb35429994963aca8b771bb2ee2c2891"
RUN=45163515182
HEAD="c0c1f851f80322c9f532e86505047498dfaf1adf"
def need(v,m):
 if not v:raise ValueError(m)
def save(path,b,mode=0o400):
 with path.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 path.chmod(mode)
 return {"name":path.name,"bytes":len(b),"sha256":hashlib.sha256(b).hexdigest()}
def js(path,v):return save(path,(json.dumps(v,sort_keys=True,indent=2)+"\n").encode())
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None
def main():
 incoming=json.load(sys.stdin)
 token=incoming.pop("token")
 need(isinstance(token,str) and token and "\n" not in token,"Invalid read token")
 need(shutil.disk_usage(D).free>=2500000000+EXPECTED_SIZE+16777216,"Reserve insufficient")
 need(not (D/"download-intent.json").exists(),"One original artifact acquisition only")
 apidir=D/"api-originals";apidir.mkdir(mode=0o700)
 rows={}
 values={}
 for name,expected in {
  "run.json":"98b98f6553de53e2c1e327d91cfc4afe5e28a7ffe0997db241e780b9c2b11e30",
  "jobs.json":"67b26bf841a87a0e39314dfc6f01eedaa2e355b59b66f53c015e27583c352399",
  "artifacts.json":"39faaab4bac624e9da43ca0b0a6fc8d78755b6ad805c5b5d845e13fb24ef4575",
  "observer-result.json":"8ec45452c56f2c76e29d3615b9562453fa0e7fefb6349a579d04661cad2be055"}.items():
  b=base64.b64decode(incoming["originals"][name],validate=True)
  need(len(b)<200000,"Unexpected metadata size")
  if expected:need(hashlib.sha256(b).hexdigest()==expected,"Retained original index changed")
  values[name]=json.loads(b);rows[name]=save(apidir/name,b)
 run=values["run.json"]
 need(run["id"]==RUN and run["run_attempt"]==2 and run["head_sha"]==HEAD and run["status"]=="completed" and run["conclusion"]=="failure","Original terminal identity mismatch")
 ai=values["artifacts.json"]
 need(ai["total_count"]==2 and len(ai["artifacts"])==2,"Original two-artifact index changed")
 selected=[x for x in ai["artifacts"] if x["id"]==14816672145 and x["name"]=="Pinkha-Coherent-Original-Products-45163515182-2"]
 need(len(selected)==1,"Exact attempt2 artifact not unique")
 a=selected[0]
 jobs=[x for x in values["jobs.json"]["jobs"] if x["id"]==137674049304]
 need(len(jobs)==1,"Selected terminal job not unique")
 job=jobs[0]
 need(job["run_id"]==RUN and job["run_attempt"]==2 and job["head_sha"]==HEAD and job["status"]=="completed" and job["conclusion"]=="failure" and job["runner_id"]==1000024635,"Selected original terminal job mismatch")
 observer=values["observer-result.json"]
 need(observer["run_id"]==RUN and observer["attempt"]==2 and observer["source_sha"]==HEAD and observer["owned_watch_remaining"] is False and observer["artifact_downloads"]==0,"Original observer boundary mismatch")
 need(a["id"]==14816672145 and a["size_in_bytes"]==EXPECTED_SIZE and a["digest"]=="sha256:"+EXPECTED_SHA and a["expired"] is False and a["workflow_run"]["id"]==RUN and a["workflow_run"]["head_sha"]==HEAD,"Original artifact identity mismatch")
 js(D/"download-intent.json",{"protocol":"coherent-original-products-451635-attempt2-original-acquisition-v1","status":"ATTEMPT_STARTED","run_id":RUN,"attempt":2,"source_sha":HEAD,"artifact_id":a["id"],"bytes":EXPECTED_SIZE,"sha256":EXPECTED_SHA,"original_metadata":rows,"new_run_status_queries":0,"new_job_status_queries":0,"native_builds":0,"product_tests":0,"source_sha256":hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()})
 phase="GITHUB_ORIGINAL_ARTIFACT_REDIRECT"
 try:
  request=urllib.request.Request("https://api.github.com/repos/davidpovarsky/anytype-swift/actions/artifacts/14816672145/zip",headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"anytapy-original-result-audit"})
  try:
   response=urllib.request.build_opener(NoRedirect).open(request,timeout=45)
   response.close()
   raise ValueError("Expected authenticated redirect")
  except urllib.error.HTTPError as e:
   need(e.code==302,"Original artifact endpoint did not redirect")
   location=e.headers.get("Location","")
  parsed=urllib.parse.urlsplit(location)
  need(parsed.scheme=="https" and parsed.hostname and (parsed.hostname.endswith(".blob.core.windows.net") or parsed.hostname.endswith(".githubusercontent.com")),"Unadmitted artifact storage host")
  phase="ORIGINAL_ARCHIVE_STREAM"
  partial=D/"original-14816672145.zip.partial"
  count=0;digest=hashlib.sha256()
  with urllib.request.urlopen(urllib.request.Request(location,headers={"User-Agent":"anytapy-original-result-audit"}),timeout=60) as response,partial.open("xb") as output:
   need(response.status==200,"Original artifact stream status mismatch")
   while True:
    data=response.read(1024*1024)
    if not data:break
    count+=len(data);need(count<=EXPECTED_SIZE,"Oversized original archive")
    need(shutil.disk_usage(D).free>=2500000000,"Reserve crossed during acquisition")
    output.write(data);digest.update(data)
   output.flush();os.fsync(output.fileno())
  need(count==EXPECTED_SIZE and digest.hexdigest()==EXPECTED_SHA,"Original archive content mismatch")
  final=D/"original-14816672145.zip"
  need(not final.exists(),"Original target exists")
  partial.rename(final);final.chmod(0o400)
  observed=final.lstat()
  need(stat.S_ISREG(observed.st_mode) and observed.st_nlink==1,"Unexpected original file identity")
  result={"status":"PASS_EXACT_ORIGINAL_ARCHIVE_AND_METADATA_RETAINED","run_id":RUN,"attempt":2,"source_sha":HEAD,"artifact_id":a["id"],"bytes":count,"sha256":digest.hexdigest(),"archive":str(final),"mode":stat.S_IMODE(observed.st_mode),"inode":str(observed.st_ino),"mtime_ns":str(observed.st_mtime_ns),"ctime_ns":str(observed.st_ctime_ns),"free":shutil.disk_usage(D).free,"original_metadata":rows,"new_status_queries":0,"archive_downloads":1,"native_builds":0,"product_tests":0}
  receipt=js(D/"download-result.json",result);print(json.dumps({**result,"receipt":receipt},sort_keys=True))
 except BaseException as e:
  result={"status":"FAIL_ORIGINAL_ACQUISITION","phase":phase,"error_type":type(e).__name__,"http_code":e.code if isinstance(e,urllib.error.HTTPError) else None,"run_id":RUN,"artifact_id":14816672145,"no_automatic_retry":True}
  js(D/"download-failure.json",result);print(json.dumps(result));raise SystemExit(1)
if __name__=="__main__":main()
