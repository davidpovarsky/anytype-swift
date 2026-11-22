import pathlib,json,hashlib,subprocess,datetime,shutil,zipfile,stat
root=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\execution-d8ea2be0")
out=root/"artifact-intake-01";out.mkdir(exist_ok=False);shutil.copyfile(__file__,out/"ACTUAL_INTAKE_SCRIPT.py")
gh=r"C:\Program Files\GitHub CLI\gh.EXE";repo="davidpovarsky/anytype-swift";run_id=45012913358
head="d8ea2be0f42e51b35001c35509dd27c9035c3c66";commands=[]
def sha(b):return hashlib.sha256(b).hexdigest()
def save():(out/"COMMANDS.json").write_text(json.dumps(commands,indent=2)+"\n",encoding="utf-8")
def command(label,args,timeout=60,output_name=None):
 row={"label":label,"argv":args,"status":"STARTING","started_at":datetime.datetime.now(datetime.timezone.utc).isoformat()};commands.append(row);save()
 op=out/(output_name or label+".stdout");ep=out/(label+".stderr")
 with op.open("wb") as o,ep.open("wb") as e:
  p=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=o,stderr=e);row.update(status="RUNNING",pid=p.pid);save()
  try:rc=p.wait(timeout)
  except subprocess.TimeoutExpired:
   row["timed_out"]=True;save();subprocess.run(["taskkill","/PID",str(p.pid),"/T","/F"],capture_output=True,timeout=20);p.wait(timeout=20);row["status"]="TIMED_OUT";save();raise
 row.update(status="COMPLETED",exit_code=rc,finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),stdout_sha256=sha(op.read_bytes()),stderr_sha256=sha(ep.read_bytes()));save()
 assert rc==0,(label,ep.read_text(errors="replace"))
 return op
run=json.loads(command("terminal-run",[gh,"api",f"repos/{repo}/actions/runs/{run_id}"]).read_bytes())
assert run["status"]=="completed" and run["head_sha"]==head and run["run_attempt"]==1
data=json.loads(command("artifact-list",[gh,"api",f"repos/{repo}/actions/runs/{run_id}/artifacts"]).read_bytes())
wanted=[a for a in data["artifacts"] if a["name"]==f"Otzaria-Original-Heart-Schema-{run_id}-1"]
assert len(wanted)==1 and not wanted[0]["expired"]
a=wanted[0];assert a["workflow_run"]["head_sha"]==head
assert a["size_in_bytes"]<100*1024**2
archive=command("ONE-artifact-download",[gh,"api",f"repos/{repo}/actions/artifacts/{a['id']}/zip"],timeout=180,output_name="original-artifact.zip")
archive_sha=sha(archive.read_bytes());assert a["digest"]=="sha256:"+archive_sha
extracted=out/"extracted";extracted.mkdir()
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 infos=z.infolist();assert sum(i.file_size for i in infos)<512*1024**2
 names=set()
 for entry in infos:
  p=pathlib.PurePosixPath(entry.filename)
  assert not p.is_absolute() and ".." not in p.parts and ":" not in entry.filename
  assert not stat.S_ISLNK(entry.external_attr>>16)
  key=entry.filename.casefold();assert key not in names;names.add(key)
 z.extractall(extracted)
indexes=list(extracted.rglob("EVIDENCE_INDEX.json"));assert len(indexes)==1
index_path=indexes[0];folder=index_path.parent;index=json.loads(index_path.read_bytes())
for entry in index["files"]:
 p=folder/entry["path"];assert p.is_file() and p.stat().st_size==entry["bytes"] and sha(p.read_bytes())==entry["sha256"],entry["path"]
result_path=folder/"RESULT.json";result=json.loads(result_path.read_bytes())
manifest=json.loads(pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-native-schema-observer-source-20261122\controls-v6-r1\EXECUTION_INPUTS.json").read_bytes())
selection=manifest["expected_cases"]["native"]
parent="TestOtzariaFixedSchemaNativeObserverV5"
native_logs=list(folder.glob("*run-native.stdout"))
case_review=None
if len(native_logs)==1:
 raw=native_logs[0].read_bytes();events=[];outputs={}
 for line in raw.splitlines():
  try:entry=json.loads(line)
  except json.JSONDecodeError:continue
  test=entry.get("Test","")
  if test.startswith(parent+"/"):
   name=test[len(parent)+1:]
   if entry.get("Action") in ("run","pass","fail","skip"):events.append({"name":name,"action":entry["Action"],"elapsed":entry.get("Elapsed"),"time":entry.get("Time")})
   if entry.get("Output"):outputs.setdefault(name,[]).append(entry["Output"])
 starts=[e["name"] for e in events if e["action"]=="run"]
 terminals=[e for e in events if e["action"] in ("pass","fail","skip")]
 assert len(starts)==len(set(starts)) and set(starts)==set(selection),(starts,selection)
 assert len(terminals)==len(set(e["name"] for e in terminals)) and set(e["name"] for e in terminals)==set(selection)
 case_review={"raw_test2json_sha256":sha(raw),"expected":selection,"events":events,
  "counts":{action:sum(e["action"]==action for e in terminals) for action in ("pass","fail","skip")},
  "failure_outputs":{e["name"]:"".join(outputs.get(e["name"],[])) for e in terminals if e["action"]=="fail"}}
 (out/"ACTUAL_CASE_REVIEW.json").write_text(json.dumps(case_review,indent=2)+"\n",encoding="utf-8")
summary={"status":"ACTUAL_ARTIFACT_VERIFIED","run_id":run_id,"attempt":1,"head":head,"workflow_conclusion":run["conclusion"],
"artifact_id":a["id"],"archive_bytes":archive.stat().st_size,"archive_sha256":archive_sha,"github_digest_match":True,
"crc_verified":True,"payload_count":len(index["files"]),"payload_bytes":sum(e["bytes"] for e in index["files"]),
"index_sha256":sha(index_path.read_bytes()),"result_sha256":sha(result_path.read_bytes()),"actual_result":result,"case_counts":case_review["counts"] if case_review else None,
"case_review_sha256":sha((out/"ACTUAL_CASE_REVIEW.json").read_bytes()) if case_review else None,
"extracted_folder":str(folder),"artifact_download_count":1}
(out/"INTAKE_RESULT.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
printed={k:v for k,v in summary.items() if k!="actual_result"}
printed["result_status"]=result.get("status");printed["result_error"]=result.get("error");printed["tests"]=result.get("tests")
if case_review:printed["failure_tails"]={k:v[-2200:] for k,v in case_review["failure_outputs"].items()}
print(json.dumps(printed))
