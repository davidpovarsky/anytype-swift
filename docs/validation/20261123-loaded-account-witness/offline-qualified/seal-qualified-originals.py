import pathlib,hashlib,json,gzip,os,subprocess,shutil
C=pathlib.Path("/mnt/development/projects/worktrees/anytype-wave15-loaded-account-witness-20261123")
E=pathlib.Path("/mnt/development/projects/evidence/loaded-account-witness-20261123")
D=pathlib.Path("/mnt/development/projects/diagnostics/loaded-account-witness-ram-graph-source-20261123")
A=E/"ram-projected-graph-attempt1";B=E/"ram-projected-offline-completion1";F=E/"ram-projected-offline-final-controller1"
OUT=C/"docs/validation/20261123-loaded-account-witness/offline-qualified"
assert shutil.disk_usage("/mnt/development").free>=1073741824+2097152
assert not OUT.exists()
def checked(p,h):
 b=p.read_bytes();assert hashlib.sha256(b).hexdigest()==h;return b
rb=checked(B/"result.json","cedb78b0e5478e9697fec61e16f5da175bed7a50d2d371583d6a34c7361e2b9c")
rf=checked(F/"result.json","a7cc6026df730b812e836d575f0450156cb3b58acfbe722998f55fca8d99f8e1")
br=json.loads(rb);fr=json.loads(rf)
mp=C/"docs/validation/20261123-loaded-account-witness/offline-completion/source-inputs.json"
mpv=json.loads(checked(mp,"1fb094e796950254e6ca7977b589c400636fea67ea622fd43259dcb039f4a03e"))
for name in ("source-before.json.gz","source-after.json.gz","ram-inventory.json.gz","generated-test-main/749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715.go"):
 checked(A/name,mpv["originals"][name]["sha256"])
for field in ("current_source_before","dependency_plan_before","dependency_plan_after","captured_source_rows_before","captured_source_rows_after","original_inputs_before","original_inputs_after"):
 v=br[field];assert pathlib.Path(v["path"]).parent==B;checked(pathlib.Path(v["path"]),v["sha256"])
