import hashlib,json,os,pathlib,stat,subprocess,sys,time,traceback
ROOT=pathlib.Path(r"C:\Users\DAVID\AppData\Local\SentinelX\anytapy-immutable-evidence\sdk06-tagged-45139431216-1")
OUT=ROOT/"full-products-stream-audit"
READER=OUT/"stream-audit-reader.py"
EXPECTED="0252c033b64a493cf7e35dc0eaf8261c4f67ab3b91d68860863e950dec58b255"
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(name,raw):
 p=OUT/name
 with p.open("xb") as f:f.write(raw);f.flush();os.fsync(f.fileno())
 os.chmod(p,stat.S_IREAD)
 return {"path":str(p),"sha256":sha(p),"bytes":len(raw)}
def sj(name,obj):return save(name,(json.dumps(obj,sort_keys=True,indent=2)+"\n").encode())
assert pathlib.Path(__file__).parent==OUT and sha(READER)==EXPECTED
freeze=json.loads((OUT/"source-freeze.json").read_bytes())
assert freeze["reader_sha256"]==EXPECTED and freeze["runner_sha256"]==sha(pathlib.Path(__file__))
assert freeze["audit_executions_before_freeze"]==0 and freeze["archive_operations_before_freeze"]==0
for n in ("launch-start.json","stdout.log","stderr.log","launch-result.json","stream-audit.json","entry-map.json.gz"):assert not (OUT/n).exists()
argv=[sys.executable,"-B",str(READER)]
start=time.time();child=None;out=b"";err=b"";failure=None;timed_out=False
record={"protocol":"sdk06-stream-only-audit-owned-launch-v1","source_reader_sha256":EXPECTED,"source_runner_sha256":sha(pathlib.Path(__file__)),"source_freeze_sha256":sha(OUT/"source-freeze.json"),"argv":argv,"cwd":str(OUT),"started_unix":start,"owned_timeout_seconds":270,"product_tests":0,"native_builds":0,"Products_extracted":False,"new_downloads":0}
try:
 child=subprocess.Popen(argv,cwd=OUT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
 record["owned_child_pid"]=child.pid
 sj("launch-start.json",record)
 try:out,err=child.communicate(timeout=270)
 except subprocess.TimeoutExpired as error:
  timed_out=True;failure={"type":type(error).__name__,"message":str(error)}
  killed=subprocess.run(["taskkill","/PID",str(child.pid),"/T","/F"],capture_output=True,timeout=10)
  record["owned_timeout_cleanup"]={"argv":["taskkill","/PID",str(child.pid),"/T","/F"],"return_code":killed.returncode,"stdout_sha256":hashlib.sha256(killed.stdout).hexdigest(),"stderr_sha256":hashlib.sha256(killed.stderr).hexdigest()}
  out,err=child.communicate(timeout=10)
 record["return_code"]=child.returncode
except BaseException as error:
 if failure is None:failure={"type":type(error).__name__,"message":str(error)}
 record["launcher_traceback"]=traceback.format_exc()
finally:
 record["stdout"]=save("stdout.log",out);record["stderr"]=save("stderr.log",err)
 record["finished_unix"]=time.time();record["timed_out"]=timed_out
 if failure is not None:record["primary_failure"]=failure
 if (OUT/"stream-audit.json").is_file():
  value=json.loads((OUT/"stream-audit.json").read_bytes())
  record["audit_receipt"]={"path":str(OUT/"stream-audit.json"),"sha256":sha(OUT/"stream-audit.json"),"status":value["status"],"verified_entries":value["verified_entry_count_on_exit"]}
 record["status"]="PASS_OWNED_STREAM_AUDIT" if child is not None and child.returncode==0 and failure is None and record.get("audit_receipt",{}).get("status")=="PASS_EXACT_5011_MANIFEST_ENTRIES_STREAM_VERIFIED" else "FAIL_OWNED_STREAM_AUDIT_ORIGINALS_PRESERVED"
 proof=sj("launch-result.json",record)
 print(json.dumps({"status":record["status"],"original_launch_receipt":proof,"owned_child_pid":record.get("owned_child_pid"),"return_code":record.get("return_code"),"audit_receipt":record.get("audit_receipt"),"source_reader_sha256":EXPECTED},sort_keys=True),flush=True)
if record["status"]!="PASS_OWNED_STREAM_AUDIT":raise SystemExit(1)
