import pathlib,json,hashlib,shutil,subprocess,datetime,time
base=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
packet=base/"controls-v6-r1"
proof=base/"delta-composition-v6-r1";proof.mkdir(exist_ok=False)
material=proof/"materialized";material.mkdir()
source=json.loads((base/"candidate-v5"/"SOURCE_MANIFEST.json").read_text())
execution=json.loads((base/"execution-382e5ac6"/"artifact-intake-01"/"extracted"/"RESULT.json").read_text())
actual={e["path"]:e for e in execution["composed_product_and_test_inputs"]}
before=[]
for e in source["candidate"]:
 p=e["path"];src=base/"candidate-v5"/"candidate"/p;b=src.read_bytes()
 assert hashlib.sha256(b).hexdigest()==e["sha256"]==actual[p]["sha256"]
 dest=material/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
 before.append({"path":p,"sha256":hashlib.sha256(b).hexdigest(),"bytes":len(b)})
commands=[]
for i,args in enumerate([["git","apply","--check",str(packet/"V5_TO_V6.patch")],["git","apply",str(packet/"V5_TO_V6.patch")]],1):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 cp=subprocess.run(args,cwd=material,capture_output=True,timeout=30)
 stdout=proof/f"{i:02d}-stdout.txt";stderr=proof/f"{i:02d}-stderr.txt";stdout.write_bytes(cp.stdout);stderr.write_bytes(cp.stderr)
 row={"argv":args,"cwd":str(material),"started_at":start,"duration_seconds":time.monotonic()-tick,"exit_code":cp.returncode,"stdout":stdout.name,"stdout_sha256":hashlib.sha256(cp.stdout).hexdigest(),"stderr":stderr.name,"stderr_sha256":hashlib.sha256(cp.stderr).hexdigest()}
 commands.append(row);assert cp.returncode==0,row
manifest=json.loads((packet/"EXECUTION_INPUTS.json").read_text())
delta=manifest["observer_product_delta"][0];expected={e["path"]:e["sha256"] for e in source["candidate"]};expected[delta["path"]]=delta["sha256"]
for e in manifest["test_sources"]:
 p=e["path"];dest=material/p;dest.parent.mkdir(parents=True,exist_ok=True);assert not dest.exists()
 shutil.copyfile(packet/e["retained_path"],dest);expected[p]=e["sha256"]
files=[]
for p in sorted(material.rglob("*")):
 if not p.is_file():continue
 rel=p.relative_to(material).as_posix();sha=hashlib.sha256(p.read_bytes()).hexdigest()
 assert expected[rel]==sha,(rel,sha)
 files.append({"path":rel,"bytes":p.stat().st_size,"sha256":sha})
assert set(expected)=={f["path"] for f in files} and len(files)==8
result={"status":"PASS_SOURCE_COMPOSITION_ONLY","baseline_run_id":45008694456,"baseline_actual_product_inputs":before,"baseline_product_composition_reused":"Actual first run's successful original d984+r14+V5 composition and compiled input hashes; no r14/V5 apply repeated.","v6_delta_sha256":hashlib.sha256((packet/"V5_TO_V6.patch").read_bytes()).hexdigest(),"commands":commands,"outputs":files,"go_builds":0,"tests":0,"native_calls":0,"product_worktree_mutated":False,"frozen_packets_mutated":False}
p=proof/"RESULT.json";p.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"path":str(p),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"commands":len(commands),"outputs":len(files),"go_builds":0,"tests":0}))
