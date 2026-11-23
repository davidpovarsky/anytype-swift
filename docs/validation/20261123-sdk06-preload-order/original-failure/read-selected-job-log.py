import datetime,hashlib,json,os,pathlib,re,shutil,subprocess,threading,time
ROOT=pathlib.Path(__file__).resolve().parent
CAP=8*1024*1024
def sha(b):return hashlib.sha256(b).hexdigest()
def save(name,b):
 p=ROOT/name
 with p.open("xb") as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {"path":name,"bytes":len(b),"sha256":sha(b)}
gh=shutil.which("gh");assert gh and pathlib.Path(gh).is_file()
argv=[gh,"api","repos/davidpovarsky/anytype-swift/actions/jobs/137914443694/logs"]
started=datetime.datetime.now(datetime.timezone.utc).isoformat()
intent={"protocol":"sdk452379-one-selected-job-log-v1","run_id":45237901921,"attempt":1,"source":"1a09867d88f475fd2b3192fabc4dd803986e5281","job_id":137914443694,"argv":argv,"deadline_seconds":60,"combined_output_cap_bytes":CAP,"selected_api_calls":1,"new_index_calls":0,"ci_mutations":0,"automatic_retries":0,"started_at":started}
intent_row=save("intent.json",json.dumps(intent,sort_keys=True,indent=2).encode()+b"\n")
chunks={"stdout":[],"stderr":[]};total=0;lock=threading.Lock();failure=[];exceeded=threading.Event()
p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
pid=p.pid;start=time.monotonic()
def drain(name,pipe):
 global total
 try:
  while True:
   data=pipe.read(32768)
   if not data:break
   with lock:
    available=CAP-total
    if len(data)>available:
     if available>0:chunks[name].append(data[:available]);total+=available
     exceeded.set()
     if not failure:failure.append("combined_output_cap_exceeded")
     try:p.kill()
     except OSError:pass
     break
    chunks[name].append(data);total+=len(data)
 except BaseException as e:
  with lock:
   if not failure:failure.append(type(e).__name__)
 finally:pipe.close()
threads=[threading.Thread(target=drain,args=(n,getattr(p,n)),daemon=True) for n in ("stdout","stderr")]
for t in threads:t.start()
timed_out=False
try:rc=p.wait(timeout=60)
except subprocess.TimeoutExpired:
 timed_out=True
 with lock:
  if not failure:failure.append("selected_job_log_deadline")
 p.kill();rc=p.wait(timeout=10)
for t in threads:t.join(timeout=5)
if any(t.is_alive() for t in threads):
 if not failure:failure.append("output_reader_not_drained")
elapsed=time.monotonic()-start
out=b"".join(chunks["stdout"]);err=b"".join(chunks["stderr"])
outrow=save("job137914443694.stdout.log",out);errrow=save("job137914443694.stderr.log",err)
if rc!=0 and not failure:failure.append("gh_nonzero")
result={"protocol":intent["protocol"],"status":"PASS_SELECTED_ORIGINAL_JOB_LOG_RETAINED" if rc==0 and not failure else "FAIL_SELECTED_JOB_LOG_READ","run_id":45237901921,"attempt":1,"job_id":137914443694,"source":intent["source"],"owned_pid":pid,"returncode":rc,"owned_child_reaped":p.poll() is not None,"timed_out":timed_out,"elapsed_seconds":elapsed,"output_readers_drained":not any(t.is_alive() for t in threads),"first_failure":failure[0] if failure else None,"output_cap":CAP,"observed_output_bytes":len(out)+len(err),"intent":intent_row,"stdout":outrow,"stderr":errrow,"selected_api_calls":1,"new_index_calls":0,"new_downloads_of_artifact":0,"ci_mutations":0,"finished_at":datetime.datetime.now(datetime.timezone.utc).isoformat()}
rr=save("result.json",json.dumps(result,sort_keys=True,indent=2).encode()+b"\n")
lines=out.decode("utf-8",errors="replace").splitlines()
selected=[]
for n,line in enumerate(lines):
 if any(s in line.lower() for s in ("traceback","error:","exception","failed","mismatch","missing","differs","refused")):
  for k in range(max(0,n-1),min(len(lines),n+3)):
   value=lines[k]
   value=re.sub(r'https?://\S+\?\S+',"<redacted-signed-or-query-url>",value)
   value=re.sub(r'(?i)(bearer\s+)[A-Za-z0-9._-]+',r'\1<redacted>',value)
   selected.append({"line":k+1,"text":value[:800]})
dedup={x["line"]:x for x in selected}
print(json.dumps({"result":result,"result_file":rr,"diagnostic_lines":[dedup[k] for k in sorted(dedup)][:80]}))
