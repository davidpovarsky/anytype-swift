from pathlib import Path
import json,hashlib,subprocess,datetime,shutil,difflib,re
base=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-original-auth-startup-20261122")
p=base/"controls-v2";v1=base/"controls-v1"
repo=Path(r"C:\Users\DAVID\Code\anytype-original-native-annotation-integration-20261122")
out=Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-continuation-20261122\auth-release-controls-v2-root-review")
out.mkdir(parents=True,exist_ok=False)
def sha(x):return hashlib.sha256(x).hexdigest()
def git(*args):
 c=subprocess.run(["git",*args],cwd=repo,capture_output=True,timeout=20);assert c.returncode==0,(args,c.stderr.decode("utf-8","replace"));return c.stdout
indexraw=(p/"INDEX.json").read_bytes();assert sha(indexraw).startswith("dd0caf3e")
index=json.loads(indexraw);assert len(index["files"])==20
for row in index["files"]:
 raw=(p/row["path"]).read_bytes();assert sha(raw)==row["sha256"] and len(raw)==row["bytes"]
assert sorted(x["path"] for x in index["files"])==sorted(f.relative_to(p).as_posix() for f in p.rglob("*") if f.is_file() and f!=p/"INDEX.json")
oldraw=(v1/"INDEX.json").read_bytes();assert sha(oldraw)=="1562ede32960cb1d6a00d04efd19c1bedfbcf4c8865acd914d150258a1bc6768"
old=json.loads(oldraw);assert len(old["files"])==18
for row in old["files"]:
 b=(v1/row["path"]).read_bytes();assert sha(b)==row["sha256"] and len(b)==row["bytes"]
manifestraw=(p/"EXECUTION_INPUTS.json").read_bytes();assert sha(manifestraw)=="aedafa37e322e06559d04b2fd6704bf369037c4332023a37cdff79e67a998644"
manifest=json.loads(manifestraw)
original={}
for x in manifest["canonical_inputs"]:
 b=git("show",x["commit"]+":"+x["path"]);assert sha(b)==x["sha256"] and len(b)==x["bytes"]
 assert git("rev-parse",x["commit"]+":"+x["path"]).decode().strip()==x["git_blob"]
 original[x["path"]]=b
for x in manifest["compiled_inputs"]:
 b=(p/x["path"]).read_bytes();assert sha(b)==x["sha256"] and len(b)==x["bytes"]
 if not x["transforms"]:assert b==original[x["canonical_path"]]
 if x["path"].endswith("Operation.swift"):assert b==original[x["canonical_path"]].replace(b"import ProtobufMessages\n",b"",1)
inverse=json.loads((p/"PROJECTION_INVERSE.json").read_bytes())
projected=(p/"compiled-inputs/Transition.swift").read_text(encoding="utf-8")
for key in ["outer_fragment","inner_fragment"]:
 assert projected.count(inverse[key])==1;projected=projected.replace(inverse[key],"",1)
original_candidate=original["Anytype/Sources/ServiceLayer/Account/EditorAccountWriteTransition.swift"]
assert projected.encode()==original_candidate.replace(b"import ProtobufMessages\n",b"",1)
assert sha(original_candidate)=="65a20edfdacbb8c5a51d647b2746a16f75ca9865984026cca5b6235f4fa4933e"
capture=(p/"compiled-inputs/OriginalCaptureAndError.swift").read_bytes()
assert capture[:19]==b"import Foundation\n\n"
error=capture[19:479];cap=capture[479:]
assert sha(error)=="e0eb6a222e495dc19a2f5ae9c4ff6ae236e3992dea285480c25919360f144176"
assert sha(cap)=="4ded1aca60644722b4c7ff84ede19ce92a5108c8909586b2b84ede5185f7236a"
owner=original["Anytype/Sources/PresentationLayer/TextEditor/Assembly/Page/EditorDocumentWriteOwner.swift"]
assert owner.count(error)==1 and owner.count(cap)==1
paths=["compiled-inputs/Transition.swift","Controls.swift","run_controls.py","README.md","EXECUTION_INPUTS.json"]
delta="".join("".join(difflib.unified_diff((v1/f).read_text(encoding="utf-8").splitlines(True),(p/f).read_text(encoding="utf-8").splitlines(True),fromfile="controls-v1/"+f,tofile="controls-v2/"+f)) for f in paths)
assert delta.encode()==(p/"V1_TO_V2.patch").read_bytes()
controls=(p/"Controls.swift").read_text(encoding="utf-8")
assert sha((p/"Controls.swift").read_bytes())=="5693db8a8426d227166cea5df6f51afc2fed58ce695c096187e5583f77a5cfe8"
assert "75_000_000" not in controls
assert controls.count("observePending(probe, transition: transition, lifetime: lifetime, log: log)")==3
assert "while transition._controlReleaseWaiterCount() == 0" in controls
assert "transition._controlReleaseWaiterCount() == 1" in controls
assert "3_000_000_000" in controls and "if releaseVerification.wait(timeout: .now() + 10)" in controls
assert manifest["case_count"]==6 and manifest["old_cases_replayed"]==0
assert manifest["case_names"]==json.loads((v1/"EXECUTION_INPUTS.json").read_bytes())["case_names"]
runner=(p/"run_controls.py").read_text(encoding="utf-8")
assert sha((p/"run_controls.py").read_bytes())=="614b9bfe7e0699ca5eef6da7cb6014c796b45f31ec5386dca98f7f743c3ce91b"
assert 'actual.get("processID") != commands[-1]["pid"]' in runner and "env=environment" in runner
compiler=Path(manifest["compiler_binding"]["path"])
assert sha(compiler.read_bytes())==manifest["compiler_binding"]["sha256"] and compiler.stat().st_size==41472
assert Path(manifest["compiler_binding"]["runtime_path"]).is_dir()
assert sha((p/"source-review/root-review/ROOT_REVIEW.json").read_bytes())=="17ce2a6b681d034b453e6c3b94d9e7c566aae172eaeef7291a1db427a549d157"
shutil.copyfile(__file__,out/"ACTUAL_ROOT_REVIEW.py")
result={"schema":"otzaria.auth-release-controls-v2-root-review/1","status":"PASS_FOR_FIRST_SIX_FOCUSED_CONTROLS","observed_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"packet":str(p),"index_sha256":sha(indexraw),"payloads":20,"old_unexecuted_v1_payloads_unchanged":18,"manifest_sha256":sha(manifestraw),"product_commit":manifest["candidate_commit"],"product_sha256":sha(original_candidate),"canonical_git_inputs":len(original),"compiled_inputs":len(manifest["compiled_inputs"]),"projection_inverse_recovers_exact_full_candidate":True,"full_v1_bodies_and_exact_v2_delta_reviewed":True,"exact_six_names":manifest["case_names"],"positive_registration":"Actual original State.releaseWaiters.count under original lock; bounded3s; native/verification gates remain held until observed. Fixture-only readout, no product hook.","compiler_sha256":sha(compiler.read_bytes()),"actual_pid_equality_required":True,"command_bounds":{"compiler_version":20,"compile":240,"execute":45},"native_or_old_tests_executed":0,"limits":"Portable original transition/Lifetime/Operation/Dispatch/Capture only. Actual Auth/LoginState/Hanlin startup integration, Apple compiler and StageB remain pending."}
raw=(json.dumps(result,indent=2)+"\n").encode();(out/"ROOT_REVIEW.json").write_bytes(raw)
print(json.dumps({"status":result["status"],"path":str(out/"ROOT_REVIEW.json"),"sha256":sha(raw),"index_sha256":sha(indexraw),"observed_at":result["observed_at"]}))
