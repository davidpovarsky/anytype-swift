import pathlib,json,hashlib,shutil,subprocess,datetime,time
base=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122")
packet=base/"controls-v6-r1"
proof=base/"delta-composition-v6-r1-lf";proof.mkdir(exist_ok=False)
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
for i,args in enumerate([["git","-c","core.autocrlf=false","-c","core.eol=lf","apply","--check",str(packet/"V5_TO_V6.patch")],["git","-c","core.autocrlf=false","-c","core.eol=lf","apply",str(packet/"V5_TO_V6.patch")]],1):
 start=datetime.datetime.now(datetime.timezone.utc).isoformat();tick=time.monotonic()
 cp=subprocess.run(args,cwd=material,capture_output=True,timeout=30)
 stdout=proof/f"{i:02d}-stdout.txt";stderr=proof/f"{i:02d}-stderr.txt";stdout.write_bytes(cp.stdout);stderr.write_bytes(cp.stderr)
 row={"argv":args,"cwd":str(material),"started_at":start,"duration_seconds":time.monotonic()-tick,"exit_code":cp.returncode,"stdout":stdout.name,"stdout_sha256":hashlib.sha256(cp.stdout).hexdigest(),"stderr":stderr.name,"stderr_sha256":hashlib.sha256(cp.stderr).hexdigest()}
 commands.append(row)
 (proof/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
 assert cp.returncode==0,row
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

observed=json.loads("{\"ok\":false,\"interpreter\":\"python3\",\"sudo\":false,\"cwd\":null,\"cleanup\":false,\"command\":[\"C:\\\\ProgramData\\\\SentinelX\\\\.venv\\\\Scripts\\\\python.exe\",\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_072ccecaca574c709dbae3de48d79f12\\\\schema_native_v6_delta_source_composition.py\"],\"output\":\"Traceback (most recent call last):\\r\\n  File \\\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_072ccecaca574c709dbae3de48d79f12\\\\schema_native_v6_delta_source_composition.py\\\", line 31, in <module>\\r\\n    assert expected[rel]==sha,(rel,sha)\\r\\n           ^^^^^^^^^^^^^^^^^^\\r\\nAssertionError: ('core/block/object/objectcreator/fixed_schema_replay.go', '42e3ca4de030dc219e9f0260ac49b72319fa926e7a96106d22d60fed3b5b49bd')\",\"duration\":1.34,\"returncode\":1,\"script_path\":\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_072ccecaca574c709dbae3de48d79f12\\\\schema_native_v6_delta_source_composition.py\",\"workdir\":\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_072ccecaca574c709dbae3de48d79f12\",\"hub_request_id\":\"hreq_dc174c1716934d7c\"}")
diagnosis=json.loads("{\"ok\":true,\"interpreter\":\"python3\",\"sudo\":false,\"cwd\":null,\"cleanup\":false,\"command\":[\"C:\\\\ProgramData\\\\SentinelX\\\\.venv\\\\Scripts\\\\python.exe\",\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_15e9659d62094ce4a38a284b594dfd14\\\\schema_native_v6_delta_line_ending_diagnosis.py\"],\"output\":\"{\\\"rows\\\": [{\\\"label\\\": \\\"before\\\", \\\"bytes\\\": 14045, \\\"sha256\\\": \\\"3fe8c34b02ee93224e8e52a139871012f4ee8d0b45ee8e1d9c690cd1a4dcdf3f\\\", \\\"lf\\\": 328, \\\"crlf\\\": 0, \\\"normalized_sha256\\\": \\\"3fe8c34b02ee93224e8e52a139871012f4ee8d0b45ee8e1d9c690cd1a4dcdf3f\\\"}, {\\\"label\\\": \\\"wanted\\\", \\\"bytes\\\": 14512, \\\"sha256\\\": \\\"fb2c8c245320efe002e4bbece3b38af572a33e262d22652f54388bb6391371c4\\\", \\\"lf\\\": 338, \\\"crlf\\\": 0, \\\"normalized_sha256\\\": \\\"fb2c8c245320efe002e4bbece3b38af572a33e262d22652f54388bb6391371c4\\\"}, {\\\"label\\\": \\\"materialized\\\", \\\"bytes\\\": 14850, \\\"sha256\\\": \\\"42e3ca4de030dc219e9f0260ac49b72319fa926e7a96106d22d60fed3b5b49bd\\\", \\\"lf\\\": 338, \\\"crlf\\\": 338, \\\"normalized_sha256\\\": \\\"fb2c8c245320efe002e4bbece3b38af572a33e262d22652f54388bb6391371c4\\\"}]}\\r\\n{\\\"key\\\": \\\"core.autocrlf\\\", \\\"exit_code\\\": 0, \\\"output\\\": \\\"file:C:/Program Files/Git/etc/gitconfig\\\\ttrue\\\"}\\r\\n{\\\"key\\\": \\\"core.eol\\\", \\\"exit_code\\\": 1, \\\"output\\\": \\\"\\\"}\",\"duration\":0.93,\"returncode\":0,\"script_path\":\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_15e9659d62094ce4a38a284b594dfd14\\\\schema_native_v6_delta_line_ending_diagnosis.py\",\"workdir\":\"C:\\\\ProgramData\\\\SentinelX\\\\uploads\\\\.sentinelx_uploads\\\\script_job_15e9659d62094ce4a38a284b594dfd14\"}")

failure=base/"delta-composition-v6-r1"
shutil.copyfile(observed["script_path"],failure/"EXECUTED_SCRIPT.py")
(failure/"SENTINEL_RESULT.json").write_text(json.dumps(observed,indent=2)+"\n",encoding="utf-8")
(failure/"LINE_ENDING_DIAGNOSIS.json").write_text(json.dumps(diagnosis,indent=2)+"\n",encoding="utf-8")
(failure/"README.md").write_text("# Preserved local source-materialization failure\n\nThe first source-only materialization applied the V6 patch with the Windows host system Git core.autocrlf=true. Both git commands exited0, but exact byte validation then failed: all338 output lines were CRLF. Its normalized SHA equals the frozen LF candidate exactly. No source/candidate/native test was changed or run. The structured command list was held in process memory and not written before the failed assertion; the actual executed script and both command raw stdout/stderr files remain retained. A distinct fresh owned continuation explicitly fixes Git newline configuration and verifies8 outputs. This is a source-admission environment correction, not Native test evidence.\n",encoding="utf-8")
