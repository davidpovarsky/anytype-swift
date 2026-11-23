#!/usr/bin/env python3
import base64,hashlib,json,os,pathlib,shutil,subprocess,time
D=pathlib.Path("/mnt/development/projects/diagnostics/coherent-original-products-451635-attempt2-original-result-20261123")
assert shutil.disk_usage(D).free>=2500000000+2223532+16777216
mapping={"run.json":"final-run-api.stdout.txt","jobs.json":"terminal-jobs-index.stdout.txt","artifacts.json":"terminal-artifacts-index.stdout.txt","observer-result.json":"observer-result.json"}
payload={"originals":{name:base64.b64encode((D/"observer-originals"/old).read_bytes()).decode("ascii") for name,old in mapping.items()}}
auth=subprocess.run(["gh","auth","token"],capture_output=True,check=True,timeout=30)
payload["token"]=auth.stdout.decode("utf-8").strip()
assert payload["token"] and "\n" not in payload["token"]
started=time.time()
with (D/"download.original.stdout").open("xb") as stdout,(D/"download.original.stderr").open("xb") as stderr:
 result=subprocess.run(["python3","-B",str(D/"download-original.py")],input=json.dumps(payload).encode(),stdout=stdout,stderr=stderr,timeout=180)
del payload["token"]
report={"protocol":"sole-original-acquisition-launch-v1","returncode":result.returncode,"elapsed_seconds":time.time()-started,"source_sha256":hashlib.sha256((D/"download-original.py").read_bytes()).hexdigest(),"launcher_sha256":hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),"stdout_sha256":hashlib.sha256((D/"download.original.stdout").read_bytes()).hexdigest(),"stderr_sha256":hashlib.sha256((D/"download.original.stderr").read_bytes()).hexdigest(),"free":shutil.disk_usage(D).free}
p=D/"download-launch.json"
with p.open("x") as f:json.dump(report,f,sort_keys=True,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
for p in (D/"download.original.stdout",D/"download.original.stderr",p):p.chmod(0o400)
print(json.dumps(report))
if result.returncode==0:print((D/"download-result.json").read_text())
else:print((D/"download-failure.json").read_text())
raise SystemExit(result.returncode)
