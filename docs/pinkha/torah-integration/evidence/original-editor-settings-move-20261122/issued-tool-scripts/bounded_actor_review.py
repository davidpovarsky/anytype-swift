import pathlib,json,hashlib
out=pathlib.Path(r"C:\Users\DAVID\AppData\Local\Temp\oe-settings-move-compile-20261122")
d=json.loads((out/"AWAIT_WITHCURRENT_DISCOVERY.json").read_bytes())
assert d["file_count"]==3 and d["match_count"]==3
rows=[]
for x in d["files"]:
 assert hashlib.sha256((out/x["snapshot"]).read_bytes()).hexdigest()==x["sha256"]
 if x["path"].endswith("OriginalEditorPropertyScope.swift"):finding="Empty closure; no captured actor property access inside the callback."
 elif x["path"].endswith("PropertiesInteractor.swift"):finding="Callback reads the immutable Sendable scope.spaceId String; no owner/computed accessor or synchronous actor method inside it. The original scope declaration was read in full at the relevant boundary."
 else:finding="The observed owner computed accessor and validateDocument call are exactly the approved MainActor.run repair."
 rows.append({"path":x["path"],"sha256":x["sha256"],"finding":finding})
record={"schema":1,"source_head":d["source_head"],"discovery_sha256":hashlib.sha256((out/"AWAIT_WITHCURRENT_DISCOVERY.json").read_bytes()).hexdigest(),"review":rows,"additional_candidates":0,"scope":"Bounded static review only; not a full compiler/isolation certification. No additional source edits and no old inventories replayed."}
(out/"AWAIT_WITHCURRENT_REVIEW.json").write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
print(json.dumps(record))