assert br["status"]=="FAILED" and br["primary_error"] is None and fr["status"]=="PASS_LATER_CURRENT_CONTROLLER_AUDIT"
assert fr["primary_error"] is None and not fr["final_errors"] and fr["matched_current_controller_records"]==28
data={};origin={};pair_rows=[]
def add(name,src):
 assert name not in data
 raw=src.read_bytes();data[name]=raw;origin[name]={"path":str(src),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
def pair(name,a,b):
 aa=a.read_bytes();bb=b.read_bytes();assert aa==bb
 add(name,a);pair_rows.append({"selected_copy":name,"original_before":str(a),"original_after":str(b),"bytes_each":len(aa),"sha256":hashlib.sha256(aa).hexdigest(),"original_pair_equal":True,"copy_role":"byte_exact_original_before_with_explicit_identical_after_link"})
pair("query/source-before.json.gz",A/"source-before.json.gz",A/"source-after.json.gz")
add("query/ram-inventory.json.gz",A/"ram-inventory.json.gz")
gen=A/"generated-test-main/749604e1b5eba79ed351a8f0a09bdd64aca9412d833b887adc5140cb42515715.go"
add("query/generated-test-main.go",gen)
add("offline/result.json",B/"result.json")
add("offline/current-source-before.json.gz",B/"current-source-before.json.gz")
pair("offline/dependency-plan-before.json.gz",B/"dependency-plan-before.json.gz",B/"dependency-plan-after.json.gz")
pair("offline/captured-sources-before.json.gz",B/"captured-sources-before.json.gz",B/"captured-sources-after.json.gz")
pair("offline/original-inputs-before.json",B/"original-inputs-before.json",B/"original-inputs-after.json")
assert {p.name for p in F.iterdir()}=={"head-before.json","head-after.json","tree.json","status.json","later-source-before.json","later-source-after.json","result.json"}
for p in sorted(F.glob("*.json")):add("later-controller/"+p.name,p)
sources=D/"offline-final-controller-source"
freeze=json.loads(checked(sources/"freeze.json","e117778ffff4ec07912a1b1b19b528ee2984ea2ef7d34d832d6f5c7167251e81"))
for v in freeze["source_files"]:
 p=pathlib.Path(v["path"]);assert p.parent==sources
 checked(p,v["sha256"]);add("later-auditor-source/"+p.name,p)
add("later-auditor-source/freeze.json",sources/"freeze.json")
stdout=checked(A/"stdout.log","240201e3a30b6391adcbdc090ef9829fe66c36c62bfd59de1eba7b0aeee61dc3")
packed=gzip.compress(stdout,compresslevel=6,mtime=0);assert gzip.decompress(packed)==stdout
data["query/stdout-original.json.gz"]=packed
origin["query/stdout-original.json.gz"]={"path":str(A/"stdout.log"),"original_bytes":len(stdout),"original_sha256":hashlib.sha256(stdout).hexdigest(),"copy_role":"gzip_derivative_with_exact_full_readback","derivative_bytes":len(packed),"derivative_sha256":hashlib.sha256(packed).hexdigest()}
pairs=pair_rows+[{"selected_copy":"later-controller/later-source-before.json","original_before":str(F/"later-source-before.json"),"original_after":str(F/"later-source-after.json"),"bytes_each":16848,"sha256":"adeb2a63ffcbfd53d3e2a3bcb6bcc980ad2a4fe2d578f72a594a454fcf507b94","both_originals_copied":True}]
assert data["later-controller/later-source-before.json"]==data["later-controller/later-source-after.json"]
data["pair-equality.json"]=(json.dumps(pairs,sort_keys=True,indent=2)+"\n").encode()

QUALIFICATION=json.loads("{\"schema\":\"qualified-offline-source-stage-v1\",\"qualification_scope\":\"source graph plus separate later current-controller audit\",\"status\":\"PASS_COMPOSED_SOURCE_STAGE\",\"query_origin\":{\"controller\":\"0f57f72e3f447d0bb67ffef783d22539094d9ad9\",\"program\":\"cd5e46269f566870489f338471f9c63e14dfd6a8dd842be221fed5b1cccff6cf\",\"original_aggregate_status\":\"FAILED\",\"result_sha256\":\"249c5a4a5a16ce7f39669925d03e804c8dab1517899c487179d123912b66601f\",\"actual_query_return_code\":0,\"stdout_complete\":true,\"cleanup_custody\":\"PASS\"},\"offline_origin\":{\"controller\":\"1b98b7a01acc3b08d48c30c566d207f499a103d2\",\"program\":\"5de50261d94fecea6ccf5b3f6f70870200c518d15b1d628bb29ca77b4418a806\",\"original_aggregate_status\":\"FAILED\",\"result_sha256\":\"cedb78b0e5478e9697fec61e16f5da175bed7a50d2d371583d6a34c7361e2b9c\",\"dependency_pair_sha256\":\"6f67e22560bc001fcdb314b3cbdfe8d562f357d9d5a513691692c66cf9b83269\",\"packages\":1455,\"modules\":204,\"input_rows\":11627,\"later_ordinary_rows\":11626,\"original_generated_rows\":1,\"codec_roundtrip\":true,\"missing_historical_current_after\":\"NOT_RECREATED\",\"missing_historical_loaded_after\":\"NOT_RECREATED\"},\"later_final_origin\":{\"source_sha256\":\"91d4c4df7b802929650c48d55dad097b349e5402647a238aa93869abd5b35662\",\"result_sha256\":\"a7cc6026df730b812e836d575f0450156cb3b58acfbe722998f55fca8d99f8e1\",\"status\":\"PASS_LATER_CURRENT_CONTROLLER_AUDIT\",\"matched_rows\":28,\"identity\":\"separate actual external auditor\",\"original_producer_file_match_only\":true},\"read_provenance\":{\"ordinary_dependencies\":\"new reads during offline completion\",\"generated_source\":\"original captured metadata and original preserved bytes\",\"captured_source_tools\":\"original before/after rows also matched current bytes\",\"codec\":\"lossless column representation; all values/types/presence retained\"},\"actual_scope_counts\":{\"source_queries_total_this_loaded_account_stage\":2,\"offline_query_replays\":0,\"new_native_builds\":0,\"new_native_controls\":0},\"native_build_admission\":false,\"four_native_controls\":\"NOT_RUN\",\"semantic_source_admission\":false,\"migration_completeness\":false,\"destination_writes\":false,\"preserved_originals\":\"All external original files remain unchanged; selected identical before/after pairs are represented by one byte-exact copy plus explicit pair linkage.\"}")
FINALJOB=json.loads("{\"id\":\"job_4d40ce67ddfa\",\"type\":\"job_result\",\"source\":\"exec@host_7ec8382e82747448\",\"severity\":\"info\",\"tool\":\"exec\",\"host\":\"host_7ec8382e82747448\",\"status\":\"succeeded\",\"exit_code\":0,\"created_at\":1795458527.6968458,\"started_at\":\"2026-11-23T18:28:47.778345+00:00\",\"finished_at\":\"2026-11-23T18:28:48.620952+00:00\",\"duration_s\":0.84,\"error\":null,\"output_truncated\":false,\"timeout_s\":180,\"read\":false,\"notified\":{\"telegram\":null,\"resend\":null},\"notify_spec\":{},\"output\":\"{\\\"status\\\": \\\"PASS_LATER_CURRENT_CONTROLLER_AUDIT\\\", \\\"result\\\": {\\\"path\\\": \\\"/mnt/development/projects/evidence/loaded-account-witness-20261123/ram-projected-offline-final-controller1/result.json\\\", \\\"bytes\\\": 11158, \\\"sha256\\\": \\\"a7cc6026df730b812e836d575f0450156cb3b58acfbe722998f55fca8d99f8e1\\\"}, \\\"matched_records\\\": 28, \\\"graph_or_test_replays\\\": 0}\"}")

data["qualification.json"]=(json.dumps(QUALIFICATION,sort_keys=True,indent=2)+"\n").encode()
data["later-controller/sentinel-original.json"]=(json.dumps(FINALJOB,sort_keys=True,indent=2)+"\n").encode()
for name in ("offline-completion-launcher.py","offline-execution-admission1.json","one-offline-completion-launch1.json","final-controller-execution-admission1.json"):
 add("launch-originals/"+name,D/name)
assert sum(map(len,data.values()))+32768<2097152
OUT.mkdir(mode=0o700)
rows=[]
for name,raw in sorted(data.items()):
 p=OUT/name;assert p.is_relative_to(OUT)
 p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 with p.open("xb") as f:os.chmod(p,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
 assert p.read_bytes()==raw
 rows.append({"path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"source":origin.get(name),"kind":"exact_copy_or_explicit_derivative" if name in origin else "new_join_metadata"})
index={"schema":"qualified-source-stage-originals-index-v1","records":rows,"pairs":pairs,"retained_ram_archive":{"path":str(A/"ram-originals.tar.gz"),"bytes":1788509,"sha256":"dc557d7ff904e8bd1fed9a536ceb834334ef2310128a9fa4a0094c4bb3ce7154","complete_prior_independent_readback":{"files":1905,"directories":259,"payload_bytes":8764623},"copy_not_needed_for_this_metadata_bundle":True},"runtime_original_bytes":sum(p.stat().st_size for r in (A,B,F) for p in r.rglob("*") if p.is_file()),"new_copied_logical_bytes":sum(x["bytes"] for x in rows),"no_runtime_replay":True}
raw=(json.dumps(index,sort_keys=True,indent=2)+"\n").encode();assert sum(x["bytes"] for x in rows)+len(raw)<=2097152
p=OUT/"evidence-index.json"
with p.open("xb") as f:os.chmod(p,0o600);f.write(raw);f.flush();os.fsync(f.fileno())
assert all(hashlib.sha256((OUT/x["path"]).read_bytes()).hexdigest()==x["sha256"] for x in rows)
q=OUT/"qualification.json"
print(json.dumps({"files":len(rows)+1,"logical_bytes":sum(x["bytes"] for x in rows)+len(raw),"allocated_bytes":sum(p.stat().st_blocks*512 for p in OUT.rglob("*") if p.is_file()),"index":{"path":str(p),"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()},"qualification":{"path":str(q),"sha256":hashlib.sha256(q.read_bytes()).hexdigest()},"runtime_original_bytes":index["runtime_original_bytes"],"free":shutil.disk_usage("/mnt/development").free}))
