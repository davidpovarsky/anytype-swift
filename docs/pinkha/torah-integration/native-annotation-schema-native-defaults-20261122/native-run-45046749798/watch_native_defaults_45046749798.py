import datetime,hashlib,json,os,pathlib,shutil,subprocess,time,zipfile
repo="davidpovarsky/anytype-swift"
run_id=45046749798
if run_id<=0: raise RuntimeError("bind the exact activated native run before observer execution")
head="0896ae82864142e0b633278a8c5cb718ddf66e1e"
owned=pathlib.Path(r"C:\Users\DAVID\Code")/f"otzaria-schema-native-defaults-observer-20261122-{run_id}"
owned.mkdir(exist_ok=False)
gh=shutil.which("gh")
if not gh: raise RuntimeError("GitHub CLI unavailable")
deadline=time.monotonic()+3300
record={"schema":"otzaria.finite-schema-native-defaults-observer/1","run_id":run_id,"expected_head":head,"events":[],"status":"OBSERVING","owned_directory":str(owned)}
def save():
 target=owned/"WATCHER_RESULT.json"
 temporary=owned/"WATCHER_RESULT.json.tmp"
 temporary.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
 os.replace(temporary,target)
def api(path,seconds=35):
 result=subprocess.run([gh,"api",path],capture_output=True,timeout=seconds)
 if result.returncode: raise RuntimeError("GitHub API request failed: "+str(result.returncode))
 return json.loads(result.stdout)
def event(kind,**values):
 record["events"].append({"utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"event":kind,**values})
 save()
try:
 previous=None
 while time.monotonic()<deadline:
  try:
   run=api(f"repos/{repo}/actions/runs/{run_id}")
  except (subprocess.TimeoutExpired,RuntimeError,json.JSONDecodeError) as error:
   event("READ_FAILED",error_type=type(error).__name__)
   time.sleep(30)
   continue
  if run["head_sha"]!=head or run["run_attempt"]!=1 or run["head_branch"]!="codex/otzaria-schema-native-defaults-20261122" or run["event"]!="push":
   raise RuntimeError("Run source or attempt changed")
  state=(run["status"],run.get("conclusion"))
  if state!=previous:
   event("RUN_STATE",status=state[0],conclusion=state[1])
   previous=state
  if state[0]=="completed":
   record["run"]={key:run.get(key) for key in ("id","head_sha","head_branch","run_attempt","event","status","conclusion","html_url","created_at","updated_at")}
   break
  time.sleep(45)
 else:
  raise TimeoutError("Finite observer deadline elapsed")
 data=api(f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100")
 wanted=f"Otzaria-Schema-Native-Defaults-{run_id}-1"
 artifacts=[a for a in data.get("artifacts",[]) if a["name"]==wanted and not a["expired"]]
 if len(artifacts)!=1: raise RuntimeError("Expected exact single native artifact")
 artifact=artifacts[0]
 if artifact["workflow_run"]["head_sha"]!=head or artifact["workflow_run"]["id"]!=run_id:
  raise RuntimeError("Artifact source differs")
 if artifact["size_in_bytes"]>64*1024*1024: raise RuntimeError("Unexpected artifact size")
 archive=owned/"native-artifact.zip"
 with archive.open("xb") as out:
  done=subprocess.run([gh,"api",f"repos/{repo}/actions/artifacts/{artifact['id']}/zip"],stdout=out,stderr=subprocess.PIPE,timeout=90)
 if done.returncode: raise RuntimeError("Artifact download failed")
 digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 extracted=owned/"extracted"
 extracted.mkdir()
 with zipfile.ZipFile(archive) as z:
  if len(z.namelist())!=len(set(z.namelist())): raise RuntimeError("Duplicate artifact members")
  if z.testzip() is not None: raise RuntimeError("Artifact CRC failure")
  for info in z.infolist():
   path=pathlib.PurePosixPath(info.filename)
   if path.is_absolute() or ".." in path.parts or len(path.parts)!=1 or info.is_dir():
    raise RuntimeError("Unexpected artifact path")
   if (info.external_attr>>16)&0o170000==0o120000:
    raise RuntimeError("Artifact symlink refused")
   (extracted/path.name).write_bytes(z.read(info))
 index=json.loads((extracted/"EVIDENCE_INDEX.json").read_text())
 files={p.name for p in extracted.iterdir() if p.is_file()}
 if files!={e["path"] for e in index["files"]}|{"EVIDENCE_INDEX.json"}:
  raise RuntimeError("Artifact manifest membership differs")
 for entry in index["files"]:
  path=extracted/entry["path"]
  raw=path.read_bytes()
  if len(raw)!=entry["bytes"] or hashlib.sha256(raw).hexdigest()!=entry["sha256"]:
   raise RuntimeError("Artifact payload hash differs")
 result=json.loads((extracted/"RESULT.json").read_text())
 if result.get("control_head")!=head: raise RuntimeError("Native result source differs")
 if result.get("diagnostic_execution_manifest_sha256")!="0653a672d696f200e1333b163a6e6362262e46629e0d70346069607d68652744": raise RuntimeError("Diagnostic result manifest differs")
 if result.get("repair_execution_manifest_sha256")!="af5e099142aa6f28b43ecf64e1fdbfb3c60a6293755074ba9f440cfd55417285": raise RuntimeError("Semantic repair result manifest differs")
 record["artifact"]={"id":artifact["id"],"name":artifact["name"],"bytes":archive.stat().st_size,"sha256":digest,"path":str(archive),"payloads":len(index["files"])}
 record["native_result"]={key:result.get(key) for key in ("status","control_head","tests","diagnostic_capture","error","error_type","owned_disposable_temp_removed")}
 record["status"]="TERMINAL_ARTIFACT_RETAINED"
 event("ARTIFACT_VERIFIED",artifact_id=artifact["id"],native_status=result.get("status"))
except BaseException as error:
 record["status"]="OBSERVER_FAILED"
 record["error_type"]=type(error).__name__
 record["error"]=str(error)
 save()
 raise
finally:
 save()
 print(json.dumps(record))
