import pathlib,json,subprocess,hashlib,re
d=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\otzaria-editor-producer-44997870962-failure")
w=pathlib.Path(r"C:\Users\DAVID\Code\anytype-original-editor-package-seal-20261121")
head="568d69f55a4b1b1bc318b8ee20144c720c8c16a5"
p="Anytype/Sources/PresentationLayer/TextEditor/EditorPage/Views/Settings/Cover/Unsplash/UnsplashItemsViewModel.swift"
def git(*a):
 r=subprocess.run(["git",*a],cwd=w,capture_output=True,timeout=60);r.check_returncode();return r.stdout
data=git("show",head+":"+p)
log=(d/"inner-0/framework-build.stdout.log").read_text(encoding="utf-8",errors="replace").splitlines()
diagnostics=[]
for i,line in enumerate(log):
 if re.search(r"^/.*:\d+:\d+: error:",line) or "Internal Error: DecodingError" in line:
  diagnostics.append({"line":i+1,"context":log[max(0,i-9):i+18]})
records=json.loads((d/"SMALL_JSON_RECORDS.json").read_bytes())
selected={x["path"]:x["content"] for x in records if any(y in x["path"] for y in ["framework-build.command.json","macro-restoration.json","source-admission.json","owned-simulator-cleanup.json"])}
controls=json.loads((d/"inner-0/source-controls-result.json").read_bytes())
selected["controls"]={k:v for k,v in controls.items() if k not in ("tests","results","source_manifest")}
before=(d/"inner-0/source-before.json").read_bytes();after=(d/"inner-0/source-after.json").read_bytes()
output={"path":p,"blob":git("rev-parse",head+":"+p).decode().strip(),"sha256":hashlib.sha256(data).hexdigest(),"content":data.decode(),"diagnostics":diagnostics,"stderr":(d/"inner-0/framework-build.stderr.log").read_text(encoding="utf-8"),"records":selected,"source_before_sha256":hashlib.sha256(before).hexdigest(),"source_after_sha256":hashlib.sha256(after).hexdigest(),"source_equal":before==after,"controls_keys":list(controls)}
(d/"DIAGNOSTIC_CONTEXT.json").write_text(json.dumps(output,indent=2),encoding="utf-8")
print(json.dumps(output))
